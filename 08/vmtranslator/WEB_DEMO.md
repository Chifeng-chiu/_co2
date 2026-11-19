# VM Translator 網頁 Demo

網頁版有兩種執行方式，功能完全相同：

- **本機伺服器**：`web_demo.py` 用 Python 翻譯
- **純靜態**：直接在瀏覽器用 `web/translator.js` 翻譯，可部署到 GitHub Pages

## 啟動（本機伺服器）

最簡單的方式：直接雙擊作業資料夾中的：

```text
start_web_demo.bat
```

或在終端機執行：

```text
python web_demo.py
```

預設會開啟：

```text
http://127.0.0.1:8000
```

若 8000 已被占用，程式會自動嘗試下一個連接埠，並在終端機顯示實際網址。

若不想自動開啟瀏覽器：

```text
python web_demo.py --no-browser
```

改用其他 port：

```text
python web_demo.py --port 8080
```

## 啟動（純靜態，不需要 Python）

直接雙擊 `web/index.html` 也可以使用；沒有後端時會自動切成瀏覽器端翻譯，右上角標示 `STATIC / Browser JS`。

## 部署到 GitHub Pages

Pages 不支援 Python，但 `web/` 是純靜態檔案，可直接託管：

1. 將整個專案推到 GitHub（`main` 或 `master` 分支）
2. Repository → **Settings → Pages**
3. **Source** 選擇 **GitHub Actions**
4. 等待 `Deploy web demo to GitHub Pages` workflow 完成
5. 開啟 `https://<帳號>.github.io/<repo>/`

`.github/workflows/pages.yml` 會自動把 `web/` 資料夾上傳為 Pages 網站。

也可以在 **Settings → Pages → Source: Deploy from a branch** 選擇分支與 `/web` 資料夾，但需要在該分支根目錄提供 `web/` 路徑，因此建議使用 GitHub Actions。

## 打不開時

請確認：

1. 使用本機伺服器時，終端機中出現 `VM Translator Demo: http://127.0.0.1:8000`
2. 瀏覽器網址是 `http://127.0.0.1:8000` 或 `https://...github.io/...`
3. 使用 `web_demo.py` 時，啟動視窗不要關閉，關閉後伺服器就會停止
4. 若直接開啟 `web/index.html`，右上角應顯示 `STATIC`；若顯示但翻譯沒反應，請重新整理頁面

## 功能

- 拖放或選擇 `.vm` 檔案
- 選擇整個資料夾
- 單一檔案模式：不加入 Bootstrap
- 資料夾專案模式：偵測到 `Sys.vm` 時加入 Bootstrap
- 即時顯示產生的 Hack Assembly
- 組譯碼編輯器風格：行號、語法著色、可捲動
- 複製或下載 `.asm`
- 「載入範例」可快速測試 `Sys.vm` + `Main.vm`

## 兩種翻譯來源

| 環境 | 翻譯執行位置 | 右上角標示 |
| --- | --- | --- |
| `python web_demo.py` | `parser.py` + `code_writer.py`（Python） | `LOCAL / Python 3` |
| GitHub Pages / `file://` | `web/translator.js`（JavaScript） | `STATIC / Browser JS` |

`web/translator.js` 是 Python 版的逐字移植，已對 Chapter 7/8 全部測試程式比對，產生的組譯碼完全相同。
