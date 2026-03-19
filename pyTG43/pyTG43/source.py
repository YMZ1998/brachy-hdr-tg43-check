import matplotlib.pyplot as plt
import numpy as np
import xlrd

from .utils import bilinearinterp, fastinterp, find_source_spreadsheet


class Source(object):
    """Source parameters object."""

    def __init__(self, rp, directory, verbose=False):
        r0 = 1
        theta0 = np.pi / 2

        self.verbose = verbose
        self.Sk = rp.SourceSequence[0].ReferenceAirKermaRate

        spreadsheet = find_source_spreadsheet(
            directory, getattr(rp, "BrachyTreatmentType", "")
        )
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
