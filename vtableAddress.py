import idc
import idautils
import idaapi
import sys, os
idaapi.require("AddBP")

REGISTERS = ['eax', 'ebx', 'ecx', 'edx', 'rax', 'rbx', 'rcx', 'rdx', 'r9', 'r10', 'r8']

def get_processor_architecture():
    info = idaapi.get_inf_structure()
    if info.is_64bit():
        return "64"
    elif info.is_32bit():
        return ""
    else:
        return "Error"

def get_con2_var_or_num(i_cnt, cur_addr):
    """
    :param i_cnt: the register of the virtual call
    :param cur_addr: the current address in the memory
    :return: "success" string and the address of the vtable's location. if it fails it sends the reason and -1
    """
    save_last_addr = cur_addr
    start_addr = idc.GetFunctionAttr(cur_addr, idc.FUNCATTR_START)
    offset = 0
    cur_addr = idc.PrevHead(cur_addr)

    while cur_addr >= start_addr:
        if idc.GetMnem(cur_addr)[:3] == "mov" and idc.GetOpnd(cur_addr, 0) == i_cnt:
            opnd2 = idc.GetOpnd(cur_addr, 1)
            place = opnd2.find('+')
            register = ''
            offset = ''
            if place != -1: # if the function is not the first in the vtable
                register = opnd2[opnd2.find('[') + 1: place]
                offset = opnd2[place + 1: opnd2.find(']')]
                return register, offset, cur_addr
            else:
                offset = "0"
                register = opnd2[opnd2.find('[') + 1: opnd2.find(']')]
                return register, offset, cur_addr
        cur_addr = idc.PrevHead(cur_addr)
    return "out of the function", "-1", cur_addr

    return '', 0


def get_bp_condition(start_addr, register_vtable, offset):
    arch = get_processor_architecture()
    if arch != "Error":
        file_name = '\\BPCond' + arch + '.py'
        condition_file = str(os.path.dirname(os.path.abspath(sys.argv[0])) + file_name)
        with open(condition_file, 'rb') as f1:
            bp_cond_text = f1.read()
        bp_cond_text = bp_cond_text.replace("<<<start_addr>>>", str(start_addr))
        bp_cond_text = bp_cond_text.replace("<<<register_vtable>>>", register_vtable)
        bp_cond_text = bp_cond_text.replace("<<<offset>>>", offset)
        return bp_cond_text
    return "# Error in BP condition"



def write_vtable2file(start_addr):
    """
     :param start_addr: The start address of the virtual call
    :return: The break point condition and the break point address
    """
    raw_opnd = idc.GetOpnd(start_addr, 0)
    if raw_opnd in REGISTERS:
        reg = raw_opnd
    else:
        for reg in REGISTERS:
            if raw_opnd.find(reg) != -1:
                break
    print reg
    opnd = get_con2_var_or_num(reg, start_addr)

    reg_vtable = opnd[0]
    offset = opnd[1]
    bp_address = opnd[2]
    set_bp = True
    cond = ""

    try:
        #TODO If a structure was already assigned to the BP (not by Virtualor), before running the code the code will\
        # assume it was examined by the user, the BP will not be set
        plus_indx = raw_opnd.find('+')
        if plus_indx != -1:
            call_offset = raw_opnd[plus_indx + 1:raw_opnd.find(']')]
            # if the offset is in hex
            if call_offset.find('h') != -1:
                call_offset = int(call_offset[:call_offset.find('h')], 16)
        if offset.find('h') != -1:
            offset = str(int(offset[:offset.find('h')], 16))
            #offset = str(int(offset) + int(call_offset))
    except ValueError:
        #if offset[:9] == "vtable_0x":
        # A offset structure was set, the old offset will be deleted
            set_bp = False
    finally:
        if set_bp:
            cond = get_bp_condition(start_addr, reg_vtable, offset)
    return cond, bp_address