[![Build Status](https://travis-ci.org/ckan/losser.svg)](https://travis-ci.org/ckan/losser)
[![Coverage Status](https://img.shields.io/coveralls/ckan/losser.svg)](https://coveralls.io/r/ckan/losser)
[![Latest Version](https://pypip.in/version/losser/badge.svg)](https://pypi.python.org/pypi/losser/)
[![Downloads](https://pypip.in/download/losser/badge.svg)](https://pypi.python.org/pypi/losser/)
[![Supported Python versions](https://pypip.in/py_versions/losser/badge.svg)](https://pypi.python.org/pypi/losser/)
[![Development Status](https://pypip.in/status/losser/badge.svg)](https://pypi.python.org/pypi/losser/)
[![License](https://pypip.in/license/losser/badge.svg)](https://pypi.python.org/pypi/losser/)


Losser
======

A little UNIX command and Python library for lossy filter, transform, and
export of JSON to Excel-compatible CSV.
Created for [ckanapi-exporter](https://github.com/ckan/ckanapi-exporter).

Losser can either be run as a UNIX command or used as a Python library
(see [Usage](#usage) below). It takes a JSON-formatted list of objects
(or a list of Python dicts) as input and produces a "table" as output.

The input objects don't all have to have the same fields or structure as each
other, and may contain sub-lists and sub-objects arbitrarily nested.

The output "table" is a list of objects that all have the same keys in the same
order, and with sub-objects and sub-lists nested no more than one level deep.
It can be output as:

* A list of Python OrderedDicts each having the same keys in the same order
* A string of JSON-formatted text representing a list of objects each having
  the same keys in the same order
  ([TODO](https://github.com/ckan/losser/issues/3))
* A string of CSV-formatted text, one object per CSV row. The rows of the CSV
  correspond to the objects in the list of output objects if they had been
  returned as Python or JSON Data, and the columns correspond to the objects'
  keys.

The input objects can be filtered and transformed before producing the output
table. You provide a list of "column query" objects in a `columns.json` file
that specifies what columns the output table should have, and how the values
for those columns should be retrieved from the input objects.

For example, if you had some input objects that looked like this:

    [
      {
        "author": "Sean Hammond",
        "title": "An Example Input Object",
        "extras":
          {
            "Delivery Unit": "Commissioning"
          {
      },
      ...
    ]

You might transform them using a `columns.json` file like this:

    {
        "Data Owner": {
            "pattern_path": "^author$"
        },
        "Title": {
            "pattern_path": "^title$"
        },
        "Delivery Unit": {
            "pattern_path": ["^extras$", "^Delivery Unit$"]
        }
    }

This would output a CSV file like this:

    Data Owner,Title,Delivery Unit
    Sean Hammond,An Example Input Object,Commissioning
    Frank Black,Another Example Object,Some Other Unit
    ...

The `columns.json` file above specifies three column headings for the output
table:

1. Data Owner
2. Title
3. Delivery Unit

The values for each column are retrieved from the input objects by following a
"pattern path": a list of regular expressions that are matched against the keys
of the input object and its sub-objects in turn to find a value.

For example the "Data Owner" field above has the pattern path `"^author$"` which
matches the string "author". This will find top-level keys named "author" in
the input objects and output their values in the "Data Owner" column of the
output table.

The "Delivery Unit" column above has a more complex pattern path:
`["^extras$", "^Delivery Unit$"]`. This will find the top-level key "extras" in
an input object and, assuming the value for the "extras" key is a sub-object,
will find and return the value for the "Delivery Unit" key in the sub-object.

Pattern paths can be arbitrarily long, recursing into arbitrarily deeply nested
sub-objects.

One of the patterns in a pattern path may match multiple keys in an object or
sub-object. In that case losser recurses on each of the matched keys and ends
up returning a list of values instead of a single value.

For example given this input object:

    {
      "update": "yearly",
      "update frequency": "monthly",
      ...
    }

The pattern path `"^update.*"` (which matches both "update" and "update
frequency") would output `"yearly, monthly"` (a quoted, comma-separated list)
in the corresponding cell in the CSV output.

If a pattern path goes through a sub-list in the input dict losser will iterate
over the list and recurse on each of its items. Again it will end up returning
a list of values instead of a single value.

For example, given a list of input objects like this:

    [
      {
        "resources": [
          {
            "format": "CSV",
            ...
          },
          {
            "format": "JSON",
            ...
          },
          ...
        ],
        ...
      },
      ...
    ]

The pattern path `["^resources$", "^format$"]` will find each object's
"resources" sub-list and then find the "format" field in each object in the
sub-list. The values in the CSV column will be lists like `"CSV, JSON"`.
List can optionally be deduplicated.

Nested lists can occur (when the input object contains a list of lists, for
example). These are flattened in the output cells.

Some of the filtering and transformations you can do with losser include:

* Extract some fields from the objects and filter out others.

  Any fields in an input object that do not match any of the pattern paths in
  the `columns.json` file are filtered out.

  ([TODO](https://github.com/ckan/losser/issues/2): Support appending unmatched
  fields to the end of the ouput table as additional columns).

* Specify the order of the columns in the output table.

  Columns are output in the same order that they appear in the `columns.json`
  file, which does not have to be the same order as the corresponding fields in
  the input objects.

* Rename fields, using a different name for the column in the output table than
  for the field in the input objects.

  For example to get the "notes" field from each input object and place them
  all in a "description" column in the output table, put this object in your
  `columns.json`:

      "Description": {
        "pattern_path": "^notes$",
      }

* Match patterns case-sensitively.

  By default patterns are matched case-insensitively. To do case-sensitive
  matching put `"case_sensitive": true` in a column query in your
  `columns.json` file:

      "Title": {
        "pattern_path": "^title$",
        "case_sensitive": true
      },

  This will match "title" in the input object, but not "Title" or "TITLE".

* Transform the matched values, for example truncating or stripping whitespace
  from strings.

* Provide arbitrary pre-processor and post-processor functions to do custom
  transformations on the input and output objects
  ([TODO](https://github.com/ckan/losser/issues/1)).

* Find inconsistently-named fields using a pattern that matches any of the
  names and combine them into a single column in the output table.

  For example you can provide a pattern like `"^update.*"` that will find keys
  named "update", "Update", "Update Frequency" etc. in different input objects
  and collect their values in a single "Update Frequency" column.

* Collect multiple fields together in a single column.

  If a pattern matches multiple fields they'll be output as a quoted
  comma-separated list in a single cell in the CSV.

  For example with an input object like this:

      {
        "Contributor 1": "Thom Yorke",
        "Contributor 2": "Nigel Godrich",
        "Contributor 3": "Jonny Greenwood",
        ...
      }

  The pattern `"^Contributor.*"` will match all three fields and the value in
  the CSV cell will be `"Thom Yorke,Nigel Godrich,Jonny Greenwood"`.

* You can specify that a pattern path should find a unique value in the object,
  and if more than one value in the object matches the pattern (and a list
  would be returned) an exception will be raised.

  Use `"unique": true` in a column query in your `columns.json` file:

      "Title": {
        "pattern_path": "^title$",
        "unique": true
      },

  This is useful for debugging pattern paths that you expect to be unique.

* You can specify that a pattern path *must* match a value in the object, and
  an exception will be raised if there's no matching path through the object
  ([TODO](https://github.com/ckan/losser/issues/4)).

* When a pattern matches multiple paths through the input object, or matches a
  path going through a sub-list, the resulting list of values in the output
  table cell can be deduplicated. Put `"deduplicate": true` in a column query
  in your `columns.json` file:

      "Format": {
          "pattern_path": ["^resources$", "^format$"],
          "deduplicate": true
      },


What it can't do (yet):

* Pattern match against the values of items (as opposed to their keys).

  When following a pattern path through an object, when losser hits an
  object/dictionary in the input, either one of the top-level objects in the
  list of input objects or a sub-object, losser matches the relevant regex
  against the object's keys and then recurses on the values of each of the
  matched keys.

  If the key matches the pattern it recurses, you can't also specify a pattern
  to match the value against.

  When it hits a string, number, boolean or ``None``/``null`` losser returns
  it. You can't give it a pattern to match the value against to decide whether
  to return it or not.

  When it hits a list losser iterates over the items in the list and for each
  item either returns it or, if it's a sub-list or sub-object, recurses.
  (When sub-lists or sub-objects would cause a nested list to be returned it's
  flattened into a single list and optionally deduplicated.) Again, you can't
  provide a pattern to be matched against each item to decide whether to
  return/recurse or not.

  Adding pattern matching against values as well as keys would add a lot of
  power.


Requirements
------------

Python 2.7.


Installation
------------

To install run:

    pip install losser

To install for development, create and activate a Python virtual environment
then do:

    git clone https://github.com/ckan/losser.git
    cd losser
    python setup.py develop
    pip install -r dev-requirements.txt


Usage
-----

On the command-line losser reads input objects from stdin and writes the output
table to stdout, making it composable with other UNIX commands. For example:

    losser --columns columns.json < input.json > output.csv

This will read input objects from `input.json`, read column queries from
`columns.json`, and write output objects to `output.csv`.

To use losser as a Python library:

    import losser.losser as losser
    table = losser.table(input_objects, columns)

`input_objects` should be a list of dicts. `columns` can be either a list of
dicts or the path to a `columns.json` file (string). The returned `table` will
be a list of dicts. If you pass `csv=True` to `table()` it'll return a
CSV-formatted string instead. See `table()`'s docstring for more arguments.


Running the Tests
-----------------

First activate your virtualenv then install the dev requirements:

    pip install -r dev-requirements.txt

Then to run the tests do:

    nosetests

To run the tests and produce a test coverage report do:

    nosetests --with-coverage --cover-inclusive --cover-erase --cover-tests
