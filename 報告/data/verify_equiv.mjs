// ============================================================
//  verify_equiv.mjs — 合成後網表的等效性驗證
//
//  對每個設計產生 N 組隨機向量，分別用
//    (a) 展平後的 NAND/DFF 網表（參考）
//    (b) LUT4 網表
//    (c) ASIC 標準元件網表
//  求值並逐一比對所有輸出位元；DFF 的輸出視為外部給定的狀態
//  （即驗證「次態函數／組合邏輯」等效）。
//
//  用法（在 hack-computer 目錄下）：
//    node ../報告/data/verify_equiv.mjs ALU CPU Inc16 And
//    N=20000 node ../報告/data/verify_equiv.mjs CPU      # 指定向量數
// ============================================================
import { loadLibrary, mergeLibs, elab } from '../../hack-computer/lib/hdl/elab.js';
import { MicroSyn } from '../../hack-computer/lib/fpga/synthesis.js';
import { AsicSyn, evalCells } from '../../hack-computer/lib/asic/synth.js';

const dirs = (process.env.DIRS ||
  '../nand2tetris/projects/1;../nand2tetris/projects/2;../nand2tetris/projects/3;../nand2tetris/projects/5'
).split(';').filter(Boolean);

let lib = {};
for (const d of dirs) lib = mergeLibs(lib, loadLibrary(d));

// 固定種子 → 結果可重現
let seed = 20261029;
const rand = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x80000000;

/** 展平 NAND/DFF 網表求值（DFF 輸出由 q 提供） */
function evalFlat(flat, vec, q) {
  const val = new Map([['0', 0], ['1', 1]]);
  flat.primaryInputs.forEach((n, i) => val.set(n, vec[i]));
  const alias = new Map((flat.aliasList || []).map(([src, dst]) => [dst, src]));
  const root = (n) => { let c = n; while (alias.has(c)) c = alias.get(c); return c; };
  for (const g of flat.gates) if (g.type === 'DFF') val.set(root(g.out), q.get(g.out) ?? 0);
  const pending = flat.gates.filter((g) => g.type === 'NAND');
  let guard = pending.length * 8;
  while (pending.length && guard-- > 0) {
    const g = pending.shift();
    const a = val.get(root(g.in[0]));
    const b = val.get(root(g.in[1]));
    if (a === undefined || b === undefined) { pending.push(g); continue; }
    val.set(root(g.out), a && b ? 0 : 1);
  }
  if (pending.length) throw new Error('展平網表求值失敗');
  return val;
}

/** LUT4 網表求值 */
function evalLut(netlist, vec, q) {
  const val = new Map([['0', 0], ['1', 1]]);
  netlist.inputs.forEach((n, i) => val.set(n, vec[i]));
  for (const [k, v] of q) val.set(k, v);
  const pending = [...netlist.luts];
  let guard = pending.length * 4;
  while (pending.length && guard-- > 0) {
    const l = pending.shift();
    if (l.inputs.some((i) => val.get(i) === undefined)) { pending.push(l); continue; }
    let idx = 0;
    for (let i = 0; i < l.inputs.length; i++) idx |= val.get(l.inputs[i]) << i;
    val.set(l.out, (l.init >> idx) & 1);
  }
  if (pending.length) throw new Error('LUT 網表求值失敗');
  return val;
}

/** ASIC 標準元件網表求值（DFF 由 q 提供，不參與求值） */
function evalAsic(netlist, vec, q) {
  const env = new Map([['0', 0], ['1', 1]]);
  netlist.inputs.forEach((n, i) => env.set(n, vec[i]));
  for (const [k, v] of q) env.set(k, v);
  return evalCells(netlist.cells.filter((c) => c.type !== 'DFF'), env);
}

const N = Number(process.env.N || 20000);
const report = {};

for (const top of process.argv.slice(2)) {
  const e = elab(lib, top);
  const syn = new MicroSyn();
  const flat = syn.flattenChip(e, e.chips[e.names[top]]);
  const opt = syn.optimizeGates(flat);
  const lutNet = syn.synthesize(e, top);
  const asicNet = new AsicSyn().map(opt, top);
  const qNets = lutNet.dffs.map((d) => d.out);

  let badLut = 0, badAsic = 0, firstBad = null;
  for (let t = 0; t < N; t++) {
    const vec = flat.primaryInputs.map(() => (rand() < 0.5 ? 0 : 1));
    const q = new Map(qNets.map((n) => [n, rand() < 0.5 ? 0 : 1]));
    const ref = evalFlat(flat, vec, q);
    const a = evalLut(lutNet, vec, q);
    const b = evalAsic(asicNet, vec, q);
    let bad = false;
    for (const n of lutNet.outputs) {
      if (n === '0' || n === '1') continue;
      const r = ref.get(n);
      if (a.get(n) !== r) { badLut++; bad = true; }
      if (b.get(n) !== r) { badAsic++; bad = true; }
    }
    if (bad && firstBad === null) firstBad = t;
  }

  report[top] = {
    vectors: N,
    dffs: qNets.length,
    outputs: lutNet.outputs.length,
    lutMismatch: badLut,
    asicMismatch: badAsic,
    firstBadVector: firstBad,
  };
}

console.log(JSON.stringify(report, null, 2));
