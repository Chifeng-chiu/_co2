# Project 04 — Hack 組合語言入門（Mult / Fill）

> Nand2Tetris Project 04：第一次不用 HDL、用 Hack 組合語言寫程式。
> 覺得難很正常——這章是從「硬體思維」切換到「程式思維」的第一關。

## 資料夾結構

```text
04/
├── README.md          # 本檔案
├── fill/
│   ├── Fill.asm           # 本人實作：鍵盤監聽 + 全螢幕填色
│   ├── Fill.hack          # 組譯後的機器碼
│   ├── Fill.tst           # 互動式測試（手動按鍵盤看螢幕）
│   ├── FillAutomatic.tst  # 自動化測試（模擬 KBD=0/1/0）
│   ├── FillAutomatic.cmp  # 自動化測試期望值
│   └── FillAutomatic.out  # 本機執行結果
└── mult/
    ├── Mult.asm  # 本人實作：R2 = R0 * R1（連加法）
    ├── Mult.tst  # 官方測試腳本（6 組測資）
    ├── Mult.cmp  # 期望值
    └── Mult.out  # 本機執行結果
```

## 背景知識（為什麼難？）

Hack 組言只有 2 種指令、3 個暫存器概念，新手會卡在 3 件事：

1. **沒有 `if / for`，只有 `A/M/D + JMP`**：全部流程控制都要自己用 Label + `D;JGT/JEQ/JMP` 兜出來。
2. **D 暫存器一次只能記一件事**：想做 `pointer[i] = color` 要拆成好幾步，還要靠 `A=M` 間接定址。
3. **記憶體映射要背**：`SCREEN = RAM[16384]` 起、共 8192 個 word 到 `RAM[24575]`，`KBD = RAM[24576]`。Fill 整題就是在操作這兩個位址。

## 1. Mult.asm — 乘法（連加法）

題目：`R2 = R0 * R1`，其中 `R0, R1, R2` 就是 `RAM[0], RAM[1], RAM[2]`。

想法很直白：把 `R0` 連加 `R1` 次。

```text
R2 = 0
i = R1
LOOP:
  if i == 0 goto END
  R2 = R2 + R0
  i = i - 1
  goto LOOP
END:
  goto END   // 無窮停住
```

對應實作（節錄）：

```asm
@2
M=0      // R2 = 0，先歸零（測資會故意把 R2 設成 -1 來檢查這行）

@1
D=M
@i
M=D      // i = R1，用 i 當倒數計數器，避免動到 R1

(LOOP)
@i
D=M
@END
D;JEQ    // i==0 就結束，順便處理 R1=0 的情況

@0
D=M
@2
M=M+D    // R2 += R0

@i
M=M-1    // i--

@LOOP
0;JMP
(END)
@END
0;JMP
```

通過 `Mult.tst` 的 6 組測資：`(0,0)`、`(1,0)`、`(0,2)`、`3*1`、`2*4`、`6*7=42`。

## 2. Fill.asm — 鍵盤控制螢幕填色

題目：無窮迴圈監聽鍵盤，有按鍵就把全螢幕塗黑，沒按就塗白。

- 黑 = `-1` = 二進位 `1111111111111111`（16 個 pixel 全黑）
- 白 = `0` = `0000000000000000`
- 螢幕共 8192 個 word（`256 x 512 / 16`），要全部掃過一遍才算畫完一幀

程式分兩層迴圈：

```text
LOOP (外層：監聽鍵盤):
  if KBD > 0 goto BLACK else goto WHITE
  WHITE: COLOR = 0,  goto FILL_START
  BLACK: COLOR = -1

FILL_START (準備畫畫):
  COLOR 存好
  pointer = SCREEN (16384)
  count = 8192

DRAW_LOOP (內層：填滿螢幕):
  if count == 0 goto LOOP   // 畫完，回去繼續監聽
  *pointer = COLOR
  pointer++
  count--
  goto DRAW_LOOP
```

關鍵技巧：

- 用 `COLOR` 變數先記住這次要畫黑還是白，內層迴圈就不用再讀鍵盤。
- 用 `pointer + count` 雙變數掃螢幕，這是組語版的 `for (i=0; i<8192; i++)`。
- 畫完一幀一定要跳回 `LOOP` 重讀 `KBD`，否則按鍵放開了畫面不會變回白色。

## 怎麼測試

用 Nand2Tetris 的 `CPUEmulator` 開啟 `.tst` 檔：

| 程式 | 測試檔 | 說明 |
|------|--------|------|
| Mult | `mult/Mult.tst` | 自動跑 6 組乘法，比對 `Mult.cmp` |
| Fill | `fill/Fill.tst` | 互動式：選 No Animation → 用鍵盤按著看螢幕變黑/白 |
| Fill | `fill/FillAutomatic.tst` | 自動化：依序設 `KBD=0/1/0` 各跑 100 萬個 tick，比對螢幕抽樣值 |

本 repo 的 `*.out` 皆為本機測試通過後的輸出。

## 心得一句話

Project 04 難的不是演算法（乘法和填色都很簡單），而是**只能用最陽春的指令把高階想法翻譯成跳來跳去的 Label**。寫完這兩題，後面寫 VM 和 Hack 高階語言時就會很有感。
