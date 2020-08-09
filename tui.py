#!/usr/bin/env python3.8
import math
import terminal
import shlex
import shutil
import sys
from ansi import *
from collections import deque, namedtuple
from datetime import datetime
from parser import Parser, ArgumentError
from signal import signal, SIGWINCH, SIG_IGN
from typing import List
from utils import printf


class Application:
    translation_table = str.maketrans('\t\n', '  ')

    def __init__(self, *, message_history=1024, command_history=1024,
            prompt=('$ ', FG_CYAN), error_prefix=('error:', FG_RED)):
        self.messages = deque(maxlen=message_history)
        self.command_history = deque(maxlen=command_history)
        self.command_index = 0
        self.cursor_index = 0
        self.prompt = prompt
        self.error_prefix = error_prefix
        self.queued_keys = []
        self.command_keys = []
        self.running = False
        self.update_dimensions()

    ##################
    # Public Methods #
    ##################

    def stop(self):
        self.running = False

    def clear(self):
        self.messages.clear()

    def error(self, *args, **kwargs):
        self.print(self.error_prefix, *args, **kwargs)

    def print(self, *parts, sep=' ', end=''):
        # Construct the separator and end string
        sep = self.construct_tuple(sep)
        end = self.construct_tuple(end)
        # Assemble the message
        message = []
        for i in range(len(parts)-1):
            message.append(self.construct_tuple(parts[i]))
            message.append(sep)
        if parts:
            message.append(self.construct_tuple(parts[-1]))
        message.append(end)
        # Append the message to the deque
        self.messages.appendleft(message)
        # Trigger on_print on the message
        self.on_print(sep[0].join(part for part, attributes in message) + end[0])
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
                return 'SIGINT'

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
                    #key = "Unrecognized Code '{}'".format(key)
                    return None
                with terminal.nonblocking_mode():
                    while sys.stdin.read(1): pass
                return key
            # If this is not a CSI, the next key goes back on the stack
            else:
                self.queued_keys.append(key)
                return 'ESCAPE'
        else:
            return key

    def on_enter(self):
        try:
            args = self.command_args
        except ValueError as e:
            self.print(self.error_prefix, e)
            self.command_keys = []
            return
        self.print(self.prompt, self.command_string, sep='')
        if args:
            self.on_command(args)
        else:
            self.messages.appendleft([])
            self.render_messages()
        saved_command = shlex.join(args)
        if saved_command and (not self.command_history or self.command_history[0] != saved_command):
            self.command_history.appendleft(saved_command)
        self.command_keys = []
        self.command_index = 0
        self.cursor_index = 0
    
    def on_backspace(self):
        if self.cursor_index == 0:
            return
        self.command_keys.pop(self.cursor_index - 1)
        self.cursor_index -= 1

    def on_delete(self):
        if self.cursor_index < len(self.command_keys) - 1:
            self.command_keys.pop(self.cursor_index)

    def on_escape(self):
        self.command_keys = []
        self.cursor_index = 0
        self.command_index = 0

    def on_left(self):
        self.cursor_index -= 1

    def on_right(self):
        self.cursor_index += 1

    def on_up(self):
        if not self.command_history or self.command_index == len(self.command_history):
            return
        self.command_index += 1
        self.command_keys = list(self.command_history[self.command_index - 1])
        self.cursor_index = len(self.command_keys)

    def on_down(self):
        if not self.command_history or self.command_index == 0:
            return
        self.command_index -= 1
        if self.command_index == 0:
            self.command_keys = []
        else:
            self.command_keys = list(self.command_history[self.command_index - 1])
        self.cursor_index = len(self.command_keys)

    def on_insert(self):
        pass

    def on_home(self):
        self.cursor_index = 0

    def on_end(self):
        self.cursor_index = len(self.command_keys)

    def on_sigint(self):
        self.stop()

    def on_keypress(self, key):
        # Ignore None
        if key is None:
            return
        # Enter or CTRL+D
        if key == '\n' or key == '\x04':
            self.on_enter()
        # Tab
        elif key == '\t':
            try:
                args = self.command_args
            except ValueError as e:
                return
            self.on_tab(args)
        # Backspace
        elif key == '\x7F':
            self.on_backspace()
        # CTRL+C
        elif key == 'SIGINT':
            self.on_sigint()
        # Arrow keys
        elif key == 'LEFT':
            self.on_left()
        elif key == 'RIGHT':
            self.on_right()
        elif key == 'UP':
            self.on_up()
        elif key == 'DOWN':
            self.on_down()
        # Special keys
        elif key == 'DELETE':
            self.on_delete()
        elif key == 'INSERT':
            self.on_insert()
        elif key == 'HOME' or key == 'PAGE UP':
            self.on_home()
        elif key == 'END' or key == 'PAGE DOWN':
            self.on_end()
        elif key == 'ESCAPE':
            self.on_escape()
        # Any other printable key
        elif key.isprintable():
            self.on_printable(key)
        # Any other misc key
        else:
            self.on_misc(key)
        # Bound cursor index
        if self.cursor_index < 0:
            self.cursor_index = 0
        elif self.cursor_index > len(self.command_keys):
            self.cursor_index = len(self.command_keys)

    def on_printable(self, key):
        self.command_keys.insert(self.cursor_index, key)
        self.cursor_index += 1

    def on_misc(self, key):
        pass

    ####################
    # Abstract Methods #
    ####################

    def on_print(self, s: str) -> None:
        """
        Abstract method. Called whenever a print() call is made.
    
        s   --  The fully assembled string generated by the print call
                without any attributes like color.
        """
        pass

    def on_startup(self) -> None:
        """
        Abstract method. Called exactly once, when the application is started
        by calling the run() function.
        """
        pass

    def on_command(self, args: List[str]) -> None:
        """
        Abstract method. Called when a command is submitted by pressing enter.
        This function is intended to be used to implement the main logic of the
        application.

        args    --  A list of string arguments entered.
        """
        pass

    def on_tab(self, args: List[str]) -> None:
        """
        Abstract method. Called when tab is pressed, intended to be
        used to implement tab-complete functionality.
        
        args    --  A list of string arguments entered so far.
        """
        pass

    def on_exit(self) -> None:
        """
        Abstract method. Called exactly once, when the application is ending because
        the stop() function has been called.
        """
        pass

    ####################
    # Internal Methods #
    ####################

    @property
    def error_prefix(self):
        return self._error_prefix

    @error_prefix.setter
    def error_prefix(self, value):
        self._error_prefix = self.construct_tuple(value)

    @property
    def prompt(self):
        return self._prompt

    @prompt.setter
    def prompt(self, value):
        self._prompt = self.construct_tuple(value)

    @property
    def command_string(self):
        return ''.join(self.command_keys)

    @command_string.setter
    def command_string(self, value):
        self.command_keys = list(value)

    @property
    def command_args(self):
        args = shlex.split(self.command_string)
        return args

    @command_args.setter
    def command_args(self, value):
        self.command_keys = list(shlex.join(value))

    def redraw(self, *args):
        self.update_dimensions()
        self.render_messages()
        self.render_prompt()

    def count_lines(self, message):
        return max(math.ceil(sum(len(part) for part, attributes in message) / self.columns), 1)

    def construct_tuple(self, part):
        if isinstance(part, tuple) and len(part) == 2:
            return (self.construct_string(part[0]), self.construct_string(part[1]))
        else:
            return (self.construct_string(part), None)

    def construct_string(self, value):
        return str(value).translate(self.translation_table)

    def update_dimensions(self):
        columns, rows = shutil.get_terminal_size()
        self.columns = columns
        self.rows = rows

    def render_messages(self):
        if self.rows < 2:
            return
        # Hide cursor
        printf(HIDE_CURSOR)
        # Start cursor on the prompt row
        current_row = self.rows
        for message in self.messages:
            # Calculate how many rows will be needed for this message
            current_row -= self.count_lines(message)
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
        prompt, attributes = self.prompt
        usable_columns = self.columns - (len(prompt) + 1)
        if usable_columns < 7:
            return
        command = self.command_string
        cursor_index = self.cursor_index
        # Truncate the command if necessary
        if len(command) > usable_columns:
            left_bound = min(max(cursor_index - usable_columns // 2, 0), len(command) - usable_columns)
            right_bound = left_bound + usable_columns
            command = (
                command[left_bound:cursor_index]
                +
                command[cursor_index:right_bound]
            )
            cursor_index -= left_bound
        printf(
            # Move the cursor to the prompt row
            POSITION_CURSOR(self.rows, 1),
            # Erase the old prompt
            CLEAR_LINE,
            # Set the prompt attributes
            attributes if attributes else "",
            # Display the prompt
            prompt,
            # Reset the cursor attributes
            SGR_RESET if attributes else "",
            # Display the current typed command
            command,
            # Move the cursor to the cursor index
            POSITION_CURSOR(self.rows, len(prompt) + cursor_index + 1)
        )


class LocalCommand:
    def __init__(self, name, callback, help, examples=()):
        self.name = name
        self.callback = callback
        self.help = help
        self.parser = Parser(add_help=False)
        self.parameter_domains = {}
        self.examples = examples
        self.has_optional_arguments = False

    def add_argument(self, name, *, required=True, choices=None, help=None):
        if not required:
            self.has_optional_arguments = True

        if required and self.has_optional_arguments:
            raise ValueError("Required arguments can't be added after optional arguments.")
        
        if callable(choices):
            self.parameter_domains[name] = choices
            choices = None

        self.parser.add_argument(
            name,
            nargs=(None if required else '?'),
            choices=choices,
            help=help
        )

    @property
    def parameters(self):
        return self.parser._actions

    @property
    def argument_string(self):
        args = []
        for action in self.parameters:
            if action.nargs == '?':
                args.append('[{}]'.format(action.dest))
            elif action.nargs == '*':
                args.append('[{} ...]'.format(action.dest))
            elif action.nargs == '+':
                args.append('<{} ...>'.format(action.dest))
            else:
                args.append('<{}>'.format(action.dest))
        return " ".join(args)

    @property
    def usage(self):
        return "{} {}".format(self.name, self.argument_string)



class Interpreter(Application):
    def __init__(self, *args, allow_abbreviations=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_abbreviations = allow_abbreviations
        self.commands = {}
        self.add_default_commands()

    def add_default_commands(self):
        help_command = self.add_command(
            'help',
            self.do_help,
            help='List available commands or get detailed information on a command.',
            examples=('help alias', 'help exit')
        )
        help_command.add_argument(
            'command',
            required=False,
            choices=lambda: self.commands.keys(),
            help='Command to display more info for.'
        )

        exit_command = self.add_command(
            'exit',
            lambda args: self.stop(),
            aliases=['quit'],
            help='Close the application.'
        )

        alias_command = self.add_command(
            'alias',
            self.do_alias,
            help='Create a shortcut for a command.'
        )
        alias_command.add_argument('new_name')
        alias_command.add_argument(
            'existing_command', choices=lambda: self.commands.keys(),
            help='An existing command to create an alias for.'
        )

    def add_command(self, name, callback, *, aliases=(), help=None, examples=()):
        '''
        Add a command to the application.

        name        --  Primary name of the command.

        callback    --  Function to be called when this command is entered. Signature:
                        callback(args: List[str])

        aliases     --  List of alternate accepted names.

        help        --  String that displays when 'help <command>' is entered.

        examples    --  List of strings that display when 'help <command>' is entered.
        '''
        command = LocalCommand(name, callback, help, examples)
        self.commands[name] = command
        for alias in aliases:
            self.commands[alias] = command
        return command

    @property
    def has_trailing_space(self):
        if self.command_keys and self.command_keys[-1].isspace():
            return True
        return False

    def argument_index(self, args):
        if not args:
            return 0

        index = len(args) - 1

        if self.has_trailing_space:
            index += 1

        return index
            

    def command_complete(self, command, commands):
        matches = [c for c in commands if c.startswith(command)]
        if len(matches) == 1:
            return matches[0]
        else:
            return matches

    def on_command(self, args):
        command, *args = args
        if command in self.commands:
            command = self.commands[command]
        else:
            if self.allow_abbreviations:
                matches = [c for c in self.commands if c.startswith(command)]
                if len(matches) == 0:
                    self.error("unrecognized command '{}'".format(command))
                    return
                elif len(matches) == 1:
                    command = self.commands[matches[0]]
                else:
                    self.error("ambiguous command:", '  '.join(matches))
                    return
            else:
                self.error("unrecognized command '{}'".format(command))
                return

        try:
            args = command.parser.parse_args(args)
            command.callback(args)
        except ArgumentError as e:
            self.print(('usage:', FG_YELLOW), command.usage)
            e = str(e)
            if e:
                self.error(e)

    def on_tab(self, args):
        # If no text is present, display all commands
        if not args:
            self.print(*self.commands.keys(), sep='  ')
            return

        command, *args = args

        # If no args are present and this command does not exist,
        # try to complete it
        if command not in self.commands:
            if not args:
                match = self.command_complete(command, self.commands)
                if isinstance(match, list):
                    self.print(*match, sep='  ')
                else:
                    self.command_string = match + ' '
                    self.cursor_index = len(self.command_keys)
            return

        command = self.commands[command]
        argument_index = self.argument_index(args)

        # If this command does not take parameters
        if not command.parameters:
            return

        # If more arguments are provided than parameters
        if argument_index >= len(command.parameters):
            self.print(command.usage)
            return

        # Define which action and argument to tab complete
        action = command.parameters[argument_index]

        # If args are provided and there is no trailing space,
        # the arg is the last arg in the list. Otherwise it is
        # an empty string.
        if args and not self.has_trailing_space:
            arg = args[-1]
        else:
            arg = ''

        # If choices are defined for this action
        if action.choices:
            domain = action.choices
        # If this action has a defined domain function
        elif action.dest in command.parameter_domains:
            domain = command.parameter_domains[action.dest]()
        else:
            domain = None

        # If the domain exists, either from an iterable or function
        if domain:
            # Find which choices match the given argument
            match = self.command_complete(arg, domain)
            # If there are multiple matches, print them
            if isinstance(match, list):
                self.print(*match, sep='  ')
            # If there is just one match, add it to the command line
            else:
                if self.has_trailing_space:
                    self.command_args = self.command_args + [match]
                else:
                    args = self.command_args
                    args[-1] = match
                    self.command_args = args
                    self.cursor_index = len(self.command_keys)
            return

        # Fallback if no better methods resolve
        self.print(command.usage)

    def do_help(self, args):
        self.print()
        if not args.command:
            result = []
            for command in set(self.commands.values()):
                self.print((command.name, FG_BRIGHT_CYAN), command.argument_string)
                if command.help:
                    self.print('  {}'.format(command.help))
                self.print()
        else:
            if args.command not in self.commands:
                raise ArgumentError("unrecognized command '{}'".format(args.command))
                return
            command = self.commands[args.command]
            if command.help:
                self.print('description:')
                self.print('   ', command.help)
                self.print()
            self.print("usage:")
            self.print('   ', (command.name, FG_BRIGHT_CYAN), command.argument_string)
            if command.parameters:
                self.print()
                self.print("parameters:")
                for parameter in command.parameters:
                    if parameter.help:
                        self.print('   ', parameter.dest + ':', parameter.help)
                    else:
                        self.print('   ', parameter.dest)
            if command.examples:
                self.print()
                self.print("examples:")
                for example in command.examples:
                    self.print('   ', example)
            self.print()
            

    def do_alias(self, args):
        if args.existing_command not in self.commands:
            raise ArgumentError("unrecognized command '{}'".format(args.existing_command))
        self.commands[args.new_name] = self.commands[args.existing_command]


class ExampleApplication(Interpreter):
    pass


if __name__ == '__main__':
    ExampleApplication().run()
