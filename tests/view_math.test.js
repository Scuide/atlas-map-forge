// node tests/view_math.test.js  (run by tests/test_view_math.py)
const assert = require("assert");
const V = require("../atlasforge/app/web/view.js");
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-6, `${a} != ${b}`);
const W = 1000, H = 600, v0 = { cx: 2048, cy: 1024, s: 0.2, fit: 0.2 };

// screen <-> map round trip
for (const [x, z] of [[0, 0], [4096, 2048], [1234, 567]]) {
  const [sx, sy] = V.viewToScreen(v0, W, H, x, z), [mx, mz] = V.viewToMap(v0, W, H, sx, sy);
  near(mx, x); near(mz, z);
}
// zoom keeps the map point under the cursor
const before = V.viewToMap(v0, W, H, 800, 100);
const v1 = V.viewZoomAt(v0, W, H, 3, 800, 100);
const after = V.viewToMap(v1, W, H, 800, 100);
near(after[0], before[0]); near(after[1], before[1]);
near(v1.s, 0.6);
// limits: not below 1x, not above 8x
near(V.viewZoomAt(v0, W, H, 0.1, 10, 10).s, 0.2);
near(V.viewZoomAt(v0, W, H, 1000, 10, 10).s, 1.6);
near(V.viewZoomLevel(V.viewZoomAt(v0, W, H, 1000, 10, 10)), 8);
// zooming at a clamped scale keeps the point too
const v8 = V.viewZoomAt(v1, W, H, 100, 300, 300), p = V.viewToMap(v1, W, H, 300, 300), q = V.viewToMap(v8, W, H, 300, 300);
near(p[0], q[0]); near(p[1], q[1]);
// pan: dragging right by 100 px moves the map point under the pointer along
const vp = V.viewPan(v1, 100, -50);
const m0 = V.viewToMap(v1, W, H, 400, 300), m1 = V.viewToMap(vp, W, H, 500, 250);
near(m0[0], m1[0]); near(m0[1], m1[1]);
console.log("ok");
