from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SOURCE_FILES_DIR = Path(__file__).resolve().parent / "source_files"


@dataclass(frozen=True)
class RadialDose:
    """Radial dose function tabulated by radius in centimeters."""

    r_cm: list[float]
    gL: list[float]


@dataclass(frozen=True)
class AnisotropyFunction:
    """Anisotropy function tabulated by angle and radius."""

    r_cm: list[float]
    theta: list[float]
    F: np.ndarray


def read_file(full_path: str | Path) -> list[list[str]]:
    """Read a CSV file into a list of rows."""
    with Path(full_path).open("r", newline="") as in_file:
        return list(csv.reader(in_file))


def read_source_file(filename: str) -> list[list[str]]:
    """Read a bundled TG43 source data CSV file."""
    return read_file(SOURCE_FILES_DIR / filename)


def make_radial_dose(radial_dose_raw: list[list[str]]) -> RadialDose:
    """Create the radial dose function from raw CSV data."""
    values = [(float(row[0]), float(row[1])) for row in radial_dose_raw[1:]]
    r_cm, gL = zip(*values)
    return RadialDose(list(r_cm), list(gL))


def make_anisotropy_function(
    anisotropy_function_raw: list[list[str]],
) -> AnisotropyFunction:
    """Create the anisotropy function from raw CSV data."""
    theta = [float(row[0]) for row in anisotropy_function_raw[2:]]
    r_cm = [float(value) for value in anisotropy_function_raw[1][1:]]

    F = np.empty((len(theta), len(r_cm)))
    F.fill(np.nan)
    for row_index, row in enumerate(anisotropy_function_raw[2:]):
        for col_index, value in enumerate(row[1:]):
            if value:
                F[row_index, col_index] = float(value)

    return AnisotropyFunction(r_cm=r_cm, theta=theta, F=F)
