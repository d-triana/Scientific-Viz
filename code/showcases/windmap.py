# ----------------------------------------------------------------------------
# Title:   Scientific Visualisation - Python & Matplotlib
# Author:  Nicolas P. Rougier
# License: BSD
# ----------------------------------------------------------------------------
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, writers
from matplotlib.collections import LineCollection


class Streamlines(object):
    """
    Copyright (c) 2011 Raymond Speth.

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

    See: http://web.mit.edu/speth/Public/streamlines.py
    """

    def __init__(
        self, X, Y, U, V, res=0.125, spacing=2, maxLen=2500, detectLoops=False
    ):
        """
        Compute a set of streamlines covering the given velocity field.

        X and Y - 1D or 2D (e.g. generated by np.meshgrid) arrays of the
                  grid points. The mesh spacing is assumed to be uniform
                  in each dimension.
        U and V - 2D arrays of the velocity field.
        res - Sets the distance between successive points in each
              streamline (same units as X and Y)
        spacing - Sets the minimum density of streamlines, in grid points.
        maxLen - The maximum length of an individual streamline segment.
        detectLoops - Determines whether an attempt is made to stop extending
                      a given streamline before reaching maxLen points if
                      it forms a closed loop or reaches a velocity node.

        Plots are generated with the 'plot' or 'plotArrows' methods.
        """

        self.spacing = spacing
        self.detectLoops = detectLoops
        self.maxLen = maxLen
        self.res = res

        xa = np.asanyarray(X)
        ya = np.asanyarray(Y)
        self.x = xa if xa.ndim == 1 else xa[0]
        self.y = ya if ya.ndim == 1 else ya[:, 0]
        self.u = U
        self.v = V
        self.dx = (self.x[-1] - self.x[0]) / (self.x.size - 1)  # assume a regular grid
        self.dy = (self.y[-1] - self.y[0]) / (self.y.size - 1)  # assume a regular grid
        self.dr = self.res * np.sqrt(self.dx * self.dy)

        # marker for which regions have contours
        self.used = np.zeros(self.u.shape, dtype=bool)
        self.used[0] = True
        self.used[-1] = True
        self.used[:, 0] = True
        self.used[:, -1] = True

        # Don't try to compute streamlines in regions where there is no velocity data
        for i in range(self.x.size):
            for j in range(self.y.size):
                if self.u[j, i] == 0.0 and self.v[j, i] == 0.0:
                    self.used[j, i] = True

        # Make the streamlines
        self.streamlines = []
        while not self.used.all():
            nz = np.transpose(np.logical_not(self.used).nonzero())
            # Make a streamline starting at the first unrepresented grid point
            self.streamlines.append(
                self._makeStreamline(self.x[nz[0][1]], self.y[nz[0][0]])
            )

    def _interp(self, x, y):
        """ Compute the velocity at point (x,y) """
        i = (x - self.x[0]) / self.dx
        ai = i % 1

        j = (y - self.y[0]) / self.dy
        aj = j % 1

        i, j = int(i), int(j)

        # Bilinear interpolation
        u = (
            self.u[j, i] * (1 - ai) * (1 - aj)
            + self.u[j, i + 1] * ai * (1 - aj)
            + self.u[j + 1, i] * (1 - ai) * aj
            + self.u[j + 1, i + 1] * ai * aj
        )

        v = (
            self.v[j, i] * (1 - ai) * (1 - aj)
            + self.v[j, i + 1] * ai * (1 - aj)
            + self.v[j + 1, i] * (1 - ai) * aj
            + self.v[j + 1, i + 1] * ai * aj
        )

        self.used[j : j + self.spacing, i : i + self.spacing] = True

        return u, v

    def _makeStreamline(self, x0, y0):
        """
        Compute a streamline extending in both directions from the given point.
        """

        sx, sy = self._makeHalfStreamline(x0, y0, 1)  # forwards
        rx, ry = self._makeHalfStreamline(x0, y0, -1)  # backwards

        rx.reverse()
        ry.reverse()

        return rx + [x0] + sx, ry + [y0] + sy

    def _makeHalfStreamline(self, x0, y0, sign):
        """
        Compute a streamline extending in one direction from the given point.
        """

        xmin = self.x[0]
        xmax = self.x[-1]
        ymin = self.y[0]
        ymax = self.y[-1]

        sx = []
        sy = []

        x = x0
        y = y0
        i = 0
        while xmin < x < xmax and ymin < y < ymax:
            u, v = self._interp(x, y)
            theta = np.arctan2(v, u)

            x += sign * self.dr * np.cos(theta)
            y += sign * self.dr * np.sin(theta)
            sx.append(x)
            sy.append(y)

            i += 1

            if self.detectLoops and i % 10 == 0 and self._detectLoop(sx, sy):
                break

            if i > self.maxLen / 2:
                break

        return sx, sy

    def _detectLoop(self, xVals, yVals):
        """ Detect closed loops and nodes in a streamline. """
        x = xVals[-1]
        y = yVals[-1]
        D = np.array(
            [np.hypot(x - xj, y - yj) for xj, yj in zip(xVals[:-1], yVals[:-1])]
        )
        return (D < 0.9 * self.dr).any()


# See https://stackoverflow.com/questions/11578760/
# matplotlib-control-capstyle-of-line-collection-large-number-of-lines
# -----------------------------------------------------------------------------
import types
from matplotlib.backend_bases import GraphicsContextBase, RendererBase


class GC(GraphicsContextBase):
    def __init__(self):
        super().__init__()
        self._capstyle = "round"


def custom_new_gc(self):
    return GC()


RendererBase.new_gc = types.MethodType(custom_new_gc, RendererBase)


# -----------------------------------------------------------------------------
Y, X = np.mgrid[-3:3:100j, -3:3:100j]
U, V = -1 - X ** 2 + Y, 1 + X - X * Y ** 2
speed = np.sqrt(U * U + V * V)

fig = plt.figure(figsize=(8, 8))
ax = fig.add_axes([0, 0, 1, 1], aspect=1, frameon=False)

lengths = []
colors = []
lines = []

cmap = plt.get_cmap("Blues_r")
s = Streamlines(X, Y, U, V)
for streamline in s.streamlines:
    x, y = streamline
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    n = len(segments)

    D = np.sqrt(((points[1:] - points[:-1]) ** 2).sum(axis=-1))
    L = D.cumsum().reshape(n, 1) + np.random.uniform(0, 1)
    C = np.zeros((n, 3))
    C[:] = (L * 1.5) % 1

    C = cmap(((L * 1.5) % 1).ravel())

    linewidths = np.zeros(n)
    linewidths[:] = 2 - ((L.reshape(n) * 1.5) % 1)
    line = LineCollection(segments, color=C, linewidth=linewidths)

    lengths.append(L)
    colors.append(C)
    lines.append(line)

    ax.add_collection(line)

ax.set_xlim(-3, +3), ax.set_xticks([])
ax.set_ylim(-3, +3), ax.set_yticks([])
plt.savefig("../../figures/showcases/windmap.png", dpi=600)
plt.show()