from ._floof import Floof
from ._exceptions import *
import argparse

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", required=True, type=str, help="filename to run")
    parser.add_argument("-v", "--verbose", type=bool, help="print intermediate steps in compilation")
    args = parser.parse_args()
    filename = args.file
    verbose = args.verbose
    code = open(filename).read()

    try:
        floof = Floof(code)
        if verbose:
            print("FLOOF MIN:")
            print(floof.to_code(target='floof'))
            print()
            print("PYTHON:")
            print(floof.to_code(target='python'))
            print()

        floof.run()
    except (FloofParseError, FloofCompileError, FloofSyntaxError, FloofRuntimeError) as e:
        print(e)

main()