#!/usr/bin/env python3
"""
Script to convert a params.json file (conforming to schemas/params-schema.json)
into individual YAML files for each parameter (conforming to schemas/udb_param_schema.json).

Usage:
    python tools/export_params_to_udb.py -i params.json -o outdir
    python tools/export_params_to_udb.py --input params.json --output-dir outdir

Arguments:
    -i, --input       Path to params.json input file (required)
    -o, --output-dir  Directory to write YAML files (required)
    -h, --help        Show this help message and exit

Each output YAML file will be named <PARAM_NAME>.yaml (upper-case).
"""
import argparse
import os
from pathlib import Path
import sys
import yaml

# Allow import from parent directory if run as a script or from test
try:
    from tools.shared_utils import make_log_helpers, load_json_object
except ModuleNotFoundError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
    from shared_utils import make_log_helpers, load_json_object

def main():
    parser = argparse.ArgumentParser(
        description="Convert params.json to UDB YAML files. Each output YAML file will be named <PARAM_NAME>.yaml (upper-case)."
    )
    parser.add_argument('-i', '--input', required=True, metavar='FILE', help='Path to params.json input file')
    parser.add_argument('-o', '--output-dir', required=True, metavar='DIR', help='Directory to write YAML files')
    args = parser.parse_args()

    error, info, fatal = make_log_helpers("export_params_to_udb.py")

    # Load input JSON
    params_data = load_json_object(args.input, fatal)
    parameters = params_data.get('parameters')
    if not isinstance(parameters, list):
        fatal("Input JSON does not contain a 'parameters' array.")

    # Prepare output directory
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    for param in parameters:
        name = param.get('name')
        if not name:
            fatal("Parameter missing 'name'")
        if 'long-name' not in param:
            fatal(f"Parameter '{name}' missing 'long-name'")
        out_name = f"{name.upper()}.yaml"
        out_path = outdir / out_name

        # Compose description: combine description and note if both exist
        desc = param.get('description', '')
        note = param.get('note', '')
        if desc and note:
            description = f"{desc}\nNOTE: {note}"
        elif desc:
            description = desc
        elif note:
            description = f"NOTE: {note}"
        else:
            description = ''

        # Build definedBy property from extension impl-defs and their instances
        defined_by = None
        impl_defs = param.get('impl-defs', [])
        extension_names = []
        for impldef in impl_defs:
            kind = impldef.get('kind')
            if kind == 'extension':
                instances = impldef.get('instances')
                if isinstance(instances, list):
                    for ext_name in instances:
                        if isinstance(ext_name, str):
                            extension_names.append(ext_name)
            elif kind == 'base':
                # Treat 'base' as an extension named 'I'
                extension_names.append('I')
        if not extension_names:
            extension_names = ['I']
        if len(extension_names) == 1:
            defined_by = {"extension": {"name": extension_names[0]}}
        else:
            defined_by = {"extension": {"anyOf": [{"name": n} for n in extension_names]}}

        # Map input to output schema
        out_obj = {
            "$schema": "param_schema.json#",
            "kind": "parameter",
            "name": name,
            "long_name": param['long-name'],
            "description": description,
            "schema": param.get('json-schema', {}),
        }
        if defined_by is not None:
            out_obj["definedBy"] = defined_by
        # Optionally add $source if available
        if 'def_filename' in param:
            out_obj["$source"] = param['def_filename']
        # Optionally add requirements if present
        if 'requirements' in param:
            out_obj['requirements'] = param['requirements']

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('---\n')
            yaml.safe_dump(out_obj, f, sort_keys=False, allow_unicode=True)
        info(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
