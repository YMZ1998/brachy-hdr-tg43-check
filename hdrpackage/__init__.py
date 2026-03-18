from __future__ import annotations

from importlib import import_module

__all__ = [
    "AnisotropyFunction",
    "BrachyPlan",
    "PointComparison",
    "PointPosition",
    "RadialDose",
    "SourcePosition",
    "calculate_dose",
    "calculate_my_dose",
    "get_anisotropy_function",
    "get_geometry_function",
    "get_radial_dose",
    "make_anisotropy_function",
    "make_radial_dose",
    "make_source_trains",
    "omp_connect",
    "point_from_poi",
    "read_file",
    "read_source_file",
]

_EXPORTS = {
    "BrachyPlan": ("hdrpackage.parse_omp_rtplan", "BrachyPlan"),
    "PointComparison": ("hdrpackage.parse_omp_rtplan", "PointComparison"),
    "PointPosition": ("hdrpackage.pyTG43", "PointPosition"),
    "SourcePosition": ("hdrpackage.pyTG43", "SourcePosition"),
    "calculate_dose": ("hdrpackage.pyTG43", "calculate_dose"),
    "calculate_my_dose": ("hdrpackage.pyTG43", "calculate_my_dose"),
    "get_anisotropy_function": ("hdrpackage.pyTG43", "get_anisotropy_function"),
    "get_geometry_function": ("hdrpackage.pyTG43", "get_geometry_function"),
    "get_radial_dose": ("hdrpackage.pyTG43", "get_radial_dose"),
    "make_source_trains": ("hdrpackage.pyTG43", "make_source_trains"),
    "point_from_poi": ("hdrpackage.pyTG43", "point_from_poi"),
    "AnisotropyFunction": ("hdrpackage.source_data", "AnisotropyFunction"),
    "RadialDose": ("hdrpackage.source_data", "RadialDose"),
    "make_anisotropy_function": ("hdrpackage.source_data", "make_anisotropy_function"),
    "make_radial_dose": ("hdrpackage.source_data", "make_radial_dose"),
    "read_file": ("hdrpackage.source_data", "read_file"),
    "read_source_file": ("hdrpackage.source_data", "read_source_file"),
    "omp_connect": ("hdrpackage.omp_connect", None),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = _EXPORTS[name]
    module = import_module(module_name)
    value = module if attribute_name is None else getattr(module, attribute_name)
    globals()[name] = value
    return value
