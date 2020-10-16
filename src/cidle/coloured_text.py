import os
BASEPATH = os.path.dirname(__file__)

def get_keywords():
    return read_file("/kws.def")

def get_builtins():
    return read_file("/builtins.def")

def read_file(filename):
    with open(BASEPATH+filename, "r") as file:
        data = file.read()
    data = data.split("\n")
    while "" in data:
        data.remove("")
    return data


if __name__ == "__main__":
    print("All of the key words are: "+str(get_keywords()))
    print()
    print("All of the builtins are: "+str(get_builtins()))
