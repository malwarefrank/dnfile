#!/usr/bin/env python3

"""Print method signatures in a programmer-friendly format.

Example output:
    void MyAssembly.MyModule.Program.Main(string args)
"""

import argparse

import dnfile


def _display_value(value):
    return getattr(value, "value", value)


def _iter_table_rows(table):
    if not table:
        return []
    return table.rows


def _type_def_name(type_def_row):
    type_name = _display_value(getattr(type_def_row, "TypeName", None))
    type_namespace = _display_value(getattr(type_def_row, "TypeNamespace", None))
    if type_namespace:
        return f"{type_namespace}.{type_name}"
    return type_name


def _format_method_parameters(method_row, signature):
    param_names = {}
    for param_ref in getattr(method_row, "ParamList", []) or []:
        param_row = param_ref.row
        if param_row is None:
            continue
        if getattr(param_row, "Sequence", 0) == 0:
            continue
        param_names[param_row.Sequence] = _display_value(param_row.Name)

    rendered = []
    for index, parameter in enumerate(signature.parameters, start=1):
        param_name = f"arg{index}"
        candidate = param_names.get(index)
        if candidate:
            param_name = candidate
        rendered.append(f"{parameter.to_programmer_string()} {param_name}")

    return ", ".join(rendered)


def _format_method_row(assembly_name, module_name, class_name, method_row):
    signature = method_row.ParsedSignature
    if getattr(signature, "kind", None) != "method":
        return str(signature)

    method_name = _display_value(method_row.Name)
    if signature.generic_param_count:
        generic_arguments = ", ".join(f"T{i}" for i in range(signature.generic_param_count))
        method_name = f"{method_name}<{generic_arguments}>"

    parameters = _format_method_parameters(method_row, signature)
    return f"{signature.return_type.to_programmer_string()} {assembly_name}.{module_name}.{class_name}.{method_name}({parameters})"


def render_file(path, verbose=False):
    dn = dnfile.dnPE(path)
    if dn.net is None or dn.net.mdtables is None:
        return

    assemblies = _iter_table_rows(getattr(dn.net.mdtables, "Assembly", None)) or [None]
    modules = _iter_table_rows(getattr(dn.net.mdtables, "Module", None)) or [None]
    type_defs = _iter_table_rows(getattr(dn.net.mdtables, "TypeDef", None))

    for assembly_row in assemblies:
        assembly_name = _display_value(getattr(assembly_row, "Name", None)) if assembly_row else "(no assembly)"
        for module_row in modules:
            module_name = _display_value(getattr(module_row, "Name", None)) if module_row else "(no module)"
            for type_def_row in type_defs:
                class_name = _type_def_name(type_def_row)
                for method_ref in getattr(type_def_row, "MethodList", []) or []:
                    method_row = method_ref.row
                    if method_row is None:
                        continue
                    print(_format_method_row(assembly_name, module_name, class_name, method_row))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print method signatures in a programmer-friendly format.")
    parser.add_argument("input", nargs="+", help="Path(s) to .NET module(s) to inspect")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show more details")
    args = parser.parse_args(argv)

    for path in args.input:
        if args.verbose:
            print(f"Processing {path}...")
        render_file(path, args.verbose)


if __name__ == "__main__":
    main()