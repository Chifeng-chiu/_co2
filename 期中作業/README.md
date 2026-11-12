# 期中作業

> 課程：計算機結構（115 學年上學期）
> 內容：期中考範圍的作業整理（Nand2Tetris Project 00 ~ 05 硬體部分）

## 說明

這個資料夾用來集中放期中作業的檔案，方便繳交與日後回顧。
期中範圍涵蓋 Nand2Tetris 前半段的硬體專案：

每週檢驗表格

| 第幾週 | 習題內容 | 有上課且準時繳交 | 補交 | 附上請假證明 | 作業連結 |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 3 | 第 1, 2 章 | 是 | | | [01](https://github.com/Chifeng-chiu/_co2/tree/main/01), [02](https://github.com/Chifeng-chiu/_co2/tree/main/02) |
| 4 | 第 3 章除 PC | 是 |  | [連結]() | [03](https://github.com/Chifeng-chiu/_co2/tree/main/03) |
| 5 | 第 4 章 | 是 | | | [04](https://github.com/Chifeng-chiu/_co2/tree/main/04) |
| 6 | HackCPU 電路圖 | 是 | | | [作業(圖片)](https://github.com/Chifeng-chiu/_co2/tree/main/%E4%BD%9C%E6%A5%AD(%E5%9C%96%E7%89%87)) |
| 7 | 第 5 章 | 是 | | | [05](https://github.com/Chifeng-chiu/_co2/tree/main/05) |
| 8 | EDA 軟體報告 | 是 | | | [報告](https://github.com/Chifeng-chiu/_co2/tree/main/%E5%A0%B1%E5%91%8A) |

---

## 作業說明

以下依上表的每週進度，逐一說明各次作業的範圍、要交的檔案與通過標準。
每題的 `.tst` 是測試腳本、`.cmp` 是期望值，模擬結果與 `.cmp` 一致才算完成；`.out` 是本機實際執行後留下的輸出。

### 作業 1（第 3 週）：第 1、2 章 — Boolean Logic 與 Boolean Arithmetic

> 繳交資料夾：[`01/`](https://github.com/Chifeng-chiu/_co2/tree/main/01)、[`02/`](https://github.com/Chifeng-chiu/_co2/tree/main/02)

**規則**：只能用原生 `Nand` 閘，以及前面已經完成並通過測試的晶片來組合，不可直接呼叫內建的 `And`、`Or`、`Mux` 等實作。

#### 第 1 章：組合邏輯閘（15 個 `.hdl`）

| 檔案 | 介面 | 功能 |
|------|------|------|
| `Not.hdl` | `in` → `out` | 反相 |
| `And.hdl` | `a, b` → `out` | 且 |
| `Or.hdl` | `a, b` → `out` | 或 |
| `Xor.hdl` | `a, b` → `out` | 互斥或（兩輸入相異為 1） |
| `Mux.hdl` | `a, b, sel` → `out` | 二選一：`sel=0` 選 `a`，`sel=1` 選 `b` |
| `DMux.hdl` | `in, sel` → `a, b` | 一分為二，未選到的輸出為 0 |
| `Not16.hdl` | `in[16]` → `out[16]` | 16 位元逐位反相 |
| `And16.hdl` | `a[16], b[16]` → `out[16]` | 16 位元逐位 AND |
| `Or16.hdl` | `a[16], b[16]` → `out[16]` | 16 位元逐位 OR |
| `Mux16.hdl` | `a[16], b[16], sel` → `out[16]` | 以 `sel` 選擇整條 16 位元匯流排 |
| `Or8Way.hdl` | `in[8]` → `out` | 8 條輸入只要有一條為 1 就輸出 1 |
| `Mux4Way16.hdl` | `a~d[16], sel[2]` → `out[16]` | 4 選 1（`sel` = 00 / 01 / 10 / 11） |
| `Mux8Way16.hdl` | `a~h[16], sel[3]` → `out[16]` | 8 選 1（`sel` = 000 ~ 111） |
| `DMux4Way.hdl` | `in, sel[2]` → `a, b, c, d` | 1 對 4 分配 |
| `DMux8Way.hdl` | `in, sel[3]` → `a~h` | 1 對 8 分配 |

#### 第 2 章：算術電路（5 個 `.hdl`）

| 檔案 | 介面 | 功能 |
|------|------|------|
| `HalfAdder.hdl` | `a, b` → `sum, carry` | 半加器：`sum = a XOR b`、`carry = a AND b` |
| `FullAdder.hdl` | `a, b, c` → `sum, carry` | 全加器：三個位元相加並產生進位 |
| `Add16.hdl` | `a[16], b[16]` → `out[16]` | 16 位元加法器（FullAdder 串接，最高位進位忽略） |
| `Inc16.hdl` | `in[16]` → `out[16]` | 加一：`out = in + 1`（溢位忽略） |
| `ALU.hdl` | `x[16], y[16]` + 6 控制位 → `out[16], zr, ng` | 算術邏輯單元，可執行 18 種運算 |

**ALU 控制位與狀態輸出**

| 訊號 | 作用 |
|------|------|
| `zx` / `nx` | 將 `x` 歸零 / 取補數 |
| `zy` / `ny` | 將 `y` 歸零 / 取補數 |
| `f` | 1 時算 `x + y`，0 時算 `x & y` |
| `no` | 將輸出取補數 |
| `zr` | 輸出為 0 時為 1（Zero flag） |
| `ng` | 輸出為負時為 1（Negative flag，即 `out[15]`） |

**通過標準**

- `01/` 各題 `.out` 與 `.cmp` 完全相符（HardwareSimulator 顯示 Comparison ended successfully）。
- `02/ALU.tst` 需涵蓋課本的 18 組控制位（0、1、-1、x、y、!x、!y、-x、-y、x+1、y+1、x-1、y-1、x+y、x-y、y-x、x&y、x|y）全數正確。

---

### 作業 2（第 4 週）：第 3 章（不含 PC）— Sequential Logic

> 繳交資料夾：[`03/`](https://github.com/Chifeng-chiu/_co2/tree/main/03)（`a/` 基本元件、`b/` 大型 RAM），共 7 個 `.hdl`

| 檔案 | 介面 | 功能 |
|------|------|------|
| `Bit.hdl` | `in, load` → `out` | 1 位元記憶體：`load=1` 時於下個時脈寫入 `in`，否則保持原值 |
| `Register.hdl` | `in[16], load` → `out[16]` | 16 位元暫存器（16 個 Bit） |
| `RAM8.hdl` | `in[16], load, address[3]` → `out[16]` | 8 個暫存器，以 3 條位址線選取 |
| `RAM64.hdl` | `in[16], load, address[6]` → `out[16]` | 64 個暫存器（高位 3 bits 選 RAM8、低位 3 bits 選暫存器） |
| `RAM512.hdl` | `in[16], load, address[9]` → `out[16]` | 512 個暫存器（8 組 RAM64） |
| `RAM4K.hdl` | `in[16], load, address[12]` → `out[16]` | 4096 個暫存器（8 組 RAM512） |
| `RAM16K.hdl` | `in[16], load, address[14]` → `out[16]` | 16384 個暫存器（4 組 RAM4K） |

**重點**

- 循序電路的輸出取決於「目前狀態」，測試檔會用 `tick` / `tock` 推進時脈，寫入後再讀回驗證。
- 大型 RAM 都是由小的 RAM 遞迴組成，位址線要正確切分（高位選模組、低位選模組內的暫存器）。
- `PC.hdl` 本次不列入作業範圍（`03/a/PC.hdl` 為自行練習的延伸實作）。

**通過標準**：各題 `.out` 與 `.cmp` 相符，且每個位址寫入後都能正確讀回。

---

### 作業 3（第 5 週）：第 4 章 — Machine Language

> 繳交資料夾：[`04/`](https://github.com/Chifeng-chiu/_co2/tree/main/04)，共 2 個 `.asm`（另附組譯後的 `.hack`）

| 檔案 | 題目 | 說明 |
|------|------|------|
| `mult/Mult.asm` | 乘法 | 計算 `R2 = R0 × R1`；`R0`、`R1` 為非負整數，`R2` 可能被預設為 -1，所以要先歸零 |
| `fill/Fill.asm` | 螢幕填色 | 無窮迴圈監聽鍵盤：`KBD > 0`（有按鍵）時把整個螢幕塗黑 `-1`，否則塗白 `0` |

**記憶體映射（Fill 會用到）**

| 位址 | 用途 |
|------|------|
| `RAM[0]` ~ `RAM[15]` | `R0` ~ `R15` 虛擬暫存器 |
| `RAM[16384]` ~ `RAM[24575]` | 螢幕（8192 個 16-bit word） |
| `RAM[24576]` | 鍵盤（`KBD`） |

**通過標準**

- `Mult.tst`：6 組測資（含 `0×0`、`0×2`、`6×7=42`）與 `Mult.cmp` 相符。
- `Fill.tst`：手動按鍵觀察畫面變化；`FillAutomatic.tst` 以 `KBD = 0 / 1 / 0` 自動驗證，與 `FillAutomatic.cmp` 相符。

---

### 作業 4（第 6 週）：Hack CPU 電路圖

> 繳交資料夾：[`作業(圖片)/`](https://github.com/Chifeng-chiu/_co2/tree/main/%E4%BD%9C%E6%A5%AD(%E5%9C%96%E7%89%87))

課堂作業：手繪 Hack CPU 的電路圖，並推導 ALU 的控制邏輯。重點是把第 1、2 章做過的閘，一路往上兜成整顆 CPU 的資料流。

**圖檔內容**

| 檔案 | 內容 |
|------|------|
| `ALU電路圖.jpg` | ALU 內部電路：`x`、`y` 先經過 `zx` / `nx`（`zy` / `ny`）的 MUX 與反相器，再進 `Add16` 與 `And16`，由 `f` 選擇後經 `no` 反相輸出；`zr` 用 `Or8Way` 判斷是否全為 0，`ng` 直接取 `out[15]` |
| `ALU習題.jpg` | 以 `zx=0, nx=1, zy=0, ny=0, f=1, no=1` 推導 `out = x - y`：先取 `x` 的補數（`-x-1`）再加 `y`，最後 `no` 反相得到 `x - y` |
| `迪摩根定律.jpg` | 迪摩根定律真值表驗證：`NOT(A+B) = A'·B'`、`NOT(A·B) = A' + B'`，用來把 AND / OR 化簡成只用 NAND 實作 |

**通過標準**

- 電路圖要能對應 `05/CPU.hdl` 的行為：A / B 暫存器、ALU、PC、資料記憶體（`addressM` / `writeM` / `outM`）與指令解碼之間接線正確。
- 能用畫出的電路解釋 A-instruction 與 C-instruction 的差異，以及 `reset` 時 PC 歸零的原因。

---

### 作業 5（第 7 週）：第 5 章 — Computer Architecture

> 繳交資料夾：[`05/`](https://github.com/Chifeng-chiu/_co2/tree/main/05)，共 3 個 `.hdl`

| 檔案 | 介面 | 功能 |
|------|------|------|
| `Memory.hdl` | `in[16], load, address[15]` → `out[16]` | 整合 RAM16K、Screen、Keyboard 的統一記憶體 |
| `CPU.hdl` | `inM[16], instruction[16], reset` → `outM[16], writeM, addressM[15], pc[15]` | 指令解碼與執行，支援 A/C instruction，`reset=1` 時 `pc = 0` |
| `Computer.hdl` | `reset` → （無輸出） | ROM32K + CPU + Memory 組成完整的 Hack 電腦 |

**Memory 位址配置**

| 位址範圍 | 對應裝置 | 大小 |
|----------|----------|------|
| `0` ~ `16383` | RAM16K | 16K words |
| `16384` ~ `24575` | Screen | 8K words |
| `24576` | Keyboard | 1 word |

**CPU 輸出訊號**

| 訊號 | 意義 |
|------|------|
| `outM[16]` | 要寫入記憶體的值 |
| `writeM` | 1 表示本週期寫入 `RAM[addressM]` |
| `addressM[15]` | 資料記憶體位址（來自 A 暫存器） |
| `pc[15]` | 下一道指令的位址 |

**通過標準**

- `Memory.tst`、`CPU.tst`、`ComputerAdd.tst`、`ComputerMax.tst`、`ComputerRect.tst` 的 `.out` 與 `.cmp` 相符。
- `Computer*.tst` 需搭配預載 ROM（`Add.hack`、`Max.hack`、`Rect.hack`）執行，能算出正確結果或畫出矩形。

---

### 作業 6（第 8 週）：EDA 軟體報告

> 繳交資料夾：[`報告/`](https://github.com/Chifeng-chiu/_co2/tree/main/%E5%A0%B1%E5%91%8A)

用開源 EDA 工具把自製的 HDL 推進真實的合成與實體設計流程，並寫成報告。

| 項目 | 內容 |
|------|------|
| 使用工具 | `hack-computer`（HDL 模擬器＋迷你 EDA）、`veryl2chip IDE`（Veryl → FPGA / ASIC） |
| 受測設計 | 自製 `And.hdl`、`Inc16.hdl`、`ALU.hdl`、`CPU.hdl`（另有官方標準解答作為對照組） |
| 流程 | RTL 展開 → 網表 → 最佳化 → 技術映射 → 佈局 → 繞線 → 靜態時序分析（STA） |
| 量化比較 | FPGA（LUT4 數量、Fmax）、ASIC（標準元件數、面積、Fmax）之 PPA 數據 |
| 等效性驗證 | 每組設計灌入 20,000 組隨機測試向量，比對 NAND / LUT4 / ASIC 三種網表輸出，須 0 錯誤 |

**繳交檔案**

- `報告/IC_EDA_實驗報告.html`、`報告/IC_EDA_實驗報告.pdf`：完整報告（數據表、公式、截圖）。
- `報告/README.md`：實驗方法、實作脈絡與心得。
- `報告/figures/`：RTL 模擬、階層電路圖、FPGA/ASIC 佈局繞線、STA 等截圖（`fig1` ~ `fig9`）。
- `報告/data/`：自動化腳本 `report_flow.mjs`、`verify_equiv.mjs` 與原始 JSON 量測數據。

**通過標準**

- 完整走完 ①～⑦ 流程，並產出可重現的數據。
- 等效性驗證 0 錯誤（功能與原始設計完全等價）。
- 報告需說明 FPGA 與 ASIC 的取捨，以及「面積小 ≠ 速度快」等觀察。

---

### 期中驗收清單

| 週次 | 作業 | 必交檔案 | 通過標準 |
|------|------|----------|----------|
| 3 | 第 1、2 章 | `01/` 15 個 `.hdl`、`02/` 5 個 `.hdl` | 各題 `.out` 與 `.cmp` 相符；ALU 18 組運算全對 |
| 4 | 第 3 章（不含 PC） | `03/` 7 個 `.hdl` | 時脈推進後每個位址的寫入 / 讀回正確 |
| 5 | 第 4 章 | `04/mult/Mult.asm`、`04/fill/Fill.asm`（+ `.hack`） | `Mult.tst`、`FillAutomatic.tst` 全數通過 |
| 6 | Hack CPU 電路圖 | `作業(圖片)/` 手繪圖 | 電路與 `CPU.hdl` 行為一致、控制邏輯推導正確 |
| 7 | 第 5 章 | `05/Memory.hdl`、`CPU.hdl`、`Computer.hdl` | 可執行 `Add` / `Max` / `Rect` 測試程式 |
| 8 | EDA 軟體報告 | `報告/`（報告 + 圖 + 數據） | 流程完整、數據可重現、等效性驗證 0 錯誤 |





