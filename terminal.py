#!/usr/bin/env python3.8
import modes
import shutil
import sys
from ansi import *
from collections import deque
from utils import printf


class Terminal:
    def __init__(self, *, message_history=1024, command_history=1024, sgr_enabled=True):
        self._sgr_enabled = sgr_enabled
        self._messages = deque(maxlen=message_history)
        self._commands = deque(maxlen=command_history)

    ##################
    # Public Methods #
    ##################

    def clear(self):
        self._messages.clear()

    def write(self, *message):
        for part in message:
            if isinstance(part, str):
                self._add_str(part)
            else:
                self._add_str(*part)

    def run(self):
        with modes.raw_mode():
            self._render_messages()
            self._render_prompt()
            while True:
                character = sys.stdin.read(1)
                printf(repr(character))

    ####################
    # Abstract Methods #
    ####################

    def on_command(self, args):
        pass

    def on_tab(self, args):
        pass

    ####################
    # Internal Methods #
    ####################

    def _add_str(self, text, attributes=None):
        self._messages.appendleft((text, attributes if self._sgr_enabled else None))

    def _render_messages(self):
        columns, rows = shutil.get_terminal_size()
        print("Cols:", columns, "Rows:", rows)

    def _render_prompt(self):
        pass


if __name__ == '__main__':
    Terminal().run()
