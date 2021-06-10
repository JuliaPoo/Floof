from dataclasses import dataclass
from typing import List, Literal, Union, Tuple, NoReturn
from enum import Enum, unique
import re

import sys
sys.setrecursionlimit(2000)

import warnings
def _warning(message, *args, **kwargs):
    print(message)
warnings.showwarning = _warning

from ._exceptions import *
from . import _atoms

@unique
class NodeType(Enum):
    DECL = 0 # Expression
    CALL = 1 # Calls a function
    NONE = 2 # Empty node

@dataclass
class Token:

    obj_str: str
    line: int
    is_name: bool

    def __str__(self):
        return self.obj_str

@dataclass
class Node:
    type: NodeType
    childs: Tuple['Node', Token]

    @staticmethod
    def _to_str(node: 'Node', template, minimise:bool=False) -> str:

        if type(node) is Token:
            return str(node)

        ntype = node.type
        if ntype == NodeType.DECL:
            argname, defi = node.childs
            return template%(argname, Node._to_str(defi, template, minimise))

        elif ntype == NodeType.CALL:
            A,B = node.childs
            A = Node._to_str(A, template, minimise)
            if minimise:
                return str(A) + (str(B) if type(B) is Token else "(%s)"%Node._to_str(B, template, minimise))
            return str(A) + "(%s)"%Node._to_str(B, template, minimise)

        elif ntype == NodeType.NONE:
            return ""

        else:
            raise FloofParseError("Unknown NodeType!")

    def to_str(self, minimise:bool=False, target:Literal['python', 'floof'] = 'floof') -> str:

        template = {
            "floof": "[%s:%s]",
            "python": "(lambda %s: %s)"
        }[target]
        if target == 'python':
            minimise = False

        return self._to_str(self, template, minimise)

    def __str__(self):
        return self.to_str(self)

VALID_NAME_REGEX = r"[a-zA-Z_][a-zA-Z0-9_]*"

ATOMS = [
    Token('_OUT_CHAR_', -1, True),
    Token('_IN_CHAR_', -1, True),
    Token('_OUT_INT_', -1, True),
    Token('_IN_INT_', -1, True)
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
    _ast : Node
        AST of `code`, initialised during `__init__`

    Methods
    -------
    from_ast(self, ast: Node) -> `FloofBlock`
        Initialises FloofBlock directly from AST

    to_code(self, target:Literal['floof', 'python'] = 'python') -> str
        Compiles FloofBlock into `target` ("floof" or "python")

    get_ast(self) -> Node
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
        """

        if _from_ast:
            self._ast = _from_ast
            return

        self.code = code
        self.line = line
        self.namespace = namespace

        self._tokens = self._tokenize()
        self._ast = self._tokens_to_ast(self._tokens, self.namespace)

    @classmethod
    def from_ast(cls, ast:Node) -> 'FloofBlock':

        """Initialises FloofBlock directly from Node

        Parameters
        ----------
        ast : Node
            Node used to initialise FloofBlock

        Returns
        -------
        FloofBlock
            Initialised FloofBlock object
        """
        return cls("", 0, [], _from_ast=ast)

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
            if re.match(r'^\s$', c):
                if c == '\n': line += 1

            elif c in '[]():':
                tokens.append(
                    Token(
                        obj_str = c,
                        line = line,
                        is_name = False
                    ))

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
                        is_name = True
                    ))
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

        start_bracket = str(tokens[start_idx])
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
            if str(c)==start_bracket:
                depth += 1
            if str(c)==end_bracket:
                if depth == 0:
                    return offset+start_idx
                depth -= 1

        t = tokens[start_idx]
        raise FloofSyntaxError(t.line, "Unbalanced bracket `%s`."%t)
        #return None

    @staticmethod
    def _tokens_to_ast(tokens:List[Token], namespace:List[Token]) -> Node:

        """Converts tokens to Node
        
        Parameters
        ----------
        tokens : List[Token]
            Tokens to parse to ast
        namespace : List[Token]
            Namespace at which the tokens are in

        Returns
        -------
        Node
            Ast of `tokens`
        """

        if len(tokens) == 0:
            return Node(NodeType.NONE, ())

        t0 = tokens[0]
        ns_str = [str(i) for i in namespace]

        if t0.is_name:

            if str(t0) not in ns_str:
                raise FloofSyntaxError(t0.line, "Name `%s` is not defined!"%t0)

            if len(tokens) == 1:
                return t0

            t1 = tokens[1]
            if str(t1) != "(":
                raise FloofSyntaxError(t1.line, "Unexpected token `%s`. Expected `(`."%t1)

            end_idx = FloofBlock._get_bracket_pair(tokens, 1)
            n_tokens = tokens[2:end_idx]

            node = Node(NodeType.CALL, (
                t0, FloofBlock._tokens_to_ast(n_tokens, namespace)
            ))

        elif str(t0) == '(':

            end_idx = FloofBlock._get_bracket_pair(tokens, 0)
            n_tokens = tokens[1:end_idx]

            node = FloofBlock._tokens_to_ast(n_tokens, namespace)

        elif str(t0) == '[':

            if len(tokens) < 5:
                raise FloofSyntaxError(t0.line, "Incomplete function declaration!")

            t1 = tokens[1]
            if not t1.is_name:
                raise FloofSyntaxError(t1.line, "Unexpected token `%s`. Expected a name"%t1)
            
            t2 = tokens[2]
            if str(t2) != ':':
                raise FloofSyntaxError(t2.line, "Unexpected token `%s`. Expected `:` instead"%t2)

            end_idx = FloofBlock._get_bracket_pair(tokens, 0)
            n_tokens = tokens[3:end_idx]
            n_namespace = namespace[:] + [t1]

            node = Node(NodeType.DECL, (
                t1, FloofBlock._tokens_to_ast(n_tokens, n_namespace)
            ))

        else:
            raise FloofSyntaxError(t0.line, "Unexpected token `%s`. Expected `(`, `[` or a name"%t0)

        while end_idx != len(tokens)-1:
            tmp = end_idx
            t = tokens[tmp+1]
            if str(t) != '(':
                raise FloofSyntaxError(t.line, "Unexpected token `%s`. Expected `(` instead"%t)
            end_idx = FloofBlock._get_bracket_pair(tokens, tmp+1)
            n_tokens = tokens[tmp+2: end_idx]
            node = Node(NodeType.CALL, (
                node, FloofBlock._tokens_to_ast(n_tokens, namespace)
            ))

        return node

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

        return self._ast.to_str(target=target)

    def get_ast(self) -> Node:

        """Gets self._ast

        Returns
        -------
        Node
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

        macro_name = Token(macro_name, line_idx+1, True)
        macro_block = FloofBlock(macro_def, line_idx+2, namespace)
        ast = macro_block.get_ast()
        
        if type(ast) != Token and ast.type == NodeType.NONE:
            raise FloofSyntaxError(idx+1, "Macro `%s` is empty"%macro_name)

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
        ast = main_block.get_ast()
        
        if type(ast) != Token and ast.type == NodeType.NONE:
            raise FloofSyntaxError(idx+1, "Main is empty")

        return main_block, j+idx+2

    @staticmethod
    def _search_macro(ast:Union[Node, Token], macro_name:str, namespace:List[Token]) -> bool:
        
        """Searches for macro in ast

        Parameters
        ----------
        ast : Union[Node, Token]
            Ast to search macro in
        macro_name : str
            Name of macro to search for

        Returns
        -------
        bool
            True if macro is found in ast. False o.w.
        """
        
        if type(ast) == Token:
            return str(ast) == macro_name

        if ast.type == NodeType.NONE:
            return False

        namespace_str = [str(t) for t in namespace]
        if macro_name not in namespace_str:
            return False

        a,b = ast.childs
        
        if ast.type==NodeType.DECL:
            if str(a) == macro_name:
                return False
            return Floof._search_macro(b, macro_name, namespace[:] + [a])

        elif ast.type==NodeType.CALL:
            ret  = Floof._search_macro(a, macro_name, namespace)
            ret |= Floof._search_macro(b, macro_name, namespace)
            return ret

        else:
            raise FloofParseError("Unexpected NodeType!")


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
                if str(name) in [str(n) for n,_ in macros]:
                    raise FloofSyntaxError(idx+1, "Macro `%s` has been defined more than once."%name)
                
                macros.append((name, macro))
                namespace.append(name)
                continue

            if line[0] == '!':
                main, end_idx = Floof._parse_main(lines, idx, namespace)
                break

        if len(lines) >= end_idx:
            leftovers = "\n".join(lines[end_idx:])
            if not re.match(r"^\s*$", leftovers):
                warnings.warn("[WARNING] Code after line %d is ignored!"%end_idx)

        # Check if main was never found
        if not main:
            raise FloofSyntaxError(-1, "No main found")

        # Create AST for full program
        main_ast = main.get_ast()
        main_namespace = namespace

        for name, macro in macros[::-1]:

            if not Floof._search_macro(main_ast, str(name), main_namespace):
                warnings.warn("[WARNING] Line %d: Macro `%s` is not used"%(name.line, str(name)))
                continue

            main_namespace = [t for t in main_namespace if str(t) != str(name)]

            main_ast = Node(
                type = NodeType.CALL,
                childs = (
                    Node(type = NodeType.DECL, childs = (name, main_ast)), 
                    macro.get_ast()))

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
        code = self._mainblock.to_code(target)
        return code

    def run(self) -> NoReturn:

        """Runs floof program"""

        globals_sandbox = {}
        for a in dir(_atoms):
            if a[0] != '_': # An atom
                globals_sandbox["_%s_"%a] = getattr(_atoms, a)

        try:
            eval(self.to_code(), globals_sandbox, {})
        except Exception as e:
            raise FloofRuntimeError(e.args[0]) from e
