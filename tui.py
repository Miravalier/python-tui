#!/usr/bin/env python3.8
import math
import terminal
import shutil
import sys
from ansi import *
from collections import deque
from utils import printf


class Application:
    translation_table = str.maketrans('\n\t', '  ')

    def __init__(self, *, message_history=1024, command_history=1024, prompt=' > '):
        self._messages = deque(maxlen=message_history)
        self._commands = deque(maxlen=command_history)
        self.prompt = prompt
        self.update_dimensions()

    ##################
    # Public Methods #
    ##################

    def clear(self):
        self._messages.clear()

    def print(self, *parts, sep=' ', end=''):
        # Construct the separator and end string
        sep = self.construct_part(sep)
        end = self.construct_part(end)
        # Assemble the message
        message = []
        for i in range(len(parts)-1):
            message.append(self.construct_part(parts[i]))
            message.append(sep)
        if parts:
            message.append(self.construct_part(parts[-1]))
        message.append(end)
        # Append the message to the deque
        self._messages.appendleft(message)
        # Re-render all messages
        self.update_dimensions()
        self._render_messages()

    def run(self):
        try:
            with terminal.raw_mode():
                while True:
                    self._render_prompt()
                    character = sys.stdin.read(1)
                    self.print(repr(character))
        except (KeyboardInterrupt, EOFError):
            pass

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

    def row_length(self, message):
        return math.ceil(sum(len(part) for part, attributes in message) / self.columns)

    def construct_part(self, part):
        part = part.translate(self.translation_table)
        if isinstance(part, str):
            return (part, None)
        else:
            return part

    def update_dimensions(self):
        columns, rows = shutil.get_terminal_size()
        self.columns = columns
        self.rows = rows

    def _render_messages(self):
        # Hide cursor
        printf(HIDE_CURSOR)
        # Start cursor on the prompt row
        current_row = self.rows
        for message in self._messages:
            # Calculate how many rows will be needed for this message
            current_row -= self.row_length(message)
            # Stop once we reach the top of the terminal
            if current_row < 1:
                break
            # Print the message into the terminal
            printf(POSITION_CURSOR(current_row, 1))
            columns_written = 0
            for part, attributes in message:
                if not part:
                    continue
                if attributes:
                    printf(attributes, part, SGR_RESET)
                else:
                    printf(part)
                columns_written += len(part)
            printf(' ' * (columns_written % self.columns))
        # Show Cursor
        printf(SHOW_CURSOR)

    def _render_prompt(self):
        # Move cursor to the prompt row, display prompt
        printf(POSITION_CURSOR(self.rows, 1), self.prompt)


if __name__ == '__main__':
    Application().run()
