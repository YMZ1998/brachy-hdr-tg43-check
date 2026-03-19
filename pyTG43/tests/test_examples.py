from pathlib import Path

import pydicom

from pyTG43 import pyTG43


ROOT = Path(__file__).resolve().parents[1]


def run_tps_comp(plan_path, struct_path, source_dir):
    rp = pydicom.dcmread(ROOT / plan_path)
    rs = pydicom.dcmread(ROOT / struct_path)
    return pyTG43.tpsComp(rp, rs, str(ROOT / source_dir))


def test_hdr_example_matches_tps():
    points = run_tps_comp("examples/HDR/RP.HDR.dcm", "examples/HDR/RS.HDR.dcm", "examples/HDR")
    assert len(points) == 2
    assert all(abs((1 - (point.dose / point.tpsdose)) * 100) < 0.1 for point in points)


def test_pdr_example_matches_tps():
    points = run_tps_comp("examples/PDR/RP.PDR.dcm", "examples/PDR/RS.PDR.dcm", "examples/PDR")
    assert len(points) == 2
    assert all(abs((1 - (point.dose / point.tpsdose)) * 100) < 0.2 for point in points)


def test_rotated_example_stays_within_reasonable_tolerance():
    points = run_tps_comp("examples/rotated/RP.dcm", "examples/rotated/RS.dcm", "examples/HDR")
    assert len(points) == 2
    assert all(abs((1 - (point.dose / point.tpsdose)) * 100) < 3.0 for point in points)


def test_tps_dvh_stats_are_numeric():
    rp = pydicom.dcmread(ROOT / "examples/PDR/RP.PDR.dcm")
    rs = pydicom.dcmread(ROOT / "examples/PDR/RS.PDR.dcm")
    rd = pydicom.dcmread(ROOT / "examples/PDR/RD.PDR.dcm")

    source = pyTG43.Source(rp, str(ROOT / "examples/PDR"))
    plan = pyTG43.Plan(source, rp, rs, rd)

    ctv = next(roi for roi in plan.ROIs if roi.name == "ctv")
    ctv.get_TPS_DVH(rp, rs, rd)

    assert isinstance(ctv.tpsmin, float)
    assert isinstance(ctv.tpsmax, float)
    assert isinstance(ctv.tpsmean, float)
    assert ctv.tpsmin <= ctv.tpsmean <= ctv.tpsmax
    assert ctv.tpsdvh.size > 0
