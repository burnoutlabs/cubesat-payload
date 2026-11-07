# cubesat-payload

A modular, customisable CubeSat-form-factor payload (chassis, frame and
electronics substrate) for student high-power rocketry competitions:
IREC (formerly Spaceport America Cup) and Launch Canada.

## Status

**Stub.** What exists is the pipeline the design will sit on: sourced
requirements as data, a generator that turns them into OpenSCAD parameters,
and the payload envelope (the keep-in volume) for each envelope family, with
tests. There is no chassis design yet.

## Scope

- **In:** the payload chassis and frame, board-stack mounting, the electronics
  substrate's mechanical interface, and the envelope and airframe-fit checks
  they must pass, for both competitions.
- **Out (for now):** payload firmware and science instruments, and the launch
  vehicle itself.

## Design principles

The [Burnout Labs org principles](https://github.com/burnoutlabs/.github)
apply. In this repo they mean:

- **CAD is code.** Geometry is generated from `scad/`. STL, 3MF and STEP are
  build outputs and are never committed.
- **Data-driven.** Dimensions, requirements and configuration live in `data/`
  as TOML. The code consumes them; a variant is a data change.
- **Modular and composable.** One chassis code path serves every envelope
  family; families are selected by configuration.

## Envelope families

Selected with `FAMILY` (`-D 'FAMILY="cds"'`). `irec` is the default for
competition builds.

| | `irec`: ESRA Payload Cube Unit (default) | `cds`: CubeSat Design Spec |
| --- | --- | --- |
| Cross-section | 100 × 100 mm, ±2 mm | 100.0 × 100.0 mm, ±0.1 mm |
| Length | 100·n mm, ±2 mm, n = 1 to 6 (1×1×n) | rail length 113.5 / 227.0 / 340.5 mm for 1U / 2U / 3U |
| 3U length, max | 302 mm | 340.5 mm (+0.1 mm, estimate) |
| Smallest round bore for the max section | 144.25 mm (derived: 102·√2) | 141.56 mm (derived: 100.1·√2) |
| Mass | payload ≥ 4.4 lb (1.996 kg, derived) | ≤ 2.00 / 4.00 / 6.00 kg for 1U / 2U / 3U |
| Source | IREC R&R 2027 REV P1, Table 3-2 and R&R-3.4.1.1 | CDS Rev 14.1, App. B and Table 1 |

The two conflict on length: a CDS 3U overruns the IREC 3U maximum by 38.5 mm.
The IREC figures are from the 2027 REV P1 rules; no 2026 edition could be
found, so check the year that binds your build (see `data/rules/irec-2027-p1.toml`).

## Airframe fit

`just airframe-fit` (also run by `just check`) checks every envelope family,
size and tolerance bound against the round diameters each airframe in
`data/airframes/` lists under `[limit]`. A section fits when its diagonal is
no larger than every limit; the margin is limit minus diagonal. Only the
cross-section is checked: no radial clearance, length or nose-cone taper.

**Hyperion-II** (`data/airframes/hyperion-ii.toml`, from
[burnoutlabs/Hyperion-II](https://github.com/burnoutlabs/Hyperion-II)
`ork/hyperion_II_v3.ork` and `DSS.md`): **no envelope fits.** Its body tubes
and the nose cone's straight section are 136.0 mm ID and the aluminium
bulkhead is Ø132.44 mm, which passes a square of at most 93.65 mm. Even the
smallest IREC section (98 mm, diagonal 138.59 mm) misses the bore by 2.59 mm
and the bulkhead by 6.15 mm. The Hyperion-II DSS sized its payload at 96 mm,
"undersized from 10cm profile to fit existing nosecone", which is below the
IREC minimum. A Payload Cube Unit at its maximum tolerance
needs a bore of at least 144.25 mm plus clearance, i.e. a 6 in class
airframe.

## Layout

```
data/               requirements as TOML: the single source of every number
  rules/            competition rules (IREC, Launch Canada)
  standards/        CDS, PC/104, LibreCube board outline and H1/H2 pinout
  loads.toml        measured, published and recommended design loads
  airframes/        one file per vehicle: the diameters the payload must pass
  envelopes.toml    envelope-family selection
scad/
  envelope.scad     payload_envelope(), min_airframe_id(), top-level render
  generated/        params.scad, generated from data/ (committed, never hand-edited)
tools/              validate_data.py, gen_params.py, list_targets.py, airframe_fit.py (stdlib only)
tests/              unittest suite and validator fixtures
docs/decisions.md   design decisions (electronics bus, battery)
```

## How to run

Needs Python ≥ 3.11 and [`just`](https://github.com/casey/just). OpenSCAD is
needed only to render; `scad/generated/params.scad` is committed so OpenSCAD
users do not need Python.

```sh
just setup    # check python, report whether openscad is installed
just check    # validate data, check params.scad is current, report airframe fit, evaluate scad/ (CI-equivalent)
just test     # unit tests
just airframe-fit  # which envelope sizes fit each airframe, with margins
just build    # render every envelope to build/*.stl (needs openscad)
just gen      # after editing data/: regenerate params.scad, then commit both
```

Without OpenSCAD, `just check` prints `SKIPPED: openscad not installed` for
its OpenSCAD step rather than claiming it passed, and the SCAD/Python parity
test reports itself as skipped. Set `REQUIRE_OPENSCAD=1` to make both fail
instead; CI (`.github/workflows/check.yml`) installs OpenSCAD and sets it, so
the OpenSCAD checks cannot be skipped there.

## Data provenance

Every number has a source. Each entry in `data/` carries `value`, `unit`,
`kind` and `source`, with an optional `note`:

- `source` names the document and clause, or the repository and path, that the
  value comes from.
- `kind` is one of `rule`, `derived`, `measured`, `design`, `estimate` or
  `recommendation`, so a design margin is never mistaken for a requirement.
  `design` is a dimension of an existing vehicle or part as its own design
  documents state it (for example an airframe's bulkhead diameter): a fact
  about that design, not a rule and not a measurement.
- Units come from a fixed set (`tools/payload_data.py`); `just check` rejects
  anything else, a missing field, or a duplicate key.

Measured loads come from the public flight logs in
[burnoutlabs/post-flight-analysis](https://github.com/burnoutlabs/post-flight-analysis).

## Prior work

Earlier team payload work (CAD, reports and test notes held outside GitHub) is
tracked in an issue for import. It is there to learn from, not to port.

## Licence

[CERN-OHL-W-2.0](LICENSE) (CERN Open Hardware Licence Version 2, Weakly Reciprocal).
