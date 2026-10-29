// ============================================================
//  report_flow.mjs — 跑完整 EDA 流程並輸出量化結果（JSON）
//
//  流程：① 展平(RTL→NAND/DFF) ② 技術無關最佳化 ③ LUT4 techmap
//        ④ 模擬退火佈局 ⑤ 迷宮繞線 ⑥ STA    ＋ ASIC 標準元件支線
//
//  用法（在 hack-computer 目錄下）：
//    node ../報告/data/report_flow.mjs ALU CPU Inc16 And
//    # 若要指定 HDL 目錄（以分號分隔）：
//    DIRS="../nand2tetris/projects/1;../nand2tetris/projects/2;../nand2tetris/projects/3;../nand2tetris/projects/5" \
//      node ../報告/data/report_flow.mjs ALU CPU
//
//  預設目錄＝我的 nand2tetris 作業（專案 1/2/3/5）
//  退火有隨機性，FPGA 部分重複 5 次並取中位數。
// ============================================================
import { loadLibrary, mergeLibs, elab } from '../../hack-computer/lib/hdl/elab.js';
import { MicroSyn } from '../../hack-computer/lib/fpga/synthesis.js';
import { MicroPnR } from '../../hack-computer/lib/fpga/pnr.js';
import { AsicSyn } from '../../hack-computer/lib/asic/synth.js';
import { AsicPnR } from '../../hack-computer/lib/asic/pnr.js';

const dirs = (process.env.DIRS ||
  '../nand2tetris/projects/1;../nand2tetris/projects/2;../nand2tetris/projects/3;../nand2tetris/projects/5'
).split(';').filter(Boolean);

let lib = {};
for (const d of dirs) lib = mergeLibs(lib, loadLibrary(d));

const tops = process.argv.slice(2);
const RUNS = 5;
const out = {};

for (const top of tops) {
  const e = elab(lib, top);
  const syn = new MicroSyn();

  // ① 展平 → 位元級 NAND/DFF 網表 ；② 技術無關最佳化
  const flat = syn.flattenChip(e, e.chips[e.names[top]]);
  const opt = syn.optimizeGates(flat);
  const rawGates = flat.gates.filter((g) => g.type === 'NAND').length;
  const optGates = opt.gates.filter((g) => g.type === 'NAND').length;

  // ③ LUT4 技術映射
  const lutNet = syn.synthesize(e, top);
  const lutCount = lutNet.luts.length;
  const dffCount = lutNet.dffs.length;

  // ④⑤⑥ 佈局 / 繞線 / STA（退火有隨機性 → 跑 5 次）
  const fpgaRuns = [];
  for (let i = 0; i < RUNS; i++) {
    const r = new MicroPnR().run(lutNet);
    fpgaRuns.push({ grid: `${r.grid.width}x${r.grid.height}`, wire: r.stats.totalWireLength, critNs: Number(r.stats.criticalPathNs), fmax: Number(r.stats.fmaxMHz) });
  }

  // ASIC 支線：標準元件映射 + row-based 佈局 + STA
  const asicNet = new AsicSyn().map(opt, top);
  const asic = new AsicPnR().run(asicNet);

  const median = (a) => a.slice().sort((x, y) => x - y)[Math.floor(a.length / 2)];

  out[top] = {
    inputs: lutNet.inputs.length,
    outputs: lutNet.outputs.length,
    rawNand: rawGates,
    optNand: optGates,
    lut4: lutCount,
    dff: dffCount,
    fpga: {
      grid: fpgaRuns[0].grid,
      wireRuns: fpgaRuns.map((r) => r.wire),
      wireMedian: median(fpgaRuns.map((r) => r.wire)),
      critMedian: median(fpgaRuns.map((r) => r.critNs)),
      fmaxMedian: median(fpgaRuns.map((r) => r.fmax)),
    },
    asic: {
      cellCount: asicNet.stats.cellCount,
      types: asicNet.stats.cellTypeCounts,
      areaUm2: asicNet.stats.areaUm2,
      rows: asic.stats.rowCount,
      wireUm: asic.stats.totalWireUm,
      critNs: Number(Number(asic.timing.criticalPathNs).toFixed(2)),
      fmax: Number(Number(asic.timing.fmaxMHz).toFixed(1)),
    },
  };
}

console.log(JSON.stringify(out, null, 2));
