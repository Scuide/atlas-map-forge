// SCU-82: maths and mesh of the 3D preview (view3d.js)
const assert = require("assert");
const v = require("../atlasforge/app/web/view3d.js");

const nx = 5, nz = 4, h = new Int16Array(nx * nz).fill(10);
const m = v.v3Mesh(h, nx, nz, 32, 24);
assert.strictEqual(m.cols, 5); assert.strictEqual(m.rows, 4);
assert.strictEqual(m.verts.length, 20 * 8);
assert.strictEqual(m.idx.length, 4 * 3 * 6);
assert.strictEqual(m.verts[1], 10 * v.V3_EXAGGERATE);
assert.ok(Math.abs(m.verts[6] - 1) < 1e-6, "flat ground faces up");
assert.strictEqual(Math.max(...m.idx) , 19);

// big grids are thinned out
const big = v.v3Mesh(new Int16Array(1025 * 1025), 1025, 1025, 8192, 8192);
assert.ok(big.cols <= v.V3_MAX_SIDE && big.rows <= v.V3_MAX_SIDE);
assert.strictEqual(big.verts[big.verts.length - 8 + 0], 8192);

// camera: the eye keeps its distance, pitch and distance are clamped
const cam = v.v3Camera(8192, 8192);
const e = v.v3Eye(cam);
assert.ok(Math.abs(Math.hypot(e[0] - cam.tx, e[1] - cam.ty, e[2] - cam.tz) - cam.dist) < 1e-6);
cam.pitch = 5; cam.dist = 1; v.v3Clamp(cam, 8192, 8192);
assert.ok(cam.pitch <= 1.5 && cam.dist >= 8192 * 0.15);

// the target projects to the centre of the screen
const mvp = v.v3Mul(v.v3Perspective(0.8, 1.5, 10, 100000), v.v3LookAt(v.v3Eye(v.v3Camera(8192, 8192)), [4096, 0, 4096], [0, 1, 0]));
const cl = (x, y, z) => [0, 1, 2, 3].map((r) => mvp[r] * x + mvp[4 + r] * y + mvp[8 + r] * z + mvp[12 + r]);
const c = cl(4096, 0, 4096);
assert.ok(Math.abs(c[0] / c[3]) < 1e-6 && Math.abs(c[1] / c[3]) < 1e-6 && c[3] > 0);

// ground height lookup
assert.strictEqual(v.v3Ground(h, nx, nz, 12, 12), 10 * v.V3_EXAGGERATE);
console.log("ok");
