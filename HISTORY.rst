=======
History
=======

0.14.1 (2023)
-------------
* fix github workflow

0.14.0 (2023)
-------------
* BREAKING CHANGE: Minimum required Python version is now 3.8
* BUGFIX: ValueError fired before UnicodeDecodeError when parsing assembly resources
* BUGFIX: mdtable row run-lists of size one were being ignored
* BUGFIX: some struct file offsets were RVA values
* FEATURE: Add ``clr_lazy_load`` option for lazy loading Metadata tables and assembly resources
* move from legacy setup.py to pyproject.toml and tox
* bump dev dependencies: mypy and isort
* update tests and examples
* update README badge to use download statistics from pypistats

0.13.0 (2022)
-------------
* BREAKING CHANGE: rename GenericMethod mdtable to MethodSpec per ECMA 335
* parse more resources, even if there are exceptions

0.12.0 (2022)
-------------
* FEATURE: parse ``#Schema`` stream as MetaDataTables
* BUGFIX: MDTableRow off-by-one for end of run
* BUGFIX: MethodSemanticsRow typo list of tables for the Method Index
* more test data

0.11.0 (2022)
-------------
* FEATURE: access .NET resources (not same as PE resources!) by a shortcut
* BUGFIX: dnstrings example
* more attributes default to None
* update dev dependencies
* remove some warnings

0.10.0 (2022)
-------------

* BREAKING CHANGE: structure attributes no longer exist by default
* BREAKING CHANGE: objects' attributes always exist, but may be None
* BUGFIX: use last stream if multiple of same name
* CI: added mypy type checking
* when duplicate stream names, behave like runtime and use last one for shortcuts
* add user_strings shortcut
* able to access MetaDataTables like a 0-based list, with square brackets
* added use of logging module for warnings
* better type hints for IDEs
* more better source comments
* more tests

0.9.0 (2021)
------------

* bugfix: row indices parsed in structures are one-based, not zero-based
* bugfix: TypeDefRow was not parsing Extends coded index
* bugfix: incorrect BLOBS_MASK and add EXTRA_DATA skip if flag set
* added CI using github workflow
* added tests and submodule dnfile-testfiles
* added style consistency using pycodestyle and isort
* added more examples
* parse MetaData tables' list-type indexes into lists of MDTableRow objects

0.8.0 (2021)
------------

* bugfix: Metadata Table indexes (i.e. indexes into other tables) were off by one

0.7.1 (2021)
------------

* bugfix: coded index always None

0.7.0 (2021)
------------

* bugfix: improper data length check

0.6.0 (2021)
------------

* bugfix: referenced wrong object
* parse utf-16 strings in #US stream

0.5.0 (2021-01-29)
------------------

* First release.
