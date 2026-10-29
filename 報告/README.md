從零打造處理器到實體佈局：開源 IC EDA 實作紀錄與學習反思
> **專案導覽**：本目錄收錄「計算機結構」課程之 IC EDA 邏輯合成與實體設計實驗成果。
> - 📄 **完整量化數據與圖表報告**：請參閱同目錄下之 [`IC_EDA_實驗報告.md`](./IC_EDA_實驗報告.md)（或 [`IC_EDA_實驗報告.html`](./IC_EDA_實驗報告.html)）
> - 📊 **原始實驗數據與自動化腳本**：存放於 [`data/`](./data/) 目錄
> - 🖼️ **各階段佈局與繞線視覺化截圖**：存放於 [`figures/`](./figures/) 目錄
項目	內容
課程	計算機結構
姓名／學號	郭鎮瑋／111410543
實驗日期	2026 年 10 月 29 日
核心工具	`hack-computer`（HDL 模擬＋微型 EDA）、`veryl2chip IDE`（WebAssembly RTL-to-Chip）
理論對標	Cornell ECE 5745: Complex Digital ASIC Design
---
一、 我是怎麼做這個實驗的？（實作脈絡與方法）
以前在寫 nand2tetris 的 `ALU.hdl` 和 `CPU.hdl` 時，我的目標很單純：只要在硬體模擬器上跑過 `.tst` 測試腳本、拿到「Comparison ended successfully」就算大功告成。但這次實驗我給自己設定了一個更貼近真實晶片設計的挑戰：「如果把我大一親手寫的 CPU 送進 EDA 合成器，它長什麼樣子？能跑多快？會不會在轉換過程中出錯？」
為了回答這些問題，我沒有只停留在網頁上點幾下按鈕看圖，而是分成四個層次推進：
1. 從「看圖」走向「自動化數據採集」
一開始我先在瀏覽器操作 `hack-computer` 與 `veryl2chip IDE`，透過視覺化介面觀察 ① RTL 展開 → ② 邏輯網表 → ③ 邏輯最佳化 → ④ 技術映射（LUT4 / 標準元件） → ⑤ 模擬退火佈局 → ⑥ 迷宮繞線 → ⑦ 靜態時序分析 (STA) 的每一步變化。
但我很快發現：模擬退火（Simulated Annealing）具有隨機性，單看一次 GUI 畫面不夠客觀。於是我把底層的 `lib/fpga` 與 `lib/asic` 函式庫拉出來，自己用 Node.js 寫了批次腳本（`data/report_flow.mjs`），針對我寫的 `ALU`、`CPU`、`Inc16`、`And` 自動連跑 5 次退火取中位數，把面積、線長、關鍵路徑（Critical Path）全部導出成 JSON 進行量化比較。
2. 設計「自己寫的 HDL」vs「官方標準解答」的對照實驗
為了知道「程式寫法」對 EDA 合成器的影響，我把工具內建的 nand2tetris 官方標準解答抓出來當作對照組，用完全相同的 EDA 管線跑過一遍。這個對照讓我抓到了本次實驗最有趣的發現（詳見下方心得）。
3. 寫腳本做 20,000 組隨機向量「等效性驗證 (Equivalence Check)」
EDA 工具把幾千個 NAND 閘化簡、又拆裝成 LUT4 或 `INV / NAND2 / AOI21 / MUX2` 標準元件後，我怎麼確定它沒有「改壞」我的電路？
參考了業界 Formal Verification 的概念與 `veryl2chip` 的四層同構測試精神，我撰寫了 `data/verify_equiv.mjs`：把 CPU 裡的 48 顆 DFF 切開當作虛擬輸入端，對每個電路灌入 20,000 組隨機測試向量，同步比對「原始展平 NAND 網表」、「FPGA LUT4 網表」與「ASIC 標準元件網表」的每一個輸出位元，最終確認 錯誤數皆為 0。
---
二、 做完這次實驗，我對 IC EDA 的全新理解與看法
這次實作徹底打破了我過去把「寫硬體（HDL）」當成「寫軟體程式」的習慣思維，以下是我最大的五個體悟：
1. 「合成（Synthesis）」不再是黑盒子，而是一連串妥協與啟發式演算法
以前覺得「合成」就是按一個按鈕把程式碼變成電路。實際拆解 ①～⑦ 階段並對照 Cornell ECE 5745 講義後才明白，裡面每一步都是在解 NP-hard 的組合最佳化問題：
邏輯最佳化是在有向無環圖（DAG）上做常數傳播與雙重否定消去（例如 `Inc16` 進位鏈因為結構規律，直接被消掉 41.7% 的冗餘閘）。
技術映射（Techmap） 是用樹狀或貪婪覆蓋把邏輯塞進 LUT4 或標準元件。
佈局與繞線（P&R） 則是靠模擬退火（SA）在 123 個溫度層裡不斷交換位置來壓低半週長線長（HPWL），再用 A* 演算法在有限通道內找路。
2. 震撼發現：功能 100% 相同的 HDL，只因寫法順序不同，LUT 數量竟差了 18%！
這是我這次實驗最驚訝的數據——我的 `ALU.hdl` 跟官方解答功能完全一樣，展平後的原始 NAND 閘數也只差 1 顆（1,279 vs 1,278）。但是經過一模一樣的合成器後：
我的 ALU：映射出 209 顆 LUT4，FPGA $F_{\max} = 32.8\text{ MHz}$，但切換到 ASIC 後端面積只有 $1,027\ \mu\text{m}^2$（$67.4\text{ MHz}$）。
官方 ALU：映射出 177 顆 LUT4，FPGA $F_{\max} = 30.0\text{ MHz}$，但 ASIC 面積卻高達 $1,175\ \mu\text{m}^2$（$47.3\text{ MHz}$）。
追查原因後發現，只是因為官方多寫了一層輸出別名（`out=o2, out=out`）以及元件宣告順序不同，改變了網表展開的拓撲順序，進而影響了貪婪（Greedy）LUT 覆蓋演算法先吃掉哪一個邏輯錐！這讓我深刻體會到：硬體描述語言的每一行結構，都在直接影響實體晶片的 PPA（Power, Performance, Area）。
3. 「面積小 ≠ 跑得快」：決定晶片時脈上限的是邏輯深度（進位鏈）
在分析靜態時序（STA）時，畫面上那條刺眼的紅線（Critical Path）給了我很強的視覺衝擊。以 `ALU` 為例，$30.45\text{ ns}$ 的延遲除以單顆 LUT 的 $1.2\text{ ns}$，代表訊號總共穿過了約 25 級 LUT——其中絕大多數都卡在 `Add16` 的 16 位元漣波進位鏈（Ripple-Carry Chain），到了 `CPU` 更因為加上了 `A 暫存器 → ALU → PC 跳躍判斷` 的控制迴路，延遲拉長到 $38.30\text{ ns}$。
而在 `Inc16` 的對照中，即便閘數被大幅化簡，只要映射出來的邏輯級數（Depth）較深，最大頻率 $F_{\max}$ 就會直接砍半（$46.0\text{ MHz}$ vs $23.0\text{ MHz}$）。這讓我真正看懂為什麼計算機結構課本一直在強調超前進位（Carry-Lookahead）與管線化（Pipelining）。
4. 親眼看見 FPGA 與 ASIC 的物理本質差異
以前背誦「FPGA 比較慢但有彈性、ASIC 比較快但開模貴」總覺得很抽象。這次把同一顆 CPU 同時切換到 FPGA 與 ASIC 後端：
FPGA（查表架構）：只用了 372 顆 LUT4，但不管裡面邏輯多簡單，過一級 LUT 就是要付 $1.2\text{ ns}$ 的過路費，$F_{\max}$ 停在 $26.1\text{ MHz}$。
ASIC（標準元件架構）：必須把真值表拆回 1,205 顆真實邏輯閘（535 顆 `INV`、273 顆 `NAND2`、191 顆 `AOI21`、158 顆 `MUX2` 與 48 顆 `DFF`），元件數量暴增，但因為單顆閘延遲極小（$0.08\sim 0.20\text{ ns}$），頻率直接躍升至 $45.1\text{ MHz}$（ALU 更翻倍到 $67.4\text{ MHz}$）。同時我也看到 48 顆 `DFF` 雖然只佔元件數的一小部分，卻吃掉了極可觀的晶片面積（每顆 $8\ \mu\text{m}^2$）。
5. 開源 Web EDA 對學習晶片設計的價值與邊界
透過 `hack-computer` 與 `veryl2chip IDE`（將 Rust 合成器編譯成 WebAssembly 在瀏覽器直接跑 SKY130 與 iCE40 流程），我們不需要安裝動輒數十 GB 的商用軟體就能透明地看見演算法內部狀態。但身為工程師，我也清楚認知到教學模型與真實 Tape-out 的差距：例如 SRAM 記憶體巨集（`RAM16K`）無法直接用邏輯閘硬兜、真實奈米製程必須考慮時鐘樹偏斜（Clock Skew）、寄生電容（RC Extraction）與形式驗證（SAT/BDD）。這份認知將成為我未來進一步接觸 OpenLANE 或商用 EDA 工具鏈最紮實的跳板。
---
三、 快速重現本專案實驗
如果你想在自己的電腦上重跑我的實驗數據與等效性驗證，只需具備 Node.js 環境並執行以下指令：
```bash
# 1. 取得 hack-computer 核心工具庫
git clone --depth 1 https://github.com/ccc-js/hack-computer.git
cd hack-computer

# 2. 執行批次合成、模擬退火佈局（5次取中位數）、繞線與 STA 分析
node ../報告/data/report_flow.mjs ALU CPU Inc16 And

# 3. 執行 20,000 組隨機向量之跨網表（NAND vs LUT4 vs ASIC）等效性驗證
node ../報告/data/verify_equiv.mjs ALU CPU Inc16 And
```
---
四、 目錄結構一覽
📄 `README.md`：本導覽文件（實驗方法脈絡與 IC EDA 核心心得）
📑 `IC_EDA_實驗報告.md` / `IC_EDA_實驗報告.html`：完整正式實驗報告（含詳細架構圖、完整數據表格与公式推導）
📁 `figures/`：實驗過程擷取之 9 張關鍵視覺化圖表（RTL 模擬、階層電路圖、FPGA 退火佈局、A* 繞線關鍵路徑、ASIC 標準列佈局、veryl2chip 畫面）
📁 `data/`：自動化測試腳本（`report_flow.mjs`, `verify_equiv.mjs`）與產出之 JSON 原始數據集
