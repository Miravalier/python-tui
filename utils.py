import sys
from functools import partial

_print = partial(print, sep='', end='')

def printf(*args, **kwargs):
    _print(*args, **kwargs)
    sys.stdout.flush()
