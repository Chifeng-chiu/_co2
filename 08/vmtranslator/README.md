# Nand2Tetris VM Translator（Chapter 7 & 8）

以 Python 3 標準函式庫實作的 Nand2Tetris VM 翻譯器，外加一個可直接部署到 GitHub Pages 的網頁版 Demo。

## 檔案結構

| 檔案 | 說明 |
| --- | --- |
| `VMTranslator.py` | 命令列入口，處理單檔／資料夾輸入與 Bootstrap 判斷 |
| `parser.py` | VM 指令解析器 |
| `code_writer.py` | Hack Assembly 產生器 |
| `web_demo.py` | 本機網頁伺服器（Python 後端翻譯） |
| `web/index.html` | 網頁介面 |
| `web/style.css` | 樣式 |
| `web/app.js` | 前端互動邏輯 |
| `web/translator.js` | 翻譯器的純 JavaScript 版本（GitHub Pages 用） |
| `start_web_demo.bat` | Windows 雙擊啟動批次檔 |

## 命令列使用

```text
python VMTranslator.py <來源檔案或資料夾>
```

- 單一 `.vm` 檔：輸出同名 `.asm`，不加入 Bootstrap
- 資料夾：翻譯其中所有 `.vm` 檔，輸出 `<資料夾名>.asm`
- 資料夾內含 `Sys.vm` 時自動加入 Bootstrap（呼叫 `Sys.init`）

範例：

```text
python VMTranslator.py 08\FunctionCalls\FibonacciElement
```

## 網頁 Demo（本機）

```text
python web_demo.py
```

開啟 `http://127.0.0.1:8000`。若該埠被占用會自動改用下一個埠。

也可以直接雙擊 `start_web_demo.bat`。

## 網頁 Demo（GitHub Pages）

GitHub Pages 只能放靜態檔案，因此網頁版把翻譯器移植成 `web/translator.js`，在瀏覽器端完成翻譯，輸出與 Python 版逐字相同。

部署步驟：

1. 建立 GitHub repository 並上傳本專案
2. 進入 repository 的 **Settings → Pages**
3. 在 **Build and deployment → Source** 選擇 **GitHub Actions**
4. Push 到 `main`（或 `master`）分支，`.github/workflows/pages.yml` 會自動部署 `web/` 資料夾
5. 完成後網址為 `https://<帳號>.github.io/<repo>/`

> 網頁會自動偵測環境：有本機 Python 後端時顯示 `LOCAL / Python 3`，靜態託管時顯示 `STATIC / Browser JS`。

## 支援的指令

- 算術：`add` `sub` `neg` `eq` `gt` `lt` `and` `or` `not`
- 記憶體：`push` / `pop`，區段包含 `constant` `local` `argument` `this` `that` `temp` `pointer` `static`
- 流程：`label` `goto` `if-goto`（標籤以函式名稱為範圍）
- 函式：`function` `call` `return`
- 多檔案專案的 `static` 符號以檔名區分
