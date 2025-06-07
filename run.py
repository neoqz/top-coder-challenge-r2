import sys
import calculate

if __name__ == "__main__":
    args = list(map(float, sys.argv[1:]))
    print(calculate.calculate(*args))

