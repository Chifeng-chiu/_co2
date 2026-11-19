#!/usr/bin/env python3
"""Local web demo for the Nand2Tetris VM Translator.

Run:
    python web_demo.py

The page is served at http://127.0.0.1:8000 and uses the same translator
modules as the command-line program.
"""

import argparse
import json
import os
import re
import sys
import tempfile
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from code_writer import CodeWriter
from parser import Parser
from VMTranslator import translate_commands

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "web"
MAX_REQUEST_BYTES = 12 * 1024 * 1024
MAX_SOURCE_CHARS = 4 * 1024 * 1024


class TranslationError(ValueError):
    """An error that should be shown to the user in the web page."""


def _safe_vm_name(name):
    raw = str(name or "").replace("\\", "/")
    base = raw.rsplit("/", 1)[-1].strip()
    if not base.lower().endswith(".vm") or base.lower() == ".vm":
        raise TranslationError("只接受 .vm 檔案：{}".format(base or "(空白檔名)"))
    if len(base) > 120:
        raise TranslationError("檔名太長：{}".format(base))

    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", base)
    if not safe or safe in (".", ".."):
        raise TranslationError("無效的檔名。")
    return safe


def _safe_project_stem(name):
    raw = str(name or "").replace("\\", "/")
    base = raw.rsplit("/", 1)[-1].strip()
    stem = os.path.splitext(base)[0]
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem).strip(" .")
    return stem or "Program"


def translate_project(files, mode="single", project_name="Program"):
    """Translate uploaded VM sources and return assembly text and metadata."""
    if mode not in ("single", "project"):
        raise TranslationError("mode 必須是 single 或 project。")
    if not isinstance(files, list) or not files:
        raise TranslationError("請先加入至少一個 .vm 檔案。")

    normalized = []
    seen_names = set()
    total_chars = 0

    for item in files:
        if not isinstance(item, dict):
            raise TranslationError("檔案資料格式錯誤。")
        name = _safe_vm_name(item.get("name"))
        content = item.get("content")
        if not isinstance(content, str):
            raise TranslationError("{} 的內容不是文字檔。".format(name))

        total_chars += len(content)
        if total_chars > MAX_SOURCE_CHARS:
            raise TranslationError("上傳內容過大。")

        key = name.casefold()
        if key in seen_names:
            raise TranslationError("檔名重複：{}".format(name))
        seen_names.add(key)
        normalized.append({"name": name, "content": content})

    if mode == "single" and len(normalized) != 1:
        raise TranslationError("單一檔案模式只能放入一個 .vm 檔。")

    if mode == "project":
        normalized.sort(key=lambda item: item["name"].casefold())
        bootstrap = any(item["name"].casefold() == "sys.vm" for item in normalized)
        output_name = _safe_project_stem(project_name) + ".asm"
    else:
        bootstrap = False
        output_name = os.path.splitext(normalized[0]["name"])[0] + ".asm"

    with tempfile.TemporaryDirectory(prefix="vmtranslator_web_") as temp_dir:
        temp_path = Path(temp_dir)
        source_paths = []
        for item in normalized:
            source_path = temp_path / item["name"]
            source_path.write_text(item["content"], encoding="utf-8")
            source_paths.append(source_path)

        output_path = temp_path / output_name
        writer = CodeWriter(str(output_path))
        try:
            if bootstrap:
                writer.write_init()

            for source_path in source_paths:
                writer.set_file_name(source_path.stem)
                translate_commands(Parser(str(source_path)), writer)
        finally:
            writer.close()

        asm = output_path.read_text(encoding="utf-8")

    return {
        "asm": asm,
        "fileName": output_name,
        "bootstrap": bootstrap,
        "fileCount": len(normalized),
        "lineCount": asm.count("\n"),
    }


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "VMTranslatorDemo/1.0"

    _ASSETS = {
        "/": ("index.html", "text/html; charset=utf-8"),
        "/index.html": ("index.html", "text/html; charset=utf-8"),
        "/style.css": ("style.css", "text/css; charset=utf-8"),
        "/app.js": ("app.js", "application/javascript; charset=utf-8"),
        "/translator.js": ("translator.js", "application/javascript; charset=utf-8"),
    }

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(200, {"ok": True})
            return
        if path == "/favicon.ico":
            self._send_bytes(204, b"", "image/x-icon")
            return

        asset = self._ASSETS.get(path)
        if asset is None:
            self._send_json(404, {"error": "Not found."})
            return

        file_name, content_type = asset
        try:
            data = (ASSET_DIR / file_name).read_bytes()
        except OSError:
            self._send_json(404, {"error": "Asset not found."})
            return
        self._send_bytes(200, data, content_type)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/translate":
            self._send_json(404, {"error": "Not found."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length."})
            return

        if content_length <= 0:
            self._send_json(400, {"error": "Empty request body."})
            return
        if content_length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "Request body is too large."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            result = translate_project(
                payload.get("files", []),
                mode=payload.get("mode", "single"),
                project_name=payload.get("projectName", "Program"),
            )
        except TranslationError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Invalid JSON request."})
            return
        except Exception:
            traceback.print_exc()
            self._send_json(500, {"error": "翻譯時發生未預期的錯誤。"})
            return

        self._send_json(200, result)

    def _send_bytes(self, status, data, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if data:
            self.wfile.write(data)

    def _send_json(self, status, value):
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, data, "application/json; charset=utf-8")

    def log_message(self, fmt, *args):
        sys.stderr.write("[web] " + (fmt % args) + "\n")


def create_server(host="127.0.0.1", port=8000):
    return ThreadingHTTPServer((host, port), DemoHandler)


def create_server_with_fallback(host, requested_port):
    """Create a server, trying nearby ports if the requested one is busy."""
    if requested_port == 0:
        candidates = [0]
    else:
        candidates = [requested_port] + list(range(requested_port + 1, requested_port + 11))

    last_error = None
    for port in candidates:
        try:
            return create_server(host, port)
        except OSError as exc:
            last_error = exc
    raise last_error


def main(argv=None):
    parser = argparse.ArgumentParser(description="Nand2Tetris VM Translator web demo")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args(argv)

    try:
        server = create_server_with_fallback(args.host, args.port)
    except OSError as exc:
        print("無法啟動伺服器：{}".format(exc), file=sys.stderr)
        return 1

    host, port = server.server_address[:2]
    url_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    url = "http://{}:{}".format(url_host, port)
    if args.port != 0 and port != args.port:
        print("連接埠 {} 已被占用，自動改用 {}。".format(args.port, port))
    print("VM Translator Demo: {}".format(url))
    print("若瀏覽器沒有自動開啟，請手動複製上面的網址。")
    print("按 Ctrl+C 結束。")

    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n伺服器已停止。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
