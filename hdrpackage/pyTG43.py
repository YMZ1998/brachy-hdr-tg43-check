"""Perform TG43 calculations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import interpolate
from scipy.spatial.distance import pdist

from hdrpackage.source_data import AnisotropyFunction, RadialDose


def find_nearest(array: np.ndarray, value: float) -> float:
    """Return the closest value in an array."""
    return array[(np.abs(array - value)).argmin()]


@dataclass(frozen=True)
class PointPosition:
    """Special point location in centimeters."""

    x: float
    y: float
    z: float

    @property
    def coords(self) -> list[float]:
        return [self.x, self.y, self.z]


@dataclass(frozen=True)
class SourcePosition:
    """Source description data for a dwell position."""

    x: float
    y: float
    z: float
    apparent_activity: float
    dwell_time: float
    Sk: float
    dose_rate_constant: float
    L: float
    t_half: float

    @property
    def coords(self) -> list[float]:
        return [self.x, self.y, self.z]

    @property
    def dwellTime(self) -> float:  # legacy compatibility
        return self.dwell_time

    @property
    def Aapp(self) -> float:  # legacy compatibility
        return self.apparent_activity


def get_geometry_function(my_source: SourcePosition, my_point: PointPosition):
    """Calculate the geometry function."""
    r_ref = 1  # cm
    theta_ref = np.pi / 2  # 90 degrees
    beta_ref = 2 * np.arctan((my_source.L / 2) / r_ref)
    gl_ref = beta_ref / (my_source.L * r_ref * np.sin(theta_ref))

    r2 = pdist(
        [
            [my_source.x, my_source.y, my_source.z],
            [my_point.x, my_point.y, my_point.z - (my_source.L / 2)],
        ]
    )
    r1 = pdist(
        [
            [my_source.x, my_source.y, my_source.z],
            [my_point.x, my_point.y, my_point.z + (my_source.L / 2)],
        ]
    )
    r = pdist(
        [
            [my_source.x, my_source.y, my_source.z],
            [my_point.x, my_point.y, my_point.z],
        ]
    )

    theta1 = np.arccos((my_point.z - my_source.z + (my_source.L / 2)) / r1)
    theta2 = np.arccos((my_point.z - my_source.z - (my_source.L / 2)) / r2)
    theta = np.arccos((my_point.z - my_source.z) / r)

    if theta == 0 or theta == np.pi:
        gl = 1 / (r**2 - (my_source.L**2 / 4))
    else:
        beta = np.abs(theta2 - theta1)
        gl = beta / (my_source.L * r * np.sin(theta))

    return gl / gl_ref


def log_interp(xdata, ydata, xnew):
    """Perform log-linear interpolation."""
    return np.exp(np.interp(np.log(xnew), np.log(xdata), np.log(ydata)))


def linear_interp_2d(xdata, ydata, zdata, xnew, ynew):
    """Perform linear 2D interpolation."""
    return interpolate.interp2d(xdata, ydata, zdata, kind="linear")(xnew, ynew)


def get_radial_dose(
    radial_dose_in: RadialDose,
    dwell_in: SourcePosition,
    point_in: PointPosition,
):
    """Calculate the radial dose function value."""
    r = pdist(
        [[dwell_in.x, dwell_in.y, dwell_in.z], [point_in.x, point_in.y, point_in.z]]
    )
    if r in radial_dose_in.r_cm:
        return radial_dose_in.gL[radial_dose_in.r_cm.index(r)]
    if r > max(radial_dose_in.r_cm) or r < min(radial_dose_in.r_cm):
        nearest_radius = find_nearest(np.array(radial_dose_in.r_cm), r)
        return radial_dose_in.gL[radial_dose_in.r_cm.index(nearest_radius)]
    return log_interp(radial_dose_in.r_cm, radial_dose_in.gL, r)


def get_anisotropy_function(
    anisotropy_function: AnisotropyFunction,
    my_source: SourcePosition,
    my_point: PointPosition,
):
    """Calculate the anisotropy function value."""
    r = pdist(
        [[my_source.x, my_source.y, my_source.z], [my_point.x, my_point.y, my_point.z]]
    )
    theta = np.degrees(np.arccos((my_point.z - my_source.z) / r))

    if r in anisotropy_function.r_cm and theta in anisotropy_function.theta:
        return anisotropy_function.F[
            anisotropy_function.theta.index(theta),
            anisotropy_function.r_cm.index(r),
        ]

    if (
        r > max(anisotropy_function.r_cm)
        or r < min(anisotropy_function.r_cm)
        or theta > max(anisotropy_function.theta)
        or theta < min(anisotropy_function.theta)
    ):
        nearest_r = find_nearest(np.array(anisotropy_function.r_cm), r)
        nearest_theta = find_nearest(np.array(anisotropy_function.theta), theta)
        return anisotropy_function.F[
            anisotropy_function.theta.index(nearest_theta),
            anisotropy_function.r_cm.index(nearest_r),
        ]

    return linear_interp_2d(
        anisotropy_function.r_cm,
        anisotropy_function.theta,
        anisotropy_function.F,
        r,
        theta,
    )


@dataclass(frozen=True)
class DosePoint:
    """Calculated dose contribution for one source-point pair."""

    my_source: SourcePosition
    my_point: PointPosition
    radial_dose_value: float
    anisotropy_function_value: float
    geometry_function_value: float
    dose_rate_out: float
    dose_total_out: float


def calculate_my_dose(
    my_source: SourcePosition,
    my_point: PointPosition,
    anisotropy_function: AnisotropyFunction,
    radial_dose_function: RadialDose,
) -> DosePoint:
    """Calculate the total dose at a point for one dwell."""
    radial_dose_val = get_radial_dose(radial_dose_function, my_source, my_point)
    anisotropy_func_val = get_anisotropy_function(
        anisotropy_function, my_source, my_point
    )
    geometry_func_val = get_geometry_function(my_source, my_point)
    dose_rate_out = (
        my_source.Sk
        * my_source.dose_rate_constant
        * geometry_func_val
        * anisotropy_func_val
        * radial_dose_val
        * (1 / 100)
    )
    dose_total_out = dose_rate_out * (my_source.dwell_time / (60 * 60))
    return DosePoint(
        my_source=my_source,
        my_point=my_point,
        radial_dose_value=radial_dose_val,
        anisotropy_function_value=anisotropy_func_val,
        geometry_function_value=geometry_func_val,
        dose_rate_out=dose_rate_out,
        dose_total_out=dose_total_out,
    )


def make_source_trains(source_class):
    """Create a flat list of dwell source positions from a brachy plan."""
    source_train = []
    for channel in source_class.channels:
        for source in channel:
            source_train.append(
                SourcePosition(
                    x=source.coords[0] / 10,
                    y=source.coords[2] / 10,
                    z=source.coords[1] / 10,
                    apparent_activity=10,
                    dwell_time=source.dwell_time,
                    Sk=source_class.ref_air_kerma_rate,
                    dose_rate_constant=1.108,
                    L=0.35,
                    t_half=source_class.half_life,
                )
            )
    return source_train


def point_from_poi(poi_in) -> PointPosition:
    """Convert a plan point of interest into TG43 coordinate order."""
    return PointPosition(
        poi_in.coords[0] / 10,
        poi_in.coords[2] / 10,
        poi_in.coords[1] / 10,
    )


def calculate_dose(
    source_train_in,
    poi_in,
    anisotropy_func: AnisotropyFunction,
    radial_dose: RadialDose,
) -> float:
    """Calculate total dose at a point of interest."""
    dose = 0
    my_point = point_from_poi(poi_in)
    for dwell in source_train_in:
        my_dose = calculate_my_dose(dwell, my_point, anisotropy_func, radial_dose)
        dose += my_dose.dose_total_out
    return dose.tolist()[0]
