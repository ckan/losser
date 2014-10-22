import re
import collections


class UniqueError(Exception):
    pass


def table(dicts, columns):
    """Query a list of dicts with a list of queries and return a table.

    A "table" is a list of OrderedDicts each having the same keys in the same
    order.

    """
    table_ = []
    for d in dicts:
        row = collections.OrderedDict()  # The row we'll return in the table.
        for column_title, column_spec in columns.items():
            row[column_title] = query(dict_=d, **column_spec)
        table_.append(row)
    return table_


def query(pattern_path, dict_, max_length=None, strip=False,
          case_sensitive=False, unique=False, deduplicate=False,
          string_transformations=None):
    """Query the given dict with the given pattern path and return the result.

    The ``pattern_path`` is a either a single regular expression string or a
    list of regex strings that will be matched against the keys of the dict and
    its subdicts to find the value(s) in the dict to return.

    The returned result is either a single value (None, "foo", 42, False...)
    or (if the pattern path matched multiple values in the dict) a list of
    values.

    If the dict contains sub-lists or sub-dicts values from these will be
    flattened into a simple flat list to be returned.

    # FIXME: If the pattern path doesn't match the keys in the dict then None
    # is returned, which is indistinguishable from if it matched a path to a
    # key whose value was None. Raise an UnmatchedPathError instead.

    """
    if string_transformations is None:
        string_transformations = []

    if max_length:
        string_transformations.append(lambda x: x[:max_length])

    if isinstance(pattern_path, basestring):
        pattern_path = [pattern_path]

    # Copy the pattern_path because we're going to modify it which can be
    # unexpected and confusing to user code.
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
            raise UniqueError(pattern_path, dict_)
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
