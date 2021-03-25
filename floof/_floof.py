import re as _re
from . import _atoms
#import sys as _sys
#_sys.setrecursionlimit(2000)

for a in dir(_atoms):
    if a[0] != '_': # An atom
        globals()["_%s_"%a] = getattr(_atoms, a)

def parse_macro(idx, lines):

    macro_name = lines[idx][1:]
    macro_def = ""
    for l in lines[idx+1:]:
        if not l:
            continue
        if l[0]=='~':
            break
        if l[0]=='!':
            raise Exception("[ERROR] Line %d: Main definition within macro not allowed"%idx)
        macro_def += l

    if not macro_name:
        raise Exception("[ERROR] Line %d: No name given to macro"%idx)

    if not _re.match(r"[^\s]+", macro_name):
        raise Exception("[ERROR] Line %d: Macro name invalid"%idx)

    if not l or l[0] != '~':
        raise Exception("[ERROR] Line %d: Macro terminator not found"%idx)

    return _re.sub(r'\s', r'', macro_name), _re.sub(r'\s', r'', macro_def)

def parse_main(idx, lines):

    main = ""
    for l in lines[idx+1:]:
        if not l:
            continue
        if l[0]=='~':
            break
        if l[0]=='#':
            raise Exception("[ERROR] Line %d: Macro definition within main not allowed"%idx)
        main += l

    if not l or l[0] != '~':
        raise Exception("[ERROR] Line %d: Main terminator not found"%idx)

    return _re.sub(r'\s', r'', main)
    
def preprocessor(code:str):

    lines = code.split("\n")

    # Remove comments
    for idx,line in enumerate(lines):
        if ';' not in line:
            continue
        lines[idx] = line.split(';')[0]

    # Parse macro and main
    macros = []
    main = None
    for idx,line in enumerate(lines):
        if not line:
            continue
        if line[0] == '#':
            (name, definition) = parse_macro(idx, lines)
            if name in [n for n,_ in macros]:
                raise Exception("[ERROR] Line %d: Macro `%s` has been defined more than once."%(idx, name))
            macros.append((name, definition))
            continue
        if line[0] == '!':
            if main:
                raise Exception("[ERROR] Line %d: More than one main found"%idx)
            main = parse_main(idx, lines)

    # Check if main was found
    if not main:
        raise Exception("[ERROR] Line ??: No main found")

    # Apply preprocessor
    for name, definition in macros[::-1]:
        if name not in main:
            print("[WARNING] Macro `%s` is not used"%name)
            continue
        main = "[%s:%s](%s)"%(name, main, definition)

    return main
    
def compile(processed_code:str):
    code = _re.sub(r'\s', r'', processed_code)
    code = _re.sub(r"(\w+):", r"lambda \1:", code)
    code = code.replace("[", "(").replace("]", ")")
    return code

def run(code:str, verbose:bool=False):
    
    code = preprocessor(code)
    if verbose:
        print("\n\n")
        print("[VERBOSE]: After preprocessor")
        print(code)
        print("\n\n")

    code = compile(code)
    if verbose:
        print("\n\n")
        print("[VERBOSE]: Compiled to python")
        print(code)
        print("\n\n")

    eval(code) # run