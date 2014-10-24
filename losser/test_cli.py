"""Tests for the command-line argument parsing."""
import mock
import losser
import os
import os.path
import StringIO
import inspect


devnull = open(os.devnull, 'w')


@mock.patch('sys.stderr', devnull)
def test_no_columns_argument():
    """It should exit with status 2 if there's no --columns argument."""
    table_function = mock.Mock()
    try:
        losser.main(args=[''], table_function=table_function)
    except SystemExit as err:
        assert err.code == 2
    assert not table_function.called


def test_help():
    """It should exit with status 0 if there's a -h argument."""
    table_function = mock.Mock()
    try:
        losser.main(args=['-h'], table_function=table_function)
    except SystemExit as err:
        assert err.code == 0
    assert not table_function.called


def test_long_help():
    """It should exit with status 0 if there's a --help argument."""
    table_function = mock.Mock()
    try:
        losser.main(args=['--help'], table_function=table_function)
    except SystemExit as err:
        assert err.code == 0
    assert not table_function.called


def test_help_and_other_args():
    """It should exit with status 0 if there's a -h argument, even if there are
    other args as well."""
    table_function = mock.Mock()
    try:
        losser.main(args=['-h', '--columns', 'test_columns.json'],
                          table_function=table_function)
    except SystemExit as err:
        assert err.code == 0
    assert not table_function.called


@mock.patch('sys.stdin')
def test_columns(mock_stdin):
    """stdin, --columns and csv=True should be passed to table()."""
    table_function = mock.Mock()

    # Mock stdin with a file-like object with some JSON text input.
    mock_stdin.read.return_value = '"foobar"'

    losser.main(
        args=['--columns', 'test_columns.json'], table_function=table_function)

    table_function.assert_called_once_with(
        "foobar", "test_columns.json", csv=True)


def test_unrecognized_argument():
    """It should exit with status 2 if given an unrecognized argument."""
    table_function = mock.Mock()
    try:
        losser.main(args=['--columns', 'test_columns.json', '--foobar'],
                          table_function=table_function)
    except SystemExit as err:
        assert err.code == 2
    assert not table_function.called


def _absolute_path(relative_path):
    return os.path.join(os.path.dirname(os.path.abspath(
        inspect.getfile(inspect.currentframe()))), relative_path)


@mock.patch('sys.stdin')
def test_input(mock_stdin):
    """If given the -i argument it should read from the file not stdin."""
    for arg in ("-i", "--input"):
        table_function = mock.Mock()
        losser.main(
            args=['--columns', 'test_columns.json',
                  arg, _absolute_path('test_input.json')],
            table_function=table_function)

        assert not mock_stdin.called
        table_function.assert_called_once_with(
            "foobar", "test_columns.json", csv=True)
