(() => {
  "use strict";

  const MAX_FILE_BYTES = 4 * 1024 * 1024;

  // "backend" = local Python server (web_demo.py)
  // "static"  = pure browser translation (GitHub Pages / file://)
  const RUNTIME = { backend: null };

  const EXAMPLES = [
    {
      name: "Sys.vm",
      content: [
        "function Sys.init 0",
        "call Main.main 0",
        "label END",
        "goto END",
        "",
      ].join("\n"),
    },
    {
      name: "Main.vm",
      content: [
        "function Main.main 0",
        "push constant 7",
        "push constant 8",
        "add",
        "return",
        "",
      ].join("\n"),
    },
  ];

  const elements = {
    modeInputs: Array.from(document.querySelectorAll('input[name="mode"]')),
    projectNameRow: document.getElementById("projectNameRow"),
    projectName: document.getElementById("projectName"),
    dropZone: document.getElementById("dropZone"),
    fileInput: document.getElementById("fileInput"),
    folderInput: document.getElementById("folderInput"),
    chooseFiles: document.getElementById("chooseFiles"),
    chooseFolder: document.getElementById("chooseFolder"),
    fileList: document.getElementById("fileList"),
    emptyFiles: document.getElementById("emptyFiles"),
    fileTotal: document.getElementById("fileTotal"),
    exampleBtn: document.getElementById("exampleBtn"),
    clearBtn: document.getElementById("clearBtn"),
    translateBtn: document.getElementById("translateBtn"),
    copyBtn: document.getElementById("copyBtn"),
    downloadBtn: document.getElementById("downloadBtn"),
    outputName: document.getElementById("outputName"),
    statusDot: document.getElementById("statusDot"),
    bootstrapTag: document.getElementById("bootstrapTag"),
    editor: document.getElementById("editor"),
    editorFileName: document.getElementById("editorFileName"),
    editorScroll: document.getElementById("editorScroll"),
    lineNumbers: document.getElementById("lineNumbers"),
    placeholder: document.getElementById("placeholder"),
    assemblyOutput: document.getElementById("assemblyOutput"),
    assemblyCode: document.getElementById("assemblyCode"),
    meta: document.getElementById("meta"),
    statusMessage: document.getElementById("statusMessage"),
    runtimeLabel: document.getElementById("runtimeLabel"),
    runtimeDetail: document.getElementById("runtimeDetail"),
    footerRuntime: document.getElementById("footerRuntime"),
    toast: document.getElementById("toast"),
  };

  const state = {
    files: new Map(),
    asm: "",
    outputName: "",
    loading: false,
    outputStale: false,
    toastTimer: 0,
  };

  function currentMode() {
    const checked = elements.modeInputs.find((input) => input.checked);
    return checked ? checked.value : "single";
  }

  function setMode(mode) {
    for (const input of elements.modeInputs) {
      input.checked = input.value === mode;
    }
    elements.projectNameRow.hidden = mode !== "project";
    refreshUi();
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function setStatus(text, kind = "") {
    elements.statusMessage.textContent = text;
    elements.statusMessage.className = "status-message" + (kind ? " " + kind : "");
    elements.statusDot.classList.remove("ready", "error");
    if (kind === "success") elements.statusDot.classList.add("ready");
    if (kind === "error") elements.statusDot.classList.add("error");
  }

  function showToast(message, kind = "") {
    window.clearTimeout(state.toastTimer);
    elements.toast.textContent = message;
    elements.toast.className = "toast show" + (kind ? " " + kind : "");
    state.toastTimer = window.setTimeout(() => {
      elements.toast.className = "toast";
    }, 2600);
  }

  function updateRuntimeBadge(kind) {
    const isBackend = kind === "backend";
    if (elements.runtimeLabel) {
      elements.runtimeLabel.textContent = isBackend ? "LOCAL" : "STATIC";
    }
    if (elements.runtimeDetail) {
      elements.runtimeDetail.textContent = isBackend ? "Python 3" : "Browser JS";
    }
    if (elements.footerRuntime) {
      elements.footerRuntime.textContent = isBackend
        ? "由本機 web_demo.py 提供服務，原始碼不會上傳到任何伺服器"
        : "翻譯在瀏覽器本機執行，可部署到 GitHub Pages，原始碼不會上傳";
    }
  }

  async function detectRuntime() {
    try {
      const response = await fetch("api/health", {
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      RUNTIME.backend = response.ok;
    } catch {
      RUNTIME.backend = false;
    }
    updateRuntimeBadge(RUNTIME.backend ? "backend" : "static");
  }

  async function translateWithBackend(payload) {
    const response = await fetch("api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify(payload),
    });

    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("伺服器回應格式錯誤。");
    }

    if (!response.ok) {
      const error = new Error(data.error || "翻譯失敗。");
      error.userMessage = true;
      throw error;
    }
    return data;
  }

  function translateInBrowser(payload) {
    if (!window.VMTranslator) {
      throw new Error("翻譯器未載入，請重新整理頁面。");
    }
    try {
      return window.VMTranslator.translateProject(
        payload.files,
        payload.mode,
        payload.projectName
      );
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : "翻譯失敗。");
    }
  }

  function lineClass(line) {
    const trimmed = line.trim();
    if (!trimmed) return "";
    if (trimmed.startsWith("//")) return "tok-comment";
    if (trimmed.startsWith("@")) return "tok-a";
    if (trimmed.startsWith("(") && trimmed.endsWith(")")) return "tok-label";
    return "tok-c";
  }

  function renderAssembly(asm) {
    const lines = asm.replace(/\n$/, "").split("\n");
    const fragment = document.createDocumentFragment();

    for (const line of lines) {
      const row = document.createElement("span");
      row.className = "code-line";

      const token = document.createElement("span");
      token.className = lineClass(line);
      token.textContent = line || " ";
      row.append(token);
      fragment.append(row);
    }

    elements.assemblyCode.replaceChildren(fragment);
    elements.lineNumbers.textContent = lines
      .map((_, index) => String(index + 1))
      .join("\n");
    elements.lineNumbers.hidden = false;
    elements.lineNumbers.scrollTop = 0;
    elements.editorScroll.scrollTop = 0;
    elements.editorScroll.scrollLeft = 0;
  }

  function refreshUi() {
    const files = Array.from(state.files.values()).sort((a, b) =>
      a.name.localeCompare(b.name, undefined, { sensitivity: "base" })
    );
    const totalBytes = files.reduce((sum, item) => sum + item.size, 0);

    elements.fileList.replaceChildren();
    for (const item of files) {
      const row = document.createElement("li");
      row.className = "file-item";

      const badge = document.createElement("span");
      badge.className = "file-type";
      badge.textContent = "VM";

      const details = document.createElement("div");
      details.className = "file-details";

      const name = document.createElement("div");
      name.className = "file-name";
      name.textContent = item.name;
      name.title = item.path || item.name;

      const size = document.createElement("div");
      size.className = "file-size";
      size.textContent = formatBytes(item.size);

      details.append(name, size);

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "file-remove";
      remove.setAttribute("aria-label", "移除 " + item.name);
      remove.title = "移除";
      remove.textContent = "×";
      remove.addEventListener("click", () => removeFile(item.name));

      row.append(badge, details, remove);
      elements.fileList.append(row);
    }

    elements.emptyFiles.hidden = files.length > 0;
    elements.fileTotal.textContent =
      files.length + " 個檔案" + (files.length ? " · " + formatBytes(totalBytes) : "");
    elements.clearBtn.disabled = files.length === 0 || state.loading;
    elements.projectNameRow.hidden = currentMode() !== "project";

    const invalidSingle = currentMode() === "single" && files.length > 1;
    elements.translateBtn.disabled = files.length === 0 || invalidSingle || state.loading;
    elements.translateBtn.classList.toggle("loading", state.loading);
    elements.editor.classList.toggle("is-loading", state.loading);
    elements.translateBtn.querySelector(".button-label").textContent = state.loading
      ? "翻譯中…"
      : "翻譯成 Hack Assembly";

    if (invalidSingle) {
      setStatus("單一檔案模式只能放入一個 .vm 檔。", "error");
    } else if (state.outputStale && state.asm) {
      setStatus("檔案已變更，請重新翻譯。", "");
    }
  }

  function markOutputStale() {
    if (!state.asm) return;
    state.outputStale = true;
    refreshUi();
  }

  function clearOutput() {
    state.asm = "";
    state.outputName = "";
    state.outputStale = false;
    elements.assemblyCode.replaceChildren();
    elements.assemblyOutput.hidden = true;
    elements.placeholder.hidden = false;
    elements.lineNumbers.textContent = "";
    elements.lineNumbers.hidden = true;
    elements.editorFileName.textContent = "untitled.asm";
    elements.outputName.textContent = "等待翻譯";
    elements.bootstrapTag.hidden = true;
    elements.meta.textContent = "";
    elements.copyBtn.disabled = true;
    elements.downloadBtn.disabled = true;
    setStatus("");
  }

  function removeFile(name) {
    state.files.delete(name.toLocaleLowerCase());
    markOutputStale();
    refreshUi();
  }

  function inferProjectName(items) {
    const firstPath = items.find((item) => item.path && item.path.includes("/"))?.path;
    if (!firstPath) return null;
    const firstPart = firstPath.split("/")[0].trim();
    return firstPart && firstPart !== "." ? firstPart : null;
  }

  async function addFileItems(items, options = {}) {
    if (!items.length) return;

    let added = 0;
    const skipped = [];

    for (const item of items) {
      const file = item.file;
      const key = file.name.toLocaleLowerCase();

      if (!file.name.toLowerCase().endsWith(".vm")) {
        skipped.push(file.name + "（不是 .vm）");
        continue;
      }
      if (file.size > MAX_FILE_BYTES) {
        skipped.push(file.name + "（檔案太大）");
        continue;
      }
      if (state.files.has(key)) {
        skipped.push(file.name + "（檔名重複）");
        continue;
      }

      let content;
      try {
        content = await file.text();
      } catch {
        skipped.push(file.name + "（讀取失敗）");
        continue;
      }

      state.files.set(key, {
        name: file.name,
        path: item.path || file.webkitRelativePath || file.name,
        content,
        size: file.size,
      });
      added += 1;
    }

    if (added > 0 && state.files.size > 1) {
      setMode("project");
    }

    if (options.suggestProjectName && currentMode() === "project") {
      const inferred = inferProjectName(items);
      if (inferred && elements.projectName.value.trim() === "Program") {
        elements.projectName.value = inferred;
      }
    }

    if (added > 0) {
      markOutputStale();
      showToast("已加入 " + added + " 個檔案。");
    }
    if (skipped.length) {
      showToast("略過：" + skipped.slice(0, 2).join("、"), "error");
    }

    refreshUi();
  }

  function loadExample() {
    state.files.clear();
    const items = EXAMPLES.map((example) => ({
      file: new File([example.content], example.name, { type: "text/plain" }),
      path: "Demo/" + example.name,
    }));
    elements.projectName.value = "Demo";
    setMode("project");
    void addFileItems(items).then(() => {
      elements.projectName.value = "Demo";
      setMode("project");
      setStatus("範例已載入，按「翻譯成 Hack Assembly」查看結果。", "");
    });
  }

  function readDirectoryEntries(reader) {
    return new Promise((resolve) => {
      const all = [];
      const readBatch = () => {
        reader.readEntries(
          (entries) => {
            if (!entries.length) {
              resolve(all);
              return;
            }
            all.push(...entries);
            readBatch();
          },
          () => resolve(all)
        );
      };
      readBatch();
    });
  }

  async function collectEntry(entry, parentPath = "") {
    const path = parentPath + entry.name;

    if (entry.isFile) {
      const file = await new Promise((resolve) => {
        entry.file(
          (value) => resolve(value),
          () => resolve(null)
        );
      });
      return file ? [{ file, path }] : [];
    }

    if (entry.isDirectory) {
      const reader = entry.createReader();
      const entries = await readDirectoryEntries(reader);
      const groups = await Promise.all(
        entries.map((child) => collectEntry(child, path + "/"))
      );
      return groups.flat();
    }

    return [];
  }

  async function collectDroppedItems(dataTransfer) {
    const entries = [];
    if (dataTransfer.items && dataTransfer.items.length) {
      for (const item of dataTransfer.items) {
        if (item.kind !== "file") continue;
        const entry = item.webkitGetAsEntry?.();
        if (entry) entries.push(entry);
      }
    }

    if (entries.length) {
      const groups = await Promise.all(entries.map((entry) => collectEntry(entry)));
      return groups.flat();
    }

    return Array.from(dataTransfer.files).map((file) => ({
      file,
      path: file.name,
    }));
  }

  async function translate() {
    if (state.loading) return;

    const files = Array.from(state.files.values());
    const mode = currentMode();

    if (!files.length) {
      showToast("請先加入 .vm 檔案。", "error");
      return;
    }
    if (mode === "single" && files.length !== 1) {
      showToast("單一檔案模式只能有一個 .vm 檔。", "error");
      refreshUi();
      return;
    }

    state.loading = true;
    state.outputStale = false;
    setStatus("正在翻譯…", "");
    refreshUi();

    try {
      const payload = {
        mode,
        projectName: elements.projectName.value.trim() || "Program",
        files: files.map((file) => ({
          name: file.name,
          content: file.content,
        })),
      };

      let data = null;

      if (RUNTIME.backend) {
        try {
          data = await translateWithBackend(payload);
        } catch (error) {
          if (error && error.userMessage) throw error;
          // Backend disappeared (static hosting or server stopped): use JS.
          RUNTIME.backend = false;
          updateRuntimeBadge("static");
        }
      }

      if (!data) {
        data = translateInBrowser(payload);
      }

      state.asm = data.asm;
      state.outputName = data.fileName;
      state.outputStale = false;

      renderAssembly(data.asm);
      elements.assemblyOutput.hidden = false;
      elements.placeholder.hidden = true;
      elements.outputName.textContent = data.fileName;
      elements.editorFileName.textContent = data.fileName;
      elements.bootstrapTag.hidden = !data.bootstrap;
      elements.copyBtn.disabled = false;
      elements.downloadBtn.disabled = false;
      elements.meta.textContent =
        data.fileCount +
        " VM FILE" +
        (data.fileCount === 1 ? "" : "S") +
        "  /  " +
        data.lineCount.toLocaleString("zh-TW") +
        " LINES  /  " +
        (data.bootstrap ? "BOOTSTRAP ON" : "BOOTSTRAP OFF");

      setStatus("翻譯完成。", "success");
      showToast("已產生 " + data.fileName);
    } catch (error) {
      const message = error instanceof Error ? error.message : "翻譯失敗。";
      setStatus(message, "error");
      showToast(message, "error");
    } finally {
      state.loading = false;
      refreshUi();
    }
  }

  async function copyAssembly() {
    if (!state.asm) return;
    try {
      await navigator.clipboard.writeText(state.asm);
      showToast("組譯碼已複製。");
    } catch {
      const helper = document.createElement("textarea");
      helper.value = state.asm;
      helper.style.position = "fixed";
      helper.style.opacity = "0";
      document.body.append(helper);
      helper.select();
      const ok = document.execCommand("copy");
      helper.remove();
      showToast(ok ? "組譯碼已複製。" : "複製失敗。", ok ? "" : "error");
    }
  }

  function downloadAssembly() {
    if (!state.asm || !state.outputName) return;
    const blob = new Blob([state.asm], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = state.outputName;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  elements.editorScroll.addEventListener("scroll", () => {
    elements.lineNumbers.scrollTop = elements.editorScroll.scrollTop;
  });

  elements.modeInputs.forEach((input) => {
    input.addEventListener("change", () => {
      elements.projectNameRow.hidden = currentMode() !== "project";
      markOutputStale();
      refreshUi();
    });
  });

  elements.projectName.addEventListener("input", markOutputStale);

  elements.chooseFiles.addEventListener("click", (event) => {
    event.stopPropagation();
    elements.fileInput.click();
  });

  elements.chooseFolder.addEventListener("click", (event) => {
    event.stopPropagation();
    elements.folderInput.click();
  });

  elements.fileInput.addEventListener("change", () => {
    const items = Array.from(elements.fileInput.files).map((file) => ({
      file,
      path: file.webkitRelativePath || file.name,
    }));
    elements.fileInput.value = "";
    void addFileItems(items);
  });

  elements.folderInput.addEventListener("change", () => {
    const items = Array.from(elements.folderInput.files).map((file) => ({
      file,
      path: file.webkitRelativePath || file.name,
    }));
    elements.folderInput.value = "";
    if (items.length > 1 || items.some((item) => item.path.includes("/"))) {
      setMode("project");
    }
    void addFileItems(items, { suggestProjectName: true });
  });

  elements.dropZone.addEventListener("click", (event) => {
    if (event.target.closest("button")) return;
    elements.fileInput.click();
  });

  elements.dropZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      elements.fileInput.click();
    }
  });

  for (const eventName of ["dragenter", "dragover"]) {
    elements.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      event.stopPropagation();
      elements.dropZone.classList.add("drag-over");
    });
  }

  for (const eventName of ["dragleave", "drop"]) {
    elements.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      event.stopPropagation();
      elements.dropZone.classList.remove("drag-over");
    });
  }

  elements.dropZone.addEventListener("drop", async (event) => {
    if (!event.dataTransfer) return;
    const items = await collectDroppedItems(event.dataTransfer);
    if (!items.length) {
      showToast("沒有找到可加入的檔案。", "error");
      return;
    }
    const hasFolder = items.some((item) => item.path.includes("/"));
    if (hasFolder || items.length > 1) setMode("project");
    await addFileItems(items, { suggestProjectName: hasFolder });
  });

  elements.exampleBtn.addEventListener("click", loadExample);

  elements.clearBtn.addEventListener("click", () => {
    state.files.clear();
    clearOutput();
    refreshUi();
  });

  elements.translateBtn.addEventListener("click", () => void translate());
  elements.copyBtn.addEventListener("click", () => void copyAssembly());
  elements.downloadBtn.addEventListener("click", downloadAssembly);

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      if (!elements.translateBtn.disabled) void translate();
    }
  });

  refreshUi();
  void detectRuntime();
})();
