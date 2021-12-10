#!/usr/bin/env python3

import sys

import dnfile

for fname in sys.argv[1:]:
    # load .NET executable
    pe = dnfile.dnPE(fname)
    # shortcut to the TypeRef table
    tr = pe.net.mdtables.TypeRef
    if not tr or tr.num_rows < 1 or not tr.rows:
        # if empty table (possible error with file), skip file
        continue
    # for each entry in the TypeRef table
    for row in tr:
        # if the ResolutionScope includes a reference to another table
        if row.ResolutionScope and row.ResolutionScope.table:
            # make note of the table name
            res_table = row.ResolutionScope.table.name
            # and resolve it to a string
            res_name = getattr(row.ResolutionScope.row, "Name") or getattr(
                row.ResolutionScope.row, "TypeName"
            )
        else:
            # otherwise
            res_table = None
            res_name = None
        # display the table entry
        if res_table:
            print(
                row.TypeName,
                row.TypeNamespace,
                res_table,
                res_name,
            )
        else:
            print(
                row.TypeName,
                row.TypeNamespace,
            )
