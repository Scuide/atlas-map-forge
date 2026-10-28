// Edit list (editor.js): rows, on/off, delete and their undo/redo, with a stubbed DOM.
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
const els = {};
const lis = [];
const ul = { textContent: "", appendChild(li) { lis.push(li); } };
const ctx = { S: { edits: [], redo: [], map: null, symmetry: true }, console };
ctx.$ = (id) => (id === "edit-list" ? ul : fake());
ctx.document = { querySelectorAll: () => [], createElement: () => { const li = { append(...c) { this.kids = c; }, classList: { toggle() {} }, className: "" }; return li; }, addEventListener() {}, getElementById: () => fake() };
Object.assign(ctx, { window: fake(), cv: fake(), ctx: fake(), draw() {}, api: async () => ({}), toast() {}, toScreen: (x, z) => [x, z],
  renderReport() {}, renderFacts() {}, loadRoute() {}, setTimeout: () => 0, clearTimeout() {}, addEventListener() {}, localStorage: {} });
vm.createContext(ctx);
const src = fs.readFileSync(path.join(__dirname, "..", "atlasforge", "app", "web", "editor.js"), "utf8");
try { vm.runInContext(src + "\n;this.ED = ED; this.edGroups = edGroups; this.edListOp = edListOp; this.edUndo = edUndo; this.edRedo = edRedo; this.edDescribe = edDescribe;", ctx); }
catch (e) { console.error(e); process.exit(1); }
const S = ctx.S;
S.edits = [
  { op: "add_mex", at: [100, 100], metal: 2 },
  { op: "brush", tool: "raise", at: [10, 10], radius: 50, stroke: 1 },
  { op: "brush", tool: "raise", at: [20, 10], radius: 50, stroke: 1 },
  { op: "del_geo", at: [5, 5] },
];
assert.strictEqual(ctx.edGroups().length, 3, "a stroke is one row");
assert.strictEqual(ctx.edDescribe(S.edits[0]), "Add metal spot (100, 100)");
// switch the stroke off: both dabs, then undo / redo
const g = ctx.edGroups()[1];
ctx.edListOp(() => { for (const x of g.edits) x.enabled = false; });
assert.ok(S.edits[1].enabled === false && S.edits[2].enabled === false);
ctx.edUndo();
assert.ok(S.edits[1].enabled !== false && S.edits[2].enabled !== false, "undo switches it on again");
ctx.edRedo();
assert.ok(S.edits[1].enabled === false, "redo switches it off");
// delete the stroke, undo brings it back in place
const g2 = ctx.edGroups()[1];   // undo/redo replace the edit objects: ask again
ctx.edListOp(() => { S.edits = S.edits.filter((x) => !g2.edits.includes(x)); });
assert.strictEqual(S.edits.length, 2);
ctx.edUndo();
assert.strictEqual(S.edits.length, 4);
assert.strictEqual(S.edits[3].op, "del_geo");
ctx.edRedo();
assert.strictEqual(S.edits.length, 2);
console.log("ok");
