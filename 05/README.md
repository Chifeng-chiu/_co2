# Project 05 — Hack 電腦（CPU / Memory / Computer）

> Nand2Tetris Project 05：把前面 chapters 做好的零件接起來，組出一台真的會跑的電腦。
> 這章沒有演算法難度，全是**接線**——但線接錯一個 bit，整台電腦就不動。

## 資料夾結構

```text
05/
├── README.md
├── CPU.hdl                 # 指令解碼 + 執行流程（本章核心）
├── Memory.hdl              # 位址空間：RAM16K + Screen + Keyboard
├── Computer.hdl            # ROM32K + CPU + Memory＝完整電腦
├── CPU.tst / CPU.cmp       # CPU 單元測試（含 DRegister 追蹤）
├── CPU.out                 # 本機執行 CPU.tst 的輸出
├── CPU-external.tst / .cmp # 簡化輸出版（不追 DRegister）
├── Memory.tst / Memory.cmp # 記憶體區段測試
├── ComputerAdd.tst / .cmp  # 整台電腦跑 Add.hack（含 reset 再跑一次）
├── ComputerMax.tst / .cmp  # 整台電腦跑 Max.hack
├── ComputerRect.tst / .cmp # 整台電腦跑 Rect.hack（螢幕畫矩形）
├── ComputerAdd-external.tst / .cmp
├── ComputerMax-external.tst / .cmp
├── ComputerRect-external.tst / .cmp
├── Add.hack                # 機器碼：R0 = 2 + 3
├── Max.hack                # 機器碼：R2 = max(R0, R1)
├── Rect.hack               # 機器碼：螢幕左上角畫 16 寬的矩形
└── 846405874_2094841488066284_1739689786206131867_n.jpg  # CPU 電路圖（參考）
```

用到的 chips 全部都是 Nand2Tetris 工具內建的（`tools/builtInChips/`）：
`Not`、`And`、`Or`、`Mux16`、`Mux4Way16`、`DMux4Way`、`ALU`、`ARegister`、`DRegister`、`PC`、`RAM16K`、`ROM32K`、`Screen`、`Keyboard`。

## 背景知識

### 1. Hack 指令長相

16 bits，兩大類：

```text
A 指令 (bit15 = 0):   0vvvvvvvvvvvvvvv        →  A = value
C 指令 (bit15 = 1):   111a cccccc ddd jjj
                              │      │    │
                              │      │    └─ j1 j2 j3：JGT / JEQ / JLT
                              │      └────── d1 d2 d3：A / D / M 目的暫存器
                              └───────────── c1..c6：ALU 控制位
```

`instruction[12]` 是 `a` 位，決定 ALU 的 y 端吃 `A` 還是 `M`。

### 2. 位址空間對應

```text
0x0000 ~ 0x3FFF   RAM16K      16K words   （一般變數 R0~R15 都在這）
0x4000 ~ 0x5FFF   Screen      8K words    （256 x 512 像素，每像素 16 bits）
0x6000            Keyboard    1 word      （只讀）
```

對應到 `Memory.hdl` 的 `address[14:13]`：

| `address[14:13]` | 區段 | 該區段使用的位址 |
|---|---|---|
| `00` | RAM16K | `address[0..13]` |
| `01` | RAM16K | `address[0..13]` |
| `10` | Screen | `address[0..12]` |
| `11` | Keyboard | — |

## 1. CPU.hdl — 解碼 → 執行 → 決定下一個 PC

整個 CPU 可以看成三段流水：**這是什麼指令 → 算出結果 → 結果要去哪、要不要跳**。

### 1.1 分辨 A 指令 / C 指令

```hdl
Not(in=instruction[15], out=isA);
Not(in=isA, out=isC);
```

`instruction[15]=0` → A 指令；`=1` → C 指令。

### 1.2 A 暫存器要裝什麼？

A 指令時裝常數；C 指令且 dest 包含 A 時，裝 ALU 算出來的結果：

```hdl
And(a=isC, b=instruction[5], out=ALUtoA);          // 是 C 指令而且 dest 有 A？
Mux16(a=instruction, b=outALU, sel=ALUtoA, out=inA);

Or(a=isA, b=ALUtoA, out=loadA);
ARegister(in=inA, load=loadA, out=outA, out[0..14]=addressM);
```

- `instruction[5]` = `d1` = 「dest 要寫進 A」
- `out[0..14]=addressM`：A 的低 15 bits 就是送往記憶體的位址
- A 指令（`@12345`）的 `isA=1`，所以 `loadA=1`，`inA` 直接取 `instruction` 的值

### 1.3 D 暫存器與 ALU

```hdl
And(a=isC, b=instruction[4], out=loadD);           // d2 = dest 要寫進 D
DRegister(in=outALU, load=loadD, out=outD);

Mux16(a=outA, b=inM, sel=instruction[12], out=inAM);

ALU(x=outD, y=inAM,
    zx=instruction[11], nx=instruction[10],
    zy=instruction[9],  ny=instruction[8],
    f=instruction[7],   no=instruction[6],
    out=outALU, out=outM, zr=zr, ng=ng);
```

- `instruction[12]` = `a` 位：`0` → ALU 的 y 端吃 A；`1` → 吃 `M`
- ALU 的輸出**同時**接到 `outALU`（給 DRegister）與 `outM`（寫回記憶體的資料）
- `zr` / `ng` 是 ALU 額外拉出來的旗標，下一步判斷跳躍要用

### 1.4 要不要寫記憶體

```hdl
And(a=isC, b=instruction[3], out=writeM);          // d3 = dest 要寫進 M
```

### 1.5 跳躍判斷

```hdl
Or(a=zr, b=ng, out=zrOrNg);
Not(in=zrOrNg, out=pos);                           // pos = (結果 > 0)

And(a=instruction[0], b=pos, out=jgt);             // JGT
And(a=instruction[1], b=zr,  out=jeq);             // JEQ
And(a=instruction[2], b=ng,  out=jlt);             // JLT

Or(a=jgt, b=jeq, out=jge);
Or(a=jge, b=jlt, out=jumpCondition);

And(a=isC, b=jumpCondition, out=loadPC);
PC(in=outA, load=loadPC, inc=true, reset=reset, out[0..14]=pc);
```

- `pos` 其實就是 `!(zr || ng)`，剛好用 NOT + OR 湊出來
- 就算 jump 條件成立，**A 指令也永遠不會跳**，所以最後要 `And(a=isC, ...)` 再過濾一次
- `PC` 的 `in` 接到 `outA`：跳躍時跳到 A 指向的位置（`@label` 把位址載進 A 再 `0;JMP`）

### 1.6 一張圖看完整條路徑

```text
instruction ──┬─> isA / isC ──┬─> inA ──> ARegister ──┬──> outA ──> ALU 的 y
               │               │                        └──> addressM
               │               └──> loadD ──> DRegister ──> ALU 的 x
               └─> ALU 控制位 ──────────────────────────> ALU ──> outALU / outM
                                                       └──> zr, ng ──> 跳躍判斷 ──> PC
```

## 2. Memory.hdl — 位址空間的分配

用一個 `DMux4Way` 把 `load` 訊號分流到不同區段，再用 `Mux4Way16` 把讀出的值選回來：

```hdl
DMux4Way(in=load, sel=address[13..14], a=loadram1, b=loadram2, c=loadscreen, d=loadkbd);
Or(a=loadram1, b=loadram2, out=loadram);

RAM16K(in=in, load=loadram,  address=address[0..13], out=ramout);
Screen(in=in, load=loadscreen, address=address[0..12], out=screenout);
Keyboard(out=kbdout);

Mux4Way16(a=ramout, b=ramout, c=screenout, d=kbdout, sel=address[13..14], out=out);
```

幾個關鍵點：

- `sel` 用 **`address[13..14]`**（不是 `[14]`），因為 16K RAM + 8K Screen 剛好需要 2 bits 選區段
- `Mux4Way16` 的 `a`、`b` **都接 `ramout`**：因為 `0x0000~0x3FFF` 是一整塊 16K RAM，`0x2000` 和 `0x3000` 只是它的上半段
- `Screen` 的位址只要 13 bits（8K words → `address[0..12]`），`Keyboard` 只讀、沒有 `load`
- 寫入位址 `0x6000` 以上是無效的，這題不管它

## 3. Computer.hdl — 三個零件串成一台電腦

```hdl
ROM32K(address=pc, out=instruction);
CPU(inM=memOut, instruction=instruction, reset=reset,
    outM=outM, writeM=writeM, addressM=addressM, pc=pc);
Memory(in=outM, load=writeM, address=addressM, out=memOut);
```

- `ROM32K` 用 `pc` 當位址取出目前這條指令 → `instruction`
- `CPU` 的 `inM` 接 `Memory` 的 `out`（讀記憶體的值）
- `CPU` 的 `outM` / `writeM` / `addressM` 回到 `Memory`（寫記憶體）
- `reset=1` 時 `PC` 歸零，程式從位址 0 重跑

## 4. 測試用的三支 Hack 程式

這三支 `.hack` 是用 `tools/Assembler` 組譯出來的機器碼，對應到 Project 06 的 `.asm`：

| 機器碼 | 來源 | 功能 |
|---|---|---|
| `Add.hack` | `06/add/Add.asm` | `R0 = 2 + 3` |
| `Max.hack` | `06/max/Max.asm` | `R2 = max(R0, R1)` |
| `Rect.hack` | `06/rect/Rect.asm` | 螢幕左上角畫 16 像素寬、`R0` 像素高的矩形 |

`ComputerAdd.tst` 會先把 `Add.hack` 載入 ROM，跑 6 個 tick，再 `set reset 1` 重置 PC 後**再跑一次**——用來驗證 reset 之後程式真的從頭執行，而不是接著上一輪的位址跑。

## 怎麼測試

用 Nand2Tetris 的 `HardwareSimulator` 開啟 `.tst` 檔：

| 測試檔 | 測的是什麼 | 比對檔 |
|------|------------|--------|
| `CPU.tst` | 只餵指令進 CPU，看 `outM` / `writeM` / `addressM` / `pc` / `DRegister` | `CPU.cmp` |
| `CPU-external.tst` | 同上但輸出欄位簡化（不追 DRegister） | `CPU-external.cmp` |
| `Memory.tst` | 寫入 RAM / Screen 各段，確認有沒有寫到錯的區段 | `Memory.cmp` |
| `ComputerAdd.tst` | 整台電腦跑 `Add.hack`，並驗證 reset | `ComputerAdd.cmp` |
| `ComputerMax.tst` | 整台電腦跑 `Max.hack` | `ComputerMax.cmp` |
| `ComputerRect.tst` | 整台電腦跑 `Rect.hack`，螢幕左上角應出現矩形 | `ComputerRect.cmp` |
| `ComputerAdd/Max/Rect-external.tst` | 對應程式的簡化輸出版本 | `*-external.cmp` |

跑 `Memory.tst`、`ComputerRect.tst` 前記得先在 `View` 選單切到 `Screen` 才能看到畫面。

## 常踩的坑

1. **`addressM` 接錯**：應該是 `ARegister` 的 `out[0..14]`，不是整個 `out`（不然位址會帶到 A 的第 15 bit）。
2. **A 指令也會跳**：`@label` + `0;JMP` 的組合裡，`0;JMP` 是 C 指令沒問題，但 `loadPC` 一定要再 `And(a=isC, ...)`，否則 `instruction[0..2]` 的殘值會誤觸發跳躍。
3. **忘記拉 `zr` / `ng`**：ALU 有這兩個輸出 pin，不拉出來就沒辦法判斷 JGT / JEQ / JLT。
4. **`Memory` 的 `sel` 用錯 bit**：用 `address[13..14]`，不是 `address[14]`。
5. **`Mux4Way16` 的 `b` 忘記接 `ramout`**：`0x2000~0x3FFF` 也是 RAM，接錯會讀到垃圾值。
6. **PC 的 `in` 要接 `outA`**，不是接 `pc+1`；跳躍位址是由 A 決定的。

## 心得一句話

Project 05 是整條路最像「做硬體」的一章：沒有演算法，只有**位元對位**。`instruction[12]` 該接哪、ALU 的旗標該從哪拉出來、`address[13..14]` 切得對不對——每一個都是 16 顆燈泡的接線題。做完這章再回頭看 Project 06 的 `Max.asm`，才會發現「`D;JGT`」其實就是 `CPU.hdl` 裡那三顆 `And` + `Not` 的高階版。
