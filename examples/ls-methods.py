#!/usr/bin/env python3

"""List methods in one or more .NET assemblies."""

import argparse

import dnfile


def _display_value(value):
    return getattr(value, "value", value)


def _iter_rows(table):
    if not table:
        return []
    return table.rows


def _qualified_type_name(type_def_row):
    namespace = _display_value(getattr(type_def_row, "TypeNamespace", None))
    name = _display_value(getattr(type_def_row, "TypeName", None))
    if namespace:
        return f"{namespace}.{name}"
    return name or "(unnamed-type)"


def _method_signature_text(method_row):
    parsed = getattr(method_row, "ParsedSignature", None)
    if parsed is None:
        return "(no-signature)"
    return parsed.to_programmer_string(_display_value(getattr(method_row, "Name", "")))


def list_methods(path):
    pe = dnfile.dnPE(path)
    if pe.net is None or pe.net.mdtables is None:
        print(f"{path}: not a .NET module")
        return

    print(f"---------- {path}")

    for type_def_row in _iter_rows(getattr(pe.net.mdtables, "TypeDef", None)):
        type_name = _qualified_type_name(type_def_row)
        for method_ref in getattr(type_def_row, "MethodList", []) or []:
            method_row = method_ref.row
            if method_row is None:
                continue
            method_name = _display_value(getattr(method_row, "Name", None)) or "(unnamed-method)"
            signature = _method_signature_text(method_row)
            print(f"{type_name}.{method_name}")
            print(f"    {signature}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="List methods and parsed signatures from .NET modules")
    parser.add_argument("input", nargs="+", help="Path(s) to .NET module(s)")
    args = parser.parse_args(argv)

    for path in args.input:
        list_methods(path)


if __name__ == "__main__":
    main()
