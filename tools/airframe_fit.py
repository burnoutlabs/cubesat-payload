#!/usr/bin/env python3
"""Report which envelope sizes fit each airframe in data/airframes/, with margins.

A section fits when its diagonal is no larger than every [limit] diameter of
the airframe. Margin = limit diameter - section diagonal, in mm; negative means
it does not fit. Cross-section only: no radial clearance, length or nose-cone
taper is checked. Exit status 1 means the data is invalid, not that something
does not fit.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload_data import BOUNDS, DATA_DIR, DataError, airframe_limits, fit_rows, load_valid  # noqa: E402


def _sizes(units: list[int]) -> str:
    return f"{units[0]}U" if len(units) == 1 else f"{units[0]}U-{units[-1]}U"


def report(params: dict, airframes: dict[str, dict[str, float]], bounds: tuple[str, ...]) -> str:
    lines = []
    for name, limits in sorted(airframes.items()):
        lines.append(f"== {name}")
        for lim, d in sorted(limits.items(), key=lambda kv: kv[1]):
            lines.append(f"   limit {lim} = {d:.2f} mm (passes a square of at most {d / math.sqrt(2):.2f} mm)")
        rows = fit_rows(params, limits, bounds)
        # The check is cross-section only, so sizes of one family and bound share a result.
        groups: dict[tuple[str, str], list[dict]] = {}
        for r in rows:
            groups.setdefault((r["family"], r["bound"]), []).append(r)
        names = sorted(limits, key=limits.get)
        lines.append("   " + "  ".join(
            [f"{'family':<7}", f"{'sizes':<6}", f"{'bound':<8}", f"{'section':>8}", f"{'diagonal':>8}"]
            + [f"{'margin ' + n:>{max(len('margin ' + n), 9)}}" for n in names] + ["result"]))
        for (family, bound), rs in groups.items():
            r = rs[0]
            cells = [f"{family:<7}", f"{_sizes([x['units'] for x in rs]):<6}", f"{bound:<8}",
                     f"{r['section']:>8.2f}", f"{r['diagonal']:>8.2f}"]
            cells += [f"{r['margins'][n]:>+{max(len('margin ' + n), 9)}.2f}" for n in names]
            cells.append("FIT" if r["fits"] else f"NO FIT ({r['governing']})")
            lines.append("   " + "  ".join(cells))
        fit = sum(r["fits"] for r in rows)
        lines.append(f"   {fit} of {len(rows)} family/size/bound combinations fit {name}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bound", choices=sorted(BOUNDS), help="check one tolerance bound (default: all)")
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        params = load_valid(args.data_dir)
        airframes = airframe_limits(args.data_dir)
    except DataError as exc:
        print(f"ERROR: data is invalid\n{exc}", file=sys.stderr)
        return 1
    if not airframes:
        print(f"ERROR: no airframes in {args.data_dir / 'airframes'}", file=sys.stderr)
        return 1
    bounds = (args.bound,) if args.bound else ("min", "nominal", "max")
    print(report(params, airframes, bounds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
