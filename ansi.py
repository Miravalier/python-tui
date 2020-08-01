SGR_RESET = '\x1B[m'
SGR_REVERSE = '\x1B[7m'

FG_BLACK = '\x1B[30m'
FG_RED = '\x1B[31m'
FG_GREEN = '\x1B[32m'
FG_YELLOW = '\x1B[33m'
FG_BLUE = '\x1B[34m'
FG_MAGENTA = '\x1B[35m'
FG_CYAN = '\x1B[36m'
FG_WHITE = '\x1B[37m'

BG_BLACK = '\x1B[40m'
BG_RED = '\x1B[41m'
BG_GREEN = '\x1B[42m'
BG_YELLOW = '\x1B[43m'
BG_BLUE = '\x1B[44m'
BG_MAGENTA = '\x1B[45m'
BG_CYAN = '\x1B[46m'
BG_WHITE = '\x1B[47m'

FG_BRIGHT_BLACK = '\x1B[90m'
FG_BRIGHT_RED = '\x1B[91m'
FG_BRIGHT_GREEN = '\x1B[92m'
FG_BRIGHT_YELLOW = '\x1B[93m'
FG_BRIGHT_BLUE = '\x1B[94m'
FG_BRIGHT_MAGENTA = '\x1B[95m'
FG_BRIGHT_CYAN = '\x1B[96m'
FG_BRIGHT_WHITE = '\x1B[97m'

BG_BRIGHT_BLACK = '\x1B[100m'
BG_BRIGHT_RED = '\x1B[101m'
BG_BRIGHT_GREEN = '\x1B[102m'
BG_BRIGHT_YELLOW = '\x1B[103m'
BG_BRIGHT_BLUE = '\x1B[104m'
BG_BRIGHT_MAGENTA = '\x1B[105m'
BG_BRIGHT_CYAN = '\x1B[106m'
BG_BRIGHT_WHITE = '\x1B[107m'

SAVE_CURSOR = '\x1B[s'
LOAD_CURSOR = '\x1B[u'
SHOW_CURSOR = '\x1B[?25h'
HIDE_CURSOR = '\x1B[?25l'

CLEAR_SCREEN = '\x1B[2J'
ALTERNATE_SCREEN = '\x1B[?1049h'
RESTORE_SCREEN = '\x1B[?1049l'

def FG_RGB(red, green, blue):
    return '\x1B[38;2;{};{};{}m'.format(red, green, blue)

def BG_RGB(red, green, blue):
    return '\x1B[48;2;{};{};{}m'.format(red, green, blue)

def POSITION_CURSOR(row, column):
    return '\x1B[{};{}H'.format(row, column)
