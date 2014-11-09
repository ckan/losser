[![Build Status](https://travis-ci.org/ckan/losser.svg)](https://travis-ci.org/ckan/losser)
[![Coverage Status](https://img.shields.io/coveralls/ckan/losser.svg)](https://coveralls.io/r/ckan/losser)
[![Latest Version](https://pypip.in/version/losser/badge.svg)](https://pypi.python.org/pypi/losser/)
[![Downloads](https://pypip.in/download/losser/badge.svg)](https://pypi.python.org/pypi/losser/)
[![Supported Python versions](https://pypip.in/py_versions/losser/badge.svg)](https://pypi.python.org/pypi/losser/)
[![Development Status](https://pypip.in/status/losser/badge.svg)](https://pypi.python.org/pypi/losser/)
[![License](https://pypip.in/license/losser/badge.svg)](https://pypi.python.org/pypi/losser/)


Losser
======

Losser is a little JSON to CSV converter:

* It takes a list of JSON objects as input and produces a CSV file as output
* The JSON objects don't all have to have the same keys or structure,
  and they may contain sub-objects and sub-lists arbitrarily nested
* Losser can *filter* the JSON objects - finding and exporting some
  fields while ignoring others
* And it can *transform* the objects - renaming and reordering fields,
  truncating and formatting values, combining multiple values into lists,
  deduplicating, etc
* Losser can be used on the command line or as a Python module

Originally created for
[ckanapi-exporter](https://github.com/ckan/ckanapi-exporter).


Installation
------------

To install run:

    pip install losser


Usage
-----

On the command line:

```bash
losser --column "Data Owner" --pattern '^author$' < input.json
```

Losser reads a list of JSON objects from stdin and writes the CSV text to
stdout. `input.json` should be a JSON file containing a list of objects.
The examples in this README use this [input.json file](input.json) (which
contains datasets exported from demo.ckan.org).

Losser will search each object for fields matching the
[regular expression](https://docs.python.org/2/howto/regex.html#regex-howto)
`^author$` and put the values in a column titled "Data Owner".
The output will be a one-column CSV file:

<table>
  <tr>
    <th>Data Owner</th>
  </tr>
  <tr>
    <td>Bundesbank</td>
  </tr>
  <tr>
    <td>Lucy Chambers</td>
  </tr>
  <tr>
    <td>...</td>
  </tr>
</table>

You can add as many columns as you want: just add a `--column` and a
`--pattern` argument for each column. The columns will appear in the order that
you specify them:

```bash
losser --column "Data Owner" --pattern '^author$' \
    --column Maintainer --pattern '^maintainer$' \
    < input.json
```

<table>
  <tr>
    <th>Data Owner</th>
    <th>Maintainer</th>
  </tr>
  <tr>
    <td>Bundesbank</td>
    <td>Rufus Pollock</td>
  </tr>
  <tr>
    <td>Lucy Chambers</td>
    <td>Someone Else</td>
  </tr>
  <tr>
    <td>...</td>
    <td>...</td>
  </tr>
</table>


### Composing with Other Commands

Losser tries to be a good UNIX citizen. It aims to do one thing and do it well,
and to be composable with other UNIX commands using `<`, `>` and `|`:

* Reads input from stdin
* Writes clean, undecorated CSV text to stdout
* Writes errors and help text to stderr not stdout
* Sets exit status to 0 normally or non-zero if something went wrong
* Is always non-interactive


### Finding Fields in Sub-Objects

To export fields from sub-objects use a _pattern path_: a pattern with more
than one argument. Our example JSON objects contain a "tracking_summary"
sub-object with a "total" field:

    [
      {
        "author": "Bundesbank",
        "maintainer": "Rufus Pollock",
        "tracking_summary": {
          "total": 456,
          "recent": 19
        },
        ...
      },
      ...
    ]

To extract this field into a third column:

```bash
losser --column "Data Owner" --pattern '^author$' \
    --column Maintainer --pattern '^maintainer$' \
    --column "Total Views" --pattern '^tracking_summary$' "total" \
    < input.json
```

<table>
  <tr>
    <th>Data Owner</th>
    <th>Maintainer</th>
    <th>Total Views</th>
  </tr>
  <tr>
    <td>Bundesbank</td>
    <td>Rufus Pollock</td>
    <td>456</td>
  </tr>
  <tr>
    <td>Lucy Chambers</td>
    <td>Someone Else</td>
    <td>200</td>
  </tr>
  <tr>
    <td>...</td>
  </tr>
</table>

A pattern path can take any number of arguments to recurse into any depth
sub-objects.


### Finding Fields in Sub-Lists

If one of the patterns in a pattern path lands on a sub-list losser will
iterate over the list and recurse on each item in the list, querying the rest
of the pattern path against each item and eventually returning a list of
results.

Our example objects contain lists of "resource" objects each with a "format"
field, among others:

    [
      {
        "author": "Bundesbank",
        "maintainer": "Rufus Pollock",
        "resources": [
          {
            "description": "CSV file extracted and cleaned from source excel.",
            "format": "CSV",
            ...
          },
          {
            "description": "Original Excel version.",
            "format": "XLS",
            ...
          },
        ],
        ...
      },
      ...
    ]

To extract each of the format fields from each dataset:

```bash
losser --column "Data Owner" --pattern '^author$' \
    --column Maintainer --pattern '^maintainer$' \
    --column "Total Views" --pattern '^tracking_summary$' "total" \
    --column Formats --pattern '^resources$' 'format' \
    < input.json
```

<table>
  <tr>
    <th>Data Owner</th>
    <th>Maintainer</th>
    <th>Total Views</th>
  </tr>
  <tr>
    <td>Bundesbank</td>
    <td>Rufus Pollock</td>
    <td>456</td>
    <td>CSV, XLS</td>
  </tr>
  <tr>
    <td>Lucy Chambers</td>
    <td>Someone Else</td>
    <td>200</td>
    <td>CSV, CSV, JSON, HTML</td>
  </tr>
  <tr>
    <td>...</td>
  </tr>
</table>

List of results are combined into **quoted, comma-separated lists** in the
output CSV.

To remove duplicates from these lists pass the `--deduplicate` option to the
column: `--column Formats --pattern '^resources$' 'format' --deduplicate`.

Column options like `--pattern`, `--deduplicate` etc apply to the preceding
`--column`. See `losser --help` for all the options.

A column query may return a nested list of results, for example if the input
object contains a list of lists. When this happens the nested list is flattened
in the output CSV.


### Matching Multiple Keys with One Pattern

If a pattern matches more than one key in an object, losser will recurse on
each matching key's value, querying the rest of the pattern path against each
value and eventually returning a list of values.

To give a simple example, the pattern `license` will match a number of keys in
our example objects (`license_title`, `license_id` and `license_url`), so
this:

```bash
losser --column "License" --pattern "license" < input.json
```

Will produce this:

<table>
  <tr>
    <th>License</th>
  </tr>
  <tr>
    <td>odc-pddl, Open Data Commons Public Domain Dedication and License (PDDL), http://www.opendefinition.org/licenses/odc-pddl</td>
  </tr>
  <tr>
    <td>cc-by, Creative Commons Attribution, http://www.opendefinition.org/licenses/cc-by</td>
  </tr>
  <tr>
    <td>...</td>
  </tr>
</table>


### Finding Inconsistently Named Keys

Different objects in the input JSON may use different keys for the same field.
For example an "Update Frequency" field that appears as "Update", "update",
"Updated", "Update Frequency", etc in different objects.

To catch all of these fields and put them into a single column in the output
CSV, just supply a pattern that matches all of them:

```bash
losser --column "Update Frequency" --pattern "^update.*" --unique < input.json
```

In this case we're assuming that each object has only one key that matches our
pattern: we don't want any lists of matching values in our CSV cells.
To enforce this we pass the `--unique` option to the column, which will crash
if more than one key matches the pattern.

By default pattern matching is case-insensitive and keys are stripped of
leading and trailing whitespace before matching. To match case-sensitively
and without stripping whitespace, pass the `--case-sensitive --strip false`
options to the column.


### Using a columns.json File

You can specify your columns in a `columns.json` file, instead of giving them
on the command line. For example:

```json
{
  "Data Owner": {
    "pattern": "^author$"
  },
  "Maintainer": {
    "pattern": "^maintainer$"
  },
  "Total Views": {
    "pattern": ["^tracking_summary$", "total"]
  },
  "Formats": {
    "pattern": ["^resources$", "format"],
    "deduplicate": true
  }
}
```

Then to use the file do:

```bash
losser --columns columns.json < input.json
```


### Using Losser from Python

To call losser from Python:

```python
import losser.losser as losser
table = losser.table(input_objects, columns)
```

`input_objects` should be a list of dicts (e.g. from reading a list of JSON
objects with `json.loads()`).

`columns` can be dict of dicts in the same format as the `columns.json` file
above, or the path to a `columns.json` file.

`table()` will return the output CSV as a list of dicts or as a UTF8-encoded,
CSV-formatted string (if you pass `csv=True`).


#### Inheriting Losser's Command Line Interface

Losser's command line interface with `--column` and related arguments is fairly
complicated to implement. You may want to offer the same command line features
in your own losser-based command without having to reimplement them.

For example [ckanapi-exporter](https://github.com/ckan/ckanapi-exporter) offers
the losser command line interface but adds its own `--url` and `--apikey`
arguments to pull the input data directly from a CKAN site instead of reading
it from stdin.

`losser.cli` provides `make_parser()` and `parse()` functions to enable
inheriting its command-line interface. Here's how you use them:

    parent_parser = losser.cli.make_parser(add_help=False, exclude_args=["-i"])
    parser = argparse.ArgumentParser(
        description="Export datasets from a CKAN site to JSON or CSV.",
        parents=[parent_parser],
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--apikey")
    try:
        parsed_args = losser.cli.parse(parser=parser)
    except losser.cli.CommandLineExit as err:
        sys.exit(err.code)
    except losser.cli.CommandLineError as err:
        if err.message:
            parser.error(err.message)
    url = parsed_args.url
    columns = parsed_args.columns
    apikey = parsed_args.apikey
    datasets = get_datasets_from_ckan(url, apikey)
    csv_string = losser.losser.table(datasets, columns, csv=True)

See [ckanapi-exporter](https://github.com/ckan/ckanapi-exporter) for a
working example.


Development
-----------

To install losser for development, create and activate a Python virtual
environment then do:

    git clone https://github.com/ckan/losser.git
    cd losser
    python setup.py develop
    pip install -r dev-requirements.txt

To run the tests do:

    nosetests

To run the tests and produce a test coverage report do:

    nosetests --with-coverage --cover-inclusive --cover-erase --cover-tests
