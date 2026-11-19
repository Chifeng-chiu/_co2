/*
 * Nand2Tetris Chapter 7 & 8 VM translator, browser / static-hosting port.
 *
 * This is a faithful JavaScript port of parser.py + code_writer.py +
 * translate_project() in web_demo.py, so the page can run on GitHub Pages
 * (or even from file://) without a Python backend.
 *
 * It produces byte-identical assembly to the Python implementation.
 */
(function (global) {
  "use strict";

  const ARITHMETIC_COMMANDS = new Set([
    "add",
    "sub",
    "neg",
    "eq",
    "gt",
    "lt",
    "and",
    "or",
    "not",
  ]);

  const COMMAND_TYPES = {
    push: "C_PUSH",
    pop: "C_POP",
    label: "C_LABEL",
    goto: "C_GOTO",
    "if-goto": "C_IF",
    function: "C_FUNCTION",
    return: "C_RETURN",
    call: "C_CALL",
  };

  const SEGMENT_POINTERS = {
    local: "LCL",
    argument: "ARG",
    this: "THIS",
    that: "THAT",
  };

  const MAX_SOURCE_CHARS = 4 * 1024 * 1024;

  class TranslationError extends Error {
    constructor(message) {
      super(message);
      this.name = "TranslationError";
    }
  }

  class Parser {
    constructor(text) {
      this._commands = [];
      this._currentIndex = -1;
      this._currentCommand = null;

      const source = String(text == null ? "" : text).replace(/^\uFEFF/, "");
      for (const rawLine of source.split(/\r\n|\r|\n/)) {
        const line = rawLine.split("//")[0].trim();
        if (line) this._commands.push(line);
      }
    }

    hasMoreLines() {
      return this._currentIndex + 1 < this._commands.length;
    }

    advance() {
      if (!this.hasMoreLines()) {
        throw new Error("No more VM commands.");
      }
      this._currentIndex += 1;
      this._currentCommand = this._commands[this._currentIndex];
    }

    _tokens() {
      if (this._currentCommand === null) {
        throw new Error("advance() must be called before reading a command.");
      }
      return this._currentCommand.split(/\s+/);
    }

    commandType() {
      const first = this._tokens()[0];

      if (ARITHMETIC_COMMANDS.has(first)) {
        return "C_ARITHMETIC";
      }
      if (Object.prototype.hasOwnProperty.call(COMMAND_TYPES, first)) {
        return COMMAND_TYPES[first];
      }
      throw new TranslationError(
        "未知的 VM 指令：" + this._currentCommand
      );
    }

    arg1() {
      const tokens = this._tokens();
      if (this.commandType() === "C_ARITHMETIC") {
        return tokens[0];
      }
      if (this.commandType() === "C_RETURN") {
        throw new TranslationError("return 指令沒有參數。");
      }
      if (tokens.length < 2) {
        throw new TranslationError("指令缺少參數：" + this._currentCommand);
      }
      return tokens[1];
    }

    arg2() {
      const tokens = this._tokens();
      if (tokens.length < 3) {
        throw new TranslationError("指令缺少第二個參數：" + this._currentCommand);
      }
      const value = Number(tokens[2]);
      if (!Number.isInteger(value)) {
        throw new TranslationError(
          "第二個參數必須是整數：" + tokens[2]
        );
      }
      return value;
    }
  }

  class CodeWriter {
    constructor() {
      this.lines = [];
      this.fileName = "Unknown";
      this.currentFunction = "";
      this.comparisonCounter = 0;
      this.returnLabelCounters = new Map();
    }

    setFileName(fileName) {
      const base = String(fileName).split(/[\\/]/).pop();
      const dot = base.lastIndexOf(".");
      this.fileName = dot > 0 ? base.slice(0, dot) : base;
      this.currentFunction = "";
    }

    writeInit() {
      this._write("// bootstrap");
      this._write("@256", "D=A", "@SP", "M=D");
      this.writeCall("Sys.init", 0);
    }

    writeArithmetic(command) {
      this._write("// " + command);

      if (command === "add" || command === "sub" || command === "and" || command === "or") {
        this._write("@SP", "AM=M-1", "D=M", "A=A-1");
        if (command === "add") {
          this._write("M=D+M");
        } else if (command === "sub") {
          this._write("M=M-D");
        } else if (command === "and") {
          this._write("M=D&M");
        } else {
          this._write("M=D|M");
        }
        return;
      }

      if (command === "neg" || command === "not") {
        this._write("@SP", "A=M-1");
        this._write(command === "neg" ? "M=-M" : "M=!M");
        return;
      }

      if (command === "eq" || command === "gt" || command === "lt") {
        this.comparisonCounter += 1;
        const trueLabel = "COMP_TRUE_" + this.comparisonCounter;
        const endLabel = "COMP_END_" + this.comparisonCounter;

        this._write("@SP", "AM=M-1", "D=M", "A=A-1", "D=M-D", "@" + trueLabel);
        if (command === "eq") {
          this._write("D;JEQ");
        } else if (command === "gt") {
          this._write("D;JGT");
        } else {
          this._write("D;JLT");
        }

        this._write(
          "@SP",
          "A=M-1",
          "M=0",
          "@" + endLabel,
          "0;JMP",
          "(" + trueLabel + ")",
          "@SP",
          "A=M-1",
          "M=-1",
          "(" + endLabel + ")"
        );
        return;
      }

      throw new TranslationError("未知的算術指令：" + command);
    }

    writePushPop(command, segment, index) {
      this._write("// " + command + " " + segment + " " + index);
      if (command === "push") {
        this._writePush(segment, index);
      } else if (command === "pop") {
        this._writePop(segment, index);
      } else {
        throw new TranslationError("未知的堆疊指令：" + command);
      }
    }

    _writePush(segment, index) {
      if (segment === "constant") {
        this._write(
          "@" + index,
          "D=A",
          "@SP",
          "A=M",
          "M=D",
          "@SP",
          "M=M+1"
        );
        return;
      }

      if (Object.prototype.hasOwnProperty.call(SEGMENT_POINTERS, segment)) {
        this._write(
          "@" + index,
          "D=A",
          "@" + SEGMENT_POINTERS[segment],
          "A=D+M",
          "D=M",
          "@SP",
          "A=M",
          "M=D",
          "@SP",
          "M=M+1"
        );
        return;
      }

      if (segment === "temp") {
        checkTempIndex(index);
        this._write(
          "@" + (5 + index),
          "D=M",
          "@SP",
          "A=M",
          "M=D",
          "@SP",
          "M=M+1"
        );
        return;
      }

      if (segment === "pointer") {
        this._write(
          "@" + pointerRegister(index),
          "D=M",
          "@SP",
          "A=M",
          "M=D",
          "@SP",
          "M=M+1"
        );
        return;
      }

      if (segment === "static") {
        this._write(
          "@" + this._staticSymbol(index),
          "D=M",
          "@SP",
          "A=M",
          "M=D",
          "@SP",
          "M=M+1"
        );
        return;
      }

      throw new TranslationError("未知的記憶體區段：" + segment);
    }

    _writePop(segment, index) {
      if (segment === "constant") {
        throw new TranslationError("pop constant 不是合法的 VM 指令。");
      }

      if (Object.prototype.hasOwnProperty.call(SEGMENT_POINTERS, segment)) {
        this._write(
          "@" + index,
          "D=A",
          "@" + SEGMENT_POINTERS[segment],
          "D=D+M",
          "@R13",
          "M=D",
          "@SP",
          "AM=M-1",
          "D=M",
          "@R13",
          "A=M",
          "M=D"
        );
        return;
      }

      if (segment === "temp") {
        checkTempIndex(index);
        this._write("@SP", "AM=M-1", "D=M", "@" + (5 + index), "M=D");
        return;
      }

      if (segment === "pointer") {
        this._write(
          "@SP",
          "AM=M-1",
          "D=M",
          "@" + pointerRegister(index),
          "M=D"
        );
        return;
      }

      if (segment === "static") {
        this._write(
          "@SP",
          "AM=M-1",
          "D=M",
          "@" + this._staticSymbol(index),
          "M=D"
        );
        return;
      }

      throw new TranslationError("未知的記憶體區段：" + segment);
    }

    writeLabel(label) {
      this._write("// label " + label);
      this._write("(" + this._scopedLabel(label) + ")");
    }

    writeGoto(label) {
      this._write("// goto " + label);
      this._write("@" + this._scopedLabel(label), "0;JMP");
    }

    writeIf(label) {
      this._write("// if-goto " + label);
      this._write(
        "@SP",
        "AM=M-1",
        "D=M",
        "@" + this._scopedLabel(label),
        "D;JNE"
      );
    }

    writeFunction(functionName, nVars) {
      this._write("// function " + functionName + " " + nVars);
      this.currentFunction = functionName;
      if (!this.returnLabelCounters.has(functionName)) {
        this.returnLabelCounters.set(functionName, 0);
      }

      this._write("(" + functionName + ")");
      for (let i = 0; i < nVars; i += 1) {
        this._write("@SP", "A=M", "M=0", "@SP", "M=M+1");
      }
    }

    writeCall(functionName, nArgs) {
      this._write("// call " + functionName + " " + nArgs);
      const returnLabel = this._newReturnLabel();

      this._write(
        "@" + returnLabel,
        "D=A",
        "@SP",
        "A=M",
        "M=D",
        "@SP",
        "M=M+1"
      );

      for (const register of ["LCL", "ARG", "THIS", "THAT"]) {
        this._write(
          "@" + register,
          "D=M",
          "@SP",
          "A=M",
          "M=D",
          "@SP",
          "M=M+1"
        );
      }

      this._write(
        "@SP",
        "D=M",
        "@5",
        "D=D-A",
        "@" + nArgs,
        "D=D-A",
        "@ARG",
        "M=D",
        "@SP",
        "D=M",
        "@LCL",
        "M=D"
      );

      this._write("@" + functionName, "0;JMP", "(" + returnLabel + ")");
    }

    writeReturn() {
      this._write("// return");

      this._write("@LCL", "D=M", "@R13", "M=D");

      this._write("@5", "A=D-A", "D=M", "@R14", "M=D");

      this._write("@SP", "AM=M-1", "D=M", "@ARG", "A=M", "M=D");

      this._write("@ARG", "D=M", "@SP", "M=D+1");

      for (const [offset, register] of [
        [1, "THAT"],
        [2, "THIS"],
        [3, "ARG"],
        [4, "LCL"],
      ]) {
        this._write(
          "@R13",
          "D=M",
          "@" + offset,
          "A=D-A",
          "D=M",
          "@" + register,
          "M=D"
        );
      }

      this._write("@R14", "A=M", "0;JMP");
    }

    _scopedLabel(label) {
      if (this.currentFunction) {
        return this.currentFunction + "$" + label;
      }
      return label;
    }

    _newReturnLabel() {
      const base = this.currentFunction || "GLOBAL";
      const index = this.returnLabelCounters.get(base) || 0;
      this.returnLabelCounters.set(base, index + 1);
      return base + "$ret." + index;
    }

    _staticSymbol(index) {
      return this.fileName + "." + index;
    }

    _write(...items) {
      for (const item of items) {
        this.lines.push(item);
      }
    }
  }

  function checkTempIndex(index) {
    if (!(index >= 0 && index <= 7)) {
      throw new TranslationError("temp 索引必須介於 0 到 7。");
    }
  }

  function pointerRegister(index) {
    if (index === 0) return "THIS";
    if (index === 1) return "THAT";
    throw new TranslationError("pointer 索引必須是 0 或 1。");
  }

  function translateCommands(parser, writer) {
    while (parser.hasMoreLines()) {
      parser.advance();
      const commandType = parser.commandType();

      if (commandType === "C_ARITHMETIC") {
        writer.writeArithmetic(parser.arg1());
      } else if (commandType === "C_PUSH") {
        writer.writePushPop("push", parser.arg1(), parser.arg2());
      } else if (commandType === "C_POP") {
        writer.writePushPop("pop", parser.arg1(), parser.arg2());
      } else if (commandType === "C_LABEL") {
        writer.writeLabel(parser.arg1());
      } else if (commandType === "C_GOTO") {
        writer.writeGoto(parser.arg1());
      } else if (commandType === "C_IF") {
        writer.writeIf(parser.arg1());
      } else if (commandType === "C_FUNCTION") {
        writer.writeFunction(parser.arg1(), parser.arg2());
      } else if (commandType === "C_CALL") {
        writer.writeCall(parser.arg1(), parser.arg2());
      } else if (commandType === "C_RETURN") {
        writer.writeReturn();
      } else {
        throw new TranslationError("不支援的指令類型：" + commandType);
      }
    }
  }

  function safeVmName(name) {
    const raw = String(name == null ? "" : name).replace(/\\/g, "/");
    const parts = raw.split("/");
    const base = parts[parts.length - 1].trim();
    const lower = base.toLowerCase();

    if (!lower.endsWith(".vm") || lower === ".vm") {
      throw new TranslationError("只接受 .vm 檔案：" + (base || "(空白檔名)"));
    }
    if (base.length > 120) {
      throw new TranslationError("檔名太長：" + base);
    }

    const safe = base.replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_");
    if (!safe || safe === "." || safe === "..") {
      throw new TranslationError("無效的檔名。");
    }
    return safe;
  }

  function safeProjectStem(name) {
    const raw = String(name == null ? "" : name).replace(/\\/g, "/");
    const parts = raw.split("/");
    const base = parts[parts.length - 1].trim();
    const dot = base.lastIndexOf(".");
    const stem = dot > 0 ? base.slice(0, dot) : base;
    const cleaned = stem
      .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
      .replace(/^[ .]+/, "")
      .replace(/[ .]+$/, "");
    return cleaned || "Program";
  }

  function translateProject(files, mode, projectName) {
    const resolvedMode = mode || "single";
    const resolvedName = projectName || "Program";

    if (resolvedMode !== "single" && resolvedMode !== "project") {
      throw new TranslationError("mode 必須是 single 或 project。");
    }
    if (!Array.isArray(files) || files.length === 0) {
      throw new TranslationError("請先加入至少一個 .vm 檔案。");
    }

    const normalized = [];
    const seen = new Set();
    let totalChars = 0;

    for (const item of files) {
      if (!item || typeof item !== "object") {
        throw new TranslationError("檔案資料格式錯誤。");
      }
      const name = safeVmName(item.name);
      if (typeof item.content !== "string") {
        throw new TranslationError(name + " 的內容不是文字檔。");
      }

      totalChars += item.content.length;
      if (totalChars > MAX_SOURCE_CHARS) {
        throw new TranslationError("上傳內容過大。");
      }

      const key = name.toLowerCase();
      if (seen.has(key)) {
        throw new TranslationError("檔名重複：" + name);
      }
      seen.add(key);
      normalized.push({ name: name, content: item.content });
    }

    if (resolvedMode === "single" && normalized.length !== 1) {
      throw new TranslationError("單一檔案模式只能放入一個 .vm 檔。");
    }

    let bootstrap;
    let outputName;

    if (resolvedMode === "project") {
      normalized.sort((a, b) =>
        a.name.toLowerCase() < b.name.toLowerCase()
          ? -1
          : a.name.toLowerCase() > b.name.toLowerCase()
          ? 1
          : 0
      );
      bootstrap = normalized.some((item) => item.name.toLowerCase() === "sys.vm");
      outputName = safeProjectStem(resolvedName) + ".asm";
    } else {
      bootstrap = false;
      const dot = normalized[0].name.lastIndexOf(".");
      outputName = (dot > 0 ? normalized[0].name.slice(0, dot) : normalized[0].name) + ".asm";
    }

    const writer = new CodeWriter();
    if (bootstrap) {
      writer.writeInit();
    }

    for (const item of normalized) {
      writer.setFileName(item.name);
      translateCommands(new Parser(item.content), writer);
    }

    const asm = writer.lines.map((line) => line + "\n").join("");

    return {
      asm: asm,
      fileName: outputName,
      bootstrap: bootstrap,
      fileCount: normalized.length,
      lineCount: writer.lines.length,
    };
  }

  const api = {
    Parser: Parser,
    CodeWriter: CodeWriter,
    TranslationError: TranslationError,
    translateCommands: translateCommands,
    translateProject: translateProject,
  };

  global.VMTranslator = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
