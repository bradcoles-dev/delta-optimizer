#!/usr/bin/env python3
"""
Convert Fabric notebook source files (notebook-content.py) to Jupyter .ipynb format
for direct import into Microsoft Fabric workspaces via the Import notebook button.

Usage:
    python scripts/build_notebooks.py

Output is written to Notebooks/dist/. Each file is named after its notebook
directory (e.g. doctor_treatment_maintenance_orchestrator.ipynb) — the filename becomes
the notebook title when imported into Fabric.
"""

import json
import os
import re
import sys

REPO_ROOT     = os.path.join(os.path.dirname(__file__), '..')
NOTEBOOKS_DIR = os.path.join(REPO_ROOT, 'Notebooks')
DIST_DIR      = os.path.join(NOTEBOOKS_DIR, 'dist')

NOTEBOOK_METADATA = {
    "a365ComputeOptions": None,
    "dependencies": {"lakehouse": None},
    "kernel_info": {"jupyter_kernel_name": None, "name": "synapse_pyspark"},
    "language_info": {"name": "python"},
    "sessionKeepAliveTimeout": 0,
}

CODE_CELL_METADATA = {"microsoft": {"language": "python", "language_group": "synapse_pyspark"}}


def parse_cells(content):
    """
    Split notebook-content.py into (cell_type, raw_content) pairs.
    Skips the file header and all METADATA blocks.
    """
    pattern = r'\n# (MARKDOWN|PARAMETERS CELL|CELL|METADATA) \*{10,}\n'
    parts   = re.split(pattern, content)
    # parts[0] = file preamble; subsequent pairs = (marker, content)
    cells = []
    i = 1
    while i < len(parts):
        cell_type    = parts[i].strip()
        cell_content = parts[i + 1] if i + 1 < len(parts) else ''
        i += 2
        if cell_type != 'METADATA':
            cells.append((cell_type, cell_content))
    return cells


def to_markdown_cell(content):
    source = []
    for line in content.split('\n'):
        if line.startswith('# '):
            source.append(line[2:] + '\n')
        elif line == '#':
            source.append('\n')
    while source and source[-1] == '\n':
        source.pop()
    if not source:
        return None
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def to_code_cell(content, is_parameters=False):
    lines = content.split('\n')
    if lines and lines[0] == '':
        lines = lines[1:]
    while lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return None
    source = [line + '\n' for line in lines]
    source[-1] = source[-1].rstrip('\n')
    metadata = dict(CODE_CELL_METADATA)
    if is_parameters:
        metadata = {**metadata, "tags": ["parameters"]}
    return {
        "cell_type":       "code",
        "execution_count": None,
        "metadata":        metadata,
        "outputs":         [],
        "source":          source,
    }


def convert_notebook(notebook_dir):
    source_path = os.path.join(notebook_dir, 'notebook-content.py')
    if not os.path.exists(source_path):
        return None

    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    cells = []
    for cell_type, cell_content in parse_cells(content):
        if cell_type == 'MARKDOWN':
            cell = to_markdown_cell(cell_content)
        elif cell_type == 'PARAMETERS CELL':
            cell = to_code_cell(cell_content, is_parameters=True)
        else:
            cell = to_code_cell(cell_content)
        if cell:
            cells.append(cell)

    return {"cells": cells, "metadata": NOTEBOOK_METADATA, "nbformat": 4, "nbformat_minor": 5}


def main():
    if not os.path.isdir(NOTEBOOKS_DIR):
        print(f"Error: Notebooks directory not found: {NOTEBOOKS_DIR}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(DIST_DIR, exist_ok=True)

    generated, errors = [], []

    for entry in sorted(os.listdir(NOTEBOOKS_DIR)):
        if not entry.endswith('.Notebook'):
            continue
        notebook_dir  = os.path.join(NOTEBOOKS_DIR, entry)
        notebook_name = entry[:-9]  # strip .Notebook suffix

        notebook = convert_notebook(notebook_dir)
        if notebook is None:
            print(f"  Skipped (no notebook-content.py): {entry}", file=sys.stderr)
            errors.append(entry)
            continue

        output_path = os.path.join(DIST_DIR, f'{notebook_name}.ipynb')
        with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(notebook, f, indent=1, ensure_ascii=False)
            f.write('\n')

        print(f"  {notebook_name}.ipynb")
        generated.append(notebook_name)

    print(f"\nGenerated {len(generated)} notebook(s) in Notebooks/dist/")
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
