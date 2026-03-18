# ruff: noqa: E402
from pathlib import Path

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")
pydicom = pytest.importorskip("pydicom")

from context import (
    BrachyPlan,
    PointComparison,
    calculate_dose,
    get_geometry_function,
    get_radial_dose,
    make_anisotropy_function,
    make_radial_dose,
    make_source_trains,
    point_from_poi,
    read_source_file,
)

RADIAL_DOSE = make_radial_dose(read_source_file("v2r_ESTRO_radialDose.csv"))
ANISOTROPY_FUNCTION = make_anisotropy_function(
    read_source_file("v2r_ESTRO_anisotropyFunction.csv")
)
TEST_DATA_PATH = Path(__file__).resolve().parent / "data" / "test_data.dcm"


class TestBrachyPlan:
    @classmethod
    def setup_class(cls):
        ds_input = pydicom.dcmread(TEST_DATA_PATH)
        cls.plan = BrachyPlan(ds_input)
        cls.source_train = make_source_trains(cls.plan)
        cls.points_of_interest = cls.plan.points
        cls.point = point_from_poi(cls.points_of_interest[0])

    def test_plan_can_be_loaded(self):
        assert self.plan is not None

    def test_patient_demographics(self):
        assert self.plan.patient_id == "PL001"
        assert self.plan.plan_name == "GYN"

    def test_source_train_length(self):
        assert len(self.source_train) == 2

    def test_poi_location(self):
        assert self.points_of_interest[0].coords == [-26.263365, -6.806701, -94.109772]

    def test_dwell_time(self):
        assert self.source_train[0].dwellTime == 33.72160035605183

    def test_channel_numbers(self):
        assert self.plan.channel_numbers == [1, 3]

    def test_prescription(self):
        assert self.plan.prescription == 7.1

    def test_radial_dose_function(self):
        assert RADIAL_DOSE.gL[0] == 1.3732
        radial_dose_val = get_radial_dose(RADIAL_DOSE, self.source_train[0], self.point)
        assert radial_dose_val == 1.0071058807379062

    def test_anisotropy_function_supports_calculation(self):
        dose = calculate_dose(
            self.source_train,
            self.points_of_interest[0],
            ANISOTROPY_FUNCTION,
            RADIAL_DOSE,
        )
        assert dose > 0

    def test_geometry_function(self):
        my_geometry_function = get_geometry_function(self.source_train[0], self.point)
        assert my_geometry_function == 0.1357340295176392

    def test_total_dose_calculation(self):
        output_table = []
        for poi in self.points_of_interest:
            my_dose = calculate_dose(
                self.source_train,
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
                    poi.dose,
                    my_dose,
                    point_compare.percentage_difference,
                ]
            )

        assert output_table == [
            ["A1", 7.157785, 7.204668479752138, -0.650737502827492],
            ["A2", 7.042215, 7.0942845357605915, -0.7339645808977835],
            ["Bladder", 3.872681, 4.09607914018399, -5.453950779231176],
            ["ICRU", 3.510379, 3.364742911392422, 4.32829765728846],
        ]
