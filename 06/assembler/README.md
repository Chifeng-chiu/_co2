# Nand2Tetris Project 6 — Hack Assembler Workbench

以 Nand2Tetris Project 6 規格實作的 **Hack 組譯器 / 反組譯器**，提供兩種使用方式：

- `assembler.py`：Python 命令列工具，可將 `.asm` 組譯成 `.hack`，也能反向將 `.hack` 反組譯成 `.asm`。
- `index.html`：單檔網頁工作台，直接雙擊即可使用，提供即時雙向轉換、指令拆解、符號表與差異比對。

兩者皆遵循官方 Hack 指令格式，包含 predefined symbols、標籤（labels）與從 `RAM[16]` 開始配置的自訂變數。

---

## 專案結構

```text
06/assembler/
├── assembler.py   # Python CLI 組譯器 / 反組譯器
├── index.html     # 單檔網頁工作台（HTML + CSS + JavaScript）
└── README.md
```

---

## 快速開始

### 網頁版

直接雙擊 `index.html`，不需要安裝任何套件或啟動伺服器。

網頁支援：

- `ASM → HACK` 與 `HACK → ASM` 雙向即時轉換
- 左右雙編輯器與行號
- 拖放或上傳 `.asm` / `.hack` 檔案
- 下載 `.asm` / `.hack`、複製結果
- 官方範例：`Add.asm`、`Max.asm`、`Rect.asm`
- 指令色塊拆解對照表
- 預定義符號、標籤、自訂變數檢視
- 與官方 `.hack` 解答逐行比對
- 深色 / 淺色主題切換（會記住選擇）
- `Ctrl + Enter`（macOS 為 `Cmd + Enter`）重新轉換

### Python CLI

需求：**Python 3.10 以上**，無第三方套件依賴。

```bash
# 將 Prog.asm 組譯成 Prog.hack
python assembler.py Prog.asm

# 指定輸出位置
python assembler.py Prog.asm -o build/Prog.hack

# 組譯並印出符號表
python assembler.py Prog.asm --symbols

# 將 Prog.hack 反組譯成 Prog.asm
python assembler.py --disassemble Prog.hack

# 反組譯並指定輸出檔名
python assembler.py -d Prog.hack -o Prog.asm

# 安靜模式，只輸出錯誤訊息
python assembler.py Prog.asm -q
```

成功時會顯示類似：

```text
[OK] Assembled 6 instructions -> Prog.hack
     labels: 0, variables: 0, errors: 0
```

若輸入檔有錯誤，工具會印出原始行號與錯誤內容，**不會產生輸出檔**，並以 exit code `1` 結束。

---

## Hack 組譯規則

支援官方 Hack assembly 語法：

```asm
// 註解：整行或行尾都可以
@2
D=A
@3
D=D+A
@0
M=D
```

### A-Instruction

```asm
@value
```

輸出格式：

```text
0 + 15-bit address
```

`value` 可以是：

- 十進位常數：`@0`、`@32767`
- 預定義符號：`@R0`、`@SCREEN`、`@KBD`
- 使用者標籤：`@LOOP`
- 自訂變數：`@counter`

### C-Instruction

```asm
dest=comp;jump
```

輸出格式：

```text
111 a cccccc ddd jjj
```

`dest`、`comp`、`jump` 皆依照官方表格處理，例如：

```asm
D=M
D=D+A
M=D
0;JMP
D;JGT
```

### 標籤 Labels

```asm
(LOOP)
    @LOOP
    0;JMP
```

標籤是虛擬的，**不佔用 ROM 位址**；標籤值為 0-based ROM address。

### 變數 Variables

首次出現且未定義的符號會自動配置到 `RAM[16]` 開始的位置：

```asm
@counter
M=D
```

### 預定義符號

`SP`、`LCL`、`ARG`、`THIS`、`THAT`、`R0`–`R15`、`SCREEN`、`KBD`。

---

## 範例

`Add.asm`：

```asm
// Adds 2 to 5 and stores the result in address 0
@2
D=A
@3
D=D+A
@0
M=D
```

執行：

```bash
python assembler.py Add.asm
```

產生的 `Add.hack`：

```text
0000000000000010
1110110000010000
0000000000000011
1110000010010000
0000000000000000
1110001100001000
```

---

## 錯誤處理

- 所有錯誤都會標示原始 `.asm` / `.hack` 行號。
- 常見錯誤包含：
  - 未知的 `comp` / `dest` / `jump`
  - 非法符號或標籤名稱
  - 重複定義標籤
  - A-指令數值超出 15-bit 範圍（`0`–`32767`）
  - `.hack` 內容不是 16 位元二進位字串
  - 無效的 C-Instruction 語法
- 網頁版可點擊錯誤訊息跳至對應行。
- CLI 版發現錯誤時不寫出輸出檔，避免產生不完整的 `.hack`。

---

## 實作重點

- **Two-pass assembler**：
  1. 第一遍收集標籤並建立 ROM 位址。
  2. 第二遍配置變數並產生 16-bit 機器碼。
- 完整官方 `comp` / `dest` / `jump` 對照表。
- 支援官方 `.asm` 檔案的註解與空白格式。
- 反組譯器可將合法 16-bit 機器碼還原為 `@value` 或 `dest=comp;jump`。
- 網頁版為單一 HTML 檔案，CSS 與 JavaScript 全部內嵌，可離線使用。

---

## 驗證

- `assembler.py` 已對 `Add.asm`、`Max.asm`、`Rect.asm` 進行組譯測試。
- 已驗證 A-Instruction 與合法 C-Instruction 的往返轉換。
- `index.html` 已通過 JavaScript 語法檢查，並以瀏覽器實際測試：
  - 載入官方範例
  - ASM ↔ HACK 模式切換
  - 指令拆解與符號表
  - 差異比對成功 / 失敗
  - 錯誤提示與行號跳轉
  - 深色 / 淺色主題切換與記憶
