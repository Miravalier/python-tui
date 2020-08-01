import ansi
import os
import sys
import termios
from contextlib import contextmanager
from fcntl import fcntl, F_GETFL, F_SETFL
from utils import printf


@contextmanager
def raw_mode():
    # Save screen buffer
    printf(ansi.SAVE_CURSOR, ansi.ALTERNATE_SCREEN, ansi.POSITION_CURSOR(1, 1))
    # Save attributes
    original_attributes = termios.tcgetattr(sys.stdin)
    # Set mode to non-canonical
    modified_attributes = list(original_attributes)
    modified_attributes[3] &= ~(termios.ECHO | termios.ICANON)
    termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, modified_attributes)
    try:
        yield None
    finally:
        # Revert attributes
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, original_attributes)
        # Reset screen buffer
        printf(ansi.RESTORE_SCREEN, ansi.LOAD_CURSOR)


@contextmanager
def nonblocking_mode():
    fd = sys.stdin.fileno()
    original_flags = fcntl(fd, F_GETFL)
    fcntl(fd, F_SETFL, original_flags | os.O_NONBLOCK)
    try:
        yield None
    finally:
        fcntl(fd, F_SETFL, original_flags)
