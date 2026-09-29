const stages = [
  ["intake", "信息采集"],
  ["source_review", "来源审阅"],
  ["personal_profile_record", "个人资料记录"],
  ["privacy_and_authorization_review", "隐私与授权"],
  ["user_content_approval", "内容批准"],
  ["format_recommendation", "格式建议"],
  ["visual_direction_choice", "视觉方向"],
  ["draft", "单页草稿"],
  ["final_review", "最终审阅"],
  ["user_approval", "用户批准"],
  ["editable_output_or_export_instructions", "可编辑输出"],
];

const statusLabels = {
  confirmed: "来源确认",
  user_approved: "用户批准",
  needs_confirmation: "待确认",
  suggested_wording: "建议措辞",
  placeholder: "占位符",
  not_supported: "不支持",
};

const els = Object.fromEntries([
  "workflowSteps", "stageBadge", "messages", "recordSummary", "recordItems", "recordEmpty",
  "runtimeDot", "runtimeLabel", "chatForm", "messageInput", "sendButton", "dropzone",
  "fileInput", "chooseFiles", "sourceList", "demoButton", "resetButton", "toast"
].map(id => [id, document.getElementById(id)]));

let current = null;

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
}

function showToast(message, error = false) {
  els.toast.textContent = message;
  els.toast.className = `toast show${error ? " error" : ""}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => els.toast.className = "toast", 3400);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "请求未完成");
  return data;
}

function renderWorkflow(stage) {
  const currentIndex = stages.findIndex(([key]) => key === stage);
  els.workflowSteps.innerHTML = stages.map(([key, label], index) => `
    <li class="step ${index < currentIndex ? "complete" : ""} ${index === currentIndex ? "current" : ""}" ${index === currentIndex ? 'aria-current="step"' : ""}>
      <span class="step-number">${index < currentIndex ? "✓" : index + 1}</span>
      <span>${label}</span>
    </li>
  `).join("");
  els.stageBadge.textContent = stages[currentIndex]?.[1] || stage;
}

function renderMessages(messages) {
  if (!messages.length) {
    els.messages.innerHTML = `<div class="message assistant">你好，我是 ProfileKit。请告诉我：你要制作什么、谁会查看、使用场景是什么，以及希望使用哪些资料。</div>`;
  } else {
    els.messages.innerHTML = messages.map(message => `
      <div class="message ${message.role}">${escapeHtml(message.content)}</div>
    `).join("");
  }
  els.messages.scrollTop = els.messages.scrollHeight;
}

function renderRecord(record) {
  const metadata = record.profile_metadata || {};
  const summaryFields = [
    ["受众", metadata.audience], ["用途", metadata.purpose],
    ["类型", metadata.output_type], ["语言", metadata.language],
  ].filter(([, value]) => value);
  els.recordSummary.innerHTML = summaryFields.map(([label, value]) => `
    <div class="meta-card"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>
  `).join("");

  const items = record.items || [];
  els.recordEmpty.hidden = items.length > 0;
  els.recordItems.hidden = items.length === 0;
  els.recordItems.innerHTML = items.map((item, index) => `
    <article class="record-item" data-decision="${item.user_decision}">
      <div class="item-heading">
        <strong>${escapeHtml(item.label)}</strong>
        <span class="status-pill ${item.status}">${statusLabels[item.status] || escapeHtml(item.status)}</span>
      </div>
      <p class="item-value">${escapeHtml(item.value)}</p>
      <p class="item-source">来源：${escapeHtml(item.source || "用户输入")}</p>
      <div class="decision-row" aria-label="${escapeHtml(item.label)} 的公开使用决定">
        ${[["include","包含"],["exclude","排除"],["revise","修改"],["restrict","限制"]].map(([decision, label]) => `
          <button class="decision ${item.user_decision === decision ? "active" : ""}" data-index="${index}" data-decision="${decision}" type="button">${label}</button>
        `).join("")}
      </div>
    </article>
  `).join("");
}

function render(state) {
  current = state;
  renderWorkflow(state.stage);
  renderMessages(state.transcript || []);
  renderRecord(state.record || {});
  const ready = state.runtime?.api_key_ready;
  els.runtimeDot.classList.toggle("ready", ready);
  els.runtimeLabel.textContent = ready
    ? `${state.runtime.provider} · ${state.runtime.model} · 本地会话`
    : "尚未找到 OpenAI API key";
  if (state.pending_source_count) {
    els.sourceList.textContent = `${state.pending_source_count} 组资料将在下一条消息中送交审阅`;
  }
}

async function refresh() {
  render(await api("/api/session"));
}

els.chatForm.addEventListener("submit", async event => {
  event.preventDefault();
  const message = els.messageInput.value.trim();
  if (!message) return;
  els.sendButton.disabled = true;
  els.messages.insertAdjacentHTML("beforeend", `<div class="message user">${escapeHtml(message)}</div><div class="message loading">ProfileKit 正在整理记录…</div>`);
  els.messages.scrollTop = els.messages.scrollHeight;
  els.messageInput.value = "";
  try {
    const data = await api("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message}),
    });
    render(data.session);
  } catch (error) {
    showToast(error.message, true);
    await refresh();
  } finally {
    els.sendButton.disabled = false;
    els.messageInput.focus();
  }
});

async function uploadFiles(files) {
  if (!files.length) return;
  const form = new FormData();
  [...files].forEach(file => form.append("files", file));
  els.sourceList.textContent = "正在安全读取资料…";
  try {
    const data = await api("/api/upload", {method: "POST", body: form});
    els.sourceList.textContent = `已读取：${data.accepted.join("、")}。资料将在下一条消息中进入来源审阅。`;
    current = data.session;
  } catch (error) {
    els.sourceList.textContent = "";
    showToast(error.message, true);
  }
}

els.chooseFiles.addEventListener("click", () => els.fileInput.click());
els.fileInput.addEventListener("change", () => uploadFiles(els.fileInput.files));
["dragenter", "dragover"].forEach(name => els.dropzone.addEventListener(name, event => {
  event.preventDefault(); els.dropzone.classList.add("dragging");
}));
["dragleave", "drop"].forEach(name => els.dropzone.addEventListener(name, event => {
  event.preventDefault(); els.dropzone.classList.remove("dragging");
}));
els.dropzone.addEventListener("drop", event => uploadFiles(event.dataTransfer.files));

els.recordItems.addEventListener("click", async event => {
  const button = event.target.closest(".decision");
  if (!button) return;
  button.disabled = true;
  try {
    render(await api(`/api/items/${button.dataset.index}`, {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({decision: button.dataset.decision}),
    }));
    showToast("资料决定已保存");
  } catch (error) {
    showToast(error.message, true);
  }
});

els.demoButton.addEventListener("click", async () => {
  render(await api("/api/demo", {method: "POST"}));
  showToast("已载入虚构演示案例");
});

els.resetButton.addEventListener("click", async () => {
  if (!confirm("开始新会话？当前本地会话记录会被替换。")) return;
  render(await api("/api/reset", {method: "POST"}));
  els.sourceList.textContent = "";
  showToast("已开始新会话");
});

els.messageInput.addEventListener("keydown", event => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) els.chatForm.requestSubmit();
});

refresh().catch(error => showToast(error.message, true));
