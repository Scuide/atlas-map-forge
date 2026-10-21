"""Two-team map symmetry."""
import math
import numpy as np

from .noise import smoothstep


class Symmetry:
    """layout: 'diag' (NW vs SE, 180 degree rotation), 'ns' or 'ew' (mirror)."""

    def __init__(self, layout, W, H):
        self.layout, self.W, self.H = layout, W, H   # W, H in elmos

    def mirror(self, x, z):
        if self.layout == "ew":
            return self.W - x, z
        if self.layout == "ns":
            return x, self.H - z
        return self.W - x, self.H - z

    def side(self, x, z):
        """Signed distance to the dividing line (< 0 = team 0)."""
        cx, cz = self.W / 2, self.H / 2
        if self.layout == "ew":
            return x - cx
        if self.layout == "ns":
            return z - cz
        return ((x - cx) * self.H / self.W + (z - cz)) / math.sqrt(2)

    def mirror_grid(self, a):
        if self.layout == "ew":
            return a[:, ::-1]
        if self.layout == "ns":
            return a[::-1, :]
        return a[::-1, ::-1]

    def symmetrize(self, a, band):
        """Blend a grid with its mirror image across the dividing line (soft band in elmos)."""
        h, w = a.shape
        zz, xx = np.meshgrid(np.linspace(0, self.H, h), np.linspace(0, self.W, w), indexing="ij")
        s = self.side(xx, zz)
        wgt = smoothstep(-band, band, s)            # w(mirror p) = 1 - w(p)
        from scipy import ndimage                   # coarse shapes averaged, fine detail keeps its strength
        low = ndimage.gaussian_filter(np.asarray(a, np.float64), 10.0)
        high = a - low
        k = np.sqrt((1 - wgt) ** 2 + wgt ** 2)
        return (1 - wgt) * low + wgt * self.mirror_grid(low) + ((1 - wgt) * high + wgt * self.mirror_grid(high)) / k

    def starts(self):
        W, H = self.W, self.H
        if self.layout == "ew":
            return [(0.11 * W, 0.5 * H), (0.89 * W, 0.5 * H)]
        if self.layout == "ns":
            return [(0.5 * W, 0.11 * H), (0.5 * W, 0.89 * H)]
        return [(0.14 * W, 0.14 * H), (0.86 * W, 0.86 * H)]


def mirror_point(h):
    """Make a square heightmap exactly 180-degree symmetric: lower half = rotated upper half."""
    n = h.shape[0]
    c = n // 2
    h[c + 1:, :] = h[:c][::-1, ::-1][: n - c - 1]
    h[c, c + 1:] = h[c, :c][::-1][: n - c - 1]
    return h


def mirror_east_west(h):
    """Make a heightmap exactly mirror symmetric across the vertical centre line (west half wins)."""
    n = h.shape[1]
    half = n // 2
    h[:, half + 1:] = h[:, :half][:, ::-1][:, : n - half - 1]
    return h


def mirror_pairs(points, sym):
    """Mex list [(x, z, metal)] for team 0 -> both sides via symmetry."""
    out = []
    for x, z, v in points:
        out.append(dict(x=float(x), z=float(z), metal=v, side=0))
        mx, mz = sym.mirror(x, z)
        out.append(dict(x=float(mx), z=float(mz), metal=v, side=1))
    return out


def _mirror_image(a, mode):
    return {"ew": a[:, ::-1], "ns": a[::-1, :], "point": a[::-1, ::-1]}[mode]


def seam_blend(a, mode, band=56, split_sigma=10.0):
    """Make a noise field symmetric without a seam.

    A hard mirror copy leaves a crease along the dividing line: the terrain on both sides runs into the
    line at different angles and the noise pattern flips. This blends the field with its mirror image in
    a band around the line (band in grid cells on each side): coarse shapes are averaged, fine detail is
    blended with variance compensation so the band does not turn flat. The result is exactly symmetric
    (the team-0 side keeps its own noise outside the band, the other side gets the mirror image).

    mode: "ew" (mirror across the vertical centre line), "ns" (horizontal line), "point" (180 degree
    rotation, seam along the centre row, matching mirror_point), "d4" (both lines)."""
    if mode == "d4":
        return seam_blend(seam_blend(a, "ew", band, split_sigma), "ns", band, split_sigma)
    a = np.asarray(a, np.float64)
    from scipy import ndimage
    nz, nx = a.shape
    if mode == "ew":
        d = (np.arange(nx) - (nx - 1) / 2.0)[None, :]
    else:
        d = (np.arange(nz) - (nz - 1) / 2.0)[:, None]
    w = smoothstep(-band, band, d)                  # weight of the mirror image; w(mirror) = 1 - w
    low = ndimage.gaussian_filter(a, split_sigma)
    high = a - low
    lowm, highm = _mirror_image(low, mode), _mirror_image(high, mode)
    k = np.sqrt((1 - w) ** 2 + w ** 2)               # keeps the strength of the fine detail
    return (1 - w) * low + w * lowm + ((1 - w) * high + w * highm) / k
