import sys as _sys

N0 = lambda f: lambda x: x
N1 = lambda f: lambda x: f(x)
N2 = lambda f: lambda x: f(f(x))
N3 = lambda f: lambda x: f(f(f(x)))
N4 = lambda f: lambda x: f(f(f(f(x))))
N5 = lambda f: lambda x: f(f(f(f(f(x)))))

INC = lambda n: lambda f: lambda x: f(n(f)(x))
ADD = lambda a: lambda b: b(INC)(a)
MUL = lambda a: lambda b: b(lambda y: ADD(y)(a))(N0)

def IN_INT():

    def recurse(n:int):
        if n in [0,1]:
            return [N0, N1][n]
        if n&1:
            return ADD(N1)(recurse(n-1))
        return MUL(N2)(recurse(n//2))

    n = int(input())
    return recurse(n)

def IN_CHAR():

    def recurse(n:int):
        if n in [0,1]:
            return [N0, N1][n]
        if n&1:
            return ADD(N1)(recurse(n-1))
        return MUL(N2)(recurse(n//2))

    n = ord(_sys.stdin.read(1))
    return recurse(n)   

def OUT_INT(arg):
    print(arg(lambda n:n+1)(0), end="")
    return arg

def OUT_CHAR(arg):
    print(chr(arg(lambda n:n+1)(0)), end="")
    return arg