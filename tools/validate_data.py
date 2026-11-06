#!/usr/bin/env python3
"""Check every TOML file under a data directory against the schema.

Checks: TOML parses (duplicate keys are a parse error), each file has [meta]
with a unique namespace, every leaf has value/unit/kind/source and nothing
else but note, units come from the allowed set, value type matches the unit,
and flattened parameter names are unique across files.

Exit 0 when valid, 1 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload_data import DATA_DIR, REPO, load_all  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("data_dir", nargs="?", type=Path, default=DATA_DIR)
    args = ap.parse_args(argv)
    params, errs = load_all(args.data_dir)
    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"FAILED: {len(errs)} error(s) in {args.data_dir}", file=sys.stderr)
        return 1
    files = len({p["file"] for p in params.values()})
    shown = args.data_dir.resolve()
    shown = shown.relative_to(REPO) if shown.is_relative_to(REPO) else shown
    print(f"OK: {len(params)} parameters from {files} files in {shown}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
