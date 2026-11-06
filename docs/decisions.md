# Design decisions

One entry per decision: what was chosen, why, and what it leaves open. A
decision changes by adding a new entry that supersedes the old one, not by
editing it.

## D-001: Electronics bus — LibreCube board specification, stacked

- **Date:** 2026-11-05
- **Status:** accepted
- **Issue:** #4 (stays open until the pinout is encoded)

**Decision.** The payload electronics use the
[LibreCube board specification](https://librecube.codeberg.page/docs/standards/board_specification/)
as a stacked mezzanine: CubeSat-Kit-style boards on 16 mm pitch, connected
through the H1/H2 headers, with SpaceCAN as the system bus.

**Why.**

- It is open and published, including the H1/H2 pinout. The CubeSat Kit Bus
  pin table has not been verified against a primary Pumpkin source, and
  LibreCube itself notes that because CubeSat internal boards were never
  formally specified there are many incompatible boards, even among vendors.
- The board outline is already encoded in `data/standards/librecube.toml`, and
  its hole pattern agrees with PC/104 to about 0.1 to 0.3 mm, so the chassis
  work does not depend on the choice of bus.
- PC/104's own bus is ISA, which is irrelevant here.

**Alternative not taken.** A project-defined backplane with slide-in cards
(the BREAD Slice/Loaf substrate, as OreSat-style card cages). IREC DTEG 2027
App. B3.6 allows card cages provided the connector is not the sole support, so
it stays possible; it was not chosen because it means defining and maintaining
a pinout of our own rather than adopting a published one.

**Still to do (#4).** Encode the H1/H2 pinout as its own sourced data file,
with a test that pin numbers are unique and complete, and record the H1 pin 40
naming inconsistency in the published table.

## D-002: Battery — 18650 Li-ion cells in a holder

- **Date:** 2026-11-05
- **Status:** accepted
- **Issue:** #9 (stays open: power budget, holder geometry and arming remain)

**Decision.** Payload power comes from 18650 Li-ion cells (cylindrical metal
cans) in a holder.

**Why.**

- IREC 2027 prohibits LiPo outright and allows Li-ion only in cylindrical
  metal cans, with rectangular holders for cylindrical cells permitted (IREC
  DTEG 2027 REV P1, D&T-6.17.1/6.17.2, applied to payloads by D&T-9.2.2).
- Launch Canada only advises that foil-pack Li-ion/LiPo should have an external
  housing (Launch Canada DTEG R4, appendix item 19.4). A pack that satisfies
  IREC therefore satisfies Launch Canada too.
- The Hyperion-II airbrakes design specified 18650 cells (`DSS.md` in
  [burnoutlabs/Hyperion-II](https://github.com/burnoutlabs/Hyperion-II)).

**Constraints this brings (IREC workmanship).** No Velcro, tie-wrap or tape as
the sole mount; orient the pack so acceleration cannot unplug a connector
(App. B3.5) or compress the holder's contact springs (App. B4.4), so the springs
must not lie along the thrust axis.

**Still to do (#9).** A power budget once electronics exist, holder geometry
generated from data that survives the design loads in `data/loads.toml`, and
the arming/inhibit scheme. An existing 18650 holder generator is GPL-3.0; use
it as an external dependency or rebuild it, and do not vendor it into this
CERN-OHL-W-2.0 repository without a licence decision.
