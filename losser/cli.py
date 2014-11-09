"""The command-line interface for losser."""
from __future__ import absolute_import

import argparse
import collections
import json
import sys
import StringIO

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


class ColumnsAndColumnsFileError(CommandLineError):
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


def make_parser(add_help=True, exclude_args=None):
    """Return an argparse.ArgumentParser object with losser's arguments.

    Other projects can call this to get an ArgumentParser with losser's
    command line interface to use as a parent parser for their own parser.
    For example::

        parent_parser = losser.cli.make_parser(
            add_help=False, exclude_args=["-i"])
        parser = argparse.ArgumentParser(
            description="Export datasets from a CKAN site to JSON or CSV.",
            parents=[parent_parser])
        parser.add_argument(...

    :param add_help: Whether or not to add losser's help text to the parser.
        Pass add_help=False if you want to use your own help text in a child
        parser.
    :type add_help: bool

    :param exclude_args: List of losser command-line arguments to exclude, use
        this to exclude any default losser arguments that you don't want in
        your own command. For example: exclude_args=["-i", "--max-length"].
    :type exclude_args: list of strings

    """
    if exclude_args is None:
        exclude_args = []
    parser = argparse.ArgumentParser(add_help=add_help)
    parser.description = ("Filter, transform and export a list of JSON "
                          "objects on stdin to JSON or CSV on stdout")
    if "--columns" not in exclude_args:
        parser.add_argument(
            "--columns", dest="columns_file",
            help="the JSON file specifying the columns to be output",
        )
    if ("-i" not in exclude_args) and ("--input" not in exclude_args):
        parser.add_argument(
            "-i", "--input",
            help="read input from the given file instead of from stdin",
            dest='input_data',  # Because input is a Python builtin.
        )
    if ("-c" not in exclude_args) and ("--column" not in exclude_args):
        parser.add_argument("-c", "--column", action=ColumnsAction)
    if "--pattern" not in exclude_args:
        parser.add_argument("--pattern", action=ColumnsAction, nargs='+')
    if "--max-length" not in exclude_args:
        parser.add_argument("--max-length", action=ColumnsAction)
    if "--strip" not in exclude_args:
        parser.add_argument("--strip", nargs="?", action=ColumnsAction)
    if "--deduplicate" not in exclude_args:
        parser.add_argument("--deduplicate", nargs='?', action=ColumnsAction)
    if "--case-sensitive" not in exclude_args:
        parser.add_argument(
            "--case-sensitive", nargs='?', action=ColumnsAction)
    if "--unique" not in exclude_args:
        parser.add_argument("--unique", nargs="?", action=ColumnsAction)
    if ("-p" not in exclude_args) and ("--pretty" not in exclude_args):
        parser.add_argument("-p", "--pretty", action="store_true")
    return parser


def parse(parser=None, args=None):
    """Parse the command line arguments, return an argparse namespace object.

    Other projects can call this function and pass in their own ArgumentParser
    object (which should have a losser ArgumentParser from make_parser() above
    as parent) to do the argument parsing and get the result (this does some
    custom post-processing, beyond what argparse's parse_args() does). For
    example::

        parent_parser = losser.cli.make_parser(...)
        parser = argparse.ArgumentParser(parents=[parent_parser])
        parser.add_argument(...)
        try:
            parsed_args = losser.cli.parse(parser=parser)
        except losser.cli.CommandLineError as err:
            ...

    :raises CommandLineError: If something went wrong during command-line
        parsing. If the exception has a non-empty .message attribute it
        contains an error message that hasn't been printed to stdout yet,
        otherwise any error message has already been printed.

    :raises CommandLineExit: If the result of command-line parsing means that
        the command should exit without continuing, but this is not because of
        an error (for example if the user passed --help). Any help text will
        already have been written to stdout, the exit code that the process
        should exit with is in the exception's .code attribute.
        CommandLineExit is a subclass of CommandLineError above.

    """
    if not parser:
        parser = make_parser()

    try:
        parsed_args = parser.parse_args(args)
    except SystemExit as err:
        raise CommandLineExit(err.code)

    try:
        columns = parsed_args.columns
    except AttributeError:
        columns = collections.OrderedDict()
        parsed_args.columns = columns

    for title, spec in columns.items():
        if "pattern" not in spec:
            raise ColumnWithoutPatternError(
                'Column "{0}" needs a pattern'.format(title))

        # Change length-1 patterns into strings (not lists of one string).
        if len(spec["pattern"]) == 1:
            spec["pattern"] = spec["pattern"][0]

    if columns and parsed_args.columns_file:
        raise ColumnsAndColumnsFileError(
            "You can't use the --column and --columns options together (yet)")
    elif parsed_args.columns_file and not columns:
        parsed_args.columns = parsed_args.columns_file
    elif (not columns) and (not parsed_args.columns_file):
        # Crash if no columns specified.
        # In the future we'll support simply converting all JSON fields to CSV
        # columns if no columns are specified, and this will be removed.
        raise NoColumnsError(
            "You must give either a --columns or at least one -c/--column "
            "argument")
    else:
        assert columns

    return parsed_args


def do(parser=None, args=None, in_=None, table_function=None):
    """Read command-line args and stdin, return the result.

    Read the command line arguments and the input data from stdin, pass them to
    the table() function to do the filter and transform, and return the string
    of CSV- or JSON-formatted text that should be written to stdout.

    Note that although the output data is returned rather than written to
    stdout, this function may write error messages or help text to stdout
    (for example if there's an error with the command-line parsing).

    :raises CommandLineError: see parse() above for details

    """
    in_ = in_ or sys.stdin
    table_function = table_function or losser.table

    parsed_args = parse(parser=parser, args=args)

    # Read the input data from stdin or a file.
    if parsed_args.input_data:
        input_data = open(parsed_args.input_data, 'r').read()
    else:
        input_data = in_.read()
    dicts = json.loads(input_data)

    csv_string = table_function(dicts, parsed_args.columns, csv=True,
                                pretty=parsed_args.pretty)

    return csv_string


def main():
    """Call do() and if it raises an exception then sys.exit() appropriately.

    This makes sure that any usage and error messages are printed correctly,
    and that the exit code is right.

    do() itself doesn't call sys.exit() because we want it to be callable from
    tests that check that it raises the right exception classes for different
    invalid inputs.

    """
    parser = make_parser()
    try:
        output = do(parser=parser)
    except CommandLineExit as err:
        sys.exit(err.code)
    except CommandLineError as err:
        if err.message:
            parser.error(err.message)
    sys.stdout.write(output)


if __name__ == "__main__": main()
