// Atlas Map Forge - 3D terrain preview. Plain WebGL, no libraries (the app works offline).
// The maths and the mesh builder are pure functions and unit-tested with node; the GL part only runs in a browser.
"use strict";

const V3_MAX_SIDE = 256;        // mesh vertices per side at most
const V3_EXAGGERATE = 2;        // heights are drawn this many times taller than they are

function v3Perspective(fovY, aspect, near, far) {
  const f = 1 / Math.tan(fovY / 2), nf = 1 / (near - far);
  return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0];
}

function v3LookAt(eye, c, up) {
  let zx = eye[0] - c[0], zy = eye[1] - c[1], zz = eye[2] - c[2];
  let l = Math.hypot(zx, zy, zz) || 1; zx /= l; zy /= l; zz /= l;
  let xx = up[1] * zz - up[2] * zy, xy = up[2] * zx - up[0] * zz, xz = up[0] * zy - up[1] * zx;
  l = Math.hypot(xx, xy, xz) || 1; xx /= l; xy /= l; xz /= l;
  const yx = zy * xz - zz * xy, yy = zz * xx - zx * xz, yz = zx * xy - zy * xx;
  return [xx, yx, zx, 0, xy, yy, zy, 0, xz, yz, zz, 0,
    -(xx * eye[0] + xy * eye[1] + xz * eye[2]), -(yx * eye[0] + yy * eye[1] + yz * eye[2]), -(zx * eye[0] + zy * eye[1] + zz * eye[2]), 1];
}

function v3Mul(a, b) {          // a * b, column-major
  const o = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) o[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
  return o;
}

// orbit camera: yaw (around the vertical axis), pitch (above the horizon), distance from the target
function v3Eye(cam) {
  const cp = Math.cos(cam.pitch);
  return [cam.tx + cam.dist * cp * Math.sin(cam.yaw), cam.ty + cam.dist * Math.sin(cam.pitch), cam.tz + cam.dist * cp * Math.cos(cam.yaw)];
}

function v3Clamp(cam, W, H) {
  cam.pitch = Math.min(Math.max(cam.pitch, 0.12), 1.5);
  cam.dist = Math.min(Math.max(cam.dist, Math.max(W, H) * 0.15), Math.max(W, H) * 3);
  return cam;
}

function v3Camera(W, H) {
  return { yaw: 0.6, pitch: 0.75, dist: Math.max(W, H) * 1.1, tx: W / 2, ty: 0, tz: H / 2 };
}

// Terrain mesh from the height grid (nx x nz int16 elmos, row-major, 8 elmos apart).
// Returns { verts: Float32Array(x,y,z,u,v,nx,ny,nz), idx: Uint32Array|Uint16Array, cols, rows }
function v3Mesh(height, nx, nz, W, H) {
  const step = Math.max(1, Math.ceil((Math.max(nx, nz) - 1) / (V3_MAX_SIDE - 1)));
  const cols = Math.ceil((nx - 1) / step) + 1, rows = Math.ceil((nz - 1) / step) + 1;
  const at = (ix, iz) => height[Math.min(nz - 1, Math.max(0, iz)) * nx + Math.min(nx - 1, Math.max(0, ix))] * V3_EXAGGERATE;
  const verts = new Float32Array(cols * rows * 8);
  let p = 0;
  for (let j = 0; j < rows; j++) {
    for (let i = 0; i < cols; i++) {
      const ix = Math.min(nx - 1, i * step), iz = Math.min(nz - 1, j * step);
      const x = Math.min(W, ix * 8), z = Math.min(H, iz * 8);
      const dx = (at(ix + step, iz) - at(ix - step, iz)) / (2 * step * 8);
      const dz = (at(ix, iz + step) - at(ix, iz - step)) / (2 * step * 8);
      const l = Math.hypot(dx, 1, dz);
      verts[p++] = x; verts[p++] = at(ix, iz); verts[p++] = z;
      verts[p++] = x / W; verts[p++] = z / H;
      verts[p++] = -dx / l; verts[p++] = 1 / l; verts[p++] = -dz / l;
    }
  }
  const idx = new Uint32Array((cols - 1) * (rows - 1) * 6);
  let q = 0;
  for (let j = 0; j < rows - 1; j++) for (let i = 0; i < cols - 1; i++) {
    const a = j * cols + i, b = a + 1, c = a + cols, d = c + 1;
    idx[q++] = a; idx[q++] = c; idx[q++] = b; idx[q++] = b; idx[q++] = c; idx[q++] = d;
  }
  return { verts, idx, cols, rows, step };
}

// ground height (drawn units) under a map position, bilinear on the grid
function v3Ground(height, nx, nz, x, z) {
  const gx = Math.min(nx - 1, Math.max(0, x / 8)), gz = Math.min(nz - 1, Math.max(0, z / 8));
  const i = Math.min(nx - 2, Math.floor(gx)), j = Math.min(nz - 2, Math.floor(gz));
  const fx = gx - i, fz = gz - j;
  const h = (a, b) => height[b * nx + a];
  const top = h(i, j) * (1 - fx) + h(i + 1, j) * fx, bot = h(i, j + 1) * (1 - fx) + h(i + 1, j + 1) * fx;
  return (top * (1 - fz) + bot * fz) * V3_EXAGGERATE;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { V3_MAX_SIDE, V3_EXAGGERATE, v3Perspective, v3LookAt, v3Mul, v3Eye, v3Clamp, v3Camera, v3Mesh, v3Ground };
}

// ------------------------------------------------------------------ GL part (browser only)
const View3D = (() => {
  if (typeof document === "undefined") return null;
  let cv = null, gl = null, ok = false, on = false;
  let prog = null, pprog = null, wprog = null;
  let mesh = null, tex = null, buf = null, ibuf = null, wbuf = null, pbuf = null, nIdx = 0, nPts = 0;
  let seen = { grid: null, relief: null, map: null };
  let cam = null, camKey = "";
  let drag = null;

  const VS = `attribute vec3 p; attribute vec2 t; attribute vec3 n; uniform mat4 m; varying vec2 uv; varying vec3 nn; varying float hh;
    void main(){ uv=t; nn=n; hh=p.y; gl_Position=m*vec4(p,1.0); }`;
  const FS = `precision mediump float; uniform sampler2D tx; varying vec2 uv; varying vec3 nn; varying float hh;
    void main(){ vec3 c=texture2D(tx,uv).rgb; float l=max(dot(normalize(nn),normalize(vec3(-0.45,0.8,-0.35))),0.0);
      gl_FragColor=vec4(c*(0.5+0.6*l),1.0); }`;
  const WVS = `attribute vec3 p; uniform mat4 m; void main(){ gl_Position=m*vec4(p,1.0); }`;
  const WFS = `precision mediump float; void main(){ gl_FragColor=vec4(0.10,0.32,0.62,0.42); }`;
  const PVS = `attribute vec3 p; attribute vec3 c; attribute float s; uniform mat4 m; varying vec3 cc;
    void main(){ cc=c; gl_Position=m*vec4(p,1.0); gl_PointSize=s; }`;
  const PFS = `precision mediump float; varying vec3 cc;
    void main(){ vec2 d=gl_PointCoord-0.5; float r=length(d); if(r>0.5) discard; gl_FragColor=vec4(r>0.4?vec3(0.05):cc,1.0); }`;

  function compile(vs, fs) {
    const mk = (type, src) => {
      const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    const p = gl.createProgram();
    gl.attachShader(p, mk(gl.VERTEX_SHADER, vs)); gl.attachShader(p, mk(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    return p;
  }

  function init(canvas) {
    cv = canvas;
    try {
      // alpha:false keeps the framebuffer opaque, so the translucent water cannot show the 2D map behind the canvas (SCU-88)
      gl = cv.getContext("webgl", { antialias: true, alpha: false }) || cv.getContext("experimental-webgl", { antialias: true, alpha: false });
      if (!gl) return false;
      gl.getExtension("OES_element_index_uint");
      if (!gl.getExtension("OES_element_index_uint")) return false;
      prog = compile(VS, FS); wprog = compile(WVS, WFS); pprog = compile(PVS, PFS);
      buf = gl.createBuffer(); ibuf = gl.createBuffer(); wbuf = gl.createBuffer(); pbuf = gl.createBuffer();
      tex = gl.createTexture();
      cv.addEventListener("pointerdown", (e) => { if (!on) return; drag = { x: e.clientX, y: e.clientY, pan: e.button === 2 || e.shiftKey }; cv.setPointerCapture(e.pointerId); });
      cv.addEventListener("pointermove", (e) => {
        if (!on || !drag || !cam) return;
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        drag.x = e.clientX; drag.y = e.clientY;
        if (drag.pan) {
          const k = cam.dist * 0.0015, c = Math.cos(cam.yaw), n = Math.sin(cam.yaw);
          cam.tx += (-c * dx - n * dy) * k;
          cam.tz += (n * dx - c * dy) * k;
        } else { cam.yaw -= dx * 0.006; cam.pitch += dy * 0.006; }
        clamp(); render(S);
      });
      const end = () => { drag = null; };
      cv.addEventListener("pointerup", end); cv.addEventListener("pointercancel", end);
      cv.addEventListener("contextmenu", (e) => e.preventDefault());
      cv.addEventListener("wheel", (e) => { if (!on || !cam) return; e.preventDefault(); cam.dist *= Math.exp(e.deltaY * 0.0012); clamp(); render(S); }, { passive: false });
      cv.addEventListener("dblclick", () => { if (on && S.map) { cam = v3Camera(S.map.W, S.map.H); render(S); } });
      ok = true;
    } catch (e) { ok = false; }
    return ok;
  }

  function clamp() { if (cam && S.map) v3Clamp(cam, S.map.W, S.map.H); }

  function upload(S) {
    const m = S.map, g = S.grid;
    if (seen.grid !== g || seen.map !== m) {
      mesh = v3Mesh(g.height, g.nx, g.nz, m.W, m.H);
      gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, mesh.verts, gl.STATIC_DRAW);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibuf); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, mesh.idx, gl.STATIC_DRAW);
      nIdx = mesh.idx.length;
      const e = 40, y = 0;      // water plane at height 0, a bit larger than the map
      gl.bindBuffer(gl.ARRAY_BUFFER, wbuf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-e, y, -e, m.W + e, y, -e, -e, y, m.H + e, m.W + e, y, -e, -e, y, m.H + e, m.W + e, y, m.H + e]), gl.STATIC_DRAW);
      // markers: x y z r g b size
      const pts = [];
      const add = (x, z, col, size, lift) => pts.push(x, v3Ground(g.height, g.nx, g.nz, x, z) + lift, z, col[0], col[1], col[2], size);
      if (S.layers.mexes) for (const k of m.mexes) add(k.x, k.z, [1, 0.85, 0.2], 9 + k.metal * 2, 14);
      if (S.layers.geos) for (const k of m.geos) add(k[0], k[1], [1, 0.3, 0.2], 12, 14);
      if (S.layers.starts) {
        const hex = (s) => [parseInt(s.slice(1, 3), 16) / 255, parseInt(s.slice(3, 5), 16) / 255, parseInt(s.slice(5, 7), 16) / 255];
        (m.teams || []).forEach((team, ti) => team.forEach((st) => add(st[0], st[1], hex(teamColor(ti)), 20, 24)));
      }
      nPts = pts.length / 7;
      gl.bindBuffer(gl.ARRAY_BUFFER, pbuf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(pts), gl.DYNAMIC_DRAW);
      seen.grid = g; seen.map = m; seen.layers = JSON.stringify([S.layers.mexes, S.layers.geos, S.layers.starts]);
      const key = m.W + "x" + m.H;
      if (!cam || camKey !== key) { cam = v3Camera(m.W, m.H); camKey = key; }
    }
    if (seen.relief !== S.img.relief) {
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, S.img.relief);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      seen.relief = S.img.relief;
    }
  }

  function render(S) {
    if (!ok || !on || !S || !S.map || !S.grid || !S.img.relief) return;
    const key = JSON.stringify([S.layers.mexes, S.layers.geos, S.layers.starts]);
    if (seen.layers && seen.layers !== key) seen.map = null;      // marker layers toggled: rebuild
    upload(S);
    const dpr = window.devicePixelRatio || 1, r = cv.getBoundingClientRect();
    const w = Math.max(1, Math.round(r.width * dpr)), h = Math.max(1, Math.round(r.height * dpr));
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    gl.viewport(0, 0, w, h);
    gl.clearColor(0.03, 0.035, 0.045, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    const far = Math.max(S.map.W, S.map.H) * 8;
    const mvp = v3Mul(v3Perspective(0.8, w / h, far / 4000, far), v3LookAt(v3Eye(cam), [cam.tx, cam.ty, cam.tz], [0, 1, 0]));

    gl.useProgram(prog);
    gl.uniformMatrix4fv(gl.getUniformLocation(prog, "m"), false, new Float32Array(mvp));
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibuf);
    const attr = (pr, name, size, stride, off) => {
      const a = gl.getAttribLocation(pr, name);
      if (a >= 0) { gl.enableVertexAttribArray(a); gl.vertexAttribPointer(a, size, gl.FLOAT, false, stride * 4, off * 4); }
    };
    attr(prog, "p", 3, 8, 0); attr(prog, "t", 2, 8, 3); attr(prog, "n", 3, 8, 5);
    gl.drawElements(gl.TRIANGLES, nIdx, gl.UNSIGNED_INT, 0);

    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
    gl.useProgram(wprog);
    gl.uniformMatrix4fv(gl.getUniformLocation(wprog, "m"), false, new Float32Array(mvp));
    gl.bindBuffer(gl.ARRAY_BUFFER, wbuf);
    attr(wprog, "p", 3, 3, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.depthMask(true); gl.disable(gl.BLEND);

    if (nPts) {
      gl.useProgram(pprog);
      gl.uniformMatrix4fv(gl.getUniformLocation(pprog, "m"), false, new Float32Array(mvp));
      gl.bindBuffer(gl.ARRAY_BUFFER, pbuf);
      attr(pprog, "p", 3, 7, 0); attr(pprog, "c", 3, 7, 3); attr(pprog, "s", 1, 7, 6);
      gl.drawArrays(gl.POINTS, 0, nPts);
    }
  }

  return {
    init, render,
    get ok() { return ok; },
    get on() { return on; },
    set(v) { on = !!v && ok; if (on) { cv.style.display = "block"; } else if (cv) cv.style.display = "none"; return on; },
    resetView() { cam = null; },
  };
})();
if (typeof module !== "undefined" && module.exports && View3D) module.exports.View3D = View3D;
