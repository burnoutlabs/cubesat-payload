# AGENTS.md

Instructions for AI coding agents working in this repository.

## Project

A modular CubeSat-form-factor payload (chassis, frame, electronics substrate)
for IREC and Launch Canada, designed as code. Currently a stub: sourced
requirements in `data/` flow through a generator into OpenSCAD parameters,
which drive the payload envelope for two families, `irec` (default) and `cds`.

## Stack

- **CAD** — OpenSCAD (not required for `just check`/`just test`; see below)
- **Data** — TOML, read with stdlib `tomllib`
- **Tooling** — Python ≥ 3.11, standard library only; `unittest`; `just`
- **Hooks** — pre-commit with gitleaks and pre-commit-hooks

## Layout

```
data/              every number, with value/unit/kind/source
scad/envelope.scad envelope module, min-airframe-ID function, -D driven render
scad/generated/    params.scad, written by tools/gen_params.py
tools/             payload_data.py (schema, loader, envelope math), CLIs
tests/             unittest suite; fixtures/ holds deliberately bad data
```

## Commands

```sh
just setup        # check python >= 3.11, report openscad
just gen          # regenerate scad/generated/params.scad from data/
just check        # validate + lint + gen --check + airframe fit + openscad check (CI-equivalent)
just test         # python -m unittest
just airframe-fit # envelope fit against data/airframes/, with margins
just build        # render build/*.stl (fails without openscad)
just clean        # remove build/ and caches
```

Run `just check && just test` before every commit.

## Conventions

- **Change data, not generated files.** A dimension or requirement goes in
  `data/` with a real `source`; then `just gen` and commit both.
- **Never hand-edit `scad/generated/`.** `just check` fails if it drifts.
- **No literal dimensions in `scad/`.** Read them from the generated params.
- Mark what a value is: `rule`, `derived`, `measured`, `design`, `estimate`
  or `recommendation`. Never present an estimate as a rule. `design` is an
  existing vehicle's or part's dimension as its design documents state it.
- The envelope math exists twice, in `tools/payload_data.py` and
  `scad/envelope.scad`. Change both; the parity test compares them when
  openscad is installed.
- No third-party Python dependencies.

## Constraints

- Do not commit secrets or credentials.
- Do not add AI attribution to commits or PR descriptions — no co-author
  trailers, session links, or "generated with" footers.
- Do not let a check report success when it could not run. A check that does
  not apply may pass, but must name itself as skipped (as `scad-check` does
  without openscad); one that could not complete must not exit 0.
- Cite only public sources. Do not name or describe private repositories here.
