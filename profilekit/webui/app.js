const stages = [
  ["intake", "Intake"],
  ["source_review", "Source review"],
  ["personal_profile_record", "Profile record"],
  ["privacy_and_authorization_review", "Privacy & permission"],
  ["user_content_approval", "Content approval"],
  ["format_recommendation", "Format recommendation"],
  ["visual_direction_choice", "Visual direction"],
  ["draft", "One-page draft"],
  ["final_review", "Final review"],
  ["user_approval", "User approval"],
  ["editable_output_or_export_instructions", "Editable output"],
];

const statusLabels = {
  confirmed: "Source confirmed",
  user_approved: "User approved",
  needs_confirmation: "Needs confirmation",
  suggested_wording: "Suggested wording",
  placeholder: "Placeholder",
  not_supported: "Not supported",
};

const els = Object.fromEntries([
  "workflowSteps", "stageBadge", "messages", "recordSummary", "recordItems", "recordEmpty",
  "runtimeDot", "runtimeLabel", "chatForm", "messageInput", "sendButton", "dropzone",
  "fileInput", "chooseFiles", "sourceList", "demoButton", "resetButton", "toast", "modelSelect"
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
  if (!response.ok) throw new Error(data.detail || "The request could not be completed.");
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
    els.messages.innerHTML = `<div class="message assistant">Hello, I’m ProfileKit. What are you creating, who will view it, what is the occasion, and which source materials should I use?</div>`;
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
    ["Audience", metadata.audience], ["Purpose", metadata.purpose],
    ["Format", metadata.output_type], ["Language", metadata.language],
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
      <p class="item-source">Source: ${escapeHtml(item.source || "User input")}</p>
      <div class="decision-row" aria-label="Public-use decision for ${escapeHtml(item.label)}">
        ${[["include","Include"],["exclude","Exclude"],["revise","Revise"],["restrict","Restrict"]].map(([decision, label]) => `
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
  renderModelSelect(state.runtime);
  els.runtimeDot.classList.toggle("ready", ready);
  els.runtimeLabel.textContent = ready
    ? `${state.runtime.provider_label} · local session`
    : `API key missing for ${state.runtime.model_label}`;
  if (state.pending_source_count) {
    els.sourceList.textContent = `${state.pending_source_count} source bundle will be reviewed with your next message.`;
  }
}

function renderModelSelect(runtime) {
  const selected = `${runtime.provider}:${runtime.model}`;
  const costLabels = {lowest: "lowest cost", low: "low cost", medium: "balanced", high: "highest cost"};
  els.modelSelect.innerHTML = (runtime.models || []).map(option => `
    <option value="${option.provider}:${option.model}" ${`${option.provider}:${option.model}` === selected ? "selected" : ""} ${option.ready ? "" : "disabled"}>
      ${escapeHtml(option.label)} · ${costLabels[option.cost_tier] || option.cost_tier}${option.ready ? "" : " · key missing"}
    </option>
  `).join("");
  els.modelSelect.title = (runtime.models || []).find(option => `${option.provider}:${option.model}` === selected)?.description || "Choose a model";
}

async function refresh() {
  render(await api("/api/session"));
}

els.chatForm.addEventListener("submit", async event => {
  event.preventDefault();
  const message = els.messageInput.value.trim();
  if (!message) return;
  els.sendButton.disabled = true;
  els.messages.insertAdjacentHTML("beforeend", `<div class="message user">${escapeHtml(message)}</div><div class="message loading">ProfileKit is organizing the record…</div>`);
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
  els.sourceList.textContent = "Reading the selected sources…";
  try {
    const data = await api("/api/upload", {method: "POST", body: form});
    els.sourceList.textContent = `Ready: ${data.accepted.join(", ")}. The sources will enter review with your next message.`;
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
    showToast("The item decision was saved.");
  } catch (error) {
    showToast(error.message, true);
  }
});

els.demoButton.addEventListener("click", async () => {
  render(await api("/api/demo", {method: "POST"}));
  showToast("The fictional demo case is ready.");
});

els.resetButton.addEventListener("click", async () => {
  if (!confirm("Start a new session? This will replace the current local session record.")) return;
  render(await api("/api/reset", {method: "POST"}));
  els.sourceList.textContent = "";
  showToast("A new session is ready.");
});

els.modelSelect.addEventListener("change", async () => {
  const [provider, model] = els.modelSelect.value.split(":", 2);
  els.modelSelect.disabled = true;
  try {
    render(await api("/api/model", {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({provider, model}),
    }));
    showToast(`Model changed to ${els.modelSelect.options[els.modelSelect.selectedIndex].text.split(" · ")[0]}.`);
  } catch (error) {
    showToast(error.message, true);
    await refresh();
  } finally {
    els.modelSelect.disabled = false;
  }
});

els.messageInput.addEventListener("keydown", event => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) els.chatForm.requestSubmit();
});

refresh().catch(error => showToast(error.message, true));
