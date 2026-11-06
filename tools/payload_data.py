"""Load, validate and flatten the TOML data in data/. Standard library only.

Schema, per file:

    [meta]                      # required
    namespace = "irec"          # prefix for every generated parameter name
    title = "..."               # required
    note = "..."                # optional; [[meta.documents]] optional

    [some.path]                 # any nesting; a table holding `value` is a leaf
    value = 100.0               # number, bool, string, or a list of them
    unit = "mm"                 # one of UNITS
    kind = "rule"               # one of KINDS
    source = "document + clause, or repo + path"
    note = "..."                # optional

A leaf at [cube_unit.section] in namespace "irec" becomes the OpenSCAD
variable `irec_cube_unit_section`.
"""

from __future__ import annotations

import math
import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data"
PARAMS_SCAD = REPO / "scad" / "generated" / "params.scad"

KINDS = {"rule", "derived", "measured", "estimate", "recommendation"}

# Unit symbol -> meaning. Kept deliberately small; add a unit here, not ad hoc.
UNITS = {
    "mm": "millimetre",
    "m": "metre",
    "kg": "kilogram",
    "lb": "pound (mass)",
    "gram": "gram (mass; 'g' is reserved-looking, so spelled out)",
    "g_n": "standard gravity, 9.80665 m/s^2 (acceleration)",
    "m/s": "metre per second",
    "um": "micrometre",
    "uCi": "microcurie",
    "pts": "competition points",
    "1": "dimensionless number, count or ratio",
    "bool": "boolean flag",
    "text": "string or enumeration",
}

LEAF_REQUIRED = ("value", "unit", "kind", "source")
LEAF_OPTIONAL = ("note",)
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
LB_TO_KG = 0.45359237  # exact, by definition of the international pound

GENERATED_HEADER = (
    "// GENERATED — do not edit.\n"
    "// Source: data/**/*.toml, written by tools/gen_params.py (`just gen`).\n"
    "// Edit the data, regenerate, and commit both. Units and provenance are in\n"
    "// the trailing comment on each line; full notes are in the TOML.\n"
)


class DataError(Exception):
    """Raised when the data cannot be loaded or does not satisfy the schema."""


def data_files(data_dir: Path) -> list[Path]:
    return sorted(p for p in Path(data_dir).rglob("*.toml") if p.is_file())


def _scalar_kind(v: object) -> str | None:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "text"
    return None


def _value_kind(v: object) -> str | None:
    """Return 'bool', 'number', 'text', or None if the shape is not allowed."""
    k = _scalar_kind(v)
    if k:
        return k
    if isinstance(v, list) and v:
        kinds = set()
        for item in v:
            if isinstance(item, list):
                # one level of nesting, numbers only (e.g. hole coordinates)
                if not item or any(_scalar_kind(x) != "number" for x in item):
                    return None
                kinds.add("number")
            else:
                kinds.add(_scalar_kind(item))
        if len(kinds) == 1 and kinds <= {"number", "text"}:
            return kinds.pop()
    return None


def _check_leaf(where: str, leaf: dict) -> list[str]:
    errs = []
    keys = set(leaf)
    missing = [k for k in LEAF_REQUIRED if k not in keys]
    extra = sorted(keys - set(LEAF_REQUIRED) - set(LEAF_OPTIONAL))
    if missing:
        errs.append(f"{where}: missing required field(s): {', '.join(missing)}")
    if extra:
        errs.append(f"{where}: unknown field(s): {', '.join(extra)}")
    unit, kind = leaf.get("unit"), leaf.get("kind")
    if "unit" in keys and unit not in UNITS:
        errs.append(f"{where}: unit {unit!r} not in allowed set {sorted(UNITS)}")
    if "kind" in keys and kind not in KINDS:
        errs.append(f"{where}: kind {kind!r} not in {sorted(KINDS)}")
    for field in ("source", "note"):
        if field in keys:
            s = leaf[field]
            if not isinstance(s, str) or not s.strip():
                errs.append(f"{where}: {field} must be a non-empty string")
            elif field == "source" and "\n" in s:
                errs.append(f"{where}: source must be a single line")
    if "value" in keys:
        vk = _value_kind(leaf["value"])
        if vk is None:
            errs.append(
                f"{where}: value must be a number, bool, string, or a non-empty "
                "list of numbers/strings (or of number lists)"
            )
        elif unit in UNITS:
            expected = {"bool": "bool", "text": "text"}.get(vk)
            if expected and unit != expected:
                errs.append(f"{where}: a {vk} value needs unit {expected!r}, got {unit!r}")
            if vk == "number" and unit in ("bool", "text"):
                errs.append(f"{where}: a numeric value cannot have unit {unit!r}")
    return errs


def _walk(table: dict, path: list[str], rel: str, out: list, errs: list) -> None:
    for key, val in table.items():
        where = f"{rel}: [{'.'.join(path + [key])}]"
        if not NAME_RE.match(key):
            errs.append(f"{where}: key must match {NAME_RE.pattern}")
            continue
        if not isinstance(val, dict):
            errs.append(f"{where}: expected a table with value/unit/kind/source")
            continue
        if "value" in val:
            nested = [k for k, v in val.items() if isinstance(v, dict)]
            if nested:
                errs.append(f"{where}: a leaf cannot also hold sub-tables {nested}")
            errs.extend(_check_leaf(where, val))
            out.append((path + [key], val))
        elif not val:
            errs.append(f"{where}: empty table")
        else:
            _walk(val, path + [key], rel, out, errs)


def load_file(path: Path, root: Path) -> tuple[str | None, list, list[str]]:
    """Return (namespace, [(path_parts, leaf)], errors) for one file."""
    rel = str(Path(path).relative_to(root)) if Path(path).is_relative_to(root) else str(path)
    try:
        with open(path, "rb") as fh:
            doc = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:  # includes duplicate keys
        return None, [], [f"{rel}: TOML error: {exc}"]
    errs: list[str] = []
    meta = doc.pop("meta", None)
    ns = None
    if not isinstance(meta, dict):
        errs.append(f"{rel}: missing [meta] table")
    else:
        ns = meta.get("namespace")
        if not isinstance(ns, str) or not NAME_RE.match(ns):
            errs.append(f"{rel}: meta.namespace must match {NAME_RE.pattern}")
            ns = None
        if not isinstance(meta.get("title"), str) or not meta["title"].strip():
            errs.append(f"{rel}: meta.title must be a non-empty string")
    leaves: list = []
    _walk(doc, [], rel, leaves, errs)
    if not leaves and not errs:
        errs.append(f"{rel}: no parameters")
    return ns, leaves, errs


def load_all(data_dir: Path = DATA_DIR) -> tuple[dict[str, dict], list[str]]:
    """Load every TOML file under data_dir.

    Returns ({flat_name: leaf + {'file': rel}}, errors). Flat names must be
    unique across all files, since they become one OpenSCAD namespace.
    """
    data_dir = Path(data_dir)
    files = data_files(data_dir)
    errs: list[str] = []
    if not files:
        errs.append(f"{data_dir}: no .toml files found")
    params: dict[str, dict] = {}
    namespaces: dict[str, str] = {}
    for f in files:
        rel = str(f.relative_to(data_dir))
        ns, leaves, ferrs = load_file(f, data_dir)
        errs.extend(ferrs)
        if ns is None:
            continue
        if ns in namespaces:
            errs.append(f"{rel}: namespace {ns!r} already used by {namespaces[ns]}")
            continue
        namespaces[ns] = rel
        for parts, leaf in leaves:
            name = "_".join([ns] + parts)
            if name in params:
                errs.append(
                    f"{rel}: [{'.'.join(parts)}] flattens to {name!r}, "
                    f"already defined in {params[name]['file']}"
                )
                continue
            params[name] = dict(leaf, file=rel)
    return params, errs


def load_valid(data_dir: Path = DATA_DIR) -> dict[str, dict]:
    params, errs = load_all(data_dir)
    if errs:
        raise DataError("\n".join(errs))
    return params


# --- OpenSCAD emission ------------------------------------------------------


def scad_literal(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, list):
        return "[" + ", ".join(scad_literal(x) for x in v) + "]"
    raise TypeError(f"cannot express {type(v).__name__} in OpenSCAD")


def render_params(params: dict[str, dict]) -> str:
    lines = [GENERATED_HEADER]
    for name in sorted(params):
        p = params[name]
        lines.append(
            f"{name} = {scad_literal(p['value'])}; "
            f"// {p['unit']}, {p['kind']}: {p['source']}\n"
        )
    return "".join(lines)


# --- Envelope math (mirrors scad/envelope.scad) -----------------------------

BOUNDS = {"max": 1, "nominal": 0, "min": -1}


def lb_to_kg(lb: float) -> float:
    return lb * LB_TO_KG


def envelope_size(params: dict, family: str, units: int, bound: str = "max") -> tuple[float, float, float]:
    """[x, y, z] in mm of the envelope box for a family, size and tolerance bound."""
    v = {k: p["value"] for k, p in params.items()}
    if bound not in BOUNDS:
        raise ValueError(f"bound must be one of {sorted(BOUNDS)}")
    sign = BOUNDS[bound]
    if family == "irec":
        if not 1 <= units <= v["irec_cube_unit_units_max"]:
            raise ValueError(f"irec units must be 1..{v['irec_cube_unit_units_max']}")
        s = v["irec_cube_unit_section"] + sign * v["irec_cube_unit_section_tol"]
        h = v["irec_cube_unit_height_per_u"] * units + sign * v["irec_cube_unit_height_tol"]
    elif family == "cds":
        n = min(v["envelope_cds_units_max"], len(v["cds_rail_length"]))
        if not 1 <= units <= n:
            raise ValueError(f"cds units must be 1..{n}")
        s = v["cds_body_section"] + sign * v["cds_body_section_tol"]
        h = v["cds_rail_length"][units - 1] + sign * v["cds_rail_length_tol"]
    else:
        raise ValueError(f"unknown family {family!r}; expected one of {v['envelope_families']}")
    return (s, s, h)


def min_airframe_id(width: float, depth: float) -> float:
    """Smallest round bore that passes a width x depth rectangle (its diagonal)."""
    return math.hypot(width, depth)


def build_targets(params: dict) -> list[tuple[str, int]]:
    """Every (family, units) pair the data defines, in family order."""
    v = {k: p["value"] for k, p in params.items()}
    limits = {
        "irec": v["irec_cube_unit_units_max"],
        "cds": min(v["envelope_cds_units_max"], len(v["cds_rail_length"])),
    }
    return [(f, n) for f in v["envelope_families"] for n in range(1, limits[f] + 1)]
