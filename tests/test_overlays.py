"""Slope and contour overlays (SCU-76): green/yellow/red classes follow the movedef limits, contours mark height bands."""
import numpy as np
import pytest

from atlasforge import SQ
from atlasforge.checks import TANK_SLOPE, BOT_SLOPE, contour_mask, slope_classes, unit_masks
from atlasforge.terrain import move_slope


def ramp(grade, n=40):
    """Height rising along x with the given rise per elmo; the interior is free of edge effects."""
    x = np.arange(n, dtype=np.float32) * SQ
    return np.tile(x * grade, (n, 1)).astype(np.float32)


def test_flat_ground_is_green():
    assert (slope_classes(np.zeros((30, 30), np.float32)) == 0).all()


@pytest.mark.parametrize("grade,cls", [(0.3, 0), (0.8, 1), (2.0, 2)])
def test_ramp_classes(grade, cls):
    inner = slope_classes(ramp(grade))[5:-5, 5:-5]
    assert (inner == cls).all()


def test_classes_match_movement_masks():
    rng = np.random.default_rng(7)
    hm = np.cumsum(rng.normal(0, 6, (60, 60)), axis=1).astype(np.float32)
    cls = slope_classes(hm)
    masks = unit_masks(hm)
    sl = move_slope(hm)
    assert ((cls == 0) == (sl < TANK_SLOPE)).all()
    assert ((cls <= 1) == (sl < BOT_SLOPE)).all()
    assert ((cls == 0) <= masks["tanks"]).all()
    assert not (masks["bots"] & (cls == 2)).any()


def test_contours_mark_band_boundaries_only():
    hm = np.array([[0, 0, 40, 40, 40]] * 3, np.float32)
    m = contour_mask(hm, 32)
    assert m[:, 1].all() and m[:, 2].all()
    assert not m[:, 0].any() and not m[:, 4].any()


def test_flat_map_has_no_contours():
    assert not contour_mask(np.full((20, 20), 17, np.float32), 16).any()


def test_smaller_step_gives_more_contours():
    hm = ramp(0.5, 60)
    coarse = contour_mask(hm, 128).sum()
    fine = contour_mask(hm, 16).sum()
    assert 0 < coarse < fine
