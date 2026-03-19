import math
from bisect import bisect_right
from pathlib import Path

import numpy as np


def euclidzip(v1, v2):
    """Fast euclidean distance between two vectors."""

    dist = [(a - b) ** 2 for a, b in zip(v1, v2)]
    return math.sqrt(sum(dist))


def clip_unit_interval(value):
    """Clip a float to the valid domain of arccos."""

    return float(np.clip(value, -1.0, 1.0))


def find_source_spreadsheet(directory, treatment_type=""):
    """Return the most relevant source spreadsheet from a directory."""

    base = Path(directory)
    matches = sorted(base.glob("*.xls"))
    if not matches:
        raise FileNotFoundError(f"No .xls source file found in '{directory}'.")

    treatment_type = treatment_type.lower()
    if treatment_type:
        preferred = [path for path in matches if treatment_type in path.name.lower()]
        if preferred:
            return str(preferred[0])

    return str(matches[0])


def fastinterp(xx, yy):
    """Return a 1D interpolation function with clamped boundaries."""

    xx = np.asarray(xx, dtype=float)
    yy = np.asarray(yy, dtype=float)
    if xx.ndim != 1 or yy.ndim != 1 or len(xx) != len(yy) or len(xx) < 2:
        raise ValueError("fastinterp expects matching 1D arrays with at least two points.")

    def interpout(x):
        if x <= xx[0]:
            return yy[0]
        if x >= xx[-1]:
            return yy[-1]

        index = np.searchsorted(xx, x, side="right")
        x1 = xx[index - 1]
        x2 = xx[index]
        y1 = yy[index - 1]
        y2 = yy[index]

        return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

    return interpout


def bilinearinterp(xi, yi, values):
    """Return a bilinear interpolation function with clamped boundaries."""

    xi = np.asarray(xi, dtype=float)
    yi = np.asarray(yi, dtype=float)
    values = np.asarray(values, dtype=float)

    if len(xi) < 2 or len(yi) < 2:
        raise ValueError("bilinearinterp expects at least two points in each dimension.")
    if values.shape != (len(yi), len(xi)):
        raise ValueError("Interpolation grid shape does not match coordinate arrays.")

    def interpolate(x, y):
        x = float(np.clip(x, xi[0], xi[-1]))
        y = float(np.clip(y, yi[0], yi[-1]))

        i = max(0, min(bisect_right(xi, x) - 1, len(xi) - 2))
        j = max(0, min(bisect_right(yi, y) - 1, len(yi) - 2))

        x1, x2 = xi[i : i + 2]
        y1, y2 = yi[j : j + 2]
        z11, z12 = values[j][i : i + 2]
        z21, z22 = values[j + 1][i : i + 2]

        return (
            z11 * (x2 - x) * (y2 - y)
            + z21 * (x - x1) * (y2 - y)
            + z12 * (x2 - x) * (y - y1)
            + z22 * (x - x1) * (y - y1)
        ) / ((x2 - x1) * (y2 - y1))

    return interpolate
