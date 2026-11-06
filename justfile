# Project task runner: cubesat-payload

set dotenv-load := false

# Linewise recipes only (no shebang recipes): those need a writable runtime dir
set shell := ["bash", "-euo", "pipefail", "-c"]

python := "python3"

# Default: show available recipes
default:
    @just --list

# Verify python >= 3.11 (tomllib) and report whether openscad is installed
setup:
    @{{ python }} -c 'import sys; v = sys.version_info; sys.exit(f"FAIL: python >= 3.11 required (tomllib), found {v.major}.{v.minor}") if v < (3, 11) else print(f"OK: python {v.major}.{v.minor}.{v.micro}")'
    @if command -v openscad >/dev/null 2>&1; then \
        echo "OK: $(openscad --version 2>&1)"; \
    else \
        echo "NOTE: openscad not installed; 'just check' will skip its OpenSCAD step and 'just build' will fail"; \
    fi

# Regenerate scad/generated/params.scad from data/ (commit the result)
gen:
    {{ python }} tools/gen_params.py

# Check data/ against the schema (fields, units, kinds, duplicate keys)
validate:
    {{ python }} tools/validate_data.py

# Fail if scad/generated/params.scad does not match data/
gen-check:
    {{ python }} tools/gen_params.py --check

# Parse every Python file (syntax gate; writes nothing; no third-party linter)
lint:
    @{{ python }} -c 'import ast, pathlib; fs = sorted(pathlib.Path(".").glob("t*/**/*.py")); [ast.parse(f.read_text(encoding="utf-8"), str(f)) for f in fs]; print(f"OK: {len(fs)} Python files parse")'

# Evaluate every scad/*.scad with openscad; prints SKIPPED if not installed
scad-check:
    @if ! command -v openscad >/dev/null 2>&1; then \
        echo "SKIPPED: openscad not installed (scad-check did not run)"; \
    else \
        tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT; \
        for f in scad/*.scad; do \
            openscad --hardwarnings -o "$tmp/$(basename "$f" .scad).echo" "$f" || exit 1; \
            echo "OK: $f"; \
        done; \
    fi

# Validate + lint + generated-file freshness + OpenSCAD check (non-mutating, CI-equivalent)
check: validate lint gen-check scad-check

# Run the unit tests
test:
    {{ python }} -m unittest discover -s tests -v

# Render every envelope the data defines to build/*.stl (requires openscad)
build: gen-check
    @command -v openscad >/dev/null 2>&1 || { echo "FAIL: openscad not installed; 'just build' cannot render (https://openscad.org/downloads.html)" >&2; exit 1; }
    @targets="$({{ python }} tools/list_targets.py)"; \
    mkdir -p build; \
    while read -r family units; do \
        out="build/${family}-${units}u-max.stl"; \
        openscad --hardwarnings -o "$out" -D "FAMILY=\"$family\"" -D "UNITS=$units" -D 'BOUND="max"' scad/envelope.scad || exit 1; \
        echo "wrote $out"; \
    done <<< "$targets"

# Remove build outputs and Python caches
clean:
    rm -rf build
    find . -type d -name __pycache__ -prune -exec rm -rf {} +
