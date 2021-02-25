KEY_WORDS = ("const", "consteval", "constexpr", "constinit", "const_cast",
             "wchar_t", "nullptr", "static", "virtual", "alignas", "alignof",
             "and", "and_eq", "asm", "auto", "bitand", "bitor", "bool",
             "break", "case", "catch", "char", "char8_t", "char16_t",
             "char32_t", "class", "continue", "enum", "explicit", "inline",
             "int", "long", "mutable", "namespace", "new", "default",
             "delete", "do", "double", "else", "export", "extern", "false",
             "float", "for", "friend", "goto", "if", "not", "not_eq", "or",
             "or_eq", "and", "and_eq", "xor", "xor_eq", "public", "private",
             "protected", "return", "short", "signed", "while", "void",
             "union", "unsigned", "typedef", "throw", "true", "try",
             "template", "this", "struct", "switch", "using", "string")


BUILTINS = ("cin", "cout", "cerr", "clog", "wcin", "wcout", "wcerr",
            "wclog", "static_assert", "static_cast", "reinterpret_cast",
            "dynamic_cast", "sizeof")


def get_keywords():
    return KEY_WORDS

def get_builtins():
    return BUILTINS

BUILTINS_COLOUR = "pink"
KEY_WORDS_COLOUR = "orange"
COMMENTS_COLOUR = "red"
STRINGS_COLOUR = "light green"
INCLUDE_COLOUR = "light blue"
