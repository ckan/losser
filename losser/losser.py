import re
import collections
import sys
import unicodecsv
import argparse
import cStringIO
import traceback
import json
import pprint


class UniqueError(Exception):
    pass


def table(dicts, columns, csv=False):
    """Query a list of dicts with a list of queries and return a table.

    A "table" is a list of OrderedDicts each having the same keys in the same
    order.

    :param dicts: the list of input dicts
    :type dicts: list of dicts

    :param columns: the list of column query dicts, or the path to a JSON file
        containing the list of column query dicts
    :type columns: list of dicts, or string

    :param csv: return a UTF8-encoded, CSV-formatted string instead of a list
        of dicts
    :type csv: bool

    :rtype: list of dicts, or CSV string

    """
    # Optionally read columns from file.
    if isinstance(columns, basestring):
        columns = read_columns_file(columns)

    table_ = []
    for d in dicts:
        row = collections.OrderedDict()  # The row we'll return in the table.
        for column_title, column_spec in columns.items():
            row[column_title] = query(dict_=d, **column_spec)
        table_.append(row)

    if csv:
        # Return a UTF8-encoded, CSV-formatted string instead of a list of
        # dicts.
        f = cStringIO.StringIO()
        try:
            _write_csv(f, table_)
            return f.getvalue()
        finally:
            f.close()
    else:
        return table_


def _write_csv(f, table):
    """Write the given table (list of dicts) to the given file as CSV.

    Writes UTF8-encoded, CSV-formatted text.

    ``f`` could be an opened file, sys.stdout, or a StringIO.

    """
    # We assume that each dict in the list has the same keys.
    fieldnames = table[0].keys()
    writer = unicodecsv.DictWriter(f, fieldnames, encoding='utf-8')
    writer.writeheader()

    # Change lists into comma-separated strings.
    for dict_ in table:
        for key, value in dict_.items():
            if type(value) in (list, tuple):
                dict_[key] = ', '.join(value)

    writer.writerows(table)


def query(pattern_path, dict_, max_length=None, strip=False,
          case_sensitive=False, unique=False, deduplicate=False,
          string_transformations=None, hyperlink=False):
    """Query the given dict with the given pattern path and return the result.

    The ``pattern_path`` is a either a single regular expression string or a
    list of regex strings that will be matched against the keys of the dict and
    its subdicts to find the value(s) in the dict to return.

    The returned result is either a single value (None, "foo", 42, False...)
    or (if the pattern path matched multiple values in the dict) a list of
    values.

    If the dict contains sub-lists or sub-dicts values from these will be
    flattened into a simple flat list to be returned.

    """
    if string_transformations is None:
        string_transformations = []

    if max_length:
        string_transformations.append(lambda x: x[:max_length])

    if hyperlink:
        string_transformations.append(
                lambda x: '=HYPERLINK("{0}")'.format(x))

    if isinstance(pattern_path, basestring):
        pattern_path = [pattern_path]

    # Copy the pattern_path because we're going to modify it which can be
    # unexpected and confusing to user code.
    original_pattern_path = pattern_path
    pattern_path = pattern_path[:]

    # We're going to be popping strings off the end of the pattern path
    # (because Python lists don't come with a convenient pop-from-front method)
    # so we need the list in reverse order.
    pattern_path.reverse()

    result = _process_object(pattern_path, dict_,
                             string_transformations=string_transformations,
                             strip=strip, case_sensitive=case_sensitive)

    if not result:
        return None  # Empty lists finally get turned into None.
    elif len(result) == 1:
        return result[0]  # One-item lists just get turned into the item.
    else:
        if unique:
            msg = "pattern_path: {0}\n\n".format(original_pattern_path)
            msg = msg + pprint.pformat(dict_)
            raise UniqueError(msg)
        if deduplicate:
            # Deduplicate the list while maintaining order.
            new_result = []
            for item in result:
                if item not in new_result:
                    new_result.append(item)
            result = new_result
        return result


def _process_object(pattern_path, object_, **kwargs):
    if type(object_) in (tuple, list):
        return _process_list(pattern_path, object_, **kwargs)
    elif isinstance(object_, dict):
        return _process_dict(pattern_path, object_, **kwargs)
    elif isinstance(object_, basestring):
        return _process_string(object_, **kwargs)
    else:
        return [object_]


def _process_string(s, string_transformations=None, strip=False, **kwargs):
    if strip:
        s = s.strip()
    if string_transformations:
        for string_transformation in string_transformations:
            s = string_transformation(s)
    return [s]


def _process_list(pattern_path, list_, **kwargs):
    result = []
    for item in list_:
        result.extend(_process_object(pattern_path[0:], item, **kwargs))
    if pattern_path:
        pattern_path.pop()
    return result


def _process_dict(pattern_path, dict_, case_sensitive=False, **kwargs):

    if not pattern_path:
        return []

    result = []
    pattern = pattern_path.pop()

    if case_sensitive:
        flags = re.UNICODE
    else:
        flags = re.UNICODE | re.IGNORECASE
    regex = re.compile(pattern, flags)

    for key in dict_:
        if regex.search(key):
            result.extend(_process_object(pattern_path, dict_[key],
                                          case_sensitive=case_sensitive,
                                          **kwargs))
    return result


def read_columns_file(f):
    """Read the JSON file specifying the columns."""
    try:
        columns = json.loads(open(f, 'r').read(),
                             object_pairs_hook=collections.OrderedDict)
    except Exception:
        traceback.print_exc()
        raise Exception("There was an error while reading {0}".format(f))

    # Options are not supported yet:
    if '__options' in columns:
        del columns['__options']

    return columns


def main(args=None):
    # This should:
    # - Read input data from stdin (JSON, also support CSV?)
    # - Print output data to stdout (CSV, JSON lines)
    # - Print errors and diagnostics to stderr, not stdout
    # - Exit with meaningful exit status

    if args is None:
        args = sys.argv[1:]

    # Parse the command-line arguments.
    parser = argparse.ArgumentParser(
        description="Filter, transform and export a list of JSON objects on "
                    "stdin to JSON or CSV on stdout",
    )
    parser.add_argument(
        "--columns",
        help="the JSON file specifying the columns to be output",
        required=True,
    )
    parser.add_argument(
        "-i", "--input",
        help="read input from the given file instead of from stdin",
        dest='input_data',  # Because input is a Python builtin.
    )
    parsed_args = parser.parse_args(args)

    # Read the input data from stdin or a file.
    if parsed_args.input_data:
        input_data = open(parsed_args.input_data, 'r').read()
    else:
        input_data = sys.stdin.read()

    dicts = json.loads(input_data)

    csv_string = table(dicts, parsed_args.columns, csv=True)
    sys.stdout.write(csv_string)


if __name__ == "__main__":
    main()
