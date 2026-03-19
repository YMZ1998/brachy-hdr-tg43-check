from datetime import datetime

import numpy as np
import pandas as pd
from scipy import interpolate

from Iridium192 import Ir_192


def Extraction(RT_Plan):
    Catheters = list()
    for j in range(len(RT_Plan.ApplicationSetupSequence[0].ChannelSequence)):
        total_time = RT_Plan.ApplicationSetupSequence[0].ChannelSequence[j].ChannelTotalTime
        total_time_weight = RT_Plan.ApplicationSetupSequence[0].ChannelSequence[j].FinalCumulativeTimeWeight

        Catheter = RT_Plan.ApplicationSetupSequence[0].ChannelSequence[j].BrachyControlPointSequence
        cum_time = 0
        time_dwell = 0
        Position = []
        for i in range(len(Catheter)):
            raw_time_dwell = Catheter[i].CumulativeTimeWeight - cum_time
            cum_time = Catheter[i].CumulativeTimeWeight

            if raw_time_dwell != 0:
                dwell = Catheter[i].ControlPoint3DPosition
                time_dwell = round(10 * raw_time_dwell * total_time / total_time_weight, 2)
                dwell.append(time_dwell)
                Position.append(np.array(dwell) / 10)

        Position = pd.DataFrame(Position, columns=['x', 'y', 'z', 'time'])
        Catheters.append(Position)

    points = RT_Plan.DoseReferenceSequence
    Calc_Matrix = []
    for k in range(len(points)):
        calc_point = np.array(points[k].DoseReferencePointCoordinates) / 10
        Calc_Matrix.append(calc_point)

    IcruDosePoints = pd.DataFrame(
        [(x.DoseReferenceDescription, round(100 * float(x.TargetPrescriptionDose), 2)) for x in points],
        columns=['Points', 'Plan (cGy)'])

    rawPlanDate = RT_Plan.SourceSequence[0].SourceStrengthReferenceDate
    rawPlanTime = RT_Plan.SourceSequence[0].SourceStrengthReferenceTime

    PlanDate = datetime(int(rawPlanDate[:4]), int(rawPlanDate[4:6]), int(rawPlanDate[6:8]), int(rawPlanTime[:2]),
                        int(rawPlanTime[2:4]))

    return (Catheters, Calc_Matrix, PlanDate, IcruDosePoints)


def Dose_Rate(Position, calc_point, fuente, PlanDate):
    deltaPlanCal = (PlanDate - fuente.CalDate).days + (PlanDate - fuente.CalDate).seconds / (24 * 3600)

    Sk = fuente.RAKR * np.exp(-np.log(2) * deltaPlanCal / fuente.MeanLife)
    r = calc_point - Position
    a = pd.DataFrame([Position.loc[i, ['x', 'y', 'z']] - Position.loc[i + 1, ['x', 'y', 'z']] if i != len(
        Position) - 1 else Position.loc[i - 1, ['x', 'y', 'z']] - Position.loc[i, ['x', 'y', 'z']] for i in
                      range(len(Position))])
    r_dot_a = [r.iloc[i].dot(a.iloc[i]) for i in range(len(r))]
    r['modulo_r'] = r.apply(lambda x: np.linalg.norm(x), axis='columns')
    a['modulo_a'] = a.apply(lambda x: np.linalg.norm(x), axis='columns')

    theta = [np.degrees(np.arccos(r_dot_a[i] / (r.modulo_r[i] * a.modulo_a[i]))) for i in range(len(r_dot_a))]

    a_norm = a[['x', 'y', 'z']].apply(lambda x: x / np.linalg.norm(x), axis='columns')

    r1 = calc_point - (Position - a_norm * fuente.length / 20)
    r1_dot_a = [r1.iloc[i].dot(a[['x', 'y', 'z']].iloc[i]) for i in range(len(r1))]
    r1['modulo_r1'] = r1.apply(lambda x: np.linalg.norm(x), axis='columns')
    theta_1 = np.array(
        [np.degrees(np.arccos(r1_dot_a[i] / (r1.modulo_r1[i] * a.modulo_a[i]))) for i in range(len(r1_dot_a))])

    r2 = calc_point - (Position + a_norm * fuente.length / 20)
    r2_dot_a = [r2.iloc[i].dot(a[['x', 'y', 'z']].iloc[i]) for i in range(len(r2))]
    r2['modulo_r2'] = r2.apply(lambda x: np.linalg.norm(x), axis='columns')
    theta_2 = np.array(
        [np.degrees(np.arccos(r2_dot_a[i] / (r2.modulo_r2[i] * a.modulo_a[i]))) for i in range(len(r2_dot_a))])

    beta = np.radians(theta_2 - theta_1)

    GL0 = 2 * np.arctan(fuente.length / 20) / (fuente.length / 10)
    GL_r_th = np.array([1 / (r.modulo_r[i] ** 2 - (fuente.length / 20) ** 2) if (theta[i] == 0 or theta[i] == 180) else
                        beta[i] / ((fuente.length / 10) * r.modulo_r[i] * np.sin(np.radians(theta[i]))) for i in
                        range(len(beta))])

    g_r = np.interp(r.modulo_r * 10, fuente.RadialDoseFuntion['r(mm)'], fuente.RadialDoseFuntion['g(r)'])

    x, y = np.meshgrid(np.linspace(0, 180, 37), np.linspace(0, 50, 11))
    # Anisotropy2D.drop('r(mm)\\theta(°)',axis=1)
    f = interpolate.interp2d(x, y, np.array(fuente.Anisotropy2D), kind='cubic')

    F_r_th = np.array([(f(theta[i], r.modulo_r[i] * 10))[0] for i in range(len(r))])

    return Sk * fuente.DoseRateConstant * (GL_r_th / GL0) * g_r * F_r_th.T


def Dose(Catheters, Calc_Matrix, fuente, PlanDate):
    """
    This funtion return a matrix of dose in the space
    """
    DoseperMatrix = []
    for calc_point in Calc_Matrix:
        DoseperCatheter = []
        for Position in Catheters:
            DoseRate = Dose_Rate(Position[['x', 'y', 'z']], calc_point, fuente, PlanDate)
            DoseperDwell = DoseRate * np.array(Position['time'] / 3600)
            DoseperCatheter.append(round(DoseperDwell.sum(), 2))
        DoseperCatheter = np.array(DoseperCatheter)
        DoseperMatrix.append(DoseperCatheter.sum())
    return DoseperMatrix


def validation(RAKR, CalDate, RT_Plan):
    fuente = Ir_192(CalDate=CalDate, RAKR=RAKR)

    Catheters, Calc_Matrix, PlanDate, IcruDosePoints = Extraction(RT_Plan)

    Dosis = Dose(Catheters, Calc_Matrix, fuente, PlanDate)

    Puntos = IcruDosePoints
    Puntos['Manual (cGy)'] = Dosis
    Puntos['Error(%)'] = round(100 * (Puntos['Plan (cGy)'] - Puntos['Manual (cGy)']) / Puntos['Manual (cGy)'], 2)

    return Puntos
