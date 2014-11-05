"""The command-line interface for losser."""
from __future__ import absolute_import

import argparse
import collections
import json
import sys

import losser.losser as losser


class CommandLineError(Exception):

    """Exception that's raised if command-line parsing fails.

    All command-line parsing exceptions raised are either CommandLineError or
    a subclass of CommandLineError.

    """

    pass


class CommandLineExit(CommandLineError):

    """Raised when argparse has tried to make Python exit.

    For example if the user gives a --help, or if they give an unrecognized
    argument like --foobar. Argparse will already have printed the usage and
    error message to stderr, so all losser needs to do is sys.exit with the
    right exit code (as opposed to other CommandLineErrors where losser needs
    to print an error message and then sys.exit()).

    """

    def __init__(self, code):
        super(CommandLineExit, self).__init__(self)
        self.code = code


class DuplicateColumnTitleError(CommandLineError):
    pass


class ColumnOptionWithNoPrecedingColumnError(CommandLineError):
    pass


class DuplicateColumnOptionError(CommandLineError):
    pass


class ColumnWithoutPatternError(CommandLineError):
    pass


class NoColumnsError(CommandLineError):
    pass


class InvalidColumnOptionArgument(CommandLineError):
    pass


def _boolify(key, value, option_string):

    key = key.replace('-', '_')

    if not value:
        return key, True

    value = value.strip().lower()

    yes_values = ('true', 'yes', 'y')
    no_values = ('false', 'no', 'n')

    if value in yes_values:
        value = True
    elif value in no_values:
        value = False
    else:
        values = ", ".join(
            ['"{0}"'.format(value) for value in yes_values + no_values])
        raise InvalidColumnOptionArgument(
            "The argument for option {0} must be one of {1}".format(
                option_string, values))

    return key, value


def _int(key, value, option_string):

    key = key.replace('-', '_')
    try:
        value = int(value)
    except ValueError:
        raise InvalidColumnOptionArgument(
            "{0} is not a valid integer argument for {1}".format(
                value, option_string))

    return key, value


class ColumnsAction(argparse.Action):

    """An argparse action for parsing --column and related arguments.

    Saves each column and its options as a dict in an OrderedDict of columns.

    """

    def __call__(self, parser, namespace, value, option_string=None):
        if not hasattr(namespace, "columns"):
            namespace.columns = collections.OrderedDict()
        if option_string in ("-c", "--column"):

            if value in namespace.columns:
                raise DuplicateColumnTitleError(
                    "You can't have two columns called {0}".format(value))

            setattr(namespace, "__currently_parsing_column", value)
            namespace.columns[value] = {}
        else:
            if not hasattr(namespace, "__currently_parsing_column"):
                raise ColumnOptionWithNoPrecedingColumnError(
                    "You need a --column before a {0}".format(option_string))
            if option_string.startswith("--"):
                key = option_string[2:]
            else:
                assert option_string.starts_with("-")
                key = option_string[1:]
            column = namespace.columns[
                getattr(namespace, "__currently_parsing_column")]
            if key in column:
                raise DuplicateColumnOptionError(
                    "You can't have two {0}'s for the same column".format(
                        option_string))

            if key in ('case-sensitive', 'unique', 'deduplicate', 'strip'):
                key, value = _boolify(key, value, option_string)

            if key == 'max-length':
                key, value = _int(key, value, option_string)

            column[key] = value


def parse(parser=None, args=None, table_function=None, in_=None):

    table_function = table_function or losser.table

    in_ = in_ or sys.stdin

    # Parse the command-line arguments.
    if not parser:
        parser = argparse.ArgumentParser()
    parser.description = ("Filter, transform and export a list of JSON "
                          "objects on stdin to JSON or CSV on stdout")
    parser.add_argument(
        "--columns", dest="columns_file",
        help="the JSON file specifying the columns to be output",
    )
    parser.add_argument(
        "-i", "--input",
        help="read input from the given file instead of from stdin",
        dest='input_data',  # Because input is a Python builtin.
    )
    parser.add_argument("-c", "--column", action=ColumnsAction)
    parser.add_argument("--pattern", action=ColumnsAction)
    parser.add_argument("--max-length", action=ColumnsAction)
    parser.add_argument("--strip", nargs="?", action=ColumnsAction)
    parser.add_argument("--deduplicate", nargs='?', action=ColumnsAction)
    parser.add_argument("--case-sensitive", nargs='?', action=ColumnsAction)
    parser.add_argument("--unique", nargs="?", action=ColumnsAction)

    try:
        parsed_args = parser.parse_args(args)
    except SystemExit as err:
        raise CommandLineExit(err.code)

    try:
        columns = parsed_args.columns
    except AttributeError:
        columns = collections.OrderedDict()

    for title, spec in columns.items():
        if "pattern" not in spec:
            raise ColumnWithoutPatternError(
                'Column "{0}" needs a pattern'.format(title))

    # Crash if no columns specified.
    # In the future we'll support simply converting all JSON fields to CSV
    # columns if no columns are specified, and this will be removed.
    if (not columns) and (not parsed_args.columns_file):
        raise NoColumnsError(
            "You must give either a --columns or at least one -c/--column "
            "argument")

    # Read the input data from stdin or a file.
    if parsed_args.input_data:
        input_data = open(parsed_args.input_data, 'r').read()
    else:
        input_data = in_.read()

    dicts = json.loads(input_data)

    if parsed_args.columns_file:
        csv_string = table_function(dicts, parsed_args.columns_file, csv=True)
    else:
        csv_string = table_function(dicts, parsed_args.columns, csv=True)
    sys.stdout.write(csv_string)


def main():
    parser = argparse.ArgumentParser()
    try:
        parse(parser)
    except CommandLineExit as err:
        sys.exit(err.code)
    except CommandLineError as err:
        if err.message:
            parser.error(err.message)


if __name__ == "__main__": main()
