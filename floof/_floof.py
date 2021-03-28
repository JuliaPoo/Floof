from dataclasses import dataclass
from typing import Type, List, Literal, Union
from enum import Enum, unique
import warnings
import re

from . import _atoms
for a in dir(_atoms):
    if a[0] != '_': # An atom
        globals()["_%s_"%a] = getattr(_atoms, a)

VALID_NAME_REGEX = r"[a-zA-Z_][a-zA-Z0-9_]*"

@dataclass
class Token:
    obj_str: str
    line: int
    obj_idx: int
    is_name: bool

@unique
class ObjType(Enum):
    EXPR = 0
    DECL = 1

@dataclass
class ExprObject:
    objname: Token
    argvals: List[Union[Type['AstObject']]]

@dataclass
class DeclObject:
    argname: Token
    definition: Type['AstObject']
    argvals: List[Union[Type['AstObject']]]

@dataclass
class AstObject:
    namespace: List[Token]
    obj_type: Union[
            Literal[ObjType.EXPR],
            Literal[ObjType.DECL],
        ]
    obj: Union[
            ExprObject,
            DeclObject
        ]

ATOMS = [
    Token('_OUT_CHAR_', -1, -1, True),
    Token('_IN_CHAR_', -1, -1, True),
    Token('_OUT_INT_', -1, -1, True),
    Token('_IN_INT_', -1, -1, True)
]

class FloofBlock:

    def __init__(self, code:str, line:int, namespace:List[Token], _from_ast=False):

        if _from_ast:
            self.ast = _from_ast
            return

        self.code = code
        self.line = line
        self.namespace = namespace

        self.tokens = self._tokenize()
        self.ast = self._tokens_to_ast(self.tokens, self.namespace)

    @classmethod
    def from_ast(cls, ast:AstObject):
        return cls(None, None, None, _from_ast = ast)

    def _tokenize(self) -> List[Token]:
        
        tokens = []
        line = self.line
        code = self.code
        idx = 0

        while True:

            if idx==len(code):
                break

            c = code[idx]

            # Ignore whitespaces
            if re.match('^\s$', c):
                if c=='\n': line+=1

            elif c in '[]():':
                tokens.append(
                    Token(
                        obj_str = c,
                        line = line,
                        obj_idx = idx,
                        is_name = False
                    )
                )

            else:
                match = re.match("^"+VALID_NAME_REGEX, code[idx:])
                if not match:
                    raise Exception(
                        "[ERROR] Line %d: Invalid name `%s...`!"%(
                            line, 
                            code[idx:min(len(code)-1, idx+10)]
                        )
                    )
                obj_str = match.group()
                tokens.append(
                    Token(
                        obj_str = obj_str,
                        line = line,
                        obj_idx = idx,
                        is_name = True
                    )
                )
                idx += len(obj_str)
                continue

            idx += 1
        
        return tokens

    @staticmethod
    def _get_bracket_pair(tokens:List[Token], start_idx:int, start_bracket:Literal['(', '[']) -> int:

        c = tokens[start_idx].obj_str
        if c != start_bracket:
            raise Exception(
                "[PARSE ERROR] `get_bracket_pair` called with `%c` when looking for %x!"%(
                    c, start_bracket
                )
            )

        if len(tokens[start_idx:]) <= 1:
            return None

        end_bracket = {
            "(":")",
            "[":"]"
        }[start_bracket]

        offset = 0
        depth = 0
        for c in tokens[start_idx+1:]:
            offset += 1
            if c.obj_str==start_bracket:
                depth += 1
            if c.obj_str==end_bracket:
                if depth == 0:
                    return offset+start_idx
                depth -= 1
        return None

    @staticmethod
    def _parse_argvals(namespace:List[Token], tokens:List[Token], start_call_idx:int) -> List[AstObject]:

        argvals = []

        while True:

            # End of tokens
            if len(tokens) == start_call_idx:
                break
            
            t = tokens[start_call_idx]
            if t.obj_str != '(':
                line = t.line
                raise Exception(
                    "[ERROR] Line %d: Unexpected token! Expected `(`, `%s` instead"%(
                        line,
                        t.obj_str
                    )
                )
            
            end_call_idx = FloofBlock._get_bracket_pair(tokens, start_call_idx, t.obj_str)
            if not end_call_idx:
                line = tokens[0].line
                raise Exception(
                    "[ERROR] Line %d: Unbalanced bracket `%c`!"%(line, t.obj_str)
                )

            call_tokens = tokens[start_call_idx+1:end_call_idx]
            arg = FloofBlock._tokens_to_ast( 
                call_tokens,
                namespace
            )
            argvals.append(arg)
            start_call_idx = end_call_idx+1

        return argvals

    @staticmethod
    def _tokens_to_ast(tokens:List[Token], namespace:List[Token]) -> AstObject:
            
        t = tokens[0]

        # Start of declaration object (DeclObject)
        if t.obj_str == '[':

            end_decl_idx = FloofBlock._get_bracket_pair(tokens, 0, t.obj_str)
            if not end_decl_idx:
                line = tokens[0].line
                raise Exception(
                    "[ERROR] Line %d: Unbalanced bracket `%c`!"%(line, t.obj_str)
                )

            argname = tokens[1]
            def_tokens = tokens[3:end_decl_idx]

            if tokens[2].obj_str != ':':
                line = tokens[2].line
                raise Exception(
                    "[ERROR] Line %d: Invalid declaration! Expected `:` token! `%s` instead"%(
                        line,
                        tokens[2].obj_str
                    )
                )

            def_ast = FloofBlock._tokens_to_ast( 
                def_tokens, 
                namespace + [argname]
            )

            start_call_idx = end_decl_idx+1
            argvals = FloofBlock._parse_argvals(
                namespace, tokens, start_call_idx,
            )

            return AstObject(
                namespace = namespace,
                obj_type = ObjType.DECL,
                obj = DeclObject(
                    argname = argname,
                    definition = def_ast,
                    argvals = argvals
                )
            )

        elif t.is_name:
            
            objname = t

            if objname.obj_str not in [t.obj_str for t in namespace]:
                raise Exception(
                    "[ERROR] Line %d: Name `%s` is not defined!"%(
                        t.line,
                        t.obj_str
                    )
                )

            start_call_idx = 1
            argvals = FloofBlock._parse_argvals(
                namespace, tokens, start_call_idx
            )

            return AstObject(
                namespace = namespace,
                obj_type = ObjType.EXPR,
                obj = ExprObject(
                    objname = objname,
                    argvals = argvals
                )
            )

        else:
            raise Exception(
                "[ERROR] Line %d: Unexpected token! Expected `[` or an object name but got `%s` instead"%(
                    t.line,
                    t.obj_str
                )
            )

    @staticmethod
    def _to_code(ast:AstObject, target:Union[Literal['floof'], Literal['python']] = 'python') -> str:

        template = {
            "floof": "[%s:%s]",
            "python": "(lambda %s: %s)"
        }[target]

        if ast.obj_type==ObjType.DECL:
            obj = ast.obj
            argname, definition, argvals = obj.argname, obj.definition, obj.argvals
            code = template%(
                argname.obj_str,
                FloofBlock._to_code(definition, target)
            )
            for arg in argvals:
                code += "(%s)"%FloofBlock._to_code(arg, target)
            
        elif ast.obj_type==ObjType.EXPR:
            obj = ast.obj
            objname, argvals = obj.objname, obj.argvals
            code = "%s"%objname.obj_str
            for arg in argvals:
                code += "(%s)"%FloofBlock._to_code(arg, target)

        else:
            raise Exception(
                "[COMPILE ERROR] Unexpected object type"
            )

        return code

    def to_code(self, target:Union[Literal['floof'], Literal['python']] = 'python') -> str:
        return self._to_code(self.ast, target)

class Floof:

    def __init__(self, code:str):

        self.code = code
        self.mainblock = self._to_FloofBlock(code)
        self.compiled = {}

    @staticmethod
    def _parse_macro(lines, line_idx, namespace):

        idx = line_idx
        macro_name = lines[idx][1:].strip()
        macro_def = ""
        for j,l in enumerate(lines[idx+1:]):
            if not l:
                macro_def += l+"\n"
                continue
            if l[0]=='~':
                break
            if l[0]=='!':
                raise Exception("[ERROR] Line %d: Main definition within macro not allowed"%idx)
            macro_def += l+"\n"

        if not macro_name:
            raise Exception("[ERROR] Line %d: No name given to macro"%idx)

        if not re.match("^%s$"%VALID_NAME_REGEX, macro_name):
            raise Exception("[ERROR] Line %d: Macro name `%s` invalid"%(idx, macro_name))

        if not l or l[0] != '~':
            raise Exception("[ERROR] Line %d: Macro `%s` terminator not found"%(idx, macro_name))

        macro_name = Token(macro_name, line_idx, -1, True)
        macro_block = FloofBlock(macro_def, line_idx+2, namespace)
        end_line = j+idx+2

        return macro_name, macro_block, end_line

    @staticmethod
    def _parse_main(lines, line_idx, namespace):

        idx = line_idx
        main = ""
        for j,l in enumerate(lines[idx+1:]):
            if not l:
                main += "\n"
                continue
            if l[0]=='~':
                break
            if l[0]=='#':
                raise Exception("[ERROR] Line %d: Macro definition within main not allowed"%idx)
            main += l+"\n"

        if not l or l[0] != '~':
            raise Exception("[ERROR] Line %d: Main terminator not found"%idx)

        return FloofBlock(main, line_idx+2, namespace), j+idx+2

    @staticmethod
    def _search_macro(ast:AstObject, macro_name:str):
        
        namespace_str = [t.obj_str for t in ast.namespace]
        if ast.obj_type == ObjType.EXPR:
            if macro_name not in namespace_str:
                return False
            if ast.obj.objname.obj_str == macro_name:
                return True
            for arg in ast.obj.argvals:
                if Floof._search_macro(arg, macro_name):
                    return True
            return False

        elif ast.obj_type == ObjType.DECL:
            if macro_name not in namespace_str:
                return False
            if ast.obj.argname.obj_str == macro_name:
                return True
            for arg in ast.obj.argvals:
                if Floof._search_macro(arg, macro_name):
                    return True
            if Floof._search_macro(ast.obj.definition, macro_name):
                return True
            return False
        
        else:
            raise Exception("[COMPILER ERROR] Unexpected ObjType")

    @staticmethod
    def _to_FloofBlock(code:str) -> FloofBlock:

        code = code
        lines = code.split("\n")

        # Remove comments
        for idx,line in enumerate(lines):
            if ';' not in line:
                continue
            lines[idx] = line.split(';')[0]

        # Parse macro and main
        namespace = ATOMS
        macros = []
        main = None
        for idx,line in enumerate(lines):

            if not line: continue

            if line[0] == '#':

                name, macro, end_idx = Floof._parse_macro(lines, idx, namespace)
                if name in [n for n,_ in macros]:
                    raise Exception("[ERROR] Line %d: Macro `%s` has been defined more than once."%(idx, name))
                
                macros.append((name, macro))
                namespace.append(name)
                continue

            if line[0] == '!':
                main, end_idx = Floof._parse_main(lines, idx, namespace)
                break

        if len(lines) >= end_idx:
            leftovers = "\n".join(lines[end_idx:])
            if not re.match("^\s*$", leftovers):
                warnings.warn("[WARNING] Code after line %d is ignored!"%end_idx)

        # Check if main was never found
        if not main:
            raise Exception("[ERROR] Line ??: No main found")

        # Create AST for full program
        main_ast, main_namespace = main.ast, main.ast.namespace

        for name, macro in macros[::-1]:

            if not Floof._search_macro(main_ast, name.obj_str):
                warnings.warn("[WARNING] Macro `%s` is not used"%name.obj_str)
                continue

            main_namespace = [t for t in main_namespace if t.obj_str != name.obj_str]
            main_ast = AstObject(
                namespace = main_namespace,
                obj_type = ObjType.DECL,
                obj = DeclObject(
                    argname = name,
                    definition = main_ast,
                    argvals = [macro.ast]
                )
            )

        return FloofBlock.from_ast(main_ast)

    def to_code(self, target:Union[Literal['floof'], Literal['python']] = 'python')->str:
        if target not in self.compiled:
            self.compiled[target] = self.mainblock.to_code(target)
        return self.compiled[target]

    def run(self):
        eval(self.to_code())