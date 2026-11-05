# 期中作業

> 課程：計算機結構（115 學年上學期）
> 內容：期中考範圍的作業整理（Nand2Tetris Project 00 ~ 05 硬體部分）

## 說明

這個資料夾用來集中放期中作業的檔案，方便繳交與日後回顧。
期中範圍涵蓋 Nand2Tetris 前半段的硬體專案：

| 章節 | 主題 | 對應專案 |
|------|------|----------|
| 00 | 課程工具與環境 | `00/` |
| 01 | Boolean Logic（And / Or / Not / Mux / DMux …） | `01/` |
| 02 | Boolean Arithmetic（HalfAdder / FullAdder / ALU …） | `02/` |
| 03 | Sequential Logic（Bit / Register / RAM / PC） | `03/` |
| 04 | Machine Language（Mult / Fill 組語） | `04/` |
| 05 | Computer Architecture（CPU / Memory / Computer） | `05/` |

## 資料夾結構

```text
期中作業/
└── README.md   # 本檔案
```

之後要放的內容可以直接建子資料夾，例如：

```text
期中作業/
├── README.md
├── 01/          # Boolean Logic 的 .hdl 與測試結果
├── 02/          # ALU 相關實作
├── 03/          # 循序邏輯電路
├── 04/          # Hack 組合語言
└── 05/          # CPU 與整台 Computer
```

## 備註

- 各章節的完整實作仍保留在 repo 根目錄的 `00/` ~ `05/`。
- 測試方式：用 Nand2Tetris 的 `HardwareSimulator` / `CPUEmulator` 開啟對應的 `.tst` 檔，比對 `.cmp` 期望值。
