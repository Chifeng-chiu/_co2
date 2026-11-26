"""A small Tkinter front end for the Jack compiler.

Run it with::

    python -m jackc.gui

or double-click ``JackCompiler-GUI.bat`` on Windows.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:  # pragma: no cover - import guard
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import filedialog, messagebox, ttk
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "This GUI needs tkinter. On Windows it ships with python.org builds; "
        "on Linux install the python3-tk package."
    ) from exc

from .compiler import Compiler
from .errors import JackError
from .parser import Parser
from .tokenizer import tokenize
from .xml_writer import class_to_xml, tokens_to_xml

MODE_SUFFIX = {"vm": ".vm", "xml": ".xml", "tokens": "T.xml"}


def _process(source: Path, mode: str) -> str:
    text = source.read_text(encoding="utf-8-sig")
    tokens = tokenize(text, filename=str(source))
    if mode == "tokens":
        return tokens_to_xml(tokens)
    class_def = Parser(tokens, filename=str(source)).parse()
    if mode == "xml":
        return class_to_xml(class_def)
    return Compiler(class_def).compile()


def _output_path(source: Path, root: Path, out_dir: Path | None, suffix: str) -> Path:
    if out_dir is None:
        return source.with_name(source.stem + suffix)
    if root.is_dir():
        relative = source.relative_to(root)
        return out_dir / relative.parent / (source.stem + suffix)
    return out_dir / (source.stem + suffix)


class JackCompilerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Jack Compiler · nand2tetris Project 10 & 11")
        self.root.geometry("960x700")
        self.root.minsize(760, 560)
        self._last_output_dir: Path | None = None
        self._configure_style()
        self._build_ui()

    # ------------------------------------------------------------------
    # Look and feel
    # ------------------------------------------------------------------
    def _configure_style(self) -> None:
        try:
            style = ttk.Style()
            for name in ("vista", "winnative", "clam"):
                if name in style.theme_names():
                    style.theme_use(name)
                    break
        except Exception:
            pass
        try:
            font = tkfont.nametofont("TkDefaultFont")
            font.configure(family="Segoe UI", size=10)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self._build_input()
        self._build_options()
        self._build_actions()
        self._build_notebook()

        self.status_var = tk.StringVar(value="就緒")
        ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=(12, 4)).pack(
            fill="x", side="bottom"
        )

    def _build_input(self) -> None:
        frame = ttk.LabelFrame(self.root, text="輸入")
        frame.pack(fill="x", padx=12, pady=(12, 6))

        self.path_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=self.path_var)
        entry.grid(row=0, column=0, sticky="ew", padx=(10, 6), pady=8)
        ttk.Button(frame, text="選擇檔案…", command=self._choose_file).grid(
            row=0, column=1, padx=(0, 6), pady=8
        )
        ttk.Button(frame, text="選擇資料夾…", command=self._choose_folder).grid(
            row=0, column=2, padx=(0, 10), pady=8
        )
        frame.columnconfigure(0, weight=1)

    def _build_options(self) -> None:
        frame = ttk.LabelFrame(self.root, text="輸出設定")
        frame.pack(fill="x", padx=12, pady=6)

        modes = ttk.Frame(frame)
        modes.grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 2))
        ttk.Label(modes, text="輸出類型：").pack(side="left")
        self.vm_var = tk.BooleanVar(value=True)
        self.xml_var = tk.BooleanVar(value=False)
        self.tokens_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(modes, text="VM 程式碼 (.vm)", variable=self.vm_var).pack(
            side="left", padx=(0, 12)
        )
        ttk.Checkbutton(modes, text="Parse XML (.xml)", variable=self.xml_var).pack(
            side="left", padx=(0, 12)
        )
        ttk.Checkbutton(modes, text="Token XML (T.xml)", variable=self.tokens_var).pack(
            side="left"
        )

        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, text="資料夾模式包含子資料夾", variable=self.recursive_var
        ).grid(row=1, column=0, columnspan=4, sticky="w", padx=10, pady=2)

        self.out_mode = tk.StringVar(value="source")
        ttk.Radiobutton(
            frame,
            text="輸出到來源檔旁",
            variable=self.out_mode,
            value="source",
            command=self._sync_out_entry,
        ).grid(row=2, column=0, sticky="w", padx=10, pady=(6, 8))
        ttk.Radiobutton(
            frame,
            text="輸出到指定資料夾",
            variable=self.out_mode,
            value="custom",
            command=self._sync_out_entry,
        ).grid(row=2, column=1, sticky="w", padx=(0, 6), pady=(6, 8))

        self.out_dir_var = tk.StringVar()
        self.out_entry = ttk.Entry(frame, textvariable=self.out_dir_var, state="disabled")
        self.out_entry.grid(row=2, column=2, sticky="ew", padx=(0, 6), pady=(6, 8))
        self.out_browse = ttk.Button(
            frame, text="瀏覽…", command=self._choose_out, state="disabled"
        )
        self.out_browse.grid(row=2, column=3, sticky="w", padx=(0, 10), pady=(6, 8))
        frame.columnconfigure(2, weight=1)

    def _build_actions(self) -> None:
        frame = ttk.Frame(self.root)
        frame.pack(fill="x", padx=12, pady=(6, 4))
        self.compile_btn = ttk.Button(frame, text="開始編譯", command=self._start_compile)
        self.compile_btn.pack(side="left")
        ttk.Button(frame, text="開啟輸出資料夾", command=self._open_output).pack(
            side="left", padx=8
        )
        ttk.Button(frame, text="清除紀錄", command=self._clear_log).pack(side="left")

    def _build_notebook(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=(4, 4))

        log_frame, self.log_text = self._make_text(notebook)
        preview_frame, self.preview_text = self._make_text(notebook)
        notebook.add(log_frame, text="編譯紀錄")
        notebook.add(preview_frame, text="輸出預覽")

        self.log_text.tag_configure("ok", foreground="#0a7d32")
        self.log_text.tag_configure("err", foreground="#b00020")
        self.log_text.tag_configure("info", foreground="#1a4fa0")

    def _make_text(self, parent: tk.Misc) -> tuple[ttk.Frame, tk.Text]:
        frame = ttk.Frame(parent)
        text = tk.Text(
            frame,
            wrap="none",
            height=12,
            font=("Consolas", 10),
            borderwidth=1,
            relief="solid",
        )
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        text.configure(state="disabled")
        return frame, text

    # ------------------------------------------------------------------
    # File pickers
    # ------------------------------------------------------------------
    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="選擇 Jack 檔案",
            filetypes=[("Jack source", "*.jack"), ("All files", "*.*")],
        )
        if path:
            self.path_var.set(path)

    def _choose_folder(self) -> None:
        path = filedialog.askdirectory(title="選擇包含 .jack 的資料夾")
        if path:
            self.path_var.set(path)

    def _choose_out(self) -> None:
        path = filedialog.askdirectory(title="選擇輸出資料夾")
        if path:
            self.out_dir_var.set(path)

    def _sync_out_entry(self) -> None:
        state = "normal" if self.out_mode.get() == "custom" else "disabled"
        self.out_entry.configure(state=state)
        self.out_browse.configure(state=state)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _log(self, message: str, tag: str | None = None) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.status_var.set("就緒")

    def _show_preview(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as error:  # pragma: no cover - defensive
            text = f"(無法讀取 {path}：{error})"
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", text)
        self.preview_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------
    def _selected_modes(self) -> list[str]:
        modes: list[str] = []
        if self.vm_var.get():
            modes.append("vm")
        if self.xml_var.get():
            modes.append("xml")
        if self.tokens_var.get():
            modes.append("tokens")
        if not modes:
            raise ValueError("請至少勾選一種輸出類型。")
        return modes

    def _collect_files(self, path: Path) -> list[Path]:
        if path.is_file():
            if path.suffix.lower() != ".jack":
                raise ValueError(f"{path.name} 不是 .jack 檔。")
            return [path]
        pattern = "**/*.jack" if self.recursive_var.get() else "*.jack"
        files = sorted(path.glob(pattern))
        if not files:
            raise ValueError(f"資料夾內找不到 .jack 檔：{path}")
        return files

    def _resolve_out_dir(self) -> Path | None:
        if self.out_mode.get() != "custom":
            return None
        text = self.out_dir_var.get().strip()
        if not text:
            raise ValueError("請指定輸出資料夾，或改選「輸出到來源檔旁」。")
        return Path(text)

    def _start_compile(self) -> None:
        self._clear_log()
        try:
            modes = self._selected_modes()
            raw = self.path_var.get().strip()
            if not raw:
                raise ValueError("請先選擇 .jack 檔案或資料夾。")
            path = Path(raw)
            if not path.exists():
                raise ValueError(f"路徑不存在：{path}")
            files = self._collect_files(path)
            out_dir = self._resolve_out_dir()
            if out_dir is not None:
                out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as error:
            messagebox.showerror("無法編譯", str(error))
            self._log(f"✗ {error}", "err")
            return

        self.compile_btn.configure(state="disabled")
        self.status_var.set("編譯中…")
        self.root.update_idletasks()

        written = 0
        failed = 0
        last_output: Path | None = None
        self._log(f"輸入：{path}", "info")
        self._log(f"找到 {len(files)} 個 .jack 檔", "info")

        try:
            for source in files:
                try:
                    produced: list[Path] = []
                    for mode in modes:
                        text = _process(source, mode)
                        destination = _output_path(source, path, out_dir, MODE_SUFFIX[mode])
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_text(text, encoding="utf-8", newline="\n")
                        produced.append(destination)
                        written += 1
                    last_output = produced[0]
                    names = ", ".join(item.name for item in produced)
                    self._log(f"✓ {source.name} → {names}", "ok")
                except JackError as error:
                    failed += 1
                    self._log(f"✗ {source.name}: {error}", "err")
                except Exception as error:  # pragma: no cover - defensive
                    failed += 1
                    self._log(f"✗ {source.name}: {error}", "err")
        finally:
            self.compile_btn.configure(state="normal")

        if last_output is not None:
            self._show_preview(last_output)
            self._last_output_dir = last_output.parent
        elif out_dir is not None:
            self._last_output_dir = out_dir
        elif path.is_dir():
            self._last_output_dir = path
        else:
            self._last_output_dir = path.parent

        if failed:
            self.status_var.set(f"完成：{written} 個輸出，{failed} 個檔案失敗")
            self._log(f"完成，但 {failed} 個檔案失敗。", "err")
            messagebox.showwarning(
                "編譯完成（有錯誤）",
                f"成功寫出 {written} 個檔案，{failed} 個檔案失敗。\n請看「編譯紀錄」了解詳情。",
            )
        else:
            self.status_var.set(f"完成：{written} 個輸出檔")
            self._log(f"完成，共寫出 {written} 個檔案。", "info")

    # ------------------------------------------------------------------
    # Misc actions
    # ------------------------------------------------------------------
    def _open_output(self) -> None:
        folder = self._last_output_dir
        if folder is None or not folder.exists():
            raw = self.path_var.get().strip()
            candidate = Path(raw) if raw else None
            if candidate is not None:
                folder = candidate if candidate.is_dir() else candidate.parent
        if folder is None or not folder.exists():
            messagebox.showinfo("開啟資料夾", "還沒有輸出。請先編譯。")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as error:  # pragma: no cover - defensive
            messagebox.showerror("無法開啟資料夾", str(error))


def main() -> None:
    try:
        root = tk.Tk()
        try:
            root.call("tk", "scaling", 1.2)
        except Exception:
            pass
        JackCompilerGUI(root)
        root.mainloop()
    except Exception:  # pragma: no cover - last-resort diagnostics
        import traceback

        detail = traceback.format_exc()
        try:
            (Path(__file__).resolve().parent.parent / "gui-error.log").write_text(
                detail, encoding="utf-8"
            )
        except Exception:
            pass
        try:
            messagebox.showerror("Jack Compiler GUI", detail)
        except Exception:
            raise


if __name__ == "__main__":  # pragma: no cover
    main()
