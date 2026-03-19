import os
from multiprocessing import Pool

import numpy as np
from pydicom.tag import Tag
from terminaltables import AsciiTable

from .models import DosePoint, Plan
from .source import Source


_source = None
_plan = None


def tpsComp(rp, rs, directory, show_plot=False, verbose=False):
    """Calculate and compare dose at reference points with TPS."""

    points = []

    source = Source(rp, directory, verbose=verbose)
    if show_plot:
        source.plot_g()
    plan = Plan(source, rp, rs)

    for point in rp[0x300A, 0x10]:
        if Tag(0x300A, 0x18) in point.keys():
            x, y, z = point[0x300A, 0x18].value
            name = point[0x300A, 0x16].value
            ref = point[0x300A, 0x12].value
            points.append(
                DosePoint([x / 10, y / 10, z / 10], source, plan, name=name, ref=ref)
            )

    table_data = [["Name", "X", "Y", "Z", "TPS (Gy)", "Calc (Gy)", "Diff (%)"]]
    for point in points:
        diff = float("nan")
        if point.tpsdose:
            diff = (1 - (point.dose / point.tpsdose)) * 100
        table_data.append(
            [
                point.name,
                f"{point.x:.2f}",
                f"{point.y:.2f}",
                f"{point.z:.2f}",
                f"{point.tpsdose:.3f}",
                f"{point.dose:.3f}",
                f"{diff:.3f}",
            ]
        )

    print(AsciiTable(table_data).table)
    return points


def _pcalc(point):
    """Parallel DosePoint calculation helper function."""

    return DosePoint(point, _source, _plan).dose


def calcDVHs(sourcei, plani, maxd, names):
    """Calculate cumulative DVHs for selected structures."""

    global _source
    global _plan

    _source = sourcei
    _plan = plani

    pool = Pool() if os.name != "nt" else None
    target_names = {name.lower() for name in names}

    try:
        for roi in _plan.ROIs:
            if not roi.name or roi.name.lower() not in target_names:
                continue
            if not getattr(roi, "dvhpts", None):
                roi.dvh = np.empty((0, 2))
                continue

            if pool is None:
                dvh = [DosePoint(point, _source, _plan).dose for point in roi.dvhpts]
            else:
                dvh = pool.map(_pcalc, roi.dvhpts)

            if not dvh:
                roi.dvh = np.empty((0, 2))
                continue

            counts, bins = np.histogram(dvh, 100, range=(0, maxd))
            cumulative = np.cumsum(counts[::-1])[::-1]
            cumulative = cumulative / cumulative.max() * 100
            roi.dvh = np.column_stack((bins[:-1], cumulative))
    finally:
        if pool is not None:
            pool.close()
            pool.join()
