// Selection of spots (editor.js): one entry per mirror set, group move and delete as one undo step, stubbed DOM.
const fs = require("fs"), vm = require("vm"), path = require("path"), assert = require("assert");
function fake() {
  const t = () => {};
  const el = new Proxy(t, {
    get(_, k) { if (k === Symbol.toPrimitive) return () => ""; if (k === "children" || k === "style") return fake(); if (k === "classList") return { toggle() {}, add() {}, remove() {}, contains() { return false; } };
      if (k === "value") return "raise"; if (k === "querySelectorAll") return () => []; return el; },
    set() { return true; }, apply() { return el; },
  });
  return el;
}
const ctx = { S: { edits: [], redo: [], map: null, symmetry: true }, console };
ctx.$ = () => fake();
ctx.document = { querySelectorAll: () => [], createElement: () => ({ append() {}, classList: { toggle() {} } }), addEventListener() {}, getElementById: () => fake() };
Object.assign(ctx, { window: fake(), cv: fake(), ctx: fake(), draw() {}, api: async () => ({}), toast() {}, toScreen: (x, z) => [x, z],
  renderReport() {}, renderFacts() {}, loadRoute() {}, setTimeout: () => 0, clearTimeout() {}, addEventListener() {}, localStorage: {} });
vm.createContext(ctx);
const src = fs.readFileSync(path.join(__dirname, "..", "atlasforge", "app", "web", "editor.js"), "utf8");
try {
  vm.runInContext(src + "\n;this.ED = ED; this.edGroups = edGroups; this.edUndo = edUndo; this.edRedo = edRedo;" +
    " this.edGroupMove = edGroupMove; this.edGroupDelete = edGroupDelete; this.edAddToGroup = edAddToGroup;" +
    " this.edSpots = edSpots; this.edSelected = edSelected; this.edInRect = edInRect;", ctx);
} catch (e) { console.error(e); process.exit(1); }
const S = ctx.S, ED = ctx.ED;
// 1000 x 1000 map, mirrored left/right: the mex at (200, 200) has its image at (800, 200)
S.map = { W: 1000, H: 1000, sym: { layout: "ew" }, geos: [[100, 300]], mexes: [{ x: 200, z: 200, metal: 2 }, { x: 210, z: 200, metal: 2 }],
  teams: [[[300, 500]]], boxes: [], issues: [] };
S.symmetry = true;
const spots = ctx.edSpots();
assert.strictEqual(spots.length, 4, "geovents, metal spots and start points are all selectable");

// a mirror pair is one entry: the image follows it
ED.group = [];
ctx.edAddToGroup(spots.filter((s) => s.kind === "mex" && s.x === 200));
ctx.edAddToGroup(spots.filter((s) => s.kind === "mex" && s.x === 200));
ctx.edAddToGroup([{ kind: "mex", x: 800, z: 200 }]);
assert.strictEqual(ED.group.length, 1, "the mirror image of a selected spot is not a second entry");
assert.ok(ctx.edSelected({ kind: "mex", x: 800, z: 200 }), "the image counts as selected");

// group move: two entries, one edit each, one group id; undo takes both back at once
ED.group = [];
ctx.edAddToGroup([{ kind: "mex", x: 200, z: 200 }, { kind: "mex", x: 210, z: 200 }]);
assert.strictEqual(ED.group.length, 2);
ctx.edGroupMove(10, 0);
assert.strictEqual(S.edits.length, 2, "one move edit per entry");
assert.deepEqual(S.edits.map((e) => e.op), ["move_mex", "move_mex"]);
assert.strictEqual(S.edits[0].group, S.edits[1].group, "they share a group id");
// the spot at 210 moves first, so the one from 200 does not land on an unmoved spot
assert.deepEqual(S.edits[0].from, [210, 200]);
assert.deepEqual(S.edits[1].to, [210, 200]);
assert.deepEqual(ED.group.map((s) => [s.x, s.z]), [[210, 200], [220, 200]], "the selection follows the move");
assert.strictEqual(ctx.edGroups().length, 1, "the list shows one row for the group");
ctx.edUndo();
assert.strictEqual(S.edits.length, 0, "undo takes the whole group back");
ctx.edRedo();
assert.strictEqual(S.edits.length, 2, "redo brings it back");

// moving a group off the map is clamped, a zero offset makes no edit
ED.group = [{ kind: "geo", x: 995, z: 300 }];
ctx.edGroupMove(20, 0);
assert.deepEqual(S.edits[S.edits.length - 1].to, [1000, 300]);
const n = S.edits.length;
ctx.edGroupMove(0, 0);
assert.strictEqual(S.edits.length, n, "no edit for a zero move");

// rectangle selection: spots inside the rectangle
ED.group = [];
ctx.edAddToGroup(spots.filter((s) => ctx.edInRect([150, 150], [260, 260], s)));
assert.strictEqual(ED.group.length, 2, "two metal spots inside, the start and the geovent outside");

// delete: the metal spots go (one undo step), starts stay selected
ED.group = [{ kind: "mex", x: 200, z: 200 }, { kind: "start", x: 300, z: 500 }];
const before = S.edits.length;
ctx.edGroupDelete();
assert.strictEqual(S.edits.length, before + 1);
assert.strictEqual(S.edits[before].op, "del_mex");
assert.deepEqual(ED.group, [{ kind: "start", x: 300, z: 500 }]);
ED.group = [{ kind: "start", x: 300, z: 500 }];
ctx.edGroupDelete();
assert.strictEqual(S.edits.length, before + 1, "start points cannot be deleted");
console.log("ok");
