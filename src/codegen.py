from structure import FunctionType, StructType, SymbolTable, sym_table, PointerType, BasicType
from threeaddr import gen
from threeaddr import alloc, temp_dict
import math

#Note:
"""
We've avoided padding for implementation purpose,
padding poses some more challenges and understanding
----++++----++++----++++----++++----++++
    |   |   |      |     |
Unaligned address will impose more runtime overhead
"""
"""
we are supporting the arguments in the main function
i) argc
ii) argv
"""

##
"""
Possible error:
i.)confusion of symbol_table_dict, sym_table
ii.)addresses are not aligned in add_args_copy_code
"""
##

#### Task:
"""
add code for global, bss
    func_call
    saving argument values at stack
    reserve space for symbols
    add code for labels
"""

####

gp_regs ={}

gp_regs[8] = ['rax', 'rbx', 'rcx', 'rdx','rsi','rdi', 'rbp' + 'rsp'] + ['r' + str(i) for i in range(8,16)]
gp_regs[4] = ['eax', 'ebx', 'ecx', 'edx','esi','edi', 'ebp' + 'esp'] + ['r' + str(i) + 'd' for i in range(8,16)]
gp_regs[2] = ['ax', 'bx', 'cx', 'dx','si','di', 'bp' + 'sp'] + ['r' + str(i) + 'w' for i in range(8,16)]
gp_regs[1] = ['al', 'bl', 'cl', 'dl','sil','dil', 'bpl' + 'spl'] + ['r' + str(i) + 'b' for i in range(8,16)]

gp_regsf = ['xmm' + str(i) for i in range(16)]

arg_regs = [
        {8:'rdi', 4:'edi',2:'di', 1:'dil'},
        {8:'rsi', 4:'esi',2:'si', 2:'sil'},
        {8:'rdx', 4:'edx',2:'dx', 2:'dl'},
        {8:'rcx', 4:'ecx',2:'cx', 2:'cl'},
        {8:'r8', 4:'r8d',2:'r8w', 2:'r8b'},
        {8:'r9', 4:'r9d',2:'r9w', 2:'r9b'}
    ]
temp_regs= [
        {8:'r10', 4:'r10d',2:'r10w', 1:'r10b'},
        {8:'r11', 4:'r11d',2:'r11w', 1:'r11b'}
    ]
arg_regsf= ['xmm' + str(i) for i in range(8)]

size_type = {1:'byte', 2:'word', 4:'dword', 8:'qword'}

decl_type= {1:'db', 2:'dw', 4:'dd', 8:'dq',16:'ddq'}
decl_type_bss = {1:'resb', 2:'resw', 4:'resd', 8:'resq',16:'resdq'}

convis ={'ah:al':'cbw','dx:ax':'cwd', 'edx:eax':'cdq', 'rdx:rax':'cqo'}

const_dict = {}

extern_functions = [
    'printf',
    'scanf',
    'malloc'
]

def add_standard_constant():
    code = ['; this section for standard constants']
    code += [
    'LF equ 10 ; line feed',
    'NULL equ 0 ; end of string',
    'TRUE equ 1',
    'FALSE equ 0',
    'EXIT_SUCCESS equ 0 ; success code',
    'STDIN equ 0 ; standard input',
    'STDOUT equ 1 ; standard output',
    'STDERR equ 2 ; standard error',
    'SYS_read equ 0 ; read',
    'SYS_write equ 1 ; write',
    'SYS_open equ 2 ; file open',
    'SYS_close equ 3 ; file close',
    'SYS_fork equ 57 ; fork',
    'SYS_exit equ 60 ; terminate',
    'SYS_creat equ 85 ; file open/create'
    ]
    return code


def add_bss():
    code = ['section .bss']
    for name in sym_table.table:
        typ = sym_table.table[name].type
        if typ.class_type == 'FunctionType':
            continue
        if '@' not in name:
            if name + '|global' not in alloc:
                name = name + '@global'
                if typ.class_type == 'BasicType':
                    code += [name + ' ' + decl_type_bss[typ.width] + ' 1']
                elif typ.class_type == 'PointerType':
                    if typ.is_array:
                        assert isinstance(typ.array_size, list), "array size must be list"
                        code += [name + ' ' + decl_type_bss[typ.array_type.width] + ' ' + str(math.prod(typ.array_size))]
                    else:
                        code += [name + ' ' + decl_type_bss[8] + ' 1']
                else:
                    assert isinstance(typ, StructType), "must be of struct type"
                    tmp_code =[]
                    
                    for key in typ.symbol_table.table:
                        typ2 = typ.symbol_table.table[key].type
                        if typ2.class_type == 'PointerType' and typ2.is_array:
                            tmp_code += [decl_type_bss[typ2.array_type.width] + ' ' + str(math.prod(typ2.array_size))]
                        else:
                            tmp_code += [decl_type_bss[typ2.width] + ' 1' ]
                    
                    #print(name, tmp_code)
                    assert tmp_code, "empty struct"

                    tmp_code[0] = name + ' ' + tmp_code[0]

                    code += tmp_code
    return code

def add_init_global_variables():
    code =[]
    for key in alloc:
        if '@' in key:
            name = key
            e_name = 'const' + str(len(const_dict))
            #const_dict[str(alloc[key])] = e_name
            const_dict[key] = e_name
        else :
            name = key.split('|')[0]
            e_name = name + '@global'

        typ = sym_table.table[name].type
        assert isinstance(typ, PointerType) or isinstance(typ,BasicType)

        if typ.class_type == 'BasicType':
            code += [e_name + ' ' + decl_type[typ.width] + ' ' + str(alloc[key])]
        else:
            if typ.is_array:
                assert typ.array_type.stype == 'char', "not char string"
                code += [e_name + ' ' + decl_type[typ.array_type.width]  + ' "' + str(alloc[key]) +'", NULL']
            else:
                code += [e_name + ' ' + decl_type[8] + ' ' + str(alloc[key])]
    
    return code


def add_data():
    code = ['section .data']
    code += add_standard_constant()
    code += [';add global variables and constants']
    code += add_init_global_variables()
    return code

def add_start(gcode):
    code = ['global _start']
    code += ['_start:']
    code += ['mov r12,  [rsp]']     #argc
    code += ['lea r13, [rsp+8]']    #starting address of argv

    assert not gcode, "Not supported exp outside functions"

    code += ['mov rdi, r12']
    code += ['mov rsi, r13']
    code += ['call main']
    code += ['end:']
    code += ['mov rax, SYS_exit ; Call code for exit']
    code += ['mov rdi, EXIT_SUCCESS ; Exit program with success']
    code += ['syscall']

    return code

def add_text(gcode, func_codes):
    code = ['section .text']
    code += add_start(gcode)
    
    for func in func_codes:
        code += add_func_code(func)
    
    return code

def get_var_addr(var_name):
    if 'const@' in var_name:
        addr =  const_dict[var_name]
    elif 'tmp@' in var_name:
        offset = temp_dict[var_name].table[var_name].offset + temp_dict[var_name].base
        addr = 'rbp-'+ str(offset)
    else:
        assert '|' in var_name, "wrong var in 3ac code"
        name = var_name.split('|')[0]
        table = var_name.split('|')[1]
        
        symbol_table = SymbolTable.symbol_table_dict[table]
        assert symbol_table, "there is no symbol table correspoding to" + table
        offset = symbol_table.table[name].offset + symbol_table.base
        

        if table == "global":
            addr = name + '@global'
        else:
            addr = 'rbp-'+ str(offset)
    return addr

def get_var_type(var_name):
    if 'const@' in var_name:
        typ = sym_table.table[var_name].type
    elif 'tmp@' in var_name:
        typ = temp_dict[var_name].table[var_name].type
    else:
        assert '|' in var_name, "wrong var in 3ac code"
        name = var_name.split('|')[0]
        table = var_name.split('|')[1]
        
        symbol_table = SymbolTable.symbol_table_dict[table]
        assert symbol_table, "there is no symbol table correspoding to" + table

        typ = symbol_table.table[name].type
    return typ

def add_args_copy_code(fname):
    code =[]
    float_args = 0
    byte8_args = 0
    other_args = 0
    args_type = sym_table.table[fname].type.param_list
    symbol_table = sym_table.table[fname].type.symbol_table

    assert symbol_table == SymbolTable.symbol_table_dict[fname], "possibly wrong implementation"

    off = 16
    code += ['; saving the arguments values in the stack']
    reserved = symbol_table.table['return'].type.width
    code += ["sub rsp, " +str(reserved) + "; adjust rsp for return entry"]
    required = symbol_table.offset

    for typ in args_type:
        if typ.stype == "float":
            float_args += 1
            if float_args <= len(arg_regsf):
                code += ["sub rsp, 4"]
                code += ["movss dword [rsp]," + arg_regsf[float_args-1]]
            else:
                code += ["sub rsp, 4"]
                code += ["movss xmm0, dword [rbp+" +str(off)+ "]"]
                code += ["movss dword [rsp], xmm0"]
        elif typ.class_type == "BasicType" or typ.class_type == "PointerType":
            byte8_args += 1
            if typ.class_type == "PointerType":
                get_width = str(8)
                get_size = size_type[8]
                width = 8
            else:
                width = typ.width
                get_width = str(typ.width)
                get_size = size_type[typ.width]
            if byte8_args <= len(arg_regs):
                code += ["sub rsp, " + get_width]
                code += ["mov "+get_size+" [rsp]," + arg_regs[byte8_args-1][width]]
            else:
                code += ["sub rsp, " + get_width]
                code += ["mov "+temp_regs[0][width]+", "+get_size+" [rbp+" +str(off)+ "]"]
                code += ["mov "+get_size+"[rsp], "+ temp_regs[0][width]]

        else:
            other_args += 1
            code += ['; copying data in stack of ' + typ.stype]
            code += add_copy_data_code(typ.width, "rbp+" +str(off))
        if typ.class_type == "PointerType":
            off += 8
            reserved += 8
        else:
            off += typ.width
            reserved += typ.width
    
    required -= reserved
    code += [';add space for symbols']
    code += ["sub rsp, "+ str(required)]

    return code

def add_return_code(name, gen_obj):
    code = []
    if gen_obj.place1:
        place1 = gen_obj.place1
        typ = SymbolTable.symbol_table_dict[name].table['return']
        if typ == 'StructType' or typ.width > 8:
            code += [';copy return value at addr in rax']
            code += add_copy_data_code(typ.width, get_var_addr(place1), 'rax')
        elif typ.stype == 'float':
            code += [';copy return value in xmm0']
            code += ["movss xmm0, " +size_type[typ.width] +"[" +get_var_addr(place1) +"]"]
        else:
            code += [';copy return value in rax']
            code += ["mov " + gp_regs[typ.width][0] + " , " +size_type[typ.width] +"[" +get_var_addr(place1) +"]"]
    else:
        code += ["xor rax, rax"]
    code += ['leave']
    code += ['ret']
    return code

def add_post_call(place3):
    code =[]
    if not place3:
        return code
    typ = get_var_type(place3)
    addr = get_var_addr(place3)
    if typ == 'StructType' or typ.width > 8:
        code += [';copy return value from addr in rax']
        code += add_copy_data_code(typ.width, 'rax', addr)
    elif typ.stype == 'float':
        code += [';copy return value from xmm0']
        code += ["movss " +size_type[typ.width] +"[" +addr+"], xmm0"]
    else:
        code += [';copy return value from rax']
        code += ["mov " + size_type[typ.width] +"[" +addr+"]" +", " +gp_regs[typ.width][0]]
    return code

def load_var(var1, var2 = None):
    code =[]
    addr = get_var_addr(var1)
    typ = get_var_type(var1)
    width = typ.width
    #print(typ, var1)
    get_size = size_type[typ.width]
    if typ.stype == 'float':
        code += ["movss "+arg_regsf[0]+", "+get_size+" ["+addr+"]"]
    else:
        code += ["mov "+temp_regs[0][width]+", "+get_size+" ["+addr+"]"]

    if not var2:
        return code

    addr = get_var_addr(var2)
    typ = get_var_type(var2)
    width = typ.width
    get_size = size_type[typ.width]

    if typ.stype == 'float':
        code += ["movss "+arg_regsf[1]+", "+get_size+" ["+addr+"]"]
    else:
        code += ["mov "+temp_regs[1][width]+", "+get_size+" ["+addr+"]"]
    return code

def add_assign_code(gen_obj):
    code =[]
    if gen_obj.op in ["long=","int=","char=","bool="]:
        code += load_var(gen_obj.place1)
        addr = get_var_addr(gen_obj.place3)
        typ = get_var_type(gen_obj.place3)
        width = typ.width
        get_size = size_type[width]
        if gen_obj.op != 'float=':
            code += ["mov " + get_size + "[" +addr+"], " + temp_regs[0][width]]
        else:
            code += ["movss " + get_size + "[" + addr+"]" + arg_regsf[0]]
    elif gen_obj.op == 'str=':
        addr1 = get_var_addr(gen_obj.place1)
        addr3 = get_var_addr(gen_obj.place3)
        typ1 = get_var_type(gen_obj.place1)
        typ3 = get_var_type(gen_obj.place3)
        #print(typ1, typ3, typ1.width, typ3.width)
        code += add_copy_data_code(min(typ1.width, typ3.width), addr1, addr3)
    elif 'struct' in gen_obj.op and '=' in gen_obj.op:
        addr1 = get_var_addr(gen_obj.place1)
        addr3 = get_var_addr(gen_obj.place3)
        typ1 = get_var_type(gen_obj.place1)
        typ3 = get_var_type(gen_obj.place3)
        assert typ1 == typ3, "missing semantic type checking assign struct"
        code += add_copy_data_code(min(typ1.width, typ3.width), addr1, addr3)
    return code

def add_plus_code(gen_obj):
    code =[]
    print(gen_obj, get_var_type(gen_obj.place1))
    code += load_var(gen_obj.place1, gen_obj.place2)
    addr = get_var_addr(gen_obj.place3)
    typ = get_var_type(gen_obj.place3)
    width = typ.width
    get_size = size_type[width]
    if gen_obj.op != 'float+':
        code += ["add r10, r11"]
        code += ["mov " + get_size + "[" +addr+"], " + temp_regs[0][width]]
    else:
        code += ["addss xmm0, xmm1"]
        code += ["movss " + get_size + "[" +addr+"], xmm0"]
    return code

def add_sub_code(gen_obj):
    code =[]
    code += load_var(gen_obj.place1, gen_obj.place2)
    addr = get_var_addr(gen_obj.place3)
    typ = get_var_type(gen_obj.place3)
    width = typ.width
    get_size = size_type[width]
    if gen_obj.op != 'float-':
        code += ["sub r10, r11"]
        code += ["mov " + get_size + "[" +addr+"], " + temp_regs[0][width]]
    else:
        code += ["subss xmm0, xmm1"]
        code += ["movss " + get_size + "[" +addr+"], xmm0"]
    return code

def add_mul_code(gen_obj):
    code =[]
    code += load_var(gen_obj.place1, gen_obj.place2)
    addr = get_var_addr(gen_obj.place3)
    typ = get_var_type(gen_obj.place3)
    width = typ.width
    get_size = size_type[width]
    if gen_obj.op != 'float*':
        code += ["imul r10, r11"]
        code += ["mov " + get_size + "[" +addr+"], " + temp_regs[0][width]]
    else:
        code += ["mulss xmm0, xmm1"]
        code += ["movss " + get_size + "[" +addr+"], xmm0"]
    return code

def add_div_code(gen_obj):
    code =[]
    place = [gen_obj.place1, gen_obj.place2, gen_obj.place3]
    addr = [get_var_addr(_) for _ in place]
    typ = [get_var_type(_) for _ in place]
    width = [_.width for _ in typ]
    get_size = [size_type[_] for _ in width]

    if gen_obj.op != 'float/' and gen_obj.op != 'char/':
        assert width[0] == width[1],"type mismatch for division"
        assert width[0] == width[2],"type mismatch for division"
        code += ["push rax"]
        code += ["mov " + gp_regs[0][width[0]] + ", " + get_size[0] + "[" +addr[0] +"]"]
        code += [convis[gp_regs[3][width[0]] +':'+gp_regs[0][width[0]]]]
        code += ["idiv " + get_size[1] + "[" + addr[1]+"]"]
        code += ["mov " + get_size[2] +"["+addr[2]+"], " + gp_regs[0][width[2]]]
        code += ["pop rax"]
    elif gen_obj.op == 'char/':
        assert width[0] == width[1],"type mismatch for division"
        assert width[0] == width[2],"type mismatch for division"
        code += ["push rax"]
        code += ["mov " + gp_regs[0][width[0]] + ", " + get_size[0] + "[" +addr[0] +"]"]
        code += [convis['ah:al']]
        code += ["idiv " + get_size[1] + "[" + addr[1]+"]"]
        code += ["mov " + get_size[2] +"["+addr[2]+"], " + gp_regs[0][width[2]]]
        code += ["pop rax"]
    else:
        code += ["divss xmm0, xmm1"]
        code += ["movss " + get_size + "[" +addr+"], xmm0"]
    return code

def add_rem_code(gen_obj):
    code =[]
    place = [gen_obj.place1, gen_obj.place2, gen_obj.place3]
    addr = [get_var_addr(_) for _ in place]
    typ = [get_var_type(_) for _ in place]
    width = [_.width for _ in typ]
    get_size = [size_type[_] for _ in width]
    if gen_obj.op != 'char%':
        assert width[0] == width[1],"type mismatch for division"
        assert width[0] == width[2],"type mismatch for division"
        code += ["push rax"]
        code += ["mov " + gp_regs[0][width[0]] + ", " + get_size[0] + "[" +addr[0] +"]"]
        code += [convis[gp_regs[3][width[0]] +':'+gp_regs[0][width[0]]]]
        code += ["idiv " + get_size[1] + "[" + addr[1]+"]"]
        code += ["mov " + get_size[2] +"["+addr[2]+"], " + gp_regs[3][width[2]]]
        code += ["pop rax"]
    else:
        assert width[0] == width[1],"type mismatch for division"
        assert width[0] == width[2],"type mismatch for division"
        code += ["push rax"]
        code += ["mov " + gp_regs[0][width[0]] + ", " + get_size[0] + "[" +addr[0] +"]"]
        code += [convis['ah:al']]
        code += ["idiv " + get_size[1] + "[" + addr[1]+"]"]
        code += ["mov " + get_size[2] +"["+addr[2]+"], ah"]
        code += ["pop rax"]
    return code

def add_load_addr(gen_obj):
    code = []
    addr = get_var_addr(gen_obj.place3)
    typ = get_var_type(gen_obj.place3)
    width = typ.width
    get_size = size_type[width]
    if gen_obj.op == 'load':
        code += load_var(gen_obj.place1)
        if 'xmm' in code[-1]:
            code += ["movss " + get_size + "[" +addr+"], xmm0"]
        else:
            code += ["mov " + get_size + "[" +addr+"], " + temp_regs[0][width]]
    else:
        addr1 = get_var_addr(gen_obj.place1)
        code += ["lea r10, [" + addr1+"]"]
        code += ["mov qword [" + addr+"], r10"]
    return code


def add_other_opcode(gen_obj):
    code =[]
    assign_op = ["long=","int=","char=","float=","str=","bool="]
    if gen_obj.op == 'ifz' or gen_obj.op == 'ifnz':
        opd = {'ifz':'je','ifz':'jne'}
        code += load_var(gen_obj.place1)
        if 'xmm' in code[-1]:
            code += ["ucomiss xmm0, 0"]
        else:
            code += ["cmp r10, 0"]
        code += [opd[gen_obj.op]+" " + gen_obj.place2]
    elif 'if_not_cmp' in gen_obj.op:
        code += load_var(gen_obj.place1, gen_obj.place2)
        if 'xmm' in code[-1]:
            code += ["ucomiss xmm0, xmm1"]
        else:    
            code += ["cmp r10, r11"]
        code += ["jne " + gen_obj.place3]
    elif gen_obj.op in ["load", "addr"]:
        code += add_load_addr(gen_obj)
    elif gen_obj.op in assign_op or ("struct" in gen_obj.op and "=" in gen_obj.op):
        code += add_assign_code(gen_obj)
    elif gen_obj.op in ['int+','long+', 'char+', 'float+', 'bool+']:
        code += add_plus_code(gen_obj)
    elif gen_obj.op in ['int*','long*', 'char*', 'float*', 'bool*']:
        code += add_mul_code(gen_obj)
    elif gen_obj.op in ['int-','long-', 'char-', 'float-', 'bool-']:
        code += add_sub_code(gen_obj)
    elif gen_obj.op in ['int/','long/', 'char/', 'float/']:
        code += add_div_code(gen_obj)
    elif gen_obj.op in ['int%', 'long%', 'char%']:
        code += add_rem_code(gen_obj)
    else:
        pass
    return code



def add_func_body_code(name, func_code):
    code =[]
    for gen_obj in func_code:
        if gen_obj.op == 'func_call':
            #add_func_call handles value assignment to place3
            code += add_func_call(gen_obj)
        elif gen_obj.op == 'return':
            code += add_return_code(name, gen_obj)
        elif gen_obj.op == 'label':
            code += [gen_obj.code]
        elif gen_obj.op == 'goto':
            code += ['jmp ' + gen_obj.place1]
        else:
            code += add_other_opcode(gen_obj)
    return code

def add_func_code(func):
    code = ['global ' + func['name']]
    code += [func['name'] + ':']
    code += ['push   rbp']
    code += ['mov    rbp,rsp']
    code += add_args_copy_code(func['name'])
    code += add_func_body_code(func['name'], func['code'])
    if code[-1] != 'ret':
        code += ['leave']
        code += ['ret']
    return code

def add_func_call(gen_obj):
    assert isinstance(gen_obj, gen), "object type error"
    assert isinstance(sym_table.table[gen_obj.place1].type, FunctionType), "not a function"

    if not sym_table.table[gen_obj.place1].type.defined and (gen_obj.place1 not in extern_functions):
        print( "\033[93m {}\033[00m" .format("Warning:")+ "Undefined refrence to" + "\033[91m {}\033[00m" .format(gen_obj.place1))
    
    code = []

    args_val = gen_obj.place2
    place3 = gen_obj.place3 if gen_obj.place3 != "None" else None
    ret_type = SymbolTable.symbol_table_dict[gen_obj.place1].table['return']
    args_type = sym_table.table[gen_obj.place1].type.param_list

    #print(args_val)
    #print(args_type, args_type[0])

    assert len(args_type) == len(args_val), "argument mismatch"

    float_args = 0
    byte8_args = 0
    other_args = 0
    shift = 0

    if ret_type.width > 8:
        shift += ret_type.width
        code += ["lea rsp, [rsp+"+str(ret_type.width)+"]"]
        code += ["lea rax, [rsp]"]

    for arg in args_val:
        typ = get_var_type(arg)
        if typ.stype == "float":
            float_args += 1
        elif typ.class_type == "PointerType" or typ.class_type == "BasicType":
            byte8_args += 1
        else:
            other_args += 1
    #print(float_args_type, byte8_args_type, other_args_type)
    #print(float_args, byte8_args, other_args)

    args_val = args_val[::-1]
    args_type = args_type[::-1]

    assert len(args_val) == len(args_type), "Mismatch in No. of args has not detected"

    code += ['; saving arguments for call']
    for arg in args_val:
        addr = get_var_addr(arg)
        typ = get_var_type(arg)
        if typ.stype == "float":
            if float_args > len(arg_regsf):
                code += ['sub rsp, 4']
                code += ['movss xmm0, dword [' + addr+']']
                code += ['movss dword [rsp], xmm0']
                shift += typ.width
            else:
                code += ['movss ' + arg_regsf[float_args-1] +', dword [' + addr + ']']
            float_args -= 1
        elif typ.class_type == "BasicType" or typ.class_type == "PointerType":
            if typ.class_type == "PointerType":
                get_width = str(8)
                get_size = size_type[8]
                width = 8
            else:
                width = typ.width
                get_width = str(typ.width)
                get_size = size_type[typ.width]
            if byte8_args > len(arg_regs):
                code += ['sub rsp, ' + get_width]
                if typ.class_type != "PointerType":
                    code += ['mov '+temp_regs[0][width]+', '+get_size+' [' + addr+']']
                elif typ.is_array:
                    code += ['lea '+temp_regs[0][8]+', [' + addr+']']
                else:
                    code += ['mov '+temp_regs[0][8]+', '+size_type[8]+' [' + addr+']']
                code += ['mov '+get_size+' [rsp], '+temp_regs[0][width]]
                shift += width
            else:
                #print(typ)
                if typ.class_type != "PointerType":
                    code += ['mov ' + arg_regs[byte8_args-1][width] +', '+get_size+' [' + addr + ']']
                elif typ.is_array:
                    code += ['lea ' + arg_regs[byte8_args-1][8] +', [' + addr + ']']
                else:
                    code += ['mov ' + arg_regs[byte8_args-1][width] +', '+get_size+' [' + addr + ']']
            byte8_args -= 1
        else:
            shift += typ.width
            code += ['; copying data in stack of ' + typ.stype]
            code += add_copy_data_code(typ.width, addr)
            other_args -= 1
    code += ["call " + gen_obj.place1]
    code += add_post_call(place3)
    code += ["add rsp," + str(shift)]
    return code

def add_copy_data_code(count, addr, rax = None):
    """
    copy data from addr and put in rax specified addr
    """
    """
    array
       addr :+
             +
             +
             +
      addr+4 -
             -
             -
             -
    """
    code =[]
    off = 0
    noff = 0
    while count:
        new_addr = addr + '+' + str(off)
        if count >= 8:
            dec = 8
        elif count >= 4:
            dec = 4
        elif count >= 2:
            dec = 2
        else:
            dec = 1
        get_size = size_type[dec]
        count -= dec
        off += dec
        if not rax:
            code += ["push " + get_size+ " [" + new_addr + "]"]
        else:
            code += ["mov " + temp_regs[0][dec] + ", " + get_size + "[" + new_addr+"]"]
            code += ["mov " + get_size + "[" + rax +"+" + str(noff)+"], " + temp_regs[0][dec]]
        noff += dec

    return code
   
def add_extern():
    code =[]
    for func in extern_functions:
        code += ['extern ' + func]
    return code
    

    

def generate(tac_code):
    func_name =""
    gcode = []
    funcs =[]
    code =[]
    for i, obj in enumerate(tac_code):
        if obj.op == 'BeginFunc':
            if func_name:
                assert False, "wrong code generated"
                exit(-1)
            func_name = tac_code[i-1].place1
            funcs += [{}]
            funcs[-1]['name'] = func_name
            funcs[-1]['code'] = []
            continue
        elif obj.op == 'EndFunc':
            if not func_name:
                assert False, "wrong code generated"
                exit(-1)
            func_name =""
            continue

        if func_name:
            funcs[-1]['code'] += [obj]
        else:
            if obj.op!= 'label':
                gcode += [obj]
    code += add_data()
    code += [';add bss section for unintialized variables']
    code += add_bss()
    code += [';add extern symbols']
    code += add_extern()
    code += add_text(gcode, funcs)

    return code


def print_asm(tac_code):
    code = generate(tac_code)
    f = open('temp.asm', 'w')
    for string in code:
        print(string, file = f)
        