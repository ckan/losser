# -*- coding: utf-8 -*-
import collections
import os.path
import inspect

import nose.tools

import losser


def test_number():
    assert losser.query([], 42) == 42


def test_string():
    assert losser.query([], "foo") == "foo"


def test_string_with_strip():
    assert losser.query([], " foo  ", strip=True) == "foo"


def test_string_with_transform():
    string_transformations = [lambda x: x[:3]]
    result = losser.query([], "foobar",
                            string_transformations=string_transformations)
    assert result == "foo"


# TODO: Test list with multiple string transformations.


def test_string_with_strip_and_transform():
    string_transformations = [lambda x: x[:3]]
    result = losser.query([], " foobar  ", strip=True,
                            string_transformations=string_transformations)
    assert result == "foo"


def test_unicode_string():
    string_transformations = [lambda x: x[:3]]
    result = losser.query([], u" fübar  ", strip=True,
                            string_transformations=string_transformations)
    assert result == u"füb"


def test_boolean():
    assert losser.query([], False) == False


def test_none():
    assert losser.query([], None) == None


def test_top_level_string_single_match():
    assert losser.query("^title$", {"title": "my title"}) == "my title"


def test_top_level_string_multiple_matches():
    d = collections.OrderedDict(
        title="my dataset",
        last_updated="recently",
        update_frequency="quite often",
    )
    losser.query("update", d) == ["recently", "quite often"]


def test_top_level_string_no_matches():
    d = collections.OrderedDict(
        title="my dataset",
        last_updated="recently",
        update_frequency="quite often",
    )
    assert losser.query("maintainer", d) is None


def test_terminal_value_is_list_of_scalars():
    """If the pattern path terminates at a list that list is returned as is."""
    d = collections.OrderedDict(
        title="my dataset",
        last_updated="recently",
        update_frequency="quite often",
        resources=[1, 2, 3]
    )
    assert losser.query("^resources$", d) == [1, 2, 3]


# TODO: What if it terminates at a dict? A dict of lists? A list of dicts?


def test_sub_dict_with_one_match():
    d = collections.OrderedDict(
        title="my dataset",
        extras=dict(
            foo="bar",
            something_else="some other thing",
        )
    )
    pattern = ["^extras$", "foo"]
    assert losser.query(pattern, d) == "bar"


def test_sub_dict_with_no_matches():
    d = collections.OrderedDict(
        title="my dataset",
        extras=dict(
            foo="bar",
            something_else="some other thing",
        )
    )
    pattern = ["^extras$", "foobar"]
    assert losser.query(pattern, d) is None


def test_sub_dict_with_multiple_matches():
    d = collections.OrderedDict(
        title="my dataset",
        extras=dict(
            foo="bar",
            foo_again="bah",
        )
    )
    pattern = ["^extras$", "foo"]
    assert losser.query(pattern, d) == ["bar", "bah"]


def test_list_of_dicts():
    d = collections.OrderedDict(
        title="my dataset",
        resources=[dict(format="CSV"), dict(format="JSON"), dict(foo="bar")],
    )
    pattern = ["^resources$", "format"]
    result = losser.query(pattern, d)
    assert result == ["CSV", "JSON"]


def test_list_of_dicts_multiple_matches():
    """Test processing a list of dicts when some of the individual dicts have
    multiple matches."""
    d = collections.OrderedDict(
        title="my dataset",
        resources=[
            collections.OrderedDict((
                ("format", "CSV"), ("formatting", "commas"))),
            collections.OrderedDict((
                ("format", "JSON"), ("formatting", "pretty printed"))),
            dict(foo="bar")
        ],
    )
    pattern = ["^resources$", "format"]
    result = losser.query(pattern, d)
    assert result == ["CSV", "commas", "JSON", "pretty printed"]


def test_case_sensitive_matching():
    d = collections.OrderedDict(
        title="my dataset",
        extras=dict(
            Title="the right title",
            title="the wrong title",
            something_else="some other thing",
        )
    )
    pattern = ["^extras$", "Title"]
    assert losser.query(pattern, d, case_sensitive=True) == "the right title"


def test_dict_of_lists():
    d = collections.OrderedDict((
        ("foo", [1, 2, 3]),
        ("bar", [4, 5, 6]),
        ("foobar", ["a", "b", "c"]),
    ))
    assert losser.query("foo", d) == [1, 2, 3, "a", "b", "c"]


def test_list_of_lists():
    d = {"foo": [[1, 2, 3], [4, 5, 6], ["a", "b", "c"]]}
    result =  losser.query("foo", d)
    assert result == [1, 2, 3, 4, 5, 6, "a", "b", "c"]


def test_tuples():
    """Test that tuples are treated the same as lists."""
    d = {"foo": ((1, 2, 3), (4, 5, 6), ("a", "b", "c"))}
    result =  losser.query("foo", d)
    assert result == [1, 2, 3, 4, 5, 6, "a", "b", "c"]


def test_unique():
    """Test the unique option."""
    d = collections.OrderedDict(
        title="my dataset",
        last_updated="recently",
        update_frequency="quite often",
    )

    nose.tools.assert_raises(losser.UniqueError, losser.query, "update", d,
                             unique=True)


def test_deduplicate():
    """Test the deduplicate option."""
    d = collections.OrderedDict(
        title="my dataset",
        resources=[dict(format="CSV"), dict(format="CSV"),
                   dict(format="JSON")],
    )
    pattern = ["^resources$", "format"]
    result = losser.query(pattern, d,  deduplicate=True)
    assert result == ["CSV", "JSON"]


def test_table():
    rows = [
        dict(title="dataset one", extras=dict(update="hourly")),
        dict(title="dataset two", extras=dict(Updated="daily")),
        dict(title="dataset three", extras={"Update Frequency": "weekly"}),
    ]
    columns = {
        "Title": dict(pattern_path="^title$"),
        "Update Frequency": dict(pattern_path=["^extras$", "update"]),
    }

    table = losser.table(rows, columns)

    assert table == [
        {"Title": "dataset one", "Update Frequency": "hourly"},
        {"Title": "dataset two", "Update Frequency": "daily"},
        {"Title": "dataset three", "Update Frequency": "weekly"},
    ]


# TODO: Test table when input dicts have different keys. Output dicts should
# all have the same keys (one key for each input column).

def test_append_unused_keys():
    """Test the append_unused_keys option.

    The values for any top-level keys in the input row that were not matched
    by any of the patterns are appended to the end of the output row.

    """
    return  # TODO
    rows = [
        dict(title="dataset one",
             author="Mr. Author One",
             description="A long description one",
             extras=dict(update="hourly"),
        ),
        dict(title="dataset two",
             author="Mr. Author One",
             description="A long description one",
             another_key="another value",
             extras=dict(Updated="daily"),
        ),
        dict(title="dataset three",
             author="Mr. Author One",
             description="A long description one",
             another_unused_key="An unused value",
             extras={"Update Frequency": "weekly"},
        ),
    ]
    columns = {
        "Title": dict(pattern_path="^title$"),
        "Update Frequency": dict(pattern_path=["^extras$", "update"]),
    }

    table = losser.table(rows, columns, append_unused=True)

    assert table == [
        {"Title": "dataset one",
         "Update Frequency": "hourly",
         "author": "Mr. Author One",
         "description": "A long description one",
        },
        {"Title": "dataset two",
         "Update Frequency": "daily",
         "author": "Mr. Author One",
         "description": "A long description one",
         "another_key": "another value",
        },
        {"Title": "dataset three",
         "Update Frequency": "weekly",
         "author": "Mr. Author One",
         "description": "A long description one",
         "another_unused_key": "An unused value",
        },
    ]


def test_blacklist():
    """Test the blacklist option.

    When the append_unused_keys option is used, keys listed in the blacklist
    will not be appended.

    """
    return  # TODO
    rows = [
        dict(title="dataset one",
             author="Mr. Author One",
             description="A long description one",
             extras=dict(update="hourly"),
             secret="secret",
        ),
        dict(title="dataset two",
             author="Mr. Author One",
             description="A long description one",
             another_key="another value",
             extras=dict(Updated="daily"),
             secret="secret",
        ),
        dict(title="dataset three",
             author="Mr. Author One",
             description="A long description one",
             another_unused_key="An unused value",
             extras={"Update Frequency": "weekly"},
             top_secret="secret",
        ),
    ]
    columns = {
        "Title": dict(pattern_path="^title$"),
        "Update Frequency": dict(pattern_path=["^extras$", "update"]),
    }
    blacklist = ["secret", "top_secret"]

    table = losser.table(rows, columns, append_unused=True,
                         blacklist=blacklist)

    for row in table:
        for key in blacklist:
            assert key not in row


# TODO: Move this test to losser.query() tests.
def test_max_length():
    """Test the max_length option."""
    max_length = 5
    rows = [dict(title="A really really long title")]
    columns = {"Title": dict(pattern_path="^title$", max_length=max_length)}

    table = losser.table(rows, columns)

    assert len(table[0]["Title"]) <= max_length


def _this_directory():
    """Return the path to this Python file's directory.

    Return the full filesystem path to the directory containing this Python
    source code file.

    """
    return os.path.dirname(os.path.abspath(
        inspect.getfile(inspect.currentframe())))


def test_table_from_file():
    """Test table() when reading columns from file."""

    rows = [
        {
            "author": "Guybrush Threepwood",
            "notes": "Test row 1",
            "resources": [
                {"format": "CSV"},
                {"format": "JSON"},
            ],
        },
        {
            "author": "LeChuck",
            "notes": "Test row 2",
            "resources": [
                {"format": "XLS"},
                {"format": "XLS"},
            ],
        },
        {
            "author": "Herman Toothrot",
            "notes": "Test row 3",
            "resources": [
                {"format": "PDF"},
                {"format": "TXT"},
            ],
        },
    ]
    path = os.path.join(_this_directory(), "test_columns.json")

    table = losser.table(rows, path)

    assert table == [
        {
            "Data Owner": "Guybrush Threepwood",
            "Description": "Test row 1",
            "Formats": ["CSV", "JSON"],
        },
        {
            "Data Owner": "LeChuck",
            "Description": "Test row 2",
            "Formats": ["XLS"],
        },
        {
            "Data Owner": "Herman Toothrot",
            "Description": "Test row 3",
            "Formats": ["PDF", "TXT"],
        },
    ]
