import math
import os
from bisect import bisect_right
from multiprocessing import Pool
from pathlib import Path as FilesystemPath

import matplotlib.pyplot as plt
import numpy as np
import xlrd
from matplotlib.path import Path
from pydicom.tag import Tag
from terminaltables import AsciiTable


def tpsComp(rp, rs, directory, show_plot=False, verbose=False):
    """Calculate and compare dose at reference points with TPS."""

    points = []

    source = Source(rp, directory, verbose=verbose)
    if show_plot:
        source.plot_g()
    plan = Plan(source, rp, rs)

    for point in rp[0x300A, 0x10]:
        if Tag(0x300A, 0x18) in point.keys():
            x, y, z = point[0x300A, 0x18].value
            name = point[0x300A, 0x16].value
            ref = point[0x300A, 0x12].value
            points.append(
                DosePoint([x / 10, y / 10, z / 10], source, plan, name=name, ref=ref)
            )

    table_data = [["Name", "X", "Y", "Z", "TPS (Gy)", "Calc (Gy)", "Diff (%)"]]
    for point in points:
        diff = float("nan")
        if point.tpsdose:
            diff = (1 - (point.dose / point.tpsdose)) * 100
        table_data.append(
            [
                point.name,
                f"{point.x:.2f}",
                f"{point.y:.2f}",
                f"{point.z:.2f}",
                f"{point.tpsdose:.3f}",
                f"{point.dose:.3f}",
                f"{diff:.3f}",
            ]
        )

    print(AsciiTable(table_data).table)
    return points


def pcalc(point):
    """Parallel DosePoint calculation helper function."""

    return DosePoint(point, source, plan).dose


def calcDVHs(sourcei, plani, maxd, names):
    """Calculate cumulative DVHs for selected structures."""

    global source
    global plan

    source = sourcei
    plan = plani

    pool = Pool() if os.name != "nt" else None
    target_names = {name.lower() for name in names}

    try:
        for roi in plan.ROIs:
            if not roi.name or roi.name.lower() not in target_names:
                continue
            if not getattr(roi, "dvhpts", None):
                roi.dvh = np.empty((0, 2))
                continue

            if pool is None:
                dvh = [DosePoint(point, source, plan).dose for point in roi.dvhpts]
            else:
                dvh = pool.map(pcalc, roi.dvhpts)

            if not dvh:
                roi.dvh = np.empty((0, 2))
                continue

            counts, bins = np.histogram(dvh, 100, range=(0, maxd))
            cumulative = np.cumsum(counts[::-1])[::-1]
            cumulative = cumulative / cumulative.max() * 100
            roi.dvh = np.column_stack((bins[:-1], cumulative))
    finally:
        if pool is not None:
            pool.close()
            pool.join()


class Source(object):
    """Source parameters object."""

    def __init__(self, rp, directory, verbose=False):
        r0 = 1
        theta0 = np.pi / 2

        self.verbose = verbose
        self.Sk = rp.SourceSequence[0].ReferenceAirKermaRate

        spreadsheet = find_source_spreadsheet(directory, getattr(rp, "BrachyTreatmentType", ""))
        self._log("xls:", spreadsheet)

        workbook = xlrd.open_workbook(spreadsheet)
        sheet = workbook.sheets()[-1]

        self.L = sheet.row(9)[2].value
        self.Delta = sheet.row(4)[2].value
        self._log("L:", self.L)
        self._log("Delta:", self.Delta)

        col = 5
        while sheet.row(10)[col].ctype == 2:
            col += 1

        anisotropy = np.ones((1, col - 5))
        radial = np.ones((1, 2))
        theta_points = []
        radius_points = [cell.value for cell in sheet.row(10)[5:col]]
        self._log("Fr:", radius_points)

        for row in np.arange(11, sheet.nrows):
            if sheet.row(row)[1].ctype != 0:
                radial = np.vstack(
                    [radial, np.array([cell.value for cell in sheet.row(row)[1:3]])]
                )
            anisotropy = np.vstack(
                [anisotropy, np.array([cell.value for cell in sheet.row(row)[5:col]])]
            )
            theta_points.append(sheet.row(row)[4].value)

        anisotropy = anisotropy[1:, :]
        radial = radial[1:, :]

        self._log("Fi:\n", anisotropy)
        self._log("gi:\n", radial)

        self.Fi = bilinearinterp(radius_points, theta_points, anisotropy)
        self.gi = fastinterp(radial[:, 0], radial[:, 1])
        self.G0 = 2 * np.arctan((self.L / 2) / r0) / (self.L * r0 * np.sin(theta0))

    def _log(self, *args):
        if self.verbose:
            print(*args)

    def F(self, r, theta):
        """Return anisotropy function value for radius in cm and angle in degrees."""

        return self.Fi(min(r, 10), theta)

    def g(self, r):
        """Return radial dose function value for radius in cm."""

        if r < 0.15:
            return self.gi(0.15)
        if r > 10:
            return self.gi(8) * np.exp(
                (r - 8) / (10 - 8) * (np.log(self.gi(10)) - np.log(self.gi(8)))
            )
        return self.gi(r)

    def plot_g(self):
        radii = np.linspace(0.1, 10, 200)
        g_vals = [self.g(radius) for radius in radii]

        plt.figure()
        plt.plot(radii, g_vals)
        plt.xlabel("r (cm)")
        plt.ylabel("g(r)")
        plt.title("Radial Dose Function g(r)")
        plt.grid()
        plt.show()

    def plot_F(self):
        theta_deg = np.linspace(0, 180, 180, endpoint=False)
        radii = np.linspace(0.1, 10, 100)

        radius_grid, theta_grid = np.meshgrid(radii, theta_deg)
        values = np.zeros_like(radius_grid)

        for i in range(radius_grid.shape[0]):
            for j in range(radius_grid.shape[1]):
                values[i, j] = self.F(radius_grid[i, j], theta_grid[i, j])

        plt.figure()
        plt.pcolormesh(radius_grid, np.radians(theta_grid), values, shading="auto")
        plt.colorbar(label="F(r, theta)")
        plt.xlabel("r (cm)")
        plt.ylabel("theta (rad)")
        plt.title("Anisotropy Function F(r, theta)")
        plt.show()

    def plot_F_polar(self):
        theta_deg = np.linspace(0, 180, 180, endpoint=False)
        radii = np.linspace(0.5, 5, 20)

        plt.figure()
        axis = plt.subplot(111, projection="polar")

        for radius in radii:
            values = [self.F(radius, theta) for theta in theta_deg]
            axis.plot(np.radians(theta_deg), values, label=f"r={radius:.1f}")

        plt.title("Anisotropy Function (Polar View)")
        plt.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
        plt.show()


class Dwell(object):
    """Planned dwell point."""

    def __init__(self, coords, t, L, app):
        self.x, self.y, self.z = coords
        self.middle = np.array(coords, dtype=float)
        self.t = t
        self.get_source_position(app, L)

    def get_source_position(self, app, L):
        """Calculate coordinates of the ends of the source."""

        app_coords = app.oldcoords(app.coords) / 10
        if len(app_coords) < 2:
            raise ValueError(f"Applicator '{app}' does not contain enough points.")

        smallest = np.inf
        closest = None

        for i, point in enumerate(app_coords[:-1]):
            next_point = app_coords[i + 1]
            segment_length = euclidzip(point, next_point)
            if segment_length == 0:
                continue

            on_segment = (
                np.round(euclidzip(point, self.middle) + euclidzip(next_point, self.middle), 4)
                - np.round(segment_length, 4)
            )
            if on_segment < smallest:
                smallest = on_segment
                closest = [point, next_point]

        if closest is None:
            raise ValueError(f"Applicator '{app}' does not define a valid source segment.")

        vector = closest[0] - closest[1]
        length = euclidzip(closest[0], closest[1])
        direction = vector / length

        cosines = [np.arccos(clip_unit_interval(value)) for value in direction]
        alpha = np.arccos(
            clip_unit_interval(
                np.cos(cosines[1]) / np.cos(np.arcsin(-np.cos(cosines[0])))
            )
        )
        beta = np.arcsin(-np.cos(cosines[0]))

        if abs(np.cos(cosines[2]) - np.sin(alpha) * np.cos(beta)) > 1e-15:
            vector = closest[1] - closest[0]
            length = euclidzip(closest[1], closest[0])
            direction = vector / length
            cosines = [np.arccos(clip_unit_interval(value)) for value in direction]
            alpha = (
                np.arccos(
                    clip_unit_interval(
                        np.cos(cosines[1]) / np.cos(np.arcsin(-np.cos(cosines[0])))
                    )
                )
                + np.pi
            )
            beta = -np.arcsin(-np.cos(cosines[0]))

        self.ends = [self.middle + L / 2 * direction, self.middle - L / 2 * direction]
        self.rotation = [alpha, beta, 0]


class DosePoint(object):
    """Point at which dose is calculated."""

    def __init__(self, coords, source, plan, name="", ref=""):
        self.x, self.y, self.z = coords
        self.coords = np.array(coords, dtype=float)
        self.name = name
        self.ref = ref
        self.source = source
        if self.ref != "":
            self.get_tpsdose(plan.rp)
        else:
            self.tpsdose = 0
        self.calc_dose(source, plan)

    def __repr__(self):
        return self.name

    def get_tpsdose(self, rp):
        """Get TPS-calculated dose for this point."""

        tpsdose = 0

        if Tag(0x300A, 0x26) in rp[0x300A, 0x10][0].keys():
            for ref_point in rp[0x300A, 0x10]:
                if self.ref == ref_point[0x300A, 0x12].value:
                    tpsdose += ref_point[0x300A, 0x26].value
        else:
            for cath in rp[0x300A, 0x230][0][0x300A, 0x280]:
                dwells = cath[0x300A, 0x2D0]

                if Tag(0x300C, 0x55) in dwells[-1].keys():
                    for ref_point in dwells[-1][0x300C, 0x55]:
                        if self.ref == ref_point[0x300C, 0x51].value:
                            tpsdose += ref_point[0x300A, 0x10C].value

            tpsdose *= rp.FractionGroupSequence[0][0x300C, 0xA][0][0x300A, 0xA4].value
            tpsdose *= rp.FractionGroupSequence[0][0x300A, 0x78].value

            if rp.BrachyTreatmentType == "PDR":
                tpsdose *= rp[0x300A, 0x230][0][0x300A, 0x280][0][0x300A, 0x28A].value

        self.tpsdose = tpsdose

    def calc_dose(self, source, plan):
        """Calculate dose for this point."""

        dose = 0
        for dwell in plan.dwells:
            if dwell.t <= 0:
                continue

            r = euclidzip(self.coords, dwell.middle)
            r1 = euclidzip(self.coords, dwell.ends[1])
            r2 = euclidzip(self.coords, dwell.ends[0])
            if 0 in {r, r1, r2}:
                continue

            source_axis = (dwell.ends[0] - dwell.ends[1]) / source.L
            theta = np.arccos(
                clip_unit_interval(np.dot(source_axis, (self.coords - dwell.middle) / r))
            )
            theta1 = np.arccos(
                clip_unit_interval(np.dot(source_axis, (self.coords - dwell.ends[1]) / r1))
            )
            theta2 = np.arccos(
                clip_unit_interval(np.dot(source_axis, (self.coords - dwell.ends[0]) / r2))
            )

            if (theta < 0.003) or ((np.pi - theta) < 0.003):
                geometry = 1 / (r ** 2 - source.L ** 2 / 4)
            else:
                beta = np.abs(theta2 - theta1)
                geometry = beta / (source.L * r * np.sin(theta))

            dose += (
                source.Sk
                * source.Delta
                * (geometry / source.G0)
                * source.g(r)
                * source.F(r, np.degrees(theta))
                * dwell.t
                / 3600
            )

        self.dose = dose / 100


class Plan(object):
    """Plan parameters."""

    def __init__(self, source, rp, rs, rd=None):
        self.rp = rp
        if rp.BrachyTreatmentType == "PDR":
            self.frac = rp[0x300A, 0x230][0][0x300A, 0x280][0][0x300A, 0x28A].value
        elif rp.BrachyTreatmentType == "HDR":
            self.frac = rp.FractionGroupSequence[0][0x300A, 0x78].value
        else:
            raise ValueError(f"Unsupported brachy treatment type: {rp.BrachyTreatmentType}")

        self.get_ROIs(rs, rp, rd)
        self.get_dwells(source, rp)
        self.rx = rp.FractionGroupSequence[0][0x300C, 0xA][0][0x300A, 0xA4].value

    def get_ROIs(self, rs, rp, rd=None):
        """Get all structures in plan."""

        self.ROIs = []
        if rp.Manufacturer == "Nucletron":
            for roi in rp[0x300F, 0x1000][0][0x3006, 0x39]:
                if len(roi.ContourSequence) == 1:
                    self.ROIs.append(ROI(roi[0x3006, 0x84].value, None, rs, rp, rd))

        for struct in rs.StructureSetROISequence:
            self.ROIs.append(ROI(struct.ROINumber, struct.ROIName, rs, rp, rd))

    def get_dwells(self, source, rp):
        """Get all dwell points in plan."""

        self.dwells = []
        for cath in rp[0x300A, 0x230][0][0x300A, 0x280]:
            dwell_pts = cath[0x300A, 0x2D0]
            weight = cath[0x300A, 0x2C8].value
            total = cath[0x300A, 0x286].value * self.frac
            previous_weight = 0
            app = None

            for roi in self.ROIs:
                if cath.ReferencedROINumber == roi.number:
                    app = roi
                elif (
                    rp.Manufacturer == "Nucletron"
                    and cath[0x300B, 0x1000].value == roi.number
                ):
                    app = roi

            if app is None:
                raise ValueError(
                    f"Unable to match catheter ROI {cath.ReferencedROINumber} to an applicator."
                )

            for dwell in dwell_pts:
                x, y, z = dwell[0x300A, 0x2D4].value
                current_weight = dwell[0x300A, 0x2D6].value
                weight_delta = current_weight - previous_weight
                if weight == 0:
                    dwell_time = 0
                else:
                    dwell_time = weight_delta / weight * total
                previous_weight = current_weight
                self.dwells.append(Dwell([x / 10, y / 10, z / 10], dwell_time, source.L, app))


class ROI(object):
    """DICOM structure."""

    def __init__(self, number, name, rs, rp, rd=None):
        self.number = number
        self.name = name
        self.coords = np.empty((0, 3))
        self.coordslist = []
        self.get_transform(rd)
        self.get_coords(rs, rp)

    def get_transform(self, rd):
        """Get transformation function for rotated orientation datasets."""

        if rd:
            nnx = np.array(rd.ImageOrientationPatient[:3])
            nny = -np.array(rd.ImageOrientationPatient[3:])
            nnz = -np.cross(nnx, nny)
        else:
            nnx, nny, nnz = np.array([1, 0, 0, 0, 1, 0, 0, 0, 1], dtype=float).reshape(
                3, -1
            )

        nox, noy, noz = np.array([1, 0, 0, 0, 1, 0, 0, 0, 1], dtype=float).reshape(3, -1)

        transform = np.vstack(
            (
                [np.dot(nnx, axis) for axis in [nox, noy, noz]],
                [np.dot(nny, axis) for axis in [nox, noy, noz]],
                [np.dot(nnz, axis) for axis in [nox, noy, noz]],
            )
        )
        inverse_transform = np.linalg.inv(transform)

        def newcoords(coords):
            return np.vstack([np.dot(transform, point) for point in coords])

        def oldcoords(coords):
            return np.vstack([np.dot(inverse_transform, point) for point in coords])

        self.newcoords = newcoords
        self.oldcoords = oldcoords

    def get_coords(self, rs, rp):
        """Get coordinates for this structure from the RS file."""

        if rs.Manufacturer == "Nucletron" and self.name is None:
            for roi in rp[0x300F, 0x1000][0][0x3006, 0x39]:
                if len(roi.ContourSequence) == 1 and roi[0x3006, 0x84].value == self.number:
                    contour = roi.ContourSequence[0]
                    self.coords = np.append(
                        self.coords, np.array(contour.ContourData).reshape((-1, 3)), axis=0
                    )
        else:
            for roi in rs.ROIContourSequence:
                if roi[0x3006, 0x84].value == self.number and Tag(0x3006, 0x40) in roi.keys():
                    for contour in roi.ContourSequence:
                        coords = np.array(contour.ContourData).reshape((-1, 3))
                        coords = np.round(self.newcoords(coords), 1)
                        self.coordslist.append(coords)

        if self.coordslist:
            self.coords = np.concatenate(self.coordslist)

    def get_TPS_DVH(self, rp, rs, rd):
        """Compute the DVH for the TPS-calculated dose distribution."""

        rx = rp.FractionGroupSequence[0][0x300C, 0xA][0][0x300A, 0xA4].value
        ix, iy, iz = self.newcoords([rd.ImagePositionPatient])[0]
        xcoords = ix + np.arange(0, rd.Columns * rd.PixelSpacing[0], rd.PixelSpacing[0])
        ycoords = iy - np.arange(0, rd.Rows * rd.PixelSpacing[1], rd.PixelSpacing[1])
        zcoords = np.round(iz + np.array(rd.GridFrameOffsetVector), 2)
        dose_ref = (rd.pixel_array * rd.DoseGridScaling)[:, :, :]

        coords = [(x, y) for y in ycoords for x in xcoords]

        for index in np.arange(len(rs.StructureSetROISequence)):
            roi_name = rs.StructureSetROISequence[index].ROIName
            if roi_name != self.name:
                continue

            contour = rs.ROIContourSequence[index]
            if "ContourSequence" not in contour:
                continue

            bool_ref = np.zeros(dose_ref.shape, dtype=bool)

            for slice_contour in contour.ContourSequence:
                contour_coords = self.newcoords(
                    np.array(slice_contour.ContourData).reshape((-1, 3))
                )
                z_index_value = np.round(np.mean(contour_coords[:, 2]), 2)
                try:
                    z_index = list(zcoords).index(z_index_value)
                except ValueError:
                    continue

                boolslice = bool_ref[z_index, :, :]
                contour_path = Path(contour_coords[:, :2])
                in_path = contour_path.contains_points(coords).reshape(
                    (dose_ref.shape[1], dose_ref.shape[2])
                )
                bool_ref[z_index, :, :] = np.logical_xor(in_path, boolslice)

            dvh = dose_ref[bool_ref == True]
            if len(dvh) == 0:
                self.tpsmin = None
                self.tpsmax = None
                self.tpsmean = None
                self.tpsdvh = np.empty((0, 2))
                continue

            self.tpsmin = float(dvh.min())
            self.tpsmax = float(dvh.max())
            self.tpsmean = float(dvh.mean())

            counts, bins = np.histogram(dvh, 100, range=(0, rx * 10))
            cumulative = np.cumsum(counts[::-1])[::-1]
            cumulative = cumulative / cumulative.max() * 100
            self.tpsdvh = np.column_stack((bins[:-1], cumulative))

    def get_DVH_pts(self, grid=2.5):
        """Calculate co-ordinates for DVH calculation inside the structure."""

        self.dvhpts = []
        if self.coords.size == 0:
            return

        slices = sorted(list(set(self.coords[:, 2])))
        for z_slice in slices:
            shapes = [coords for coords in self.coordslist if coords[0, 2] == z_slice]
            if not shapes:
                continue

            coords = np.concatenate(shapes)[:, :2]
            minx = coords[:, 0].min() - 0.5
            maxx = coords[:, 0].max() + 0.5
            miny = coords[:, 1].min() - 0.5
            maxy = coords[:, 1].max() + 0.5
            calcgrid = [
                [x, y]
                for y in np.arange(miny, maxy, grid)
                for x in np.arange(minx, maxx, grid)
            ]
            boolgrid = np.zeros(len(calcgrid), dtype=bool)
            for contour in shapes:
                contour_path = Path(contour[:, :2])
                in_path = contour_path.contains_points(calcgrid)
                boolgrid = np.logical_xor(boolgrid, in_path)
            calcpts = [calcgrid[i] for i in np.where(boolgrid)[0]]
            self.dvhpts.extend(
                [
                    list(self.oldcoords([[point[0], point[1], z_slice]])[0, [0, 1, 2]] / 10)
                    for point in calcpts
                ]
            )

    def __repr__(self):
        if self.name is not None:
            return self.name
        return "Oncentra Applicator"


def euclidzip(v1, v2):
    """Fast euclidean distance between two vectors."""

    dist = [(a - b) ** 2 for a, b in zip(v1, v2)]
    return math.sqrt(sum(dist))


def clip_unit_interval(value):
    """Clip a float to the valid domain of arccos."""

    return float(np.clip(value, -1.0, 1.0))


def find_source_spreadsheet(directory, treatment_type=""):
    """Return the most relevant source spreadsheet from a directory."""

    base = FilesystemPath(directory)
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

        x1, x2 = xi[i: i + 2]
        y1, y2 = yi[j: j + 2]
        z11, z12 = values[j][i: i + 2]
        z21, z22 = values[j + 1][i: i + 2]

        return (
            z11 * (x2 - x) * (y2 - y)
            + z21 * (x - x1) * (y2 - y)
            + z12 * (x2 - x) * (y - y1)
            + z22 * (x - x1) * (y - y1)
        ) / ((x2 - x1) * (y2 - y1))

    return interpolate
