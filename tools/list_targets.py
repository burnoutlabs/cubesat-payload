#!/usr/bin/env python3
"""Print one "family units" line per envelope that `just build` renders.

Sizes come from the data (irec.cube_unit.units_max, envelope.cds_units_max),
so adding a size is a data change, not a justfile change.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload_data import DataError, build_targets, load_valid  # noqa: E402


def main() -> int:
    try:
        params = load_valid()
    except DataError as exc:
        print(f"ERROR: data is invalid\n{exc}", file=sys.stderr)
        return 1
    for family, units in build_targets(params):
        print(family, units)
    return 0


if __name__ == "__main__":
    sys.exit(main())
