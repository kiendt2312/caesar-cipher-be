"use strict";

const byId = (id) => document.getElementById(id);
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const MAX_FILE_BYTES = Number(document.body.dataset.maxBytes);
const REQUEST_TIMEOUT_MS = 15000;
const KEY_PATTERN = /^[+-]?[0-9]+$/;
const MESSAGES = {
  fileType: document.body.dataset.messageFileType,
  fileSize: document.body.dataset.messageFileSize,
  fileEmpty: document.body.dataset.messageFileEmpty,
  keyMissing: document.body.dataset.messageKeyMissing,
  keyInvalid: document.body.dataset.messageKeyInvalid,
  system: document.body.dataset.messageSystem,
};

const elements = {
  modeEncrypt: byId("modeEncrypt"),
  modeDecrypt: byId("modeDecrypt"),
  helperText: byId("helperText"),
  typeText: byId("typeText"),
  typeFile: byId("typeFile"),
  inputTitle: byId("inputTitle"),
  outputTitle: byId("outputTitle"),
  textWrap: byId("textWrap"),
  fileWrap: byId("fileWrap"),
  textInput: byId("textInput"),
  inputHighlight: byId("inputHighlight"),
  fileInput: byId("fileInput"),
  dropZone: byId("dropZone"),
  fileCard: byId("fileCard"),
  fileName: byId("fileName"),
  fileSize: byId("fileSize"),
  filePreview: byId("filePreview"),
  inputStatus: byId("inputStatus"),
  keyInput: byId("keyInput"),
  keyStatus: byId("keyStatus"),
  normalizedKey: byId("normalizedKey"),
  outputStatus: byId("outputStatus"),
  result: byId("result"),
  analysis: byId("analysis"),
  actionButton: byId("actionButton"),
  copyInput: byId("copyInput"),
  copyKey: byId("copyKey"),
  copyOutput: byId("copyOutput"),
  clearOutput: byId("clearOutput"),
  downloadOutput: byId("downloadOutput"),
  notice: byId("notice"),
  noticeTitle: byId("noticeTitle"),
  noticeMessage: byId("noticeMessage"),
  shiftTitle: byId("shiftTitle"),
  sourceAlphabet: byId("sourceAlphabet"),
  shiftedAlphabet: byId("shiftedAlphabet"),
  sourceLabel: byId("sourceLabel"),
  shiftedLabel: byId("shiftedLabel"),
};

const state = {
  mode: "encrypt",
  inputType: "text",
  file: null,
  fileText: "",
  result: null,
  view: "result",
  loading: false,
  requestVersion: 0,
  fileReadVersion: 0,
};

const escapeHtml = (value) => String(value).replace(
  /[&<>"]/g,
  (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character],
);

function colorize(text) {
  let result = "";
  let group = "";
  let buffer = "";
  const flush = () => {
    if (buffer !== "") {
      result += `<span class="${group}">${escapeHtml(buffer)}</span>`;
      buffer = "";
    }
  };
  for (const character of text) {
    const code = character.charCodeAt(0);
    const nextGroup = code >= 65 && code <= 90
      ? "char-upper"
      : code >= 97 && code <= 122
        ? "char-lower"
        : "char-other";
    if (nextGroup !== group) {
      flush();
      group = nextGroup;
    }
    buffer += character;
  }
  flush();
  return result;
}

function setStatus(element, text, kind = "neutral") {
  element.className = `status-bar${kind === "neutral" ? "" : ` ${kind}`}`;
  element.querySelector(".status-icon").textContent = kind === "valid" ? "✓" : kind === "error" ? "!" : "·";
  element.querySelector("span:last-child").textContent = text;
}

function showNotice(kind, title, message = "") {
  elements.notice.className = `notice ${kind}`;
  elements.notice.hidden = false;
  elements.noticeTitle.textContent = title;
  elements.noticeMessage.textContent = message;
}

function hideNotice() {
  elements.notice.hidden = true;
  elements.noticeTitle.textContent = "";
  elements.noticeMessage.textContent = "";
}

function currentInputText() {
  return state.inputType === "text" ? elements.textInput.value : state.fileText;
}

function parseKey() {
  const raw = elements.keyInput.value.trim();
  if (raw === "") {
    return { valid: false, missing: true, raw };
  }
  if ((state.inputType === "file" && raw.length > 32) || !KEY_PATTERN.test(raw)) {
    return { valid: false, missing: false, raw };
  }
  try {
    return { valid: true, raw, value: BigInt(raw) };
  } catch (error) {
    return { valid: false, missing: false, raw, error };
  }
}

function normalizedKey(parsed = parseKey()) {
  if (!parsed.valid) return null;
  return Number(((parsed.value % 26n) + 26n) % 26n);
}

function shiftAlphabet(key, operation) {
  // Display-only mapping for the alphabet table; server responses remain authoritative.
  const direction = operation === "encrypt" ? 1 : -1;
  return [...ALPHABET].map((_, index) => ALPHABET[(index + direction * key + 26) % 26]);
}

const sourceCells = [];
const shiftedCells = [];
for (const letter of ALPHABET) {
  const sourceCell = document.createElement("span");
  sourceCell.textContent = letter;
  elements.sourceAlphabet.appendChild(sourceCell);
  sourceCells.push(sourceCell);

  const shiftedCell = document.createElement("span");
  elements.shiftedAlphabet.appendChild(shiftedCell);
  shiftedCells.push(shiftedCell);
}

function renderShiftTable() {
  const key = normalizedKey() ?? 0;
  const shifted = shiftAlphabet(key, state.mode);
  const used = new Set(
    [...currentInputText()]
      .filter((letter) => /^[A-Za-z]$/.test(letter))
      .map((letter) => letter.toUpperCase()),
  );
  for (let index = 0; index < ALPHABET.length; index += 1) {
    shiftedCells[index].textContent = shifted[index];
    sourceCells[index].classList.toggle("used", used.has(ALPHABET[index]));
    shiftedCells[index].classList.toggle("used", used.has(ALPHABET[index]));
  }
  const encrypting = state.mode === "encrypt";
  elements.sourceLabel.textContent = encrypting ? "Bản rõ" : "Bản mã";
  elements.shiftedLabel.textContent = encrypting ? "Bản mã" : "Bản rõ";
  elements.shiftTitle.textContent = `Khóa ${key} · A → ${shifted[0]}`;
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} byte`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MiB`;
}

function validateInput() {
  if (state.inputType === "text") {
    const text = elements.textInput.value;
    if (text.length === 0) {
      setStatus(elements.inputStatus, "Chưa có dữ liệu");
      return false;
    }
    const lineCount = text.split(/\r\n|\r|\n/).length;
    setStatus(elements.inputStatus, `Văn bản hợp lệ · ${text.length} ký tự · ${lineCount} dòng`, "valid");
    return true;
  }

  if (state.file === null) {
    setStatus(elements.inputStatus, "Chưa chọn file");
    return false;
  }
  if (!/\.txt$/i.test(state.file.name)) {
    setStatus(elements.inputStatus, MESSAGES.fileType, "error");
    return false;
  }
  if (state.file.size > MAX_FILE_BYTES) {
    setStatus(elements.inputStatus, MESSAGES.fileSize, "error");
    return false;
  }
  if (state.file.size === 0) {
    setStatus(elements.inputStatus, MESSAGES.fileEmpty, "error");
    return false;
  }
  setStatus(elements.inputStatus, `File .txt hợp lệ · ${formatSize(state.file.size)}`, "valid");
  return true;
}

function validateKey() {
  const parsed = parseKey();
  if (!parsed.valid) {
    elements.normalizedKey.textContent = "";
    const message = parsed.missing ? MESSAGES.keyMissing : MESSAGES.keyInvalid;
    setStatus(elements.keyStatus, message, parsed.missing ? "neutral" : "error");
    return false;
  }
  const normalized = normalizedKey(parsed);
  elements.normalizedKey.textContent = parsed.value === BigInt(normalized) ? "" : `Chuẩn hóa → ${normalized}`;
  setStatus(elements.keyStatus, "Khóa hợp lệ", "valid");
  return true;
}

function clearResult({ keepNotice = false } = {}) {
  state.result = null;
  state.view = "result";
  elements.result.className = "output empty";
  elements.result.textContent = "Kết quả sẽ hiển thị ở đây sau khi xử lý.";
  elements.analysis.replaceChildren();
  setStatus(elements.outputStatus, "Chưa xử lý");
  if (!keepNotice) hideNotice();
}

function render() {
  const encrypting = state.mode === "encrypt";
  const hasResult = state.result !== null;
  const inputValid = validateInput();
  const keyValid = validateKey();

  elements.modeEncrypt.classList.toggle("active", encrypting);
  elements.modeDecrypt.classList.toggle("active", !encrypting);
  elements.modeEncrypt.setAttribute("aria-selected", String(encrypting));
  elements.modeDecrypt.setAttribute("aria-selected", String(!encrypting));
  elements.typeText.setAttribute("aria-pressed", String(state.inputType === "text"));
  elements.typeFile.setAttribute("aria-pressed", String(state.inputType === "file"));
  elements.textWrap.hidden = state.inputType !== "text";
  elements.fileWrap.hidden = state.inputType !== "file";
  elements.inputTitle.textContent = encrypting ? "Bản rõ" : "Bản mã";
  elements.outputTitle.textContent = encrypting ? "Bản mã" : "Bản rõ";
  elements.helperText.textContent = encrypting
    ? "Nhập bản rõ bên dưới để mã hóa bằng hệ mật Caesar."
    : "Nhập bản mã bên dưới để giải mã bằng hệ mật Caesar.";

  elements.inputHighlight.innerHTML = colorize(elements.textInput.value);
  elements.copyInput.disabled = state.loading || currentInputText() === "";
  elements.copyKey.disabled = state.loading || elements.keyInput.value === "";
  elements.copyOutput.disabled = state.loading || !hasResult;
  elements.clearOutput.disabled = state.loading || !hasResult;
  elements.downloadOutput.disabled = state.loading || !hasResult;
  elements.actionButton.disabled = state.loading || !(inputValid && keyValid);
  elements.actionButton.classList.toggle("loading", state.loading);
  elements.actionButton.textContent = state.loading ? "Đang xử lý…" : encrypting ? "Mã hóa" : "Giải mã";

  document.querySelectorAll("[data-lockable]").forEach((control) => {
    control.setAttribute("aria-disabled", String(state.loading));
    control.disabled = state.loading;
  });
  elements.dropZone.tabIndex = state.loading ? -1 : 0;
  if (!state.loading) {
    elements.copyInput.disabled = currentInputText() === "";
    elements.copyKey.disabled = elements.keyInput.value === "";
    elements.copyOutput.disabled = !hasResult;
    elements.clearOutput.disabled = !hasResult;
    elements.downloadOutput.disabled = !hasResult;
    elements.actionButton.disabled = !(inputValid && keyValid);
  }

  elements.result.hidden = state.view !== "result";
  elements.analysis.hidden = state.view !== "analysis";
  document.querySelectorAll("#outputPanel [data-view]").forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.dataset.view === state.view));
  });
  renderShiftTable();
}

function selectMode(mode) {
  state.mode = mode;
  clearResult();
  render();
}

function selectInputType(type) {
  state.inputType = type;
  clearResult();
  setStatus(elements.inputStatus, type === "text" ? "Chưa có dữ liệu" : "Chưa chọn file");
  render();
}

function displaySelectedFile() {
  elements.fileName.textContent = state.file.name;
  elements.fileSize.textContent = formatSize(state.file.size);
  elements.dropZone.hidden = true;
  elements.fileCard.hidden = false;
}

async function setFile(file) {
  const fileReadVersion = state.fileReadVersion + 1;
  state.fileReadVersion = fileReadVersion;
  state.file = file;
  state.fileText = "";
  clearResult();
  displaySelectedFile();
  const preliminarilyValid = /\.txt$/i.test(file.name) && file.size > 0 && file.size <= MAX_FILE_BYTES;
  if (preliminarilyValid) {
    try {
      const fileText = await file.text();
      if (fileReadVersion !== state.fileReadVersion || state.file !== file) return;
      state.fileText = fileText;
    } catch (error) {
      if (fileReadVersion !== state.fileReadVersion || state.file !== file) return;
      showNotice("warning", "Không thể xem trước file", "Máy chủ vẫn sẽ kiểm tra file khi xử lý.");
    }
  }
  if (fileReadVersion !== state.fileReadVersion || state.file !== file) return;
  const preview = state.fileText.length > 12000 ? `${state.fileText.slice(0, 12000)}\n…` : state.fileText;
  elements.filePreview.innerHTML = colorize(preview);
  render();
}

function removeFile() {
  state.fileReadVersion += 1;
  state.file = null;
  state.fileText = "";
  elements.fileInput.value = "";
  elements.filePreview.textContent = "";
  elements.dropZone.hidden = false;
  elements.fileCard.hidden = true;
  clearResult();
  render();
}

async function copyText(text, successTitle) {
  try {
    await navigator.clipboard.writeText(text);
    showNotice("success", successTitle);
  } catch (error) {
    showNotice("warning", "Không thể sao chép", "Trình duyệt đã chặn bộ nhớ tạm; hãy sao chép thủ công.");
  }
}

function addAnalysisRow(term, description) {
  const row = document.createElement("div");
  const label = document.createElement("dt");
  const value = document.createElement("dd");
  label.textContent = term;
  value.textContent = description;
  row.append(label, value);
  elements.analysis.appendChild(row);
}

function showResult(result, source) {
  state.result = result;
  state.view = "result";
  elements.result.className = "output";
  elements.result.innerHTML = colorize(result);
  elements.analysis.replaceChildren();

  let uppercase = 0;
  let lowercase = 0;
  let unchanged = 0;
  for (const character of source) {
    const code = character.charCodeAt(0);
    if (code >= 65 && code <= 90) uppercase += 1;
    else if (code >= 97 && code <= 122) lowercase += 1;
    else unchanged += 1;
  }
  addAnalysisRow("Chế độ", state.mode === "encrypt" ? "Mã hóa" : "Giải mã");
  addAnalysisRow("Nguồn", state.inputType === "text" ? "Văn bản" : `File · ${state.file.name}`);
  addAnalysisRow("Khóa nhập / chuẩn hóa", `${elements.keyInput.value.trim()} / ${normalizedKey()}`);
  addAnalysisRow("Tổng ký tự", String(source.length));
  addAnalysisRow("Chữ hoa dịch chuyển", String(uppercase));
  addAnalysisRow("Chữ thường dịch chuyển", String(lowercase));
  addAnalysisRow("Ký tự giữ nguyên", String(unchanged));
}

async function parseApiResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    const error = new Error(MESSAGES.system);
    error.isApiError = true;
    error.status = response.status;
    throw error;
  }
  let body;
  try {
    body = await response.json();
  } catch (error) {
    const responseError = new Error(MESSAGES.system);
    responseError.isApiError = true;
    responseError.status = response.status;
    throw responseError;
  }
  if (!response.ok || body.success !== true) {
    const apiError = new Error(typeof body.message === "string" ? body.message : MESSAGES.system);
    apiError.isApiError = true;
    apiError.status = response.status;
    throw apiError;
  }
  return body;
}

async function fetchWithTimeout(url, options) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    window.clearTimeout(timeout);
  }
}

const realApi = {
  async text(operation, text, key) {
    const jsonKey = BigInt(key).toString();
    const body = `{"text":${JSON.stringify(text)},"key":${jsonKey}}`;
    const response = await fetchWithTimeout(`/api/caesar/${operation}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return parseApiResponse(response);
  },

  async file(operation, file, key, responseMode) {
    const data = new FormData();
    data.append("file", file);
    data.append("key", key);
    data.append("action", operation);
    data.append("response_mode", responseMode);
    const response = await fetchWithTimeout("/api/caesar/file", { method: "POST", body: data });
    if (responseMode === "content") return parseApiResponse(response);

    const contentType = response.headers.get("content-type") || "";
    if (!response.ok || contentType.toLowerCase().includes("application/json")) {
      return parseApiResponse(response);
    }
    if (!contentType.toLowerCase().startsWith("text/plain")) {
      const error = new Error(MESSAGES.system);
      error.isApiError = true;
      error.status = response.status;
      throw error;
    }
    return {
      blob: await response.blob(),
      disposition: response.headers.get("content-disposition") || "",
    };
  },
};

function textResultFilename() {
  return state.mode === "encrypt" ? "ket-qua.encrypted.txt" : "ket-qua.decrypted.txt";
}

function filenameFromDisposition(disposition) {
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch (error) {
      // Continue to the server-provided ASCII fallback below.
    }
  }
  const quotedMatch = disposition.match(/filename="((?:\\.|[^"])*)"/i);
  return quotedMatch ? quotedMatch[1].replace(/\\([\\"])/g, "$1") : null;
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function processInput() {
  if (elements.actionButton.disabled) return;
  const requestVersion = state.requestVersion + 1;
  state.requestVersion = requestVersion;
  state.loading = true;
  hideNotice();
  clearResult({ keepNotice: true });
  setStatus(elements.outputStatus, "Đang gửi yêu cầu…");
  render();

  const source = currentInputText();
  const key = elements.keyInput.value.trim();
  const actionLabel = state.mode === "encrypt" ? "Mã hóa" : "Giải mã";
  try {
    const response = state.inputType === "text"
      ? await realApi.text(state.mode, elements.textInput.value, key)
      : await realApi.file(state.mode, state.file, key, "content");
    if (requestVersion !== state.requestVersion) return;
    showResult(response.result, source);
    setStatus(elements.outputStatus, `${actionLabel} thành công · ${response.result.length} ký tự`, "valid");
    showNotice("success", `${actionLabel} thành công`, "Kết quả đã sẵn sàng để sao chép hoặc tải xuống.");
  } catch (error) {
    if (requestVersion !== state.requestVersion) return;
    clearResult({ keepNotice: true });
    if (error.isApiError) {
      setStatus(elements.outputStatus, `${actionLabel} thất bại`, "error");
      showNotice("error", `${actionLabel} thất bại`, error.message);
    } else {
      setStatus(elements.outputStatus, "Không thể kết nối tới máy chủ", "error");
      showNotice("error", "Lỗi kết nối", "Không thể gọi máy chủ. Vui lòng thử lại.");
    }
  } finally {
    if (requestVersion === state.requestVersion) {
      state.loading = false;
      render();
    }
  }
}

async function downloadResult() {
  if (state.result === null || state.loading) return;
  state.loading = true;
  render();
  try {
    let filename;
    if (state.inputType === "file") {
      const response = await realApi.file(
        state.mode,
        state.file,
        elements.keyInput.value.trim(),
        "file",
      );
      filename = filenameFromDisposition(response.disposition);
      if (filename === null) {
        const error = new Error(MESSAGES.system);
        error.isApiError = true;
        throw error;
      }
      saveBlob(response.blob, filename);
    } else {
      filename = textResultFilename();
      saveBlob(new Blob([state.result], { type: "text/plain;charset=utf-8" }), filename);
    }
    showNotice("success", "Đã tạo file tải xuống", filename);
  } catch (error) {
    clearResult({ keepNotice: true });
    const message = error.isApiError ? error.message : "Không thể tải kết quả. Vui lòng thử lại.";
    setStatus(elements.outputStatus, "Tải kết quả thất bại", "error");
    showNotice("error", "Tải kết quả thất bại", message);
  } finally {
    state.loading = false;
    render();
  }
}

function resetAll() {
  state.requestVersion += 1;
  state.mode = "encrypt";
  state.inputType = "text";
  state.file = null;
  state.fileText = "";
  state.view = "result";
  state.loading = false;
  state.fileReadVersion += 1;
  elements.textInput.value = "";
  elements.keyInput.value = "";
  elements.fileInput.value = "";
  elements.filePreview.textContent = "";
  elements.dropZone.hidden = false;
  elements.fileCard.hidden = true;
  document.querySelectorAll("#outputPanel [data-view]").forEach((tab) => {
    tab.setAttribute("aria-selected", String(tab.dataset.view === "result"));
  });
  clearResult();
  setStatus(elements.inputStatus, "Chưa có dữ liệu");
  setStatus(elements.keyStatus, "Chưa nhập khóa");
  render();
}

elements.modeEncrypt.addEventListener("click", () => selectMode("encrypt"));
elements.modeDecrypt.addEventListener("click", () => selectMode("decrypt"));
elements.typeText.addEventListener("click", () => selectInputType("text"));
elements.typeFile.addEventListener("click", () => selectInputType("file"));
elements.textInput.addEventListener("input", () => { hideNotice(); clearResult(); render(); });
elements.textInput.addEventListener("scroll", () => { elements.inputHighlight.scrollTop = elements.textInput.scrollTop; });
elements.keyInput.addEventListener("input", () => { hideNotice(); clearResult(); render(); });
byId("clearInput").addEventListener("click", () => {
  if (state.inputType === "file") removeFile();
  else {
    elements.textInput.value = "";
    clearResult();
    render();
    elements.textInput.focus();
  }
});
byId("clearKey").addEventListener("click", () => {
  elements.keyInput.value = "";
  clearResult();
  render();
  elements.keyInput.focus();
});
elements.copyInput.addEventListener("click", () => copyText(currentInputText(), "Đã sao chép đầu vào"));
elements.copyKey.addEventListener("click", () => copyText(elements.keyInput.value, "Đã sao chép khóa"));
elements.copyOutput.addEventListener("click", () => copyText(state.result, "Đã sao chép kết quả"));
elements.clearOutput.addEventListener("click", () => { clearResult(); render(); });
elements.downloadOutput.addEventListener("click", downloadResult);
elements.actionButton.addEventListener("click", processInput);
byId("resetAll").addEventListener("click", resetAll);
byId("closeNotice").addEventListener("click", hideNotice);
byId("pickFile").addEventListener("click", (event) => { event.stopPropagation(); elements.fileInput.click(); });
byId("changeFile").addEventListener("click", () => elements.fileInput.click());
byId("removeFile").addEventListener("click", removeFile);
elements.fileInput.addEventListener("change", () => {
  const [file] = elements.fileInput.files;
  if (file) setFile(file);
});
elements.dropZone.addEventListener("click", (event) => {
  if (state.loading) return;
  if (event.target !== byId("pickFile")) elements.fileInput.click();
});
elements.dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    if (state.loading) return;
    elements.fileInput.click();
  }
});
for (const eventName of ["dragenter", "dragover"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    if (!state.loading) elements.dropZone.classList.add("drag-over");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("drag-over");
  });
}
elements.dropZone.addEventListener("drop", (event) => {
  if (state.loading) return;
  const [file] = event.dataTransfer.files;
  if (file) setFile(file);
});
byId("example").addEventListener("click", () => {
  state.inputType = "text";
  elements.textInput.value = "Hello World";
  elements.keyInput.value = "3";
  clearResult();
  render();
  elements.actionButton.focus();
});
document.querySelectorAll("#outputPanel [data-view]").forEach((tab) => {
  tab.addEventListener("click", () => {
    state.view = tab.dataset.view;
    render();
  });
});

render();
