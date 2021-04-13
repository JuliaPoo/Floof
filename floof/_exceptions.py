class FloofSyntaxError(Exception):

    """Exception raised for syntax errors in Floof program"""

    def __init__(self, line:int, msg:str):

        """
        Parameters
        ----------
        line : int
            Line number of error
        msg : str
            Explanation of error
        """

        line_str = "??" if line==-1 else str(line)
        super().__init__("Syntax error! Line %s: %s"%(line_str, msg))

class FloofCompileError(Exception):

    """Exception raised for errors within the compiler"""

    def __init__(self, msg:str):
        super().__init__("Compile error! %s"%msg)

class FloofParseError(Exception):

    """Exception raised for errors within the parser"""

    def __init__(self, msg:str):
        super().__init__("Parse error! %s"%msg)

class FloofRuntimeError(Exception):

    """Exception raised for errors during runtime"""

    def __init__(self, msg:str):
        super().__init__("Floof Runtime error! %s"%msg)