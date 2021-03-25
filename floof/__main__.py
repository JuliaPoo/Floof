from ._floof import run
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", required=True, type=str, help="filename to run")
    parser.add_argument("-v", "--verbose", type=bool, help="print intermediate steps in compilation")
    args = parser.parse_args()
    filename = args.file
    verbose = args.verbose
    code = open(filename).read()
    run(code, verbose=verbose)

main()