import sys as _sys

_N0 = lambda f: lambda x: x
_N1 = lambda f: lambda x: f(x)
_N2 = lambda f: lambda x: f(f(x))

_INC = lambda n: lambda f: lambda x: f(n(f)(x))
_ADD = lambda a: lambda b: b(_INC)(a)

def _in_int(n:int):
    if n in [0,1]:
        return [_N0, _N1][n]
    if n&1:
        return _INC(_in_int(n-1))
    n_f = _in_int(n//2)
    return _ADD(n_f)(n_f)

def IN_INT():
    n = int(input())
    return _in_int(n)

def IN_CHAR():
    n = ord(_sys.stdin.read(1))
    return _in_int(n)   

def OUT_INT(arg):
    print(arg(lambda n:n+1)(0), end="")
    return arg

def OUT_CHAR(arg):
    print(chr(arg(lambda n:n+1)(0)), end="")
    return arg