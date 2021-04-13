from dataclasses import dataclass
from typing import List, Literal, Union, Tuple, NoReturn
from enum import Enum, unique
import re

import sys
sys.setrecursionlimit(100000)

import warnings
def _warning(message, *args, **kwargs):
    print(message)
warnings.showwarning = _warning

from ._exceptions import *
from . import _atoms

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
    NONE = 2

@dataclass
class ExprObject:
    objname: Token
    argvals: List['AstObject']

@dataclass
class DeclObject:
    argname: Token
    definition: 'AstObject'
    argvals: List['AstObject']

@dataclass
class AstObject:
    namespace: List[Token]
    obj_type: Literal[ObjType.EXPR, ObjType.DECL, ObjType.NONE]
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

    """
    Class used to represent a FloofBlock's definition (main block and macro blocks)

    ...

    Attributes
    ----------
    code : str
        Definition of block, in floof syntax.
    line : int
        Line number where the block was from
    namespace : List[Token]
        Contains all tokens that block can reference

    _tokens : List[Token]
        Tokens in `code`, initialised during `__init__`
    _ast : AstObject
        AST of `code`, initialised during `__init__`
    _compiled : Dict
        Cached compiled code, populated on `to_code` call.

    Methods
    -------
    from_ast(self, ast: AstObject) -> `FloofBlock`
        Initialises FloofBlock directly from AST

    to_code(self, target:Literal['floof', 'python'] = 'python') -> str
        Compiles FloofBlock into `target` ("floof" or "python")

    get_ast(self) -> AstObject
        Returns self._ast
    """

    def __init__(self, code:str, line:int, namespace:List[Token], _from_ast=False) -> NoReturn:

        """
        Parameters
        ----------
        code : str
            Definition of block, in floof syntax.
        line : int
            Line number where the block was from
        namespace : List[Token]
            Contains all tokens that block can reference
        _from_ast : optional (Default False)
            For internal use. Initialises FloofBlock from AstObject. Use `FloofBlock.from_ast` instead
        """

        self._compiled = {}

        if _from_ast:
            self._ast = _from_ast
            return

        self.code = code
        self.line = line
        self.namespace = namespace

        self._tokens = self._tokenize()
        self._ast = self._tokens_to_ast(self._tokens, self.namespace)

    @classmethod
    def from_ast(cls, ast:AstObject) -> 'FloofBlock':

        """Initialises FloofBlock directly from AstObject

        Parameters
        ----------
        ast : AstObject
            AstObject used to initialise FloofBlock

        Returns
        -------
        FloofBlock
            Initialised FloofBlock object
        """

        return cls(None, None, None, _from_ast = ast)

    def _tokenize(self) -> List[Token]:

        """Tokenizes self.code

        Returns
        -------
        List[Token]
            Tokens corresponding to self.code
        """
        
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
                    code_snippet = code[idx:min(len(code)-1, idx+10)]
                    raise FloofSyntaxError(line, "Invalid name `%s...`!"%code_snippet)
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
    def _get_bracket_pair(tokens:List[Token], start_idx:int) -> int:

        """Gets corresponding closing bracket

        Parameters
        ----------
        tokens : List[Token]
            Tokens to search for closing bracket
        start_idx : int
            Index into `tokens` that contains opening bracket

        Returns
        -------
        int
            Index into `tokens` that contains the closing braket
        """

        start_bracket = tokens[start_idx].obj_str
        if start_bracket not in '[(':
            raise FloofParseError("`get_bracket_pair` called with `%c` when looking for one of either `(` or `[`!"%start_bracket)

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

        """Parse floof syntax for calls (arg1)(arg2)...

        Parameters
        ----------
        namespace : List[Token]
            namespace as which the calls are in
        tokens : List[Token]
            tokens to parse the calls
        start_call_idx : int
            index into `tokens` that indicates start of call
            Either `start_call_idx` indexes beyond `tokens` or the token
            it indexes is `(`

        Returns
        -------
        List[AstObject]
            List of arguments [arg1, arg2, arg3...]
        """

        argvals = []

        while True:

            # End of tokens
            if len(tokens) == start_call_idx:
                break
            
            t = tokens[start_call_idx]
            if t.obj_str != '(':
                line = t.line
                raise FloofSyntaxError(line, "Unexpected token! Expected `(`, `%s` instead"%t.obj_str)
            
            end_call_idx = FloofBlock._get_bracket_pair(tokens, start_call_idx)
            if not end_call_idx:
                line = tokens[0].line
                raise FloofSyntaxError(line, "Unbalanced bracket `%c`!"%t.obj_str)

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

        """Converts tokens to AstObject
        
        Parameters
        ----------
        tokens : List[Token]
            Tokens to parse to AstObject
        namespace : List[Token]
            Namespace at which the tokens are in

        Returns
        -------
        AstObject
            AstObject of `tokens`
        """

        if len(tokens) == 0:
            return AstObject(
                namespace = namespace,
                obj_type = ObjType.NONE,
                obj = None
            )

        t = tokens[0]

        # Start of declaration object (DeclObject)
        if t.obj_str == '[':

            end_decl_idx = FloofBlock._get_bracket_pair(tokens, 0)
            if not end_decl_idx:
                line = tokens[0].line
                raise FloofSyntaxError(line, "Unbalanced bracket `%c`!"%t.obj_str)

            argname = tokens[1]
            def_tokens = tokens[3:end_decl_idx]

            if tokens[2].obj_str != ':':
                line = tokens[2].line
                raise FloofSyntaxError(line, "Invalid declaration! Expected `:` token! `%s` instead"%tokens[2].obj_str)

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
                raise FloofSyntaxError(t.line, "Name `%s` is not defined!"%t.obj_str)

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
            raise FloofSyntaxError(t.line, "Unexpected token! Expected `[` or an object name. Got `%s` instead"%t.obj_str)

    @staticmethod
    def _to_code(ast:AstObject, target:Literal['floof', 'python'] = 'python') -> str:

        """Converts AstObject to code

        Parameters
        ----------
        ast : AstObject
            AstObject to convert to code to
        target : Literal['floof', 'python'], optional (default 'python')
            Target to compile to

        Returns
        -------
        str
            String representing code of `target`
        """

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

        elif ast.obj_type==ObjType.NONE:
            code = ""

        else:
            raise FloofCompileError("Unexpected object type")

        return code

    def to_code(self, target:Literal['floof', 'python'] = 'python') -> str:

        """Compiles Floof program into `target` ("floof" or "python")

        Parameters
        ----------
        target : Literal['floof', 'python'], optional (default 'python')
            Target to compile to

        Returns
        -------
        str
            String representing code of `target`
        """

        if target not in self._compiled:
            self._compiled[target] = self._to_code(self._ast, target)
        return self._compiled[target]

    def get_ast(self) -> AstObject:

        """Gets self._ast

        Returns
        -------
        AstObject
            self._ast
        """

        return self._ast

class Floof:

    """
    Class used to represent a Floof program

    ...

    Attributes
    ----------
    code : str
        Floof program code
    _mainblock : FloofBlock
        FloofBlock that represents the whole program. Initialised during __init__
    _compiled : Dict
        Cached compiled code, populated on `to_code` call.
        

    Methods
    -------
    to_code(self, target:Literal['floof', 'python'] = 'python') -> str
        Compiles Floof program into `target` ("floof" or "python")
    run(self) -> NoReturn
        Runs floof program
    """

    def __init__(self, code:str) -> NoReturn:

        """
        Parameters
        ----------
        code : str
            Floof program code
        """

        self.code = code
        self._mainblock = self._to_FloofBlock(code)
        self._compiled = {}

    @staticmethod
    def _parse_macro(lines:List[str], line_idx:int, namespace:List[Token]) -> Tuple[Token, FloofBlock, int]:

        """Parses macro

        Parameters
        ----------
        lines : List[str]
            lines of code that contains macro
            macro name has to be in the first line (lines[0])
        line_idx : int
            line index at which this macro is in the original Floof program
        namespace : List[Token]
            Contains all tokens that this macro can reference

        Returns
        -------
        Tuple[Token, FloofBlock, int]
            Token: Token that represents the name of the macro
            FloofBlock: FloofBlock that contains macro definition
            int: last line of macro
        """

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
                raise FloofSyntaxError(idx+1, "Main definition within macro not allowed")
            macro_def += l+"\n"

        if not macro_name:
            raise FloofSyntaxError(idx+1, "No name given to macro")

        if not re.match("^%s$"%VALID_NAME_REGEX, macro_name):
            raise FloofSyntaxError(idx+1, "Macro name `%s` invalid"%macro_name)

        if not l or l[0] != '~':
            raise FloofSyntaxError(idx+1, "Macro `%s` terminator not found"%macro_name)

        macro_name = Token(macro_name, line_idx+1, -1, True)
        macro_block = FloofBlock(macro_def, line_idx+2, namespace)
        if macro_block.get_ast().obj_type == ObjType.NONE:
            raise FloofSyntaxError(idx+1, "Macro `%s` is empty"%macro_name.obj_str)

        end_line_idx = j+idx+2

        return macro_name, macro_block, end_line_idx

    @staticmethod
    def _parse_main(lines:List[str], line_idx:int, namespace:List[Token]) -> Tuple[FloofBlock, int]:

        """Parses main block

        Parameters
        ----------
        lines : List[str]
            lines of code that contains main
            the token `!` has to be in the first line (lines[0])
        line_idx : int
            line index at which the main block is in the original Floof program
        namespace : List[Token]
            Contains all tokens that this main block can reference

        Returns
        -------
        Tuple[FloofBlock, int]
            FloofBlock: FloofBlock that contains main definition
            int: last line of main
        """

        idx = line_idx
        main = ""
        for j,l in enumerate(lines[idx+1:]):
            if not l:
                main += "\n"
                continue
            if l[0]=='~':
                break
            if l[0]=='#':
                raise FloofSyntaxError(idx+1, "Macro definition within main not allowed")
            main += l+"\n"

        if not l or l[0] != '~':
            raise FloofSyntaxError(idx+1, "Main terminator not found")

        main_block = FloofBlock(main, line_idx+2, namespace)
        if main_block.get_ast().obj_type == ObjType.NONE:
            raise FloofSyntaxError(idx+1, "Main is empty")

        return main_block, j+idx+2

    @staticmethod
    def _search_macro(ast:AstObject, macro_name:str) -> bool:
        
        """Searches for macro in ast

        Parameters
        ----------
        ast : AstObject
            Ast to search macro in
        macro_name : str
            Name of macro to search for

        Returns
        -------
        bool
            True if macro is found in ast. False o.w.
        """

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

        elif ast.obj_type == ObjType.NONE:
            return False
        
        else:
            raise FloofCompileError("Unexpected ObjType")

    @staticmethod
    def _to_FloofBlock(code:str) -> FloofBlock:

        """Converts Floof program into a FloofBlock

        Parameters
        ----------
        code : str
            The floof program

        Returns
        -------
        FloofBlock
            FloofBlock that represents the floof program
        """

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
        end_idx = 0
        for idx,line in enumerate(lines):

            if not line: continue

            if line[0] == '#':

                name, macro, end_idx = Floof._parse_macro(lines, idx, namespace)
                if name.obj_str in [n.obj_str for n,_ in macros]:
                    raise FloofSyntaxError(idx+1, "Macro `%s` has been defined more than once."%name.obj_str)
                
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
            raise FloofSyntaxError(-1, "No main found")

        # Create AST for full program
        main_ast = main.get_ast()
        main_namespace = main_ast.namespace

        for name, macro in macros[::-1]:

            main_namespace = [t for t in main_namespace if t.obj_str != name.obj_str]

            if not Floof._search_macro(main_ast, name.obj_str):
                warnings.warn("[WARNING] Line %d: Macro `%s` is not used"%(name.line, name.obj_str))
                continue

            main_ast = AstObject(
                namespace = main_namespace,
                obj_type = ObjType.DECL,
                obj = DeclObject(
                    argname = name,
                    definition = main_ast,
                    argvals = [macro.get_ast()]
                )
            )

        return FloofBlock.from_ast(main_ast)

    def to_code(self, target:Literal['floof', 'python'] = 'python') -> str:

        """Compiles Floof program into `target` ("floof" or "python")

        Parameters
        ----------
        target : Literal['floof', 'python'], optional (default 'python')
            Target to compile to

        Returns
        -------
        str
            String representing code of `target`
        """

        if target not in self._compiled:
            self._compiled[target] = self._mainblock.to_code(target)
        return self._compiled[target]

    def run(self) -> NoReturn:

        """Runs floof program"""

        globals_sandbox = {}
        for a in dir(_atoms):
            if a[0] != '_': # An atom
                globals_sandbox["_%s_"%a] = getattr(_atoms, a)

        eval(self.to_code(), globals_sandbox, {})