"""
Takes 1 command line argument and prints it out without a newline
"""
import sys
if len(sys.argv) != 2:
    print("Expected only 1 argument")
    sys.exit(1)
print(end=sys.argv[1])