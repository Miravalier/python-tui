#!/usr/bin/env python3.8
import math
import terminal
import shlex
import shutil
import sys
from ansi import *
from collections import deque
from utils import printf
from select import select


class Application:
    translation_table = str.maketrans('\n\t', '  ')

    def __init__(self, *, message_history=1024, command_history=1024, prompt=' > '):
        self.messages = deque(maxlen=message_history)
        self.commands = deque(maxlen=command_history)
        self.prompt = prompt
        self.update_dimensions()
        self.queued_keys = []
        self.command_keys = []

    @property
    def command_string(self):
        return ''.join(self.command_keys)

    @property
    def command_args(self):
        return shlex.split(self.command_string)

    ##################
    # Public Methods #
    ##################

    def clear(self):
        self.messages.clear()

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
        self.messages.appendleft(message)
        # Re-render all messages
        self.update_dimensions()
        self.render_messages()

    def run(self):
        try:
            with terminal.raw_mode():
                while True:
                    self.render_prompt()
                    self.on_keypress(self.getkey())
        except (KeyboardInterrupt, EOFError):
            pass

    def getkey(self):
        if self.queued_keys:
            key = self.queued_keys.pop()
        else:
            try:
                key = sys.stdin.read(1)
            except KeyboardInterrupt:
                #return 'SIGINT'
                raise

        # If an escape key is pressed
        if key == ESCAPE_KEY:
            with terminal.nonblocking_mode():
                key = sys.stdin.read(1)
            # If no key is waiting, return escape
            if not key:
                return 'ESCAPE'
            # If the next key is a [, this is a CSI
            if key == '[':
                with terminal.nonblocking_mode():
                    key = sys.stdin.read(1)
                # If no key is waiting after CSI, return None
                if not key:
                    return None
                try:
                    key = ANSI_CONTROL_SEQUENCES[key]
                except KeyError:
                    key = "Unrecognized Code '{}'".format(key)
                with terminal.nonblocking_mode():
                    while sys.stdin.read(1): pass
                return key
            # If this is not a CSI, the next key goes back on the stack
            else:
                self.queued_keys.append(key)
                return 'ESCAPE'
        else:
            return key

    def on_keypress(self, key):
        # On enter, run on_command and clear the command
        if key == '\n':
            try:
                args = self.command_args
            except ValueError as e:
                self.print(('error:', FG_RED), e)
                self.command_keys = []
                return
            self.on_command(args)
            self.command_keys = []
        # On tab, run on_tab
        elif key == '\t':
            try:
                args = self.command_args
            except ValueError as e:
                return
            self.on_tab(args)
        # On backspace, pop a character
        elif key == '\x7F':
            try:
                self.command_keys.pop()
            except IndexError:
                pass
        # On CTRL+C, clear the current command
        elif key == 'SIGINT':
            self.command_keys = []
        # On any other key, add it to the current command
        else:
            self.command_keys.append(key)

    ####################
    # Abstract Methods #
    ####################

    def on_command(self, args):
        # If no args were entered, print an empty line
        if not args:
            return
        # All commands are unrecognized by default
        self.print("Unrecognized command {}".format(repr(args[0])))

    def on_tab(self, args):
        pass

    ####################
    # Internal Methods #
    ####################

    def row_length(self, message):
        return math.ceil(sum(len(part) for part, attributes in message) / self.columns)

    def construct_part(self, part):
        if isinstance(part, (tuple, list)):
            if len(part) != 2:
                raise TypeError("print requires strings or (string, attribute) tuples")
            return (self.construct_string(part[0]), part[1])
        else:
            return (self.construct_string(part), None)

    def construct_string(self, value):
        return str(value).translate(self.translation_table)

    def update_dimensions(self):
        columns, rows = shutil.get_terminal_size()
        self.columns = columns
        self.rows = rows

    def render_messages(self):
        # Hide cursor
        printf(HIDE_CURSOR)
        # Start cursor on the prompt row
        current_row = self.rows
        for message in self.messages:
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
            printf(' ' * (self.columns - columns_written % self.columns))
        # Show Cursor
        printf(SHOW_CURSOR)

    def render_prompt(self):
        # Move cursor to the prompt row, erase the old line, display prompt and current command
        printf(POSITION_CURSOR(self.rows, 1), CLEAR_LINE, self.prompt, self.command_string)


if __name__ == '__main__':
    Application().run()
