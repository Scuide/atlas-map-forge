// Atlas Map Forge - preview view maths (zoom / pan / screen <-> map). Pure functions, no DOM: unit-tested with node.
// A view is { cx, cy, s, fit }: map position at the canvas centre, pixels per elmo, and the "fit" scale (1x zoom).
"use strict";

const VIEW_MAX_ZOOM = 8;      // times the fitted scale

function viewToScreen(v, w, h, x, z) {
  return [(x - v.cx) * v.s + w / 2, (z - v.cy) * v.s + h / 2];
}

function viewToMap(v, w, h, sx, sy) {
  return [(sx - w / 2) / v.s + v.cx, (sy - h / 2) / v.s + v.cy];
}

// the scale limits: 1x = the fitted map, 8x = eight times closer
function viewLimits(v) {
  return [v.fit, v.fit * VIEW_MAX_ZOOM];
}

// zoom by the factor f so that the map position under (sx, sy) stays under the pointer
function viewZoomAt(v, w, h, f, sx, sy) {
  const [lo, hi] = viewLimits(v);
  const ns = Math.min(Math.max(v.s * f, lo), hi);
  const ex = v.cx + (sx - w / 2) / v.s, ey = v.cy + (sy - h / 2) / v.s;
  return { ...v, cx: ex - (sx - w / 2) / ns, cy: ey - (sy - h / 2) / ns, s: ns };
}

// move the view by a pointer drag of (dx, dy) screen pixels from the view `from`
function viewPan(from, dx, dy) {
  return { ...from, cx: from.cx - dx / from.s, cy: from.cy - dy / from.s };
}

// zoom as a multiple of the fitted scale (1 = whole map)
function viewZoomLevel(v) {
  return v.fit ? v.s / v.fit : 1;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { VIEW_MAX_ZOOM, viewToScreen, viewToMap, viewLimits, viewZoomAt, viewPan, viewZoomLevel };
}
