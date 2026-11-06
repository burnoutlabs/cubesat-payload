// envelope.scad: the payload envelope box for each envelope family.
//
// This is the keep-in volume a chassis must fit, not a chassis. Every
// dimension comes from generated/params.scad, which tools/gen_params.py
// writes from data/. Do not hard-code a dimension here; add it to data/.
//
// Top-level parameters (override with -D):
//   FAMILY         "irec" = ESRA Payload Cube Unit, 100 n mm +/- 2 (default,
//                  from envelope_default_family); "cds" = CubeSat Design Spec,
//                  rail lengths 113.5 / 227.0 / 340.5 mm
//   UNITS          size in U: irec 1..irec_cube_unit_units_max,
//                  cds 1..envelope_cds_units_max
//   BOUND          "max" = nominal + tolerance, "nominal", "min" = nominal - tolerance
//   SHOW_AIRFRAME  true ghosts the smallest round bore that passes the section
//
// Example:
//   openscad -D 'FAMILY="cds"' -D UNITS=3 -D 'BOUND="max"' -o cds-3u.stl scad/envelope.scad
//
// Library use: `use <envelope.scad>` gives payload_envelope(),
// payload_envelope_size() and min_airframe_id() without the top-level render.

include <generated/params.scad>

FAMILY = envelope_default_family;
UNITS = 3;
BOUND = "max";
SHOW_AIRFRAME = false;

// +1, 0 or -1: which side of the tolerance band to take.
function _bound_sign(bound) =
    bound == "max" ? 1 : bound == "nominal" ? 0 : bound == "min" ? -1 : undef;

// [x, y, z] in mm of the envelope for a family, size and bound.
function payload_envelope_size(family = "irec", units = 3, bound = "max") =
    let (sgn = _bound_sign(bound))
    assert(!is_undef(sgn), str("BOUND must be \"max\", \"nominal\" or \"min\", got ", bound))
    assert(is_num(units) && units == floor(units), str("UNITS must be a whole number, got ", units))
    family == "irec"
        ? assert(units >= 1 && units <= irec_cube_unit_units_max,
                 str("irec UNITS must be 1..", irec_cube_unit_units_max, ", got ", units))
          let (s = irec_cube_unit_section + sgn * irec_cube_unit_section_tol,
               h = irec_cube_unit_height_per_u * units + sgn * irec_cube_unit_height_tol)
          [s, s, h]
    : family == "cds"
        ? assert(units >= 1 && units <= min(envelope_cds_units_max, len(cds_rail_length)),
                 str("cds UNITS must be 1..", envelope_cds_units_max, ", got ", units))
          let (s = cds_body_section + sgn * cds_body_section_tol,
               h = cds_rail_length[units - 1] + sgn * cds_rail_length_tol)
          [s, s, h]
    : assert(false, str("FAMILY must be one of ", envelope_families, ", got ", family));

// Smallest airframe inner diameter that passes a [width, depth] cross-section:
// its diagonal. No radial clearance is added.
function min_airframe_id(section) = norm([section[0], section[1]]);

// The envelope as a solid, centred on the Z axis, base on Z = 0.
module payload_envelope(family = "irec", units = 3, bound = "max") {
    size = payload_envelope_size(family, units, bound);
    translate([-size.x / 2, -size.y / 2, 0]) cube(size);
}

// --- Top-level render ---------------------------------------------------------

_size = payload_envelope_size(FAMILY, UNITS, BOUND);
echo(str("ENVELOPE family=", FAMILY, " units=", UNITS, " bound=", BOUND,
         " size_mm=", _size, " min_airframe_id_mm=", min_airframe_id(_size)));

payload_envelope(FAMILY, UNITS, BOUND);
if (SHOW_AIRFRAME)
    %cylinder(d = min_airframe_id(_size), h = _size.z, $fn = 96);
