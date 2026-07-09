#!/bin/bash

# Regenerate pypi-deps.json from pyproject.toml (the single dependency source).
# Pillow's build needs pybind11 (its build-system.requires), which isn't a
# runtime dep, so it's generated separately and placed first (modules build in
# order, and --no-build-isolation means build deps must already be installed).
set -e
cd "$(dirname "$0")"

flatpak-pip-generator --pyproject-file=../../pyproject.toml --output pypi-deps
flatpak-pip-generator pybind11 --output pybind11-mod

python3 - <<'PY'
import json
import os

with open("pypi-deps.json") as f:
    deps = json.load(f)
with open("pybind11-mod.json") as f:
    deps["modules"].insert(0, json.load(f))
with open("pypi-deps.json", "w") as f:
    json.dump(deps, f, indent=4)
    f.write("\n")
os.remove("pybind11-mod.json")
PY
