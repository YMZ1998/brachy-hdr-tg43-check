import numpy as np

import pyTG43


def test_fastinterp_clamps_to_bounds():
    interp = pyTG43.fastinterp([0.2, 1.0, 2.0], [2.0, 4.0, 8.0])

    assert interp(0.1) == 2.0
    assert interp(0.2) == 2.0
    assert interp(1.5) == 6.0
    assert interp(3.0) == 8.0


def test_bilinearinterp_handles_edges_and_out_of_range_inputs():
    interp = pyTG43.bilinearinterp(
        [0.0, 1.0],
        [0.0, 1.0],
        np.array([[1.0, 2.0], [3.0, 4.0]]),
    )

    assert interp(0.0, 0.0) == 1.0
    assert interp(1.0, 1.0) == 4.0
    assert interp(-1.0, 0.5) == 1.5
    assert interp(0.5, 2.0) == 3.0


def test_find_source_spreadsheet_prefers_matching_treatment_type(tmp_path):
    (tmp_path / "source-hdr.xls").write_text("", encoding="ascii")
    (tmp_path / "source-pdr.xls").write_text("", encoding="ascii")

    match = pyTG43.find_source_spreadsheet(tmp_path, "PDR")

    assert match.endswith("source-pdr.xls")
