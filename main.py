#!/usr/bin/env python

from hdrpackage.parse_omp_rtplan import BrachyPlan, PointComparison
from hdrpackage.pyTG43 import *
import dicom
from tabulate import tabulate
import os
import sys
from numpy import around


def _prompt_for_rtplan_path():
    """Prompt until a valid RTPLAN file path is provided."""
    while True:
        input_path = input("Enter RTPLAN DICOM file path: ").strip()
        if input_path.upper() == 'QUIT':
            sys.exit()

        if not input_path:
            print("Please enter a file path")
            continue

        full_path = os.path.abspath(os.path.expanduser(input_path))
        if os.path.isfile(full_path):
            return full_path

        print("File not found. Please enter a valid RTPLAN path")


def main():
    """Main function for TG43 dose check."""

    print(tabulate([
        ["v0.1 VCC"],
        ["Enter 'quit' at any time to exit program"],
        ['']
    ], headers=["HDR Brachytherapy Dose Check"]))

    rtplan_path = _prompt_for_rtplan_path()
    print("\nLoading RTPlan from local file...")

    ds_input = dicom.read_file(rtplan_path)
    try:
        my_plan = BrachyPlan(ds_input)
    except AttributeError:
        print("Dataset could not be opened\nAre you sure it is a brachytherapy plan?")
        sys.exit()

    print("RTPlan loaded successfully...")
    my_source_train = make_source_trains(my_plan)
    points_of_interest = my_plan.points

    output_table = []
    for poi in points_of_interest:
        my_dose = calculate_dose(my_source_train, poi)
        point_compare = PointComparison(
            point_name=poi.name,
            omp_dose=poi.dose,
            pytg43_dose=my_dose
        )
        output_table.append([
            poi.name,
            around([poi.dose], decimals=2).tolist()[0],
            around([my_dose], decimals=2).tolist()[0],
            around([point_compare.percentage_difference], decimals=2).tolist()[0]
        ])

    print("Dose check results for plan: %s" % my_plan.plan_name)
    print("\n" + tabulate(
        output_table,
        headers=["Point name", "OMP dose (Gy)", "pyTG43 dose (Gy)", "% difference"]
    ))


if __name__ == '__main__':
    main()
