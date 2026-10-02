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
  "fileInput", "chooseFiles", "sourceList", "demoScenario", "demoButton", "resetButton", "toast", "modelSelect",
  "recordTab", "previewTab", "recordView", "previewView", "themeSelect", "profilePreview", "previewNote", "pdfButton"
  , "customizeButton", "customizeDialog", "closeCustomize", "preferencesForm", "savePreferences",
  "prefName", "prefRole", "prefIntroduction", "prefAudience", "prefOccasion", "prefPurpose", "prefTone",
  "prefTheme", "prefAccent", "prefFont", "prefDensity", "prefVisual", "prefPrivacy"
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

function renderThemeSelect(state) {
  els.themeSelect.innerHTML = (state.themes || []).map(theme => `
    <option value="${theme.id}" ${theme.id === state.profile_theme ? "selected" : ""}>
      ${escapeHtml(theme.label)} · ${escapeHtml(theme.description)}
    </option>
  `).join("");
}

function renderPreview(state) {
  const profile = state.presentation || {};
  const sections = (profile.sections || []).map(section => `
    <section class="profile-section">
      <h4>${escapeHtml(section.heading)}</h4>
      ${section.items.map(item => `
        <div class="profile-entry">
          <span>${escapeHtml(item.label)}</span>
          <p>${escapeHtml(item.value)}</p>
        </div>
      `).join("")}
    </section>
  `).join("");
  els.profilePreview.className = `profile-page theme-${profile.theme || "academic"}`;
  els.profilePreview.style.setProperty("--profile-accent", profile.accent_color || "#147d70");
  els.profilePreview.dataset.font = profile.font_style || "hybrid";
  els.profilePreview.dataset.density = profile.layout_density || "balanced";
  els.profilePreview.innerHTML = `
    <header class="profile-header">
      <p class="profile-kicker">One-page profile</p>
      <h3>${escapeHtml(profile.title || "Your Name")}</h3>
      <p class="profile-role">${escapeHtml(profile.role || "Personal Profile")}</p>
      ${profile.context ? `<p class="profile-context">${escapeHtml(profile.context)}</p>` : ""}
    </header>
    <div class="profile-body">
      <p class="profile-intro">${escapeHtml(profile.introduction || "Your approved introduction will appear here.")}</p>
      <div class="profile-sections">${sections || `<div class="profile-placeholder">Approve profile details to build the page.</div>`}</div>
    </div>
    <footer>ProfileKit · privacy-reviewed profile <span>1 / 1</span></footer>
  `;
  requestAnimationFrame(() => {
    const body = els.profilePreview.querySelector(".profile-body");
    const crowded = body && body.scrollHeight > body.clientHeight + 1;
    els.previewNote.textContent = crowded
      ? "This page is crowded. Choose Compact density, shorten entries, or export the PDF to check its one-page fit."
      : "The preview updates automatically. Restricted and unconfirmed sensitive items stay out of the public page.";
  });
  const empty = !(state.record?.items || []).length;
  els.pdfButton.classList.toggle("disabled", empty);
  els.pdfButton.setAttribute("aria-disabled", empty.toString());
}

function render(state) {
  current = state;
  renderWorkflow(state.stage);
  renderMessages(state.transcript || []);
  renderRecord(state.record || {});
  renderThemeSelect(state);
  renderPreview(state);
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
    const configured = data.configured || [];
    els.sourceList.textContent = configured.length
      ? `Applied ${configured.join(", ")}. Other sources will enter review with your next message.`
      : `Ready: ${data.accepted.join(", ")}. The sources will enter review with your next message.`;
    current = data.session;
    render(data.session);
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
  render(await api(`/api/demo?scenario=${encodeURIComponent(els.demoScenario.value)}`, {method: "POST"}));
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

function selectView(view) {
  const preview = view === "preview";
  els.previewView.hidden = !preview;
  els.recordView.hidden = preview;
  els.previewTab.classList.toggle("active", preview);
  els.recordTab.classList.toggle("active", !preview);
  els.previewTab.setAttribute("aria-selected", preview.toString());
  els.recordTab.setAttribute("aria-selected", (!preview).toString());
}

els.previewTab.addEventListener("click", () => selectView("preview"));
els.recordTab.addEventListener("click", () => selectView("record"));

els.themeSelect.addEventListener("change", async () => {
  els.themeSelect.disabled = true;
  try {
    render(await api("/api/theme", {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({theme: els.themeSelect.value}),
    }));
    showToast("The preview and PDF theme were updated.");
  } catch (error) {
    showToast(error.message, true);
    await refresh();
  } finally {
    els.themeSelect.disabled = false;
  }
});

els.pdfButton.addEventListener("click", event => {
  if (els.pdfButton.classList.contains("disabled")) {
    event.preventDefault();
    showToast("Add or load profile content before exporting a PDF.", true);
  }
});

function itemValue(label) {
  return (current?.record?.items || []).find(item => item.label.toLowerCase() === label.toLowerCase())?.value || "";
}

function openPreferences() {
  const metadata = current?.record?.profile_metadata || {};
  els.prefName.value = itemValue("Preferred name");
  els.prefRole.value = itemValue("Current role");
  els.prefIntroduction.value = itemValue("Short introduction");
  els.prefAudience.value = metadata.audience || "";
  els.prefOccasion.value = metadata.occasion || "";
  els.prefPurpose.value = metadata.purpose || "";
  els.prefTone.value = metadata.tone || "";
  els.prefTheme.value = current?.profile_theme || "academic";
  els.prefAccent.value = current?.accent_color || "#147d70";
  els.prefFont.value = current?.font_style || "hybrid";
  els.prefDensity.value = current?.layout_density || "balanced";
  els.prefVisual.value = metadata.visual_preferences || "";
  els.prefPrivacy.value = metadata.privacy_restrictions || "";
  els.customizeDialog.showModal();
}

els.customizeButton.addEventListener("click", openPreferences);
els.closeCustomize.addEventListener("click", () => els.customizeDialog.close());
els.customizeDialog.addEventListener("click", event => {
  if (event.target === els.customizeDialog) els.customizeDialog.close();
});

els.preferencesForm.addEventListener("submit", async event => {
  event.preventDefault();
  els.savePreferences.disabled = true;
  const payload = {
    name: els.prefName.value.trim(), role: els.prefRole.value.trim(),
    introduction: els.prefIntroduction.value.trim(), audience: els.prefAudience.value.trim(),
    occasion: els.prefOccasion.value.trim(), purpose: els.prefPurpose.value.trim(), tone: els.prefTone.value.trim(),
    theme: els.prefTheme.value, accent_color: els.prefAccent.value,
    font_style: els.prefFont.value, layout_density: els.prefDensity.value,
    visual_preferences: els.prefVisual.value.trim(), privacy_restrictions: els.prefPrivacy.value.trim(),
  };
  try {
    render(await api("/api/preferences", {
      method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
    }));
    els.customizeDialog.close();
    selectView("preview");
    showToast("Content and design preferences were applied.");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.savePreferences.disabled = false;
  }
});

els.messageInput.addEventListener("keydown", event => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) els.chatForm.requestSubmit();
});

refresh().catch(error => showToast(error.message, true));
