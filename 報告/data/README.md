# 數據與腳本說明

本目錄是報告 `IC_EDA_實驗報告.md` 的量測數據與可重現腳本。

## 檔案

| 檔案 | 內容 |
|---|---|
| `metrics_my_designs.json` | 我的 ALU／CPU／Inc16／And：展平閘數、最佳化閘數、LUT4、DFF、佈局格、線長、關鍵路徑、Fmax、ASIC 元件數／面積／列數／線長 |
| `metrics_builtin_corpus.json` | 同上，但對象是 nand2tetris 官方語料（對照組） |
| `equivalence_my_designs.json` | 等效性驗證：4 個設計 × 20,000 組隨機向量，LUT／ASIC 網表與展平 NAND 網表的錯誤數（皆為 0） |
| `report_flow.mjs` | 跑 ①～⑦ 合成／佈局／繞線／STA，輸出 JSON |
| `verify_equiv.mjs` | 跑等效性驗證，輸出 JSON |

## 環境

- Node.js ≥ 20（本次 v24.14.0）
- 需要 `hack-computer` 這個 repo（純 JS，不需編譯）：

```bash
cd <本課程資料夾>
git clone --depth 1 https://github.com/ccc-js/hack-computer.git
```

目錄結構需為：

```
計算機結構/
├─ hack-computer/          ← git clone 下來的工具
├─ nand2tetris/projects/   ← 我的 HDL（1、2、5）
└─ 報告/data/              ← 本目錄的腳本（import 路徑 ../../hack-computer）
```

## 重跑

```bash
cd hack-computer

# 1) 合成／佈局／繞線／STA（FPGA 退火重複 5 次取中位數）
node ../報告/data/report_flow.mjs ALU CPU Inc16 And

# 2) 等效性驗證（預設 20000 組隨機向量）
node ../報告/data/verify_equiv.mjs ALU CPU Inc16 And

# 3) 想換 HDL 目錄（分號分隔）或向量數
DIRS="../nand2tetris/projects/1;../nand2tetris/projects/2;../nand2tetris/projects/3;../nand2tetris/projects/5" \
  node ../報告/data/report_flow.mjs CPU
N=50000 node ../報告/data/verify_equiv.mjs CPU
```

## 注意

- 佈局使用**模擬退火**，含隨機性：線長每次約差 ±1%，但關鍵路徑（由 LUT 級數主導）幾乎不變。
- 本工具的延遲／面積是**教學用簡化模型**（LUT 1.2 ns、INV 1 µm²…），數值只能做相對比較，不可當成真實晶片規格。
- 含內建記憶體（`Screen`、`RAM16K`）的設計（如 Pong）不支援合成，這是工具限制。
