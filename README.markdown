[![Build Status](https://travis-ci.org/ckan/losser.svg)](https://travis-ci.org/ckan/losser)
[![Coverage Status](https://img.shields.io/coveralls/ckan/losser.svg)](https://coveralls.io/r/ckan/losser)


Losser
======

A little UNIX command and Python library for lossy filter, transform, and
export of JSON to JSON or CSV.

TODO: Detailed explanation.


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


Usage
-----

TODO: How to use on command-line and from Python.


Running the Tests
-----------------

First activate your virtualenv then install the dev requirements:

    pip install -r dev-requirements.txt

Then to run the tests do:

    nosetests

To run the tests and produce a test coverage report do:

    nosetests --with-coverage --cover-inclusive --cover-erase --cover-tests
