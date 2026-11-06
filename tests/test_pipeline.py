"""Tests for the data -> parameters -> envelope pipeline. Standard library only."""

from __future__ import annotations

import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(TOOLS))

import gen_params  # noqa: E402
import payload_data as pd  # noqa: E402


def gen(*args: str) -> int:
    """Run gen_params in-process with its console output swallowed."""
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        return gen_params.main(list(args))


def run_tool(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS / script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class TestValidator(unittest.TestCase):
    def test_repo_data_is_valid(self):
        params, errs = pd.load_all(pd.DATA_DIR)
        self.assertEqual(errs, [])
        self.assertIn("irec_cube_unit_section", params)

    def test_good_fixture_passes(self):
        params, errs = pd.load_all(FIXTURES / "good")
        self.assertEqual(errs, [])
        self.assertEqual(sorted(params), ["demo_box_enabled", "demo_box_width"])

    def assert_rejected(self, fixture: str, *expected: str):
        _, errs = pd.load_all(FIXTURES / fixture)
        joined = "\n".join(errs)
        for text in expected:
            self.assertIn(text, joined)
        proc = run_tool("validate_data.py", str(FIXTURES / fixture))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("FAILED", proc.stderr)

    def test_rejects_unit_outside_allowed_set(self):
        self.assert_rejected("bad_unit", "unit 'furlong' not in allowed set")

    def test_rejects_missing_source_and_unknown_kind(self):
        self.assert_rejected("bad_missing_field", "missing required field(s): source", "kind 'guess'")

    def test_rejects_duplicate_key(self):
        self.assert_rejected("bad_duplicate_key", "TOML error")

    def test_rejects_flattened_name_collision(self):
        self.assert_rejected("bad_name_collision", "flattens to 'demo_box_inner_width'")

    def test_value_type_must_match_unit(self):
        errs = pd._check_leaf("x", {"value": "abc", "unit": "mm", "kind": "rule", "source": "s"})
        self.assertTrue(any("needs unit 'text'" in e for e in errs), errs)


class TestGenerator(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = self.tmp / "params.scad"

    def test_output_is_deterministic(self):
        first = pd.render_params(pd.load_valid())
        second = pd.render_params(pd.load_valid())
        self.assertEqual(first, second)
        self.assertEqual(gen("--out", str(self.out)), 0)
        on_disk = self.out.read_bytes()
        self.assertEqual(gen("--out", str(self.out)), 0)
        self.assertEqual(self.out.read_bytes(), on_disk)

    def test_header_and_sorted(self):
        text = pd.render_params(pd.load_valid())
        self.assertTrue(text.startswith("// GENERATED — do not edit."))
        names = re.findall(r"^([a-z][a-z0-9_]*) = ", text, flags=re.M)
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), len(set(names)))

    def test_committed_file_is_current(self):
        proc = run_tool("gen_params.py", "--check")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_check_fails_when_missing_or_stale(self):
        self.assertEqual(gen("--check", "--out", str(self.out)), 1)
        self.assertEqual(gen("--out", str(self.out)), 0)
        self.assertEqual(gen("--check", "--out", str(self.out)), 0)
        self.out.write_text(self.out.read_text(encoding="utf-8") + "x = 1;\n", encoding="utf-8")
        self.assertEqual(gen("--check", "--out", str(self.out)), 1)

    def test_check_does_not_write(self):
        gen("--check", "--out", str(self.out))
        self.assertFalse(self.out.exists())


class TestAirframeFit(unittest.TestCase):
    """Envelope cross-section diagonal vs each airframe's [limit] diameters."""

    def setUp(self):
        self.params = pd.load_valid()

    def row(self, limits, family, units, bound):
        rows = pd.fit_rows(self.params, limits, (bound,))
        return next(r for r in rows if r["family"] == family and r["units"] == units)

    def test_irec_min_section_diagonal_does_not_fit_136_bore(self):
        r = self.row({"bore": 136.0}, "irec", 1, "min")
        self.assertEqual(r["section"], 98.0)
        self.assertAlmostEqual(r["diagonal"], 138.59, places=2)
        self.assertAlmostEqual(r["margins"]["bore"], -2.59, places=2)
        self.assertFalse(r["fits"])

    def test_section_fits_a_large_enough_bore(self):
        r = self.row({"bore": 150.0}, "irec", 3, "max")
        self.assertAlmostEqual(r["margins"]["bore"], 150.0 - 102.0 * 2 ** 0.5, places=6)
        self.assertTrue(r["fits"])

    def test_diagonal_equal_to_bore_fits(self):
        d = pd.min_airframe_id(100.0, 100.0)
        self.assertTrue(self.row({"bore": d}, "irec", 2, "nominal")["fits"])

    def test_smallest_limit_governs(self):
        r = self.row({"wide": 200.0, "narrow": 138.0}, "irec", 1, "min")
        self.assertEqual(r["governing"], "narrow")
        self.assertTrue(r["margins"]["wide"] > 0)
        self.assertFalse(r["fits"])

    def test_every_airframe_in_data_is_checked(self):
        airframes = pd.airframe_limits()
        files = sorted((pd.DATA_DIR / "airframes").glob("*.toml"))
        self.assertEqual(len(airframes), len(files))
        n = len(pd.build_targets(self.params)) * 3
        for name, limits in airframes.items():
            with self.subTest(airframe=name):
                self.assertEqual(len(pd.fit_rows(self.params, limits)), n)

    def test_hyperion_ii_fits_no_envelope(self):
        limits = pd.airframe_limits()["hyperion_ii"]
        self.assertEqual(limits, {"nose_cone_straight_id": 136.0, "body_tube_id": 136.0, "bulkhead_diameter": 132.44})
        rows = pd.fit_rows(self.params, limits)
        self.assertEqual([r for r in rows if r["fits"]], [])
        self.assertEqual({r["governing"] for r in rows}, {"bulkhead_diameter"})

    def test_rejects_limit_that_is_not_a_diameter_in_mm(self):
        with self.assertRaises(pd.DataError) as cm:
            pd.airframe_limits(FIXTURES / "bad_airframe_limit")
        self.assertIn("positive diameter in mm", str(cm.exception))

    def test_cli_reports_result_per_airframe(self):
        proc = run_tool("airframe_fit.py")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("== hyperion_ii", proc.stdout)
        self.assertIn("138.59", proc.stdout)
        self.assertIn("NO FIT (bulkhead_diameter)", proc.stdout)
        self.assertIn("0 of 27 family/size/bound combinations fit hyperion_ii", proc.stdout)


class TestEnvelopeMath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params = pd.load_valid()
        cls.v = {k: p["value"] for k, p in cls.params.items()}

    def test_cds_3u_rail_length_exceeds_irec_3u_max(self):
        cds = pd.envelope_size(self.params, "cds", 3, "nominal")
        irec_max = pd.envelope_size(self.params, "irec", 3, "max")
        self.assertEqual(cds[2], 340.5)
        self.assertEqual(irec_max[2], 302.0)
        self.assertGreater(cds[2], irec_max[2])

    def test_irec_bounds(self):
        self.assertEqual(pd.envelope_size(self.params, "irec", 1, "max"), (102.0, 102.0, 102.0))
        self.assertEqual(pd.envelope_size(self.params, "irec", 6, "nominal"), (100.0, 100.0, 600.0))
        self.assertEqual(pd.envelope_size(self.params, "irec", 2, "min"), (98.0, 98.0, 198.0))

    def test_min_id_for_100mm_square(self):
        self.assertAlmostEqual(pd.min_airframe_id(100.0, 100.0), 141.42, places=2)
        self.assertAlmostEqual(
            pd.min_airframe_id(100.0, 100.0), self.v["envelope_min_airframe_id_irec_nominal"], places=2
        )
        s = pd.envelope_size(self.params, "irec", 3, "max")
        self.assertAlmostEqual(
            pd.min_airframe_id(s[0], s[1]), self.v["envelope_min_airframe_id_irec_max"], places=2
        )

    def test_irec_min_mass_in_kg(self):
        kg = pd.lb_to_kg(self.v["irec_payload_mass_min"])
        self.assertAlmostEqual(kg, 1.996, places=3)
        self.assertAlmostEqual(kg, self.v["irec_payload_mass_min_kg"], places=4)

    def test_out_of_range_inputs_raise(self):
        for args in (("irec", 0, "max"), ("irec", 7, "max"), ("cds", 4, "max"), ("cds", 1, "loose"), ("pc104", 1, "max")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                pd.envelope_size(self.params, *args)

    def test_build_targets_follow_data(self):
        targets = pd.build_targets(self.params)
        self.assertIn(("irec", 6), targets)
        self.assertIn(("cds", 3), targets)
        self.assertNotIn(("cds", 4), targets)


# REQUIRE_OPENSCAD=1 (set in CI) turns the skip into a failure.
REQUIRE_OPENSCAD = os.environ.get("REQUIRE_OPENSCAD") == "1"


@unittest.skipUnless(
    shutil.which("openscad") or REQUIRE_OPENSCAD,
    "openscad not installed: SCAD/Python parity not checked",
)
class TestScadParity(unittest.TestCase):
    """The envelope math exists in Python and OpenSCAD; check they agree."""

    def setUp(self):
        if not shutil.which("openscad"):
            self.fail("REQUIRE_OPENSCAD=1 but openscad is not installed")

    ECHO = re.compile(r"size_mm=\[([^\]]+)\] min_airframe_id_mm=([0-9.e+-]+)")

    def scad_envelope(self, family: str, units: int, bound: str):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "e.echo"
            subprocess.run(
                ["openscad", "-o", str(out), "-D", f'FAMILY="{family}"', "-D", f"UNITS={units}",
                 "-D", f'BOUND="{bound}"', str(REPO / "scad" / "envelope.scad")],
                check=True, capture_output=True, text=True,
            )
            m = self.ECHO.search(out.read_text(encoding="utf-8"))
        self.assertIsNotNone(m)
        return [float(x) for x in m.group(1).split(",")], float(m.group(2))

    def test_parity(self):
        params = pd.load_valid()
        for family, units, bound in (("irec", 3, "max"), ("irec", 1, "min"), ("cds", 3, "nominal")):
            with self.subTest(family=family, units=units, bound=bound):
                size, min_id = self.scad_envelope(family, units, bound)
                expected = pd.envelope_size(params, family, units, bound)
                for got, want in zip(size, expected):
                    self.assertAlmostEqual(got, want, places=3)
                self.assertAlmostEqual(min_id, pd.min_airframe_id(expected[0], expected[1]), places=2)


if __name__ == "__main__":
    unittest.main()
