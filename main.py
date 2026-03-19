from __future__ import annotations

import os
import sys

import pydicom
from numpy import around
from tabulate import tabulate

from hdrpackage import (
    BrachyPlan,
    PointComparison,
    calculate_dose,
    make_anisotropy_function,
    make_radial_dose,
    make_source_trains,
    read_source_file,
)

RADIAL_DOSE = make_radial_dose(read_source_file("v2r_ESTRO_radialDose.csv"))
ANISOTROPY_FUNCTION = make_anisotropy_function(
    read_source_file("v2r_ESTRO_anisotropyFunction.csv")
)


def _prompt_for_rtplan_path():
    """Prompt until a valid RTPLAN file path is provided."""
    while True:
        input_path = input("Enter RTPLAN DICOM file path: ").strip()
        if input_path.upper() == "QUIT":
            sys.exit()

        if not input_path:
            print("Please enter a file path")
            continue

        full_path = os.path.abspath(os.path.expanduser(input_path))
        if os.path.isfile(full_path):
            return full_path

        print("File not found. Please enter a valid RTPLAN path")


def main():
    print("\nLoading RTPlan from local file...")
    # rtplan_path = _prompt_for_rtplan_path()
    rtplan_path =r"D:\code\TG43\brachy-hdr-tg43-check\tests\data\rtplan.dcm"
    # rtplan_path =r"D:\code\TG43\brachy-hdr-tg43-check\pyTG43\examples\HDR\RP.HDR.dcm"

    ds_input = pydicom.dcmread(rtplan_path)
    try:
        my_plan = BrachyPlan(ds_input)
    except AttributeError:
        print("Dataset could not be opened\nAre you sure it is a brachytherapy plan?")
        sys.exit(1)

    print("RTPlan loaded successfully...")
    my_source_train = make_source_trains(my_plan)

    output_table = []
    for poi in my_plan.points:
        my_dose = calculate_dose(
            my_source_train,
            poi,
            ANISOTROPY_FUNCTION,
            RADIAL_DOSE,
        )
        point_compare = PointComparison(
            point_name=poi.name,
            omp_dose=poi.dose,
            pytg43_dose=my_dose,
        )
        output_table.append(
            [
                poi.name,
                around([poi.dose], decimals=2).tolist()[0],
                around([my_dose], decimals=2).tolist()[0],
                around([point_compare.percentage_difference], decimals=2).tolist()[0],
            ]
        )

    print(f"Dose check results for plan: {my_plan.plan_name}")
    print(
        "\n"
        + tabulate(
            output_table,
            headers=["Point name", "OMP dose (Gy)", "pyTG43 dose (Gy)", "% difference"],
        )
    )


if __name__ == "__main__":
    main()
