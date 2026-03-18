from Dose import Dose
from Extraction import Extraction
from Iridium192 import Ir_192


def validation(RAKR, CalDate, RT_Plan):
    fuente = Ir_192(CalDate=CalDate, RAKR=RAKR)

    Catheters, Calc_Matrix, PlanDate, IcruDosePoints = Extraction(RT_Plan)

    Dosis = Dose(Catheters, Calc_Matrix, fuente, PlanDate)

    Puntos = IcruDosePoints
    Puntos['Manual (cGy)'] = Dosis
    Puntos['Error(%)'] = round(100 * (Puntos['Plan (cGy)'] - Puntos['Manual (cGy)']) / Puntos['Manual (cGy)'], 2)

    return Puntos
