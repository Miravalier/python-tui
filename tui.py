#!/usr/bin/env python3.8
import math
import terminal
import shlex
import shutil
import sys
from ansi import *
from collections import deque
from signal import signal, SIGWINCH, SIG_IGN
from utils import printf


class Application:
    translation_table = str.maketrans('\n\t', '  ')

    def __init__(self, *, message_history=1024, command_history=1024,
            prompt=' > ', error_prefix=('error:', FG_RED)):
        self.messages = deque(maxlen=message_history)
        self.commands = deque(maxlen=command_history)
        self.prompt = prompt
        self.error_prefix = error_prefix
        self.queued_keys = []
        self.command_keys = []
        self.running = False
        self.update_dimensions()

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
        self.render_messages()

    def run(self):
        with terminal.raw_mode():
            self.running = True
            signal(SIGWINCH, self.redraw)
            self.on_startup()
            try:
                while self.running:
                    self.render_prompt()
                    self.on_keypress(self.getkey())
            except KeyboardInterrupt:
                pass
            self.on_exit()
            signal(SIGWINCH, SIG_IGN)

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
        # On enter or CTRL+D, run on_command and clear the command
        if key == '\n' or key == '\x04':
            try:
                args = self.command_args
            except ValueError as e:
                self.print(self.error_prefix, e)
                self.command_keys = []
                return
            self.on_command(args)
            self.command_keys = []
        # On tab, run on_tab
        elif key == '\t':
            try:
                args = self.command_args
                self.command_keys = list(shlex.join(args))
            except ValueError as e:
                #self.print(self.error_prefix, e)
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
        # Arrow keys
        elif key == 'LEFT':
            pass
        elif key == 'RIGHT':
            pass
        elif key == 'UP':
            pass
        elif key == 'DOWN':
            pass
        # Special Keys
        elif key == 'INSERT':
            pass
        elif key == 'HOME':
            pass
        elif key == 'DELETE':
            pass
        elif key == 'END':
            pass
        elif key == 'PAGE UP':
            pass
        elif key == 'PAGE DOWN':
            pass
        # On any other key, add it to the current command
        else:
            self.command_keys.append(key)

    ####################
    # Abstract Methods #
    ####################

    def on_startup(self):
        # By default do nothing
        pass

    def on_command(self, args):
        # If no args were entered, print an empty line
        if not args:
            self.print()
            return
        # All commands are unrecognized by default
        self.print(self.error_prefix, "unrecognized command {}".format(repr(args[0])))

    def on_tab(self, args):
        # By default do nothing
        pass

    def on_exit(self):
        # By default do nothing
        pass

    ####################
    # Internal Methods #
    ####################

    @property
    def command_string(self):
        return ''.join(self.command_keys)

    @property
    def command_args(self):
        return shlex.split(self.command_string)

    def redraw(self, *args):
        self.update_dimensions()
        self.render_messages()
        self.render_prompt()

    def row_length(self, message):
        return max(math.ceil(sum(len(part) for part, attributes in message) / self.columns), 1)

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
