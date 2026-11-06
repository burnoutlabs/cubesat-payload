#!/usr/bin/env python3
"""Generate scad/generated/params.scad from the TOML data.

Output is deterministic: parameters sorted by name, no timestamps. With
--check, write nothing and exit 1 if the file on disk differs from what
would be generated (stale or missing).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload_data import DATA_DIR, PARAMS_SCAD, REPO, DataError, load_valid, render_params  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if the output is stale; write nothing")
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    ap.add_argument("--out", type=Path, default=PARAMS_SCAD)
    args = ap.parse_args(argv)
    try:
        params = load_valid(args.data_dir)
    except DataError as exc:
        print(f"ERROR: data is invalid; run tools/validate_data.py\n{exc}", file=sys.stderr)
        return 1
    text = render_params(params)
    out = args.out
    shown = out.resolve().relative_to(REPO) if out.resolve().is_relative_to(REPO) else out
    if args.check:
        current = out.read_text(encoding="utf-8") if out.exists() else None
        if current != text:
            state = "missing" if current is None else "stale"
            print(f"STALE: {shown} is {state}; run `just gen` and commit it", file=sys.stderr)
            return 1
        print(f"OK: {shown} is up to date")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {shown} ({len(params)} parameters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
