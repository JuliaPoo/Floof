# Floof

_Floof_ is a minimal programming language comprised entirely of one object type: `T ::= T -> T`, or in other words, the only object type in _Floof_ is a function of type `T`, whose input and output is also of type `T`. The exception to this are the reserved functions that take in user input, which has no arguments, and the reserved functions that prints, which has side effects.

## Introduction

### Function Definitions

A function in _Floof_ consists of an `argument_name` and a `definition`. The syntax is as follows:

```
[argument_name:definition]
```

The function can then be called as such:

```
[argument_name:definition](argument)
```

Examples:

```
[f:f]                   ; Identity function
[f:[x:f(f(x))]](g)(y)   ; Equivalent to g(g(y))
```

### Literals Representation

The only literals in _Floof_ are nonnegative integers and implemented as special functions of type `T`. The integer `n` is implemented as a function that takes in a function `f` and an object `x` and returns `f^n(x)`.

Examples:

```
[f:[x:x]]         ; Represents the literal `0`
[f:[x:f(x)]]      ; Represents the literal `1`
[f:[x:f(f(x))]]   ; Represents the literal `2`
```

### Input and Output

_Floof_ takes in either integers or char, and can output (print) in either integer or char. Several reserved names are used for these:

```
_IN_INT_()      ; Waits for user to input a non-negative
                ; integer and returns it in the representation
                ; mentioned above
                
_IN_CHR_()      ; Waits for user to input a character and
                ; returns an integer representing the Unicode 
                ; code point of that character, in the 
                ; representation mentioned above

_OUT_INT_(arg)  ; Prints the integer represented by `arg` of 
                ; type `T`. Returns `arg`.

_OUT_CHAR_(arg) ; Prints a char in the Unicode code indexed by the
                ; integer represented by `arg` of type `T`
                ; Returns `arg`.
```

Examples:

```
_OUT_INT_(
    [f:[x:x]]
)                       ; Prints `1`
```

```
_OUT_CHAR_(
    _IN_CHAR_()
)                       ; Waits for user to input a character and echos it out
```

### Comments

Comments start with a `;`. Everything in a line after a `;` is ignored and treated as a comment.

### Program Format

A _Floof_ program consists of several macro _blocks_ and a main _block_. Each _block_ starts with either a `#` or a `!` and ends with a `~`. Each _block_ can contain only one expression.

#### Macro _blocks_

Macro _blocks_ are meant to modularise the program. Once defined, they can be used further down in the program. Macro blocks cannot reference themselves. They have the following format:

```
#<macro_name>
<macro_definition>
~
```

`macro_name` must follow these conditions:
1. Start with a letter or the underscore character.
2. Cannot start with a number.
3. Can only contain alpha-numeric characters and underscores (A-z, 0-9, and _)
4. Case-sensitive (age, Age and AGE are three different variables)

`macro_definition` must consist of a single expression.

Macros are also defined top down. A macro cannot reference a macro below it in a file. 

Examples:

```
#N0     ; Represents the integer 0
[f:[x:x]]
~

#INC    ; INC(a) computes a+1
[n:
    [f:
        [x:
            f(n(f)(x))
        ]
    ]
]
~

#N1     ; Represents the integer 1
INC(N0) ; Used the above macros
~

#N2     ; Represents the integer 2
INC(N1)
~
```

#### Main _block_

Each _Floof_ program can only contain one main _block_. The main _block_ is what the interpreter will run. Any macros that the main _block_ uses must be defined above it. They have the following format:

```
!
<main_definition>
~
```

`main_definition` must consist of a single expression.

Examples:

```
!       ; Prints `1`
_OUT_INT_(
    [f:[x:x]]
)
~
```

```
#N1     ; Represents the integer 1
[f:[x:f(x)]]
~

#INC    ; INC(a) computes a+1
[n:
    [f:
        [x:
            f(n(f)(x))
        ]
    ]
]
~

!       ; Prints `2`
_OUT_INT_(
    INC(N1)
)
~ 
```

### Running a _Floof_ program

This repository contains a python3 interpreter. Run:

```sh
python -m floof -f <filename>
```

An additional `-v` flag can be given to make the interpreter output intermediate representations of the _Floof_ program.

Try running _Floof_ programs in the folder [./examples](./examples).

## Tips

You can build data structures with just type `T`s! Abstract it out! You might wanna take a look at [./examples](./examples) for examples.

[Programming with Nothing](https://codon.com/programming-with-nothing) by Tom Stuart can get you started on some possible constructions.


## Credits Due

I got the idea for this programming language from reading [Tom Stuart](https://codon.com/programming-with-nothing). Do check him out!
