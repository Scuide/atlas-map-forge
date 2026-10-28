// Atlas Map Forge - editor stage A: move / add / delete metal spots, geovents and start points.
// State lives in S.edits (a list, see atlasforge/edits.py); the server applies it to the generated design.
"use strict";

const ED = {
  on: false,
  tool: "move",
  sel: null,            // { kind, x, z } selected metal spot (for the metal field)
  drag: null,           // { kind, ref, x, z } while a spot is being dragged
  hover: null,          // map position under the pointer (add tools)
  pending: null,        // ghosts that stay until the server answered
  stroke: null,         // { id, last } while a brush stroke is drawn; last = map position of the last dab
  strokeSeq: 0,
  ramp: null,           // { a: [x, z] } a ramp start point A, waiting for the second click (B)
  rampDrag: null,       // { a, cur } while a ramp is dragged from A to B
  paint: null,          // { pts } while a paint stroke is drawn (one edit, one undo step)
  poly: null,           // { pts } corners of a fill polygon placed so far (closed by double click or the first corner)
  stamp: null,          // { src: [x0, z0, x1, z1] } the copied rectangle; every click pastes it
  stampDrag: null,      // { a, cur } while the rectangle to copy is dragged
  terrain: false,       // the terrain layers shown are computed with brush edits
  last: null,           // { tpl, values, seed } the current map was generated with
  seq: 0,
  timer: null,
  hist: [],             // list operations (delete, on/off) for undo: { before, n }; n = edit count after the operation
  rhist: [],            // the same for redo: { after, n }; n = edit count before the operation
  hl: null,             // edit group highlighted in the preview (clicked in the edit list)
  base: {},             // fields of a loaded project file we do not know (kept when saving)
  group: null,          // selected spots and start points [{ kind, x, z }]; one entry per mirror set, the mirror images follow
  marquee: null,        // { a, cur, hit } while a selection rectangle is dragged (Shift + drag), map positions
  mdrag: null,          // { x, z, cur } while the selection is dragged
  groupSeq: 0,          // edits made together (one selection move or delete) share a group id: one undo step
};
const ED_NUDGE = 8;     // arrow keys move the selection by this many elmos, Shift + arrow by 1

// ------------------------------------------------------------------ symmetry (mirrors atlasforge/symmetry.py)
function edOrbit(x, z) {
  const sy = S.map && S.map.sym;
  if (!sy || !S.symmetry) return [[x, z]];
  const W = S.map.W, H = S.map.H;
  if (sy.kind === "rot") {
    const out = [];
    for (let k = 0; k < sy.n; k++) {
      const a = 2 * Math.PI * k / sy.n, dx = x - W / 2, dz = z - H / 2;
      out.push([W / 2 + dx * Math.cos(a) - dz * Math.sin(a), H / 2 + dx * Math.sin(a) + dz * Math.cos(a)]);
    }
    return out;
  }
  if (sy.layout === "ew") return [[x, z], [W - x, z]];
  if (sy.layout === "ns") return [[x, z], [x, H - z]];
  return [[x, z], [W - x, H - z]];
}

// ------------------------------------------------------------------ settings guard (decision: confirm before regenerating)
function edSettingsKey() {
  const seed = Math.max(1, parseInt($("seed").value, 10) || 1);
  return JSON.stringify([S.tpl.id, S.values[S.tpl.id], seed]);
}

function edAsk() {
  return new Promise((resolve) => {
    const box = $("ed-confirm");
    const done = (v) => { box.classList.add("hidden"); $("ed-ok").onclick = $("ed-cancel").onclick = null; resolve(v); };
    $("ed-ok").onclick = () => done(true);
    $("ed-cancel").onclick = () => done(false);
    box.classList.remove("hidden");
  });
}

async function editorGuard() {
  if (!S.edits.length || !ED.last || edSettingsKey() === ED.last.key) return true;
  if (ED.asking) return false;
  ED.asking = true;
  try {
    if (await edAsk()) { S.edits = []; S.redo = []; ED.hist = []; ED.rhist = []; edUpdateUi(); return true; }
    // cancelled: put the old settings back, the map stays untouched
    S.values[ED.last.tpl] = JSON.parse(ED.last.values);
    store("values", S.values);
    $("seed").value = ED.last.seed;
    if (S.tpl.id !== ED.last.tpl) selectTemplate(ED.last.tpl); else renderParams();
    return false;
  } finally { ED.asking = false; }
}

function editorAfterPreview(m, seed) {
  S.edits = m.edits || [];
  ED.hist = []; ED.rhist = []; ED.hl = null;
  S.redo = [];
  ED.terrain = S.edits.some(edAffectsRelief);              // the preview is computed with these edits already
  S.symmetry = m.symmetry !== false;
  $("ed-sym").checked = S.symmetry;
  ED.last = { key: JSON.stringify([m.template, m.values, seed]), tpl: m.template, values: JSON.stringify(m.values), seed };
  ED.sel = null;
  ED.group = null;
  edShowProblems(m);
  edUpdateUi();
}

// ------------------------------------------------------------------ sending edits
function edSend(delay = 80) {
  clearTimeout(ED.timer);
  ED.timer = setTimeout(async () => {
    const seq = ++ED.seq;
    try {
      const terrain = ED.terrain || S.edits.some(edAffectsRelief);
      ED.terrain = S.edits.some(edAffectsRelief);
      const r = await api("edit", { id: S.map.id, edits: S.edits, symmetry: S.symmetry });
      if (seq !== ED.seq) return;
      // an edit the server refuses is dropped again, with the reason
      const bad = (r.problems || []).filter((p) => p.index === S.edits.length - 1 && ED.fresh);
      if (bad.length) {
        toast(bad[0].reason.charAt(0).toUpperCase() + bad[0].reason.slice(1) + ".");
        S.edits.pop();
        r.problems = r.problems.filter((p) => p !== bad[0]);
        edSend(0);
      }
      const wasFresh = ED.fresh;
      ED.fresh = false;
      const known = new Set((S.map.issues || []).map((i) => `${i.text}|${i.x}|${i.z}`));
      Object.assign(S.map, r);
      const added = (r.issues || []).filter((i) => !known.has(`${i.text}|${i.x}|${i.z}`));
      if (wasFresh && added.length) {                              // a placement just made something invalid
        const worst = added.find((i) => i.level === "error") || added[0];
        toast((worst.level === "error" ? "Problem: " : "Warning: ") + worst.text + (added.length > 1 ? ` (+${added.length - 1} more)` : "") + ".");
      }
      ED.pending = null;
      S.img.reach = {};
      S.img.overlay = {};
      if (terrain) await edReloadTerrain();
      if (S.route) await loadRoute(S.route);
      renderReport();
      renderFacts();
      edShowProblems(S.map);
      edUpdateUi();
      draw();
    } catch (e) { toast(e.message); ED.pending = null; draw(); }
  }, delay);
}

function edCommit(edit) {
  S.edits.push(edit);
  S.redo = [];
  ED.rhist = [];
  ED.fresh = true;
  edUpdateUi();
  edSend();
}

function edShowProblems(m) {
  const ul = $("report");
  for (const li of ul.querySelectorAll("li.ed-problem")) li.remove();
  for (const p of m.problems || []) {
    const li = document.createElement("li");
    li.className = "no ed-problem";
    li.textContent = `Edit ${p.index + 1} skipped: ${p.reason}`;
    ul.appendChild(li);
  }
}

// a brush stroke is many dabs sharing one stroke id: undo and redo take the whole stroke back at once
// the same for a selection move or delete: the edits share a group id
const edSameStep = (a, b) => (a.stroke !== undefined && a.stroke === b.stroke) || (a.group !== undefined && a.group === b.group);
function edMove(from, to) {
  const top = from.pop();
  to.push(top);
  while (from.length && edSameStep(top, from[from.length - 1])) to.push(from.pop());
}
const edClone = (a) => JSON.parse(JSON.stringify(a));
const edUndo = () => {
  const h = ED.hist[ED.hist.length - 1];
  if (h && h.n === S.edits.length) {                                // the last step was a list operation
    ED.hist.pop();
    ED.rhist.push({ after: edClone(S.edits), n: h.before.length });
    S.edits = h.before;
    edUpdateUi(); edSend();
    return;
  }
  if (S.edits.length) { edMove(S.edits, S.redo); edUpdateUi(); edSend(); }
};
const edRedo = () => {
  const h = ED.rhist[ED.rhist.length - 1];
  if (h && h.n === S.edits.length) {
    ED.rhist.pop();
    ED.hist.push({ before: edClone(S.edits), n: h.after.length });
    S.edits = h.after;
    ED.fresh = false; edUpdateUi(); edSend();
    return;
  }
  if (S.redo.length) { edMove(S.redo, S.edits); ED.fresh = false; edUpdateUi(); edSend(); }
};

// ------------------------------------------------------------------ edit list (side panel)
const ED_ICON = { move_mex: "◆", add_mex: "◆", del_mex: "◆", set_metal: "◆", move_geo: "▲", add_geo: "▲", del_geo: "▲",
  move_start: "⚑", set_box: "▭", brush: "⛰", paint: "🖌", features: "🌲" };

function edDescribe(e) {
  const at = (p) => `(${Math.round(p[0])}, ${Math.round(p[1])})`;
  switch (e.op) {
    case "move_mex": return `Move metal spot ${at(e.from)} → ${at(e.to)}`;
    case "add_mex": return `Add metal spot ${at(e.at)}`;
    case "del_mex": return `Delete metal spot ${at(e.at)}`;
    case "set_metal": return `Metal ${e.metal} at ${at(e.at)}`;
    case "move_geo": return `Move geovent ${at(e.from)} → ${at(e.to)}`;
    case "add_geo": return `Add geovent ${at(e.at)}`;
    case "del_geo": return `Delete geovent ${at(e.at)}`;
    case "move_start": return `Move start point ${at(e.from)} → ${at(e.to)}`;
    case "set_box": return `Start box, team ${e.team + 1}`;
    case "brush": return `Terrain: ${e.tool}`;
    case "stamp": return `Stamp → ${at(e.to)}${e.rotate ? `, turned ${e.rotate}°` : ""}${e.flip ? ", mirrored" : ""}`;
    case "paint": {
      const what = e.material === "erase" ? "Erase paint" : `Paint: ${e.material}`;
      if (e.fill === "poly") return `${what}, polygon`;
      if (e.fill === "band") return `${what}, heights ${e.low} to ${e.high}`;
      return what;
    }
    case "features": return `${e.mode === "add" ? "Add" : "Remove"} ${e.kind || "trees"}`;
  }
  return e.op;
}

// the list shows one row per user action: the dabs of a brush stroke are one row
function edGroups() {
  const out = [];
  S.edits.forEach((e, i) => {
    const last = out[out.length - 1];
    if (last && edSameStep(last.edits[0], e)) { last.idx.push(i); last.edits.push(e); }
    else out.push({ idx: [i], edits: [e] });
  });
  return out;
}

function edListOp(fn) {                                            // a list change: one undo step, clears redo
  const before = edClone(S.edits);
  fn();
  ED.hist.push({ before, n: S.edits.length });
  ED.rhist = [];
  S.redo = [];
  ED.fresh = false;
  edUpdateUi(); edSend(0);
}

function edRenderList() {
  const box = $("edit-list-block");
  if (!box) return;
  box.classList.toggle("hidden", !ED.on || !S.edits.length);
  const ul = $("edit-list");
  ul.textContent = "";
  const groups = edGroups();
  if (ED.hl && !groups.some((g) => g.edits[0] === ED.hl.edits[0])) ED.hl = null;
  groups.forEach((g, n) => {
    const e = g.edits[0], on = e.enabled !== false;
    const li = document.createElement("li");
    li.className = (on ? "" : "off ") + (ED.hl && ED.hl.edits[0] === e ? "hl" : "");
    const eye = document.createElement("button");
    eye.className = "ed-eye";
    eye.textContent = on ? "👁" : "—";
    eye.title = on ? "Switch this edit off" : "Switch this edit on";
    eye.onclick = (ev) => { ev.stopPropagation(); edListOp(() => { for (const x of g.edits) x.enabled = on ? false : true; }); };
    const label = document.createElement("span");
    label.className = "ed-lab";
    const dabs = g.edits.length > 1 ? ` (${g.edits.length} ${e.group !== undefined ? "items" : "dabs"})` : "";
    label.textContent = `${n + 1}. ${ED_ICON[e.op] || "•"} ${edDescribe(e)}${dabs}`;
    li.onclick = () => { ED.hl = ED.hl && ED.hl.edits[0] === e ? null : g; edRenderList(); draw(); };
    const del = document.createElement("button");
    del.className = "ed-del";
    del.textContent = "✕";
    del.title = "Delete this edit";
    del.onclick = (ev) => { ev.stopPropagation(); edListOp(() => { S.edits = S.edits.filter((x) => !g.edits.includes(x)); }); };
    li.append(eye, label, del);
    ul.appendChild(li);
  });
}

function edDrawHighlight() {
  if (!ED.hl) return;
  ctx.save();
  ctx.strokeStyle = "#4dd2ff"; ctx.fillStyle = "rgba(77,210,255,.18)"; ctx.lineWidth = 3;
  const ring = (p, r) => {
    const [sx, sy] = toScreen(p[0], p[1]);
    const rr = r ? Math.abs(toScreen(p[0] + r, p[1])[0] - sx) : 16;
    ctx.beginPath(); ctx.arc(sx, sy, Math.max(rr, 10), 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  };
  for (const e of ED.hl.edits) {
    if (e.op === "set_box" || (e.op === "paint" && e.fill === "poly")) { ctx.beginPath(); (e.points || []).forEach((p, i) => { const [sx, sy] = toScreen(p[0], p[1]); i ? ctx.lineTo(sx, sy) : ctx.moveTo(sx, sy); }); ctx.closePath(); ctx.fill(); ctx.stroke(); }
    else if (e.op === "paint" && e.fill === "band") { if (e.at) ring(e.at); }
    else if (e.op === "stamp") { for (const r of [edStampSrcPts(e.src), edStampDstPts(e.src, e.to, e.rotate, e.flip)]) { ctx.beginPath(); r.forEach((p, i) => { const [sx, sy] = toScreen(p[0], p[1]); i ? ctx.lineTo(sx, sy) : ctx.moveTo(sx, sy); }); ctx.closePath(); ctx.fill(); ctx.stroke(); } }
    else if (e.op === "paint") for (const p of e.points || []) ring(p, e.radius);
    else if (e.op === "brush" || e.op === "features") { ring(e.at, e.radius); if (e.to) ring(e.to, e.radius); }
    else { if (e.from) ring(e.from); ring(e.to || e.at); }
  }
  ctx.restore();
}

function edUpdateUi() {
  edRenderList();
  $("ed-toggle").classList.toggle("on", ED.on);
  $("ed-extra").classList.toggle("hidden", !ED.on);
  const treeMode = ED.tool === "brush" && edIsTreeTool();
  for (const b of document.querySelectorAll("#ed-extra [data-tool]")) b.classList.toggle("on", b.dataset.tool === ED.tool && !(treeMode && b.dataset.tool === "brush"));
  $("ed-trees").classList.toggle("on", treeMode);
  $("ed-brush-opts").classList.toggle("hidden", ED.tool !== "brush");
  $("ed-paint-opts").classList.toggle("hidden", ED.tool !== "paint");
  $("ed-stamp-opts").classList.toggle("hidden", ED.tool !== "stamp");
  $("ed-sinfo").textContent = ED.stamp ? `copy ${Math.round(ED.stamp.src[2] - ED.stamp.src[0])} × ${Math.round(ED.stamp.src[3] - ED.stamp.src[1])}: click to paste` : "drag a rectangle to copy";
  $("ed-pradius-wrap").classList.toggle("hidden", edPaintMode() !== "stroke");
  $("ed-band-wrap").classList.toggle("hidden", edPaintMode() !== "band");
  if (ED.tool !== "paint" || edPaintMode() !== "poly") ED.poly = null;      // open polygon corners belong to the poly fill
  $("ed-target-wrap").classList.toggle("hidden", $("ed-brush").value !== "flatten");
  $("ed-density-wrap").classList.toggle("hidden", !$("ed-brush").value.endsWith("-add"));
  $("ed-step-wrap").classList.toggle("hidden", $("ed-brush").value !== "terrace");
  if (ED.tool !== "brush" || !edIsRampTool()) ED.ramp = null;      // a pending ramp start belongs to the ramp tool
  $("ed-undo").disabled = !S.edits.length;
  $("ed-redo").disabled = !S.redo.length;
  $("ed-count").textContent = S.edits.length ? `${S.edits.length} edit${S.edits.length > 1 ? "s" : ""}` : "";
  edRenderBalance();
  cv.classList.toggle("editing", ED.on);
  $("ed-save").disabled = !S.map;
  if (S.map && S.map.sym) $("ed-sym").disabled = false;
}

// live metal balance per team / start position; the deviation from the average sets the colour
function edRenderBalance() {
  const box = $("ed-balance");
  box.textContent = "";
  const rows = ED.on && S.map && S.map.balance ? S.map.balance : [];
  for (const r of rows) {
    const a = Math.abs(r.dev);
    const span = document.createElement("span");
    span.className = "ed-bal " + (a <= 0.02 ? "ok" : a <= 0.10 ? "warn" : "bad");
    const pct = r.dev ? ` (${r.dev > 0 ? "+" : ""}${Math.round(r.dev * 100)}%)` : "";
    span.textContent = `${r.label}: ${r.metal.toFixed(1)}${pct}`;
    box.append(span);
  }
}

// ------------------------------------------------------------------ picking and dragging
function edPick(sx, sy) {
  const m = S.map;
  let best = null, bd = 1e9;
  const test = (kind, x, z, rad, ref) => {
    const [px, py] = toScreen(x, z);
    const d = Math.hypot(px - sx, py - sy);
    if (d <= rad + 4 && d < bd) { bd = d; best = { kind, x, z, ref }; }
  };
  for (const g of m.geos) test("geo", g[0], g[1], Math.max(6, Math.min(16, 48 * S.view.s)) * 1.3, g);
  for (const mx of m.mexes) test("mex", mx.x, mx.z, mexRadius(mx.metal), mx);
  m.teams.forEach((team) => team.forEach((p) => test("start", p[0], p[1], Math.max(9, Math.min(20, 70 * S.view.s)), p)));
  return best || edBoxPick(sx, sy);
}

// ------------------------------------------------------------------ start boxes (set_box)
// A rectangular polygon (4 axis-aligned points) resizes at its corners; any polygon moves from its inside.
function edRect(poly) {
  return poly.length === 4 && poly.every((p, i) => {
    const q = poly[(i + 1) % 4];
    return Math.abs(p[0] - q[0]) < 1e-6 || Math.abs(p[1] - q[1]) < 1e-6;
  });
}

function edInside(poly, x, z) {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, zi] = poly[i], [xj, zj] = poly[j];
    if ((zi > z) !== (zj > z) && x < (xj - xi) * (z - zi) / (zj - zi) + xi) c = !c;
  }
  return c;
}

function edBoxPick(sx, sy) {
  const [mx, mz] = toMap(sx, sy);
  let inside = null;
  for (const b of S.map.boxes || []) {
    for (let pi = 0; pi < b.polygons.length; pi++) {
      const poly = b.polygons[pi], ref = { team: b.team, poly: pi, pts: poly };
      if (edRect(poly)) {
        const ci = poly.findIndex((p) => Math.hypot(toScreen(p[0], p[1])[0] - sx, toScreen(p[0], p[1])[1] - sy) <= 9);
        if (ci >= 0) return { kind: "boxcorner", x: poly[ci][0], z: poly[ci][1], ref: { ...ref, corner: ci } };
      }
      if (!inside && edInside(poly, mx, mz)) inside = { kind: "box", x: mx, z: mz, ref };
    }
  }
  return inside;
}

// points of the box while it is dragged: d.cur is the pointer (box) or the grabbed corner (boxcorner)
function edBoxPts(d) {
  const pts = d.ref.pts, W = S.map.W, H = S.map.H;
  const xs = pts.map((p) => p[0]), zs = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), z0 = Math.min(...zs), z1 = Math.max(...zs);
  if (d.kind === "boxcorner") {
    const c = pts[d.ref.corner];
    const a = c[0] === x0 ? [d.cur[0], x1] : [x0, d.cur[0]];
    const b = c[1] === z0 ? [d.cur[1], z1] : [z0, d.cur[1]];
    const [ax, bx] = [Math.min(...a), Math.max(...a)], [az, bz] = [Math.min(...b), Math.max(...b)];
    return [[ax, az], [bx, az], [bx, bz], [ax, bz]].map((p) => [Math.round(p[0]), Math.round(p[1])]);
  }
  const dx = Math.min(Math.max(d.cur[0] - d.x, -x0), W - x1), dz = Math.min(Math.max(d.cur[1] - d.z, -z0), H - z1);
  return pts.map((p) => [Math.round(p[0] + dx), Math.round(p[1] + dz)]);
}

// ------------------------------------------------------------------ selection: a rectangle picks spots, start points and geovents
// ED.group keeps one entry per mirror set; its mirror images follow it (edOrbit), so a move or delete acts once
const edSameSpot = (a, b) => Math.abs(a[0] - b[0]) < 0.5 && Math.abs(a[1] - b[1]) < 0.5;
const edIsSpot = (hit) => !!hit && (hit.kind === "mex" || hit.kind === "geo" || hit.kind === "start");
const edSelected = (hit) => edIsSpot(hit) && !!ED.group && ED.group.some((s) => edOrbit(s.x, s.z).some((p) => edSameSpot(p, [hit.x, hit.z])));

function edSpots() {
  const m = S.map, out = [];
  for (const g of m.geos) out.push({ kind: "geo", x: g[0], z: g[1] });
  for (const mx of m.mexes) out.push({ kind: "mex", x: mx.x, z: mx.z });
  m.teams.forEach((team) => team.forEach((p) => out.push({ kind: "start", x: p[0], z: p[1] })));
  return out;
}

function edAddToGroup(spots) {
  for (const s of spots) {
    if (!ED.group.some((g) => edOrbit(g.x, g.z).some((p) => edSameSpot(p, [s.x, s.z])))) ED.group.push(s);
  }
}

// the offset the selection is drawn at while it is dragged (whole map units, as it is committed)
function edGroupOffset() {
  if (!ED.mdrag) return [0, 0];
  return [Math.round(ED.mdrag.cur[0] - ED.mdrag.x), Math.round(ED.mdrag.cur[1] - ED.mdrag.z)];
}

// one undo step: a move edit per entry (the server mirrors it). Entries moving onto an unmoved spot go first.
function edGroupMove(dx, dz) {
  const W = S.map.W, H = S.map.H, gid = ++ED.groupSeq;
  const sorted = [...ED.group].sort((a, b) => dx ? (dx > 0 ? b.x - a.x : a.x - b.x) : (dz > 0 ? b.z - a.z : a.z - b.z));
  const edits = [];
  for (const s of sorted) {
    const to = [Math.min(Math.max(Math.round(s.x + dx), 0), W), Math.min(Math.max(Math.round(s.z + dz), 0), H)];
    if (to[0] === s.x && to[1] === s.z) continue;
    edits.push({ op: "move_" + s.kind, from: [s.x, s.z], to, group: gid });
    s.x = to[0]; s.z = to[1];
  }
  edCommitMany(edits);
}

// one undo step. Start points stay (they cannot be deleted) and stay selected.
function edGroupDelete() {
  const gid = ++ED.groupSeq;
  const edits = ED.group.filter((s) => s.kind !== "start").map((s) => ({ op: "del_" + s.kind, at: [s.x, s.z], group: gid }));
  if (!edits.length) { toast("Start points cannot be deleted."); return; }
  edCommitMany(edits);
  ED.group = ED.group.filter((s) => s.kind === "start");
}

function edCommitMany(list) {
  if (!list.length) return;
  S.edits.push(...list);
  S.redo = [];
  ED.rhist = [];
  ED.fresh = true;
  edUpdateUi();
  edSend();
}

const edInRect = (a, b, s) => s.x >= Math.min(a[0], b[0]) && s.x <= Math.max(a[0], b[0]) && s.z >= Math.min(a[1], b[1]) && s.z <= Math.max(a[1], b[1]);

const edPos = (e) => {
  const r = cv.getBoundingClientRect();
  return [e.clientX - r.left, e.clientY - r.top];
};
const edClamp = (p) => [Math.min(Math.max(p[0], 0), S.map.W), Math.min(Math.max(p[1], 0), S.map.H)];

cv.addEventListener("pointerdown", (e) => {
  if (!ED.on || !S.map || e.button !== 0 || S.space) return;      // Space + drag pans
  const [sx, sy] = edPos(e);
  const hit = edPick(sx, sy);
  const [mx, mz] = edClamp(toMap(sx, sy));
  if (ED.tool === "move") {
    if (e.shiftKey) {                                  // Shift + drag: a selection rectangle
      e.stopImmediatePropagation();
      ED.marquee = { a: [mx, mz], cur: [mx, mz], hit: edIsSpot(hit) ? hit : null };
      cv.setPointerCapture(e.pointerId);
      draw();
      return;
    }
    if (edSelected(hit)) {                             // a selected spot: the whole selection moves
      e.stopImmediatePropagation();
      ED.mdrag = { x: mx, z: mz, cur: [mx, mz] };
      cv.setPointerCapture(e.pointerId);
      draw();
      return;
    }
    ED.group = null;
    if (!hit) return;                                  // empty ground: normal panning
    e.stopImmediatePropagation();
    ED.sel = hit.kind === "mex" ? hit : null;
    if (ED.sel) $("ed-metal").value = hit.ref.metal;
    ED.drag = { kind: hit.kind, x: hit.x, z: hit.z, cur: [hit.x, hit.z], ref: hit.ref };
    cv.setPointerCapture(e.pointerId);
    draw();
  } else if (ED.tool === "brush" && e.altKey) {       // pipette: take the height under the pointer as flatten target
    e.stopImmediatePropagation();
    const h = edHeightAt(mx, mz);
    if (h !== null) { $("ed-target").value = h; toast("Target height " + h); }
    draw();
  } else if (ED.tool === "brush" && edIsRampTool()) {
    e.stopImmediatePropagation();
    cv.setPointerCapture(e.pointerId);
    if (ED.ramp) edRampCommit(ED.ramp.a, [mx, mz]);                // second click: B
    else ED.rampDrag = { a: [mx, mz], cur: [mx, mz] };  // first click or drag: A (and B when dragged)
    draw();
  } else if (ED.tool === "stamp") {                    // drag: the rectangle to copy; click: paste the copy there
    e.stopImmediatePropagation();
    cv.setPointerCapture(e.pointerId);
    ED.stampDrag = { a: [mx, mz], cur: [mx, mz] };
    draw();
  } else if (ED.tool === "paint" && edPaintMode() === "band" && e.altKey) {   // pipette: Alt = from, Shift+Alt = to
    e.stopImmediatePropagation();
    const h = edHeightAt(mx, mz);
    if (h !== null) { $(e.shiftKey ? "ed-bhigh" : "ed-blow").value = h; toast((e.shiftKey ? "Up to height " : "From height ") + h); }
    draw();
  } else if (ED.tool === "paint" && edPaintMode() === "band") {
    e.stopImmediatePropagation();
    let low = Number($("ed-blow").value), high = Number($("ed-bhigh").value);
    if (!Number.isFinite(low) || !Number.isFinite(high)) { toast("Enter the two heights of the band."); return; }
    if (low > high) [low, high] = [high, low];
    const ed = { op: "paint", material: $("ed-pmat").value, fill: "band", low, high, strength: edPaintStrength() };
    if ($("ed-bpatch").checked) ed.at = [Math.round(mx), Math.round(mz)];
    edCommit(ed);
    draw();
  } else if (ED.tool === "paint" && edPaintMode() === "poly") {
    e.stopImmediatePropagation();
    const p = [mx, mz];
    if (!ED.poly) ED.poly = { pts: [p] };
    else {
      const [fx, fy] = toScreen(ED.poly.pts[0][0], ED.poly.pts[0][1]);
      if (ED.poly.pts.length >= 3 && Math.hypot(fx - sx, fy - sy) < 10) edPolyCommit();   // first corner again: close
      else if (ED.poly.pts.length < 400) ED.poly.pts.push(p);
    }
    draw();
  } else if (ED.tool === "paint") {
    e.stopImmediatePropagation();
    cv.setPointerCapture(e.pointerId);
    ED.paint = { pts: [[mx, mz]] };
    draw();
  } else if (ED.tool === "brush" && edIsFeatureTool()) {  // trees, rocks, wrecks: one click plants or clears the circle
    e.stopImmediatePropagation();
    edFeatureCommit([mx, mz]);
    draw();
  } else if (ED.tool === "brush") {
    e.stopImmediatePropagation();
    cv.setPointerCapture(e.pointerId);
    ED.stroke = { id: ++ED.strokeSeq, last: null };
    edDab(mx, mz);
    draw();
  } else if (ED.tool === "del") {
    e.stopImmediatePropagation();
    if (!hit) return;
    if (hit.kind === "start") { toast("Start points cannot be deleted."); return; }
    if (hit.kind.startsWith("box")) { toast("Start boxes cannot be deleted, drag them instead."); return; }
    ED.pending = null;
    edCommit({ op: "del_" + hit.kind, at: [hit.x, hit.z] });
  } else {                                             // mex / geo: add
    e.stopImmediatePropagation();
    if (ED.tool === "mex") {
      const metal = Math.min(9, Math.max(0.1, parseFloat($("ed-metal").value) || 2));
      edCommit({ op: "add_mex", at: [Math.round(mx), Math.round(mz)], metal });
    } else edCommit({ op: "add_geo", at: [Math.round(mx), Math.round(mz)] });
  }
}, true);

cv.addEventListener("pointermove", (e) => {
  if (!S.map) return;
  const [hx, hy] = edPos(e);
  const prev = ED.issueHover;
  ED.issueHover = (S.map.issues || []).find((i) => {
    const [ix, iy] = toScreen(i.x, i.z);
    return Math.hypot(ix - hx, iy - hy) < 24;
  }) || null;
  if (prev !== ED.issueHover && !ED.drag) draw();
}, true);

cv.addEventListener("pointermove", (e) => {
  if (!ED.on || !S.map) return;
  const [sx, sy] = edPos(e);
  if (ED.paint) {
    e.stopImmediatePropagation();
    const p = edClamp(toMap(sx, sy)), l = ED.paint.pts[ED.paint.pts.length - 1];
    ED.hover = p;
    if (Math.hypot(p[0] - l[0], p[1] - l[1]) >= edPaintRadius() * 0.2 && ED.paint.pts.length < 400) ED.paint.pts.push(p);
    draw();
  } else if (ED.stroke) {
    e.stopImmediatePropagation();
    const [mx, mz] = edClamp(toMap(sx, sy));
    ED.hover = [mx, mz];
    const l = ED.stroke.last;
    if (!l || Math.hypot(mx - l[0], mz - l[1]) >= edBrushRadius() * 0.25) edDab(mx, mz);
    draw();
  } else if (ED.rampDrag) {
    e.stopImmediatePropagation();
    ED.rampDrag.cur = edClamp(toMap(sx, sy));
    draw();
  } else if (ED.marquee) {
    e.stopImmediatePropagation();
    ED.marquee.cur = edClamp(toMap(sx, sy));
    draw();
  } else if (ED.mdrag) {
    e.stopImmediatePropagation();
    ED.mdrag.cur = edClamp(toMap(sx, sy));
    draw();
  } else if (ED.stampDrag) {
    e.stopImmediatePropagation();
    ED.stampDrag.cur = ED.hover = edClamp(toMap(sx, sy));
    draw();
  } else if (ED.drag) {
    e.stopImmediatePropagation();
    ED.drag.cur = edClamp(toMap(sx, sy));
    draw();
  } else if (ED.tool === "mex" || ED.tool === "geo" || ED.tool === "brush" || ED.tool === "paint" || ED.tool === "stamp") {
    ED.hover = edClamp(toMap(sx, sy));
    draw();
  }
}, true);

const edEnd = (e) => {
  if (ED.paint) {
    e.stopImmediatePropagation();
    const pts = ED.paint.pts.map((p) => [Math.round(p[0]), Math.round(p[1])]);
    ED.paint = null;
    edCommit({ op: "paint", material: $("ed-pmat").value, points: pts, radius: edPaintRadius(), strength: edPaintStrength() });
    draw();
    return;
  }
  if (ED.stroke) { e.stopImmediatePropagation(); ED.stroke = null; draw(); return; }
  if (ED.stampDrag) {
    e.stopImmediatePropagation();
    const r = ED.stampDrag;
    ED.stampDrag = null;
    const src = [Math.min(r.a[0], r.cur[0]), Math.min(r.a[1], r.cur[1]), Math.max(r.a[0], r.cur[0]), Math.max(r.a[1], r.cur[1])].map(Math.round);
    if (Math.hypot(r.cur[0] - r.a[0], r.cur[1] - r.a[1]) * S.view.s > 3) {           // dragged: a new copy
      if (src[2] - src[0] < 16 || src[3] - src[1] < 16) toast("The rectangle to copy must be at least 16 elmos on each side.");
      else { ED.stamp = { src }; toast("Copied. Click where the copy goes (Q turns it, M mirrors it)."); }
      edUpdateUi();
    } else if (ED.stamp) edStampCommit(r.a);                                          // a click: paste
    else toast("Drag a rectangle first to copy its heights.");
    draw();
    return;
  }
  if (ED.rampDrag) {
    e.stopImmediatePropagation();
    const r = ED.rampDrag;
    ED.rampDrag = null;
    if (Math.hypot(r.cur[0] - r.a[0], r.cur[1] - r.a[1]) * S.view.s > 3) edRampCommit(r.a, r.cur);   // dragged: A to B
    else ED.ramp = { a: r.a };                          // a click: A is set, B comes with the next click
    draw();
    return;
  }
  if (ED.marquee) {
    e.stopImmediatePropagation();
    const m = ED.marquee;
    ED.marquee = null;
    if (Math.hypot(m.cur[0] - m.a[0], m.cur[1] - m.a[1]) * S.view.s <= 3) {   // a click with Shift: that spot, or none
      ED.group = m.hit ? [{ kind: m.hit.kind, x: m.hit.x, z: m.hit.z }] : null;
    } else {
      ED.group = [];
      edAddToGroup(edSpots().filter((s) => edInRect(m.a, m.cur, s)));
      if (!ED.group.length) ED.group = null;
    }
    draw();
    return;
  }
  if (ED.mdrag) {
    e.stopImmediatePropagation();
    const [dx, dz] = edGroupOffset();
    ED.mdrag = null;
    if (dx || dz) edGroupMove(dx, dz);
    draw();
    return;
  }
  if (!ED.drag) return;
  e.stopImmediatePropagation();
  const d = ED.drag;
  ED.drag = null;
  const moved = Math.hypot(d.cur[0] - d.x, d.cur[1] - d.z) * S.view.s > 3;   // a click only selects
  if (moved && d.kind.startsWith("box")) {
    edCommit({ op: "set_box", team: d.ref.team, poly: d.ref.poly, points: edBoxPts(d) });
  } else if (moved) {
    ED.pending = { kind: d.kind, pts: edOrbit(d.cur[0], d.cur[1]) };
    edCommit({ op: "move_" + d.kind, from: [d.x, d.z], to: [Math.round(d.cur[0]), Math.round(d.cur[1])] });
  }
  draw();
};
cv.addEventListener("pointerup", edEnd, true);
cv.addEventListener("pointercancel", edEnd, true);
cv.addEventListener("pointerleave", () => { ED.hover = null; if (ED.on) draw(); });

// ------------------------------------------------------------------ drawing
function drawEditor() {
  if (!S.map) return;
  edDrawHighlight();
  for (const i of S.map.issues || []) {                            // live checks: red = error, yellow = warning
    const [sx, sy] = toScreen(i.x, i.z);
    ctx.beginPath();
    ctx.arc(sx, sy, 18, 0, Math.PI * 2);
    ctx.lineWidth = 3;
    ctx.strokeStyle = i.level === "error" ? "#ff4d4d" : "#ffd23c";
    ctx.stroke();
    ctx.fillStyle = ctx.strokeStyle;                               // "!" badge so the warning is visible on any terrain
    ctx.beginPath();
    ctx.arc(sx + 14, sy - 14, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#111";
    ctx.font = "bold 11px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("!", sx + 14, sy - 13);
  }
  const hi = ED.issueHover;                                        // tooltip with the reason, next to the object
  if (hi) {
    const [sx, sy] = toScreen(hi.x, hi.z);
    ctx.font = "12px sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    const w = ctx.measureText(hi.text).width + 12;
    const tx = Math.min(sx + 24, cv.width - w - 4), ty = Math.max(sy - 30, 14);
    ctx.fillStyle = "rgba(20,20,20,.92)";
    ctx.fillRect(tx, ty - 11, w, 22);
    ctx.strokeStyle = hi.level === "error" ? "#ff4d4d" : "#ffd23c";
    ctx.lineWidth = 1;
    ctx.strokeRect(tx, ty - 11, w, 22);
    ctx.fillStyle = "#fff";
    ctx.fillText(hi.text, tx + 6, ty);
  }
  if (!ED.on) return;
  if (ED.tool === "move") {                            // corner handles of rectangular start boxes
    for (const b of S.map.boxes || []) for (const poly of b.polygons) if (edRect(poly)) for (const p of poly) {
      const [sx, sy] = toScreen(p[0], p[1]);
      ctx.fillStyle = "#fff";
      ctx.fillRect(sx - 4, sy - 4, 8, 8);
    }
  }
  if (ED.drag && ED.drag.kind.startsWith("box")) {     // live preview of the box being dragged
    const pts = edBoxPts(ED.drag);
    ctx.save();
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#fff";
    ctx.beginPath();
    pts.forEach((p, i) => { const [sx, sy] = toScreen(p[0], p[1]); i ? ctx.lineTo(sx, sy) : ctx.moveTo(sx, sy); });
    ctx.closePath();
    ctx.stroke();
    ctx.restore();
  }
  const ghost = (kind, pts, strong) => {
    ctx.save();
    ctx.setLineDash([5, 4]);
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#fff";
    ctx.fillStyle = kind === "geo" ? "rgba(255,122,26,.45)" : kind === "start" ? "rgba(255,255,255,.3)" : "rgba(60,200,255,.45)";
    pts.forEach((p, i) => {
      const [sx, sy] = toScreen(p[0], p[1]);
      ctx.globalAlpha = i === 0 || strong ? 1 : 0.7;
      ctx.beginPath();
      if (kind === "geo") ctx.rect(sx - 8, sy - 8, 16, 16);
      else ctx.arc(sx, sy, kind === "start" ? 14 : mexRadius(2), 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });
    ctx.restore();
  };
  if (ED.drag && !ED.drag.kind.startsWith("box")) ghost(ED.drag.kind, edOrbit(ED.drag.cur[0], ED.drag.cur[1]), true);
  else if (ED.pending) ghost(ED.pending.kind, ED.pending.pts, false);
  else if (ED.hover && (ED.tool === "mex" || ED.tool === "geo")) ghost(ED.tool, edOrbit(ED.hover[0], ED.hover[1]), false);
  if (ED.tool === "paint" && edPaintMode() !== "stroke") {   // fills: the open polygon (and its images) up to the pointer
    if (ED.poly) {
      const pts = ED.hover ? ED.poly.pts.concat([ED.hover]) : ED.poly.pts;
      const imgs = pts.map((p) => edOrbit(p[0], p[1]));
      ctx.save();
      ctx.fillStyle = EDPAINT_COLORS[$("ed-pmat").value] || "rgba(255,255,255,0.4)";
      ctx.strokeStyle = "#fff"; ctx.setLineDash([4, 3]);
      for (let k = 0; k < imgs[0].length; k++) {
        ctx.globalAlpha = k ? 0.4 : 1;
        ctx.lineWidth = k ? 1 : 2;
        ctx.beginPath();
        imgs.forEach((o, i) => { const [x, y] = toScreen(o[k][0], o[k][1]); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
        ctx.closePath(); ctx.fill(); ctx.stroke();
      }
      ctx.restore();
    }
  } else if (ED.paint || (ED.tool === "paint" && ED.hover)) {   // paint: the stroke so far, or the ring of the brush
    const pts = ED.paint ? ED.paint.pts : [ED.hover];
    ctx.save();
    ctx.lineCap = ctx.lineJoin = "round";
    ctx.strokeStyle = EDPAINT_COLORS[$("ed-pmat").value] || "rgba(255,255,255,0.4)";
    ctx.lineWidth = Math.max(2, 2 * edPaintRadius() * S.view.s);
    ctx.beginPath();
    pts.forEach((p, i) => { const [x, y] = toScreen(p[0], p[1]); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
    if (pts.length === 1) { const [x, y] = toScreen(pts[0][0], pts[0][1]); ctx.lineTo(x + 0.01, y); }
    ctx.stroke();
    if (!ED.paint && ED.hover) {
      const [x, y] = toScreen(ED.hover[0], ED.hover[1]);
      ctx.setLineDash([4, 3]); ctx.lineWidth = 2; ctx.strokeStyle = "#fff";
      ctx.beginPath(); ctx.arc(x, y, edPaintRadius() * S.view.s, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.restore();
  } else if (ED.tool === "stamp") {
    edDrawStamp();
  } else if (ED.tool === "brush" && edIsRampTool()) {         // ramp: the strip from A to the pointer, width = radius
    const a = ED.rampDrag ? ED.rampDrag.a : ED.ramp && ED.ramp.a;
    const b = ED.rampDrag ? ED.rampDrag.cur : ED.hover;
    if (a && b) {
      const [ax, ay] = toScreen(a[0], a[1]);
      const [bx, by] = toScreen(b[0], b[1]);
      ctx.save();
      ctx.lineCap = "round";
      ctx.strokeStyle = "rgba(255,255,255,0.2)";
      ctx.lineWidth = edBrushRadius() * S.view.s;
      ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
      ctx.setLineDash([4, 3]);
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#fff";
      ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
      ctx.restore();
    }
  } else if (ED.tool === "brush" && ED.hover) {        // brush ring: the reach of one dab, thin rings at the mirror images
    ctx.save();
    ctx.setLineDash([4, 3]);
    ctx.strokeStyle = "#fff";
    edOrbit(ED.hover[0], ED.hover[1]).forEach(([ox, oz], k) => {
      const [sx, sy] = toScreen(ox, oz);
      ctx.globalAlpha = k ? 0.4 : 1;
      ctx.lineWidth = k ? 1 : 2;
      ctx.beginPath();
      ctx.arc(sx, sy, edBrushRadius() * S.view.s, 0, Math.PI * 2);
      ctx.stroke();
    });
    ctx.restore();
  }
  if (ED.sel && ED.sel.ref) {
    const [sx, sy] = toScreen(ED.sel.ref.x, ED.sel.ref.z);
    ctx.beginPath();
    ctx.arc(sx, sy, mexRadius(ED.sel.ref.metal) + 5, 0, Math.PI * 2);
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#ffd23c";
    ctx.stroke();
  }
  if (ED.group) {                                      // selection: a ring on every spot, mirror images included
    const [gdx, gdz] = edGroupOffset();
    ctx.save();
    ctx.setLineDash([3, 3]);
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#7fd4ff";
    for (const s of ED.group) for (const [x, z] of edOrbit(s.x + gdx, s.z + gdz)) {
      const [sx, sy] = toScreen(x, z);
      ctx.beginPath();
      ctx.arc(sx, sy, 12, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.restore();
  }
  if (ED.marquee) {                                    // the selection rectangle
    const [ax, ay] = toScreen(ED.marquee.a[0], ED.marquee.a[1]);
    const [bx, by] = toScreen(ED.marquee.cur[0], ED.marquee.cur[1]);
    ctx.save();
    ctx.setLineDash([4, 3]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#7fd4ff";
    ctx.fillStyle = "rgba(127,212,255,.12)";
    ctx.fillRect(ax, ay, bx - ax, by - ay);
    ctx.strokeRect(ax, ay, bx - ax, by - ay);
    ctx.restore();
  }
}

// ------------------------------------------------------------------ toolbar and keys
$("ed-toggle").onclick = () => { ED.on = !ED.on; ED.drag = ED.hover = ED.group = ED.marquee = ED.mdrag = null; edUpdateUi(); draw(); };
for (const b of document.querySelectorAll("#ed-extra [data-tool]")) b.onclick = () => { ED.tool = b.dataset.tool; edUpdateUi(); };
$("ed-trees").onclick = () => edBrushTool($("ed-brush").value.startsWith("trees-") ? $("ed-brush").value : "trees-add");
$("ed-undo").onclick = edUndo;
$("ed-redo").onclick = edRedo;
$("ed-sym").onchange = () => { S.symmetry = $("ed-sym").checked; edSend(0); };
$("ed-brush").onchange = edUpdateUi;
$("ed-pmat").onchange = edUpdateUi;
$("ed-pmode").onchange = () => { edUpdateUi(); draw(); };
$("ed-srot").onchange = $("ed-sflip").onchange = () => draw();
$("ed-metal").onchange = () => {
  const v = Math.min(9, Math.max(0.1, parseFloat($("ed-metal").value) || 2));
  if (ED.sel && ED.sel.ref) edCommit({ op: "set_metal", at: [ED.sel.x, ED.sel.z], metal: v });
};

document.addEventListener("keydown", (e) => {
  if (e.target.matches("input, textarea") || !S.map || !$("help").classList.contains("hidden")) return;   // the help overlay takes the keys
  if ((e.ctrlKey || e.metaKey) && !e.altKey) {
    const k = e.key.toLowerCase();
    if (k === "z" && !e.shiftKey) { e.preventDefault(); edUndo(); }
    else if (k === "y" || (k === "z" && e.shiftKey)) { e.preventDefault(); edRedo(); }
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === "e") { $("ed-toggle").click(); }
  else if (ED.on && k === "v") { ED.tool = "move"; edUpdateUi(); }
  else if (ED.on && k === "1") { ED.tool = "mex"; edUpdateUi(); e.stopImmediatePropagation(); }
  else if (ED.on && k === "2") { ED.tool = "geo"; edUpdateUi(); e.stopImmediatePropagation(); }
  else if (ED.on && k === "x") { ED.tool = "del"; edUpdateUi(); }
  else if (ED.on && k === "b") { ED.tool = "brush"; edUpdateUi(); }
  else if (ED.on && k === "p") { ED.tool = "paint"; edUpdateUi(); }
  else if (ED.on && k === "r") { edBrushTool("ramp"); }
  else if (ED.on && k === "f") { edBrushTool("flatten"); }
  else if (ED.on && (e.code === "BracketLeft" || e.code === "BracketRight")) {   // e.key is { } with Shift, so go by code
    e.preventDefault();
    edNudge(e.code === "BracketRight" ? 1 : -1, e.shiftKey);
  }
  else if (ED.on && k === "delete" && ED.group) { e.preventDefault(); edGroupDelete(); draw(); }
  else if (ED.on && ED.tool === "move" && ED.group && k.startsWith("arrow")) {   // arrows move the selection, Shift by 1 elmo
    e.preventDefault();
    const n = e.shiftKey ? 1 : ED_NUDGE;
    const d = { arrowleft: [-n, 0], arrowright: [n, 0], arrowup: [0, -n], arrowdown: [0, n] }[k] || [0, 0];
    edGroupMove(d[0], d[1]);
    draw();
  }
  else if (ED.on && k === "k") { ED.tool = "stamp"; edUpdateUi(); }
  else if (ED.on && ED.tool === "stamp" && k === "q") { e.stopImmediatePropagation(); edStampTurn(e.shiftKey ? -90 : 90); }
  else if (ED.on && ED.tool === "stamp" && k === "m") { e.stopImmediatePropagation(); $("ed-sflip").checked = !$("ed-sflip").checked; draw(); }
  else if (ED.on && k === "escape" && ED.poly) { ED.poly = null; draw(); }     // first Esc drops the open polygon
  else if (ED.on && k === "escape" && ED.tool === "stamp" && ED.stamp) { ED.stamp = null; edUpdateUi(); draw(); }
  else if (ED.on && k === "escape") { ED.ramp = null; ED.group = null; ED.tool = "move"; edUpdateUi(); draw(); }
}, true);

// ------------------------------------------------------------------ brush (terrain, stage B)
const edIsBrush = (x) => x.op === "brush";
const edAffectsRelief = (x) => x.op === "brush" || x.op === "stamp" || x.op === "paint";     // the server's cached relief picture is replaced
const EDPAINT_COLORS = { path: "rgba(200,180,140,0.55)", concrete: "rgba(190,190,190,0.55)",
  scorch: "rgba(40,30,25,0.6)", lava: "rgba(255,110,20,0.6)", erase: "rgba(255,255,255,0.25)" };
function edPaintMode() { return $("ed-pmode").value; }       // stroke | poly | band (a declaration: edUpdateUi needs it early)
function edPolyCommit() {                                      // one edit for the whole polygon; repeated corners dropped
  const pts = [];
  for (const p of (ED.poly ? ED.poly.pts : []).map((q) => [Math.round(q[0]), Math.round(q[1])])) {
    const l = pts[pts.length - 1];
    if (!l || Math.hypot(p[0] - l[0], p[1] - l[1]) > 2) pts.push(p);
  }
  ED.poly = null;
  if (pts.length < 3) { toast("A fill polygon needs at least 3 corners."); draw(); return; }
  edCommit({ op: "paint", material: $("ed-pmat").value, fill: "poly", points: pts, strength: edPaintStrength() });
  draw();
}
cv.addEventListener("dblclick", (e) => {                       // double click closes the fill polygon
  if (!ED.on || !ED.poly) return;
  e.stopImmediatePropagation();
  edPolyCommit();
}, true);
const edPaintRadius = () => Math.min(1000, Math.max(8, Number($("ed-pradius").value) || 96));
const edPaintStrength = () => Math.min(1, Math.max(0.1, Number($("ed-pstrength").value) || 1));
const edBrushRadius = () => Math.min(2000, Math.max(8, Number($("ed-radius").value) || 200));
const edBrushStrength = () => Math.min(1, Math.max(0, Number($("ed-strength").value)));
const edIsRampTool = () => $("ed-brush").value === "ramp";
const edStep = () => Math.max(1, Math.round(Number($("ed-step").value) || 20));
const edIsFeatureTool = () => /^(trees|rocks|wrecks)-/.test($("ed-brush").value);
const edDensity = () => Math.min(1, Math.max(0, Number($("ed-density").value) || 0));

// one features edit per click: trees, rocks or wrecks added or removed in the circle of the radius (mirrored)
function edFeatureCommit(at) {
  const [kind, mode] = $("ed-brush").value.split("-");
  edCommit({ op: "features", kind, mode, at: [Math.round(at[0]), Math.round(at[1])],
             radius: edBrushRadius(), density: edDensity() });
}
const edTarget = () => {                             // flatten target height, null = the height under each dab
  const v = $("ed-target").value;
  return v === "" || !Number.isFinite(Number(v)) ? null : Math.round(Number(v));
};

// the Brush tool with one of its modes: the keys R, F and B pick the mode in the dropdown
function edBrushTool(mode) {
  ED.tool = "brush";
  $("ed-brush").value = mode;
  edUpdateUi();
}

// [ ] change the radius by 8 elmos, Shift+[ ] the strength by 0.05
function edNudge(dir, strength) {
  if (strength) $("ed-strength").value = Math.min(1, Math.max(0, Math.round((edBrushStrength() + dir * 0.05) * 20) / 20));
  else $("ed-radius").value = Math.min(2000, Math.max(8, edBrushRadius() + dir * 8));
  edUpdateUi();
  draw();
}

// the terrain height at a map position (the grid is one cell per 8 elmos), for the flatten pipette
function edHeightAt(x, z) {
  const g = S.grid;
  if (!g) return null;
  const ix = Math.min(g.nx - 1, Math.max(0, Math.round(x / 8))), iz = Math.min(g.nz - 1, Math.max(0, Math.round(z / 8)));
  return g.height[iz * g.nx + ix];
}

// ramp from A to B: one edit, so one undo step
function edRampCommit(a, b) {
  ED.ramp = null;
  ED.rampDrag = null;
  const at = [Math.round(a[0]), Math.round(a[1])], to = [Math.round(b[0]), Math.round(b[1])];
  if (at[0] === to[0] && at[1] === to[1]) { toast("A ramp needs two different points."); draw(); return; }
  edCommit({ op: "brush", tool: "ramp", at, to, radius: edBrushRadius(), strength: edBrushStrength() });
}

// stamp: corners of the copied rectangle, and of its copy at `to` turned `rot` degrees clockwise (mirrored left-right
// first when flip), in the order of the source corners top-left, top-right, bottom-right, bottom-left
const edStampSrcPts = (s) => [[s[0], s[1]], [s[2], s[1]], [s[2], s[3]], [s[0], s[3]]];
function edStampDstPts(s, to, rot, flip) {
  const hw = (s[2] - s[0]) / 2, hh = (s[3] - s[1]) / 2;
  return [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]].map(([x, z]) => {
    if (flip) x = -x;
    for (let k = 0; k < (rot || 0) / 90; k++) [x, z] = [-z, x];          // a quarter turn clockwise (z points down)
    return [to[0] + x, to[1] + z];
  });
}
const edStampRot = () => Number($("ed-srot").value) || 0;
const edStampBlend = () => Math.min(1000, Math.max(0, Number($("ed-sblend").value) || 0));
function edStampCommit(p) {                                    // one paste = one edit, so one undo step
  edCommit({ op: "stamp", src: ED.stamp.src, to: [Math.round(p[0]), Math.round(p[1])], rotate: edStampRot(),
             flip: $("ed-sflip").checked, blend: edStampBlend() });
}
function edDrawStamp() {
  const poly = (pts, k) => {
    ctx.globalAlpha = k ? 0.4 : 1;
    ctx.lineWidth = k ? 1 : 2;
    ctx.beginPath();
    pts.forEach((p, i) => { const [x, y] = toScreen(p[0], p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.closePath(); ctx.fill(); ctx.stroke();
  };
  ctx.save();
  ctx.setLineDash([4, 3]);
  ctx.strokeStyle = "#fff";
  ctx.fillStyle = "rgba(255,255,255,0.12)";
  if (ED.stampDrag) {                                           // the rectangle being copied
    const a = ED.stampDrag.a, b = ED.stampDrag.cur;
    poly(edStampSrcPts([Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])]), 0);
  } else if (ED.stamp) {
    poly(edStampSrcPts(ED.stamp.src), 0);
    if (ED.hover) {                                             // the copy under the pointer and at every mirror image
      const pts = edStampDstPts(ED.stamp.src, ED.hover, edStampRot(), $("ed-sflip").checked);
      const imgs = pts.map((p) => edOrbit(p[0], p[1]));
      ctx.fillStyle = "rgba(120,200,255,0.2)";
      for (let k = 0; k < imgs[0].length; k++) {
        const q = imgs.map((o) => o[k]);
        poly(q, k);
        const [cx, cy] = toScreen(q[0][0], q[0][1]);            // a dot on the copied top-left corner shows the turn
        ctx.beginPath(); ctx.arc(cx, cy, k ? 3 : 5, 0, Math.PI * 2); ctx.fillStyle = "#fff"; ctx.fill();
        ctx.fillStyle = "rgba(120,200,255,0.2)";
      }
    }
  }
  ctx.restore();
}
function edStampTurn(d) {
  $("ed-srot").value = String((edStampRot() + d + 360) % 360);
  draw();
}

// one dab of the stroke: a brush edit at a map position, tagged with the stroke it belongs to
function edDab(x, z) {
  const tool = $("ed-brush").value, target = tool === "flatten" ? edTarget() : null;
  // noise: the stroke id seeds the pattern, so every dab of one stroke shares it and a reload replays it exactly
  const extra = tool === "noise" ? { seed: ED.stroke.id } : tool === "terrace" ? { amount: edStep() } : {};
  edCommit({
    op: "brush", tool, at: [Math.round(x), Math.round(z)],
    radius: edBrushRadius(), strength: edBrushStrength(), stroke: ED.stroke.id,
    ...(target === null ? {} : { target }), ...extra,
  });
  ED.stroke.last = [x, z];
}

// the terrain layers changed: fetch the new picture, heights and cells (the server dropped its cache)
async function edReloadTerrain() {
  const id = S.map.id;
  const [relief, height, cells, hazard] = await Promise.all([
    api(layerUrl("relief", S.img.reliefSize)),
    api(`layer/${id}/height`),
    api(`layer/${id}/cells`),
    S.map.has_hazard ? api(`layer/${id}/hazard`) : null,
  ]);
  if (!S.map || S.map.id !== id) return;
  S.img.relief = relief;
  S.img.hazard = hazard;
  S.grid = { ...S.grid, height: new Int16Array(height), cells: new Uint8Array(cells) };
}

// ------------------------------------------------------------------ project files (.forge.json)
async function edSave() {
  const title = ($("title").value || S.map.title || "map").trim();
  const data = Object.assign({}, ED.base, {
    template: S.map.template, values: S.map.values, seed: S.map.seed, symmetry: S.symmetry, edits: S.edits, title,
    app_version: S.info.version,
  });
  try {
    const r = await api("project_save", { data });
    toastAction("Project saved: " + r.path, "Open folder", () => api("open", { path: r.path }).catch((e) => toast(e.message)));
  } catch (e) { toast(e.message); }
}

async function edOpen(file) {
  edLoad({ text: await file.text() });
}

async function edLoad(req) {
  try { applyProject(await api("project_load", req)); } catch (e) { toast(e.message); }
}

function applyProject(r) {
  const p = r.project;
  const t = S.info.templates.find((x) => x.id === p.template);
  if (!t) throw new Error("Unknown template: " + p.template);
  ED.base = r.extra || {};
  S.values[p.template] = Object.assign({}, S.values[p.template] || {}, p.values || {});
  S.seeds[p.template] = p.seed;
  S.edits = p.edits || [];
  ED.hist = []; ED.rhist = []; ED.hl = null;
  S.symmetry = p.symmetry !== false;
  ED.last = null;                                    // loading replaces the map: nothing to confirm
  selectTemplate(p.template);
  clearTimeout(pvTimer);
  $("seed").value = p.seed;
  S.titleEdited[p.template] = !!p.title;
  runPreview(true).then(() => { if (p.title) $("title").value = p.title; });
}

$("ed-save").onclick = () => S.map && edSave();
$("ed-open").onclick = async () => {
  if (!pickAvailable) return $("ed-file").click();
  try {
    const p = await window.pywebview.api.pick_project(S.info.settings.projdir || "");
    if (p) edLoad({ path: p });
  } catch (e) { toast(e.message); }
};
$("ed-file").onchange = () => { const f = $("ed-file").files[0]; $("ed-file").value = ""; if (f) edOpen(f); };
edUpdateUi();
