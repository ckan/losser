"""Tests for the command-line argument parsing."""
from __future__ import absolute_import

import collections
import inspect
import os
import os.path

import losser.cli as cli

import mock

import nose.tools


# We use this in various tests to patch sys.stdout so that losser's command
# line interface doesn't errors and help text to stdout when running the tests.
DEVNULL = open(os.devnull, 'w')


# In the future we'll support simply converting all JSON fields to CSV
# columns if no columns are specified, and this test will be removed.
def test_no_columns_argument():
    """It should crash if there are no --column or --columns args."""
    table_function = mock.Mock()
    nose.tools.assert_raises(
        cli.NoColumnsError, cli.do, args=[],
        table_function=table_function)
    assert not table_function.called


def test_help():
    """It should exit with code 0 if there's a -h argument."""
    table_function = mock.Mock()
    try:
        cli.do(args=['-h'], table_function=table_function)
        assert False, "losser -h should raise an exception"
    except cli.CommandLineExit as err:
        assert err.code == 0
    assert not table_function.called


def test_long_help():
    """It should exit with code 0 if there's a --help argument."""
    table_function = mock.Mock()
    try:
        cli.do(args=['--help'], table_function=table_function)
        assert False, "losser --help should raise an exception"
    except cli.CommandLineExit as err:
        assert err.code == 0
    assert not table_function.called


def test_help_and_other_args():
    """A -h argument should override other arguments.

    It should exit with status 0 if there's a -h argument, even if there are
    other args as well.

    """
    table_function = mock.Mock()
    try:
        cli.do(
            args=['-h', '--columns', 'test_columns.json'],
            table_function=table_function)
        assert False, "losser -h should raise an exception"
    except cli.CommandLineExit as err:
        assert err.code == 0
    assert not table_function.called


def test_columns():
    """stdin, --columns and csv=True should be passed to table()."""
    table_function = mock.Mock()

    # Mock stdin with a file-like object with some JSON text input.
    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    cli.do(
        args=['--columns', 'test_columns.json'], table_function=table_function,
        in_=mock_stdin)

    table_function.assert_called_once_with(
        "foobar", "test_columns.json", csv=True)


@mock.patch('sys.stderr', DEVNULL)
def test_columns_with_no_arg():
    """It should crash if given a ``--columns`` option with no argument."""
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    try:
        cli.do(
            args=['--columns'], table_function=table_function, in_=mock_stdin)
        assert False, "It should raise if given --columns with no arg"
    except cli.CommandLineExit as err:
        assert err.code == 2

    assert not table_function.called


@mock.patch('sys.stderr', DEVNULL)
def test_unrecognized_argument():
    """It should exit with status 2 if given an unrecognized argument."""
    table_function = mock.Mock()
    try:
        cli.do(args=['--columns', 'test_columns.json', '--foobar'],
                  table_function=table_function)
        assert False, "It should raise if given an unrecognized argument"
    except cli.CommandLineExit as err:
        assert err.code == 2
    assert not table_function.called


def _absolute_path(relative_path):
    return os.path.join(os.path.dirname(os.path.abspath(
        inspect.getfile(inspect.currentframe()))), relative_path)


def test_input():
    """If given the -i argument it should read from the file not stdin."""
    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    for arg in ("-i", "--input"):
        table_function = mock.Mock()
        cli.do(
            args=['--columns', 'test_columns.json',
                  arg, _absolute_path('test_input.json')],
            table_function=table_function, in_=mock_stdin)

        assert not mock_stdin.called
        table_function.assert_called_once_with(
            "foobar", "test_columns.json", csv=True)


def test_with_one_column_argument():
    """Simple test with one --column and one --pattern argument."""
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    cli.do(
        args=["--column", "Title", "--pattern", "^title$"],
        table_function=table_function,
        in_=mock_stdin)

    table_function.assert_called_once_with(
        u"foobar",
        collections.OrderedDict(Title={"pattern": "^title$"}),
        csv=True)


def test_with_many_column_arguments():
    """Complex test with multiple columns and options on command line."""
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    cli.do(
        args=[
            "--column", "Title", "--pattern", "^title$", "--case-sensitive",
            "--strip", "no",
            "--column", "Description", "--pattern", "^notes$", "--unique",
            "--column", "Owner", "--pattern", "^author$", "--max-length=255",
            "--deduplicate", "True",
        ],
        table_function=table_function, in_=mock_stdin)

    expected_columns = collections.OrderedDict()
    expected_columns["Title"] = {
        "pattern": "^title$", "case_sensitive": True, "strip": False}
    expected_columns["Description"] = {
        "pattern": "^notes$", "unique": True}
    expected_columns["Owner"] = {
        "pattern": "^author$", "max_length": 255, "deduplicate": True}
    table_function.assert_called_once_with(
        "foobar", expected_columns, csv=True)


def test_with_repeated_column_option():
    """It should crash if the same option is repeated for the same column."""
    table_function = mock.Mock()
    args = ["--column", "Title", "--pattern", "^title$", "--pattern",
            "repeated"]
    nose.tools.assert_raises(
        cli.DuplicateColumnOptionError, cli.do, args=args,
        table_function=table_function)
    assert not table_function.called


def test_with_implicit_true():
    """Passing a bool like ``--unique`` with no arg should turn the option on.

    Boolean column options like unique can be turned on with ``--unique true``
    or with just ``--unique`` with no arg. This test tests the no arg version.

    """
    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    expected_columns = {
        "Title": {
            "pattern": "^title$",
            "unique": True,
        },
    }

    table_function = mock.Mock()
    cli.do(
        args=["--column", "Title", "--pattern", "^title$", "--unique"],
        table_function=table_function, in_=mock_stdin)

    table_function.assert_called_once_with(
        "foobar", expected_columns, csv=True)


def test_with_explicit_true():
    """Passing --case-sensitive true should turn on case-sensitive."""
    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    expected_columns = {
        "Title": {
            "pattern": "^title$",
            "case_sensitive": True,
        },
    }

    for value in ("true", "True", "y", "Y", "yes", "Yes", "YES"):
        table_function = mock.Mock()
        cli.do(
            args=[
                "--column", "Title", "--pattern", "^title$",
                "--case-sensitive", value,
            ],
            table_function=table_function,
            in_=mock_stdin
        )

        table_function.assert_called_once_with(
            "foobar", expected_columns, csv=True)


def test_with_explicit_false():
    """Passing --strip false should turn off strip."""
    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    expected_columns = {
        "Title": {
            "pattern": "^title$",
            "strip": False,
        },
    }

    for value in ("false", "False", "n", "N", "no", "No", "NO"):
        table_function = mock.Mock()
        cli.do(
            args=[
                "--column", "Title", "--pattern", "^title$",
                "--strip", value,
            ],
            table_function=table_function,
            in_=mock_stdin
        )

        table_function.assert_called_once_with(
            "foobar", expected_columns, csv=True)


def test_column_with_no_pattern():
    """It should crash if given a --column with no --pattern."""
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    nose.tools.assert_raises(
        cli.ColumnWithoutPatternError, cli.do,
        args=["--column", "Title"], table_function=table_function,
        in_=mock_stdin)
    assert not table_function.called


def test_column_option_with_no_column():
    """It should crash if given a column option without a preceding --column.

    """
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    for option in ("--unique", "--strip", "--deduplicate", "--case-sensitive",
                   "--pattern", "--max-length"):
        nose.tools.assert_raises(
            cli.ColumnOptionWithNoPrecedingColumnError,
            cli.do, args=[option, "foo"], table_function=table_function,
            in_=mock_stdin)
        assert not table_function.called


def test_boolean_option_with_invalid_arg():
    """It should crash if given a column option with an invalid argument."""
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    for option in ("--unique", "--strip", "--deduplicate", "--case-sensitive"):
        nose.tools.assert_raises(
            cli.InvalidColumnOptionArgument, cli.do,
            args=["--column", "foo", option, "invalid"],
            table_function=table_function, in_=mock_stdin)
        assert not table_function.called


def test_max_length():
    """Simple test of the --max-length option."""
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    cli.do(
        args=["--column", "Title", "--pattern", "^title$",
              "--max-length", "255"],
        table_function=table_function,
        in_=mock_stdin)

    table_function.assert_called_once_with(
        u"foobar",
        collections.OrderedDict(
            Title={"pattern": "^title$", "max_length": 255}),
        csv=True)


@mock.patch('sys.stderr', DEVNULL)
def test_max_length_with_no_arg():
    """It should raise if given ``--max-length`` with no argument."""
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    try:
        cli.do(
            args=["--column", "foo", "--pattern", "foo", "--max-length"],
            table_function=table_function, in_=mock_stdin)
        assert False, "It should raise if given --max-length with no arg"
    except cli.CommandLineExit as err:
        assert err.code == 2

    assert not table_function.called


def test_max_length_with_invalid_arg():
    """It should raise if given ``--max-length`` with an invalid argument."""
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    args = ["--column", "foo", "--pattern", "foo", "--max-length", "invalid"]
    nose.tools.assert_raises(
        cli.InvalidColumnOptionArgument, cli.do, args=args,
        table_function=table_function, in_=mock_stdin)

    assert not table_function.called


def test_pattern_with_multiple_arguments():
    """The --pattern option can take more than one argument."""
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    cli.do(
        args=["--column", "Formats", "--pattern", "^resources$", "^format$"],
        table_function=table_function,
        in_=mock_stdin)

    table_function.assert_called_once_with(
        u"foobar",
        collections.OrderedDict(
            Formats={"pattern": ["^resources$", "^format$"]}),
        csv=True)


def test_column_and_columns_together():
    """It should raise if given ``--column`` and ``--columns`` together."""
    table_function = mock.Mock()

    mock_stdin = mock.Mock()
    mock_stdin.read.return_value = '"foobar"'

    args = ["--column", "foo", "--pattern", "foo", "--columns", "columns.json"]
    nose.tools.assert_raises(
        cli.ColumnsAndColumnsFileError, cli.do, args=args,
        table_function=table_function, in_=mock_stdin)

    assert not table_function.called
