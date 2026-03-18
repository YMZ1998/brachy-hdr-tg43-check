"""Classes for holding parsed data from an RTPlan file."""

from __future__ import annotations

from dataclasses import dataclass


class BrachyPlan:
    def __init__(self, ds):
        self.ds = ds
        application_setup = ds.ApplicationSetupSequence[0]
        source = ds.SourceSequence[0]

        self.applicator = application_setup[0x300B, 0x100F].value
        self.points = self.get_poi()
        self.channel_numbers = self.get_channel_numbers()
        self.prescription = float(
            ds.FractionGroupSequence[0]
            .ReferencedBrachyApplicationSetupSequence[0]
            .BrachyApplicationSetupDose
        )
        self.treatment_model = ds.TreatmentMachineSequence[0].TreatmentMachineName
        self.ref_air_kerma_rate = float(source.ReferenceAirKermaRate)
        self.channels = self.get_channel_dwell_times()
        self.total_number_dwells = sum(len(channel) for channel in self.channels)
        self.half_life = float(source.SourceIsotopeHalfLife)
        self.patient_id = ds.PatientID
        self.plan_name = ds.RTPlanLabel

    @property
    def application_setup(self):
        return self.ds.ApplicationSetupSequence[0]

    def get_channel_numbers(self):
        return [
            int(channel.SourceApplicatorID)
            for channel in self.application_setup.ChannelSequence
        ]

    def get_poi(self):
        return [self.Point(point) for point in self.ds.DoseReferenceSequence]

    def get_channel_dwell_times(self):
        channel_dwells = []
        for channel in self.application_setup.ChannelSequence:
            total_channel_time = float(channel.ChannelTotalTime)
            control_points = channel.BrachyControlPointSequence
            number_of_dwells = int(channel.NumberOfControlPoints / 2)

            dwell_weights = []
            dwells_list = []
            for index in range(0, len(control_points), 2):
                start = float(control_points[index].CumulativeTimeWeight)
                end = float(control_points[index + 1].CumulativeTimeWeight)
                dwell_weights.append(end - start)
                dwells_list.append(control_points[index])

            dwell_times = [
                (total_channel_time / number_of_dwells) * weight
                for weight in dwell_weights
            ]
            channel_dwells.append(
                [
                    self.Dwell(control_sequence, dwell_time, dwell_weight)
                    for control_sequence, dwell_time, dwell_weight in zip(
                        dwells_list,
                        dwell_times,
                        dwell_weights,
                    )
                ]
            )
        return channel_dwells

    @dataclass(frozen=True)
    class Point:
        name: str
        coords: list[float]
        dose: float

        def __init__(self, ds_sequence):
            object.__setattr__(self, "name", ds_sequence.DoseReferenceDescription)
            object.__setattr__(
                self,
                "coords",
                [float(value) for value in ds_sequence.DoseReferencePointCoordinates],
            )
            object.__setattr__(self, "dose", float(ds_sequence.TargetPrescriptionDose))

    @dataclass(frozen=True)
    class Dwell:
        coords: list[float]
        dwell_time: float
        time_weight: float

        def __init__(self, control_sequence, d_time, d_weight):
            object.__setattr__(
                self,
                "coords",
                [float(value) for value in control_sequence.ControlPoint3DPosition],
            )
            object.__setattr__(self, "time_weight", d_weight)
            object.__setattr__(self, "dwell_time", d_time)


@dataclass(frozen=True)
class PointComparison:
    point_name: str
    omp_dose: float
    pytg43_dose: float

    @property
    def abs_difference(self) -> float:
        return self.omp_dose - self.pytg43_dose

    @property
    def percentage_difference(self) -> float:
        return 100 * ((self.omp_dose / self.pytg43_dose) - 1)
