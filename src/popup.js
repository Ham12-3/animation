const STORAGE_KEY = "projectManagerFinderLeads";
const LEAD_STATUSES = ["Saved", "Drafted", "Messaged", "Replied", "Follow-up", "Closed"];

let leads = [];

const elements = {
  roleInput: document.querySelector("#roleInput"),
  locationInput: document.querySelector("#locationInput"),
  industryInput: document.querySelector("#industryInput"),
  keywordInput: document.querySelector("#keywordInput"),
  queryPreview: document.querySelector("#queryPreview"),
  openLinkedInSearchButton: document.querySelector("#openLinkedInSearchButton"),
  openGoogleSearchButton: document.querySelector("#openGoogleSearchButton"),
  loadCurrentProfileButton: document.querySelector("#loadCurrentProfileButton"),
  leadNameInput: document.querySelector("#leadNameInput"),
  leadTitleInput: document.querySelector("#leadTitleInput"),
  leadUrlInput: document.querySelector("#leadUrlInput"),
  leadNotesInput: document.querySelector("#leadNotesInput"),
  leadStatusInput: document.querySelector("#leadStatusInput"),
  saveLeadButton: document.querySelector("#saveLeadButton"),
  resetLeadFormButton: document.querySelector("#resetLeadFormButton"),
  draftLeadSelect: document.querySelector("#draftLeadSelect"),
  outreachGoalInput: document.querySelector("#outreachGoalInput"),
  messageDraftInput: document.querySelector("#messageDraftInput"),
  generateDraftButton: document.querySelector("#generateDraftButton"),
  copyDraftButton: document.querySelector("#copyDraftButton"),
  exportCsvButton: document.querySelector("#exportCsvButton"),
  leadFilterInput: document.querySelector("#leadFilterInput"),
  leadList: document.querySelector("#leadList"),
  statusMessage: document.querySelector("#statusMessage")
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializePopup);
} else {
  initializePopup();
}

async function initializePopup() {
  leads = await loadLeads();
  wireEvents();
  updateQueryPreview();
  renderLeadOptions();
  renderLeads();
}

function wireEvents() {
  [
    elements.roleInput,
    elements.locationInput,
    elements.industryInput,
    elements.keywordInput
  ].forEach((input) => input.addEventListener("input", updateQueryPreview));

  elements.openLinkedInSearchButton.addEventListener("click", openLinkedInSearch);
  elements.openGoogleSearchButton.addEventListener("click", openGoogleSearch);
  elements.loadCurrentProfileButton.addEventListener("click", loadCurrentProfile);
  elements.saveLeadButton.addEventListener("click", saveLeadFromForm);
  elements.resetLeadFormButton.addEventListener("click", resetLeadForm);
  elements.generateDraftButton.addEventListener("click", generateMessageDraft);
  elements.copyDraftButton.addEventListener("click", copyMessageDraft);
  elements.exportCsvButton.addEventListener("click", exportLeadsAsCsv);
  elements.leadFilterInput.addEventListener("input", renderLeads);
  elements.draftLeadSelect.addEventListener("change", generateMessageDraft);
  elements.leadList.addEventListener("click", handleLeadAction);
  elements.leadList.addEventListener("change", handleLeadStatusChange);
}

// Storage is wrapped so the extension can still be opened directly while developing.
function loadLeads() {
  if (hasChromeStorage()) {
    return new Promise((resolve) => {
      chrome.storage.local.get({ [STORAGE_KEY]: [] }, (result) => {
        resolve(Array.isArray(result[STORAGE_KEY]) ? result[STORAGE_KEY] : []);
      });
    });
  }

  try {
    return Promise.resolve(JSON.parse(localStorage.getItem(STORAGE_KEY)) || []);
  } catch {
    return Promise.resolve([]);
  }
}

function persistLeads() {
  if (hasChromeStorage()) {
    return new Promise((resolve) => {
      chrome.storage.local.set({ [STORAGE_KEY]: leads }, resolve);
    });
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(leads));
  return Promise.resolve();
}

function hasChromeStorage() {
  return typeof chrome !== "undefined" && Boolean(chrome.storage?.local);
}

function getSearchParts() {
  return [
    elements.roleInput.value,
    elements.locationInput.value,
    elements.industryInput.value,
    elements.keywordInput.value
  ]
    .map((value) => value.trim())
    .filter(Boolean);
}

function updateQueryPreview() {
  const parts = getSearchParts();
  const query = parts.join(" ");
  elements.queryPreview.textContent = query
    ? `Search query: ${query}`
    : "Add a role, location, industry, or keyword to build a search.";
}

function openLinkedInSearch() {
  const query = getSearchParts().join(" ").trim();
  if (!query) {
    showStatus("Add at least one search term first.", true);
    return;
  }

  const url = `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(query)}`;
  openNewTab(url);
}

function openGoogleSearch() {
  const role = elements.roleInput.value.trim() || "Project Manager";
  const location = elements.locationInput.value.trim();
  const industry = elements.industryInput.value.trim();
  const keywords = elements.keywordInput.value.trim();
  const quotedParts = [role, location, industry, keywords]
    .filter(Boolean)
    .map((part) => `"${part}"`)
    .join(" ");
  const url = `https://www.google.com/search?q=${encodeURIComponent(`site:linkedin.com/in ${quotedParts}`)}`;

  openNewTab(url);
}

function openNewTab(url) {
  if (typeof chrome !== "undefined" && chrome.tabs?.create) {
    chrome.tabs.create({ url });
    return;
  }

  window.open(url, "_blank", "noopener,noreferrer");
}

async function loadCurrentProfile() {
  const activeTab = await getActiveTab();

  if (!activeTab?.url || !isLinkedInProfileUrl(activeTab.url)) {
    showStatus("Open a LinkedIn profile tab first.", true);
    return;
  }

  const profileFromPage = await requestProfileFromContentScript(activeTab.id);
  const fallbackProfile = parseProfileFromTab(activeTab);
  const profile = {
    ...fallbackProfile,
    ...removeEmptyFields(profileFromPage || {})
  };

  elements.leadNameInput.value = profile.name || "";
  elements.leadTitleInput.value = profile.title || "";
  elements.leadUrlInput.value = normalizeProfileUrl(profile.url || activeTab.url);
  showStatus("Loaded the current LinkedIn profile.");
}

function getActiveTab() {
  if (typeof chrome === "undefined" || !chrome.tabs?.query) {
    return Promise.resolve(null);
  }

  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      resolve(tabs[0] || null);
    });
  });
}

function requestProfileFromContentScript(tabId) {
  if (!tabId || typeof chrome === "undefined" || !chrome.tabs?.sendMessage) {
    return Promise.resolve(null);
  }

  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { type: "GET_LINKEDIN_PROFILE" }, (response) => {
      if (chrome.runtime.lastError) {
        resolve(null);
        return;
      }

      resolve(response || null);
    });
  });
}

function parseProfileFromTab(tab) {
  const titleWithoutLinkedIn = (tab.title || "").replace(/\s*\|\s*LinkedIn\s*$/i, "");
  const [name = "", title = ""] = titleWithoutLinkedIn.split(/\s+-\s+/, 2);

  return {
    name: name.trim(),
    title: title.trim(),
    url: tab.url
  };
}

async function saveLeadFromForm() {
  const profileUrl = normalizeProfileUrl(elements.leadUrlInput.value);

  if (!isLinkedInProfileUrl(profileUrl)) {
    showStatus("Use a valid LinkedIn profile URL that starts with https://www.linkedin.com/in/.", true);
    return;
  }

  const now = new Date().toISOString();
  const lead = {
    id: profileUrl,
    name: elements.leadNameInput.value.trim() || "Unnamed lead",
    title: elements.leadTitleInput.value.trim(),
    url: profileUrl,
    notes: elements.leadNotesInput.value.trim(),
    status: elements.leadStatusInput.value,
    createdAt: now,
    updatedAt: now
  };

  upsertLead(lead);
  await persistLeads();
  renderLeadOptions();
  renderLeads();
  elements.draftLeadSelect.value = lead.id;
  showStatus("Lead saved.");
}

function upsertLead(lead) {
  const existingIndex = leads.findIndex((existingLead) => existingLead.id === lead.id);

  if (existingIndex >= 0) {
    leads[existingIndex] = {
      ...leads[existingIndex],
      ...lead,
      createdAt: leads[existingIndex].createdAt || lead.createdAt
    };
    return;
  }

  leads.unshift(lead);
}

function resetLeadForm() {
  elements.leadNameInput.value = "";
  elements.leadTitleInput.value = "";
  elements.leadUrlInput.value = "";
  elements.leadNotesInput.value = "";
  elements.leadStatusInput.value = "Saved";
  showStatus("Lead form cleared.");
}

function renderLeadOptions() {
  const selectedValue = elements.draftLeadSelect.value;
  const options = ['<option value="">Select a lead</option>']
    .concat(
      leads.map((lead) => {
        const label = lead.name || lead.url;
        return `<option value="${escapeHtml(lead.id)}">${escapeHtml(label)}</option>`;
      })
    )
    .join("");

  elements.draftLeadSelect.innerHTML = options;
  elements.draftLeadSelect.value = leads.some((lead) => lead.id === selectedValue) ? selectedValue : "";
}

function renderLeads() {
  const filterText = elements.leadFilterInput.value.trim().toLowerCase();
  const visibleLeads = leads.filter((lead) => {
    const searchableText = [lead.name, lead.title, lead.url, lead.notes, lead.status]
      .join(" ")
      .toLowerCase();

    return searchableText.includes(filterText);
  });

  if (visibleLeads.length === 0) {
    elements.leadList.innerHTML = '<p class="empty-state">No saved leads yet.</p>';
    return;
  }

  elements.leadList.innerHTML = visibleLeads.map(renderLeadCard).join("");
}

function renderLeadCard(lead) {
  const statusOptions = LEAD_STATUSES.map((status) => {
    const selected = status === lead.status ? "selected" : "";
    return `<option ${selected}>${escapeHtml(status)}</option>`;
  }).join("");

  return `
    <article class="lead-card">
      <h3>${escapeHtml(lead.name || "Unnamed lead")}</h3>
      <p>${escapeHtml(lead.title || "No headline saved")}</p>
      ${lead.notes ? `<p>${escapeHtml(lead.notes)}</p>` : ""}
      <label>
        Status
        <select data-action="status" data-lead-id="${escapeHtml(lead.id)}">
          ${statusOptions}
        </select>
      </label>
      <div class="lead-actions">
        <button class="secondary" type="button" data-action="use-draft" data-lead-id="${escapeHtml(lead.id)}">Use for draft</button>
        <a href="${escapeHtml(lead.url)}" target="_blank" rel="noreferrer">Open profile</a>
        <button class="danger" type="button" data-action="delete" data-lead-id="${escapeHtml(lead.id)}">Delete</button>
      </div>
    </article>
  `;
}

async function handleLeadAction(event) {
  const actionButton = event.target.closest("[data-action]");
  if (!actionButton) {
    return;
  }

  const leadId = actionButton.dataset.leadId;
  const lead = leads.find((savedLead) => savedLead.id === leadId);

  if (!lead) {
    return;
  }

  if (actionButton.dataset.action === "use-draft") {
    elements.draftLeadSelect.value = lead.id;
    generateMessageDraft();
    showStatus("Lead loaded for drafting.");
  }

  if (actionButton.dataset.action === "delete") {
    const shouldDelete = window.confirm(`Delete ${lead.name || "this lead"}?`);
    if (!shouldDelete) {
      return;
    }

    leads = leads.filter((savedLead) => savedLead.id !== lead.id);
    await persistLeads();
    renderLeadOptions();
    renderLeads();
    showStatus("Lead deleted.");
  }
}

async function handleLeadStatusChange(event) {
  if (event.target.dataset.action !== "status") {
    return;
  }

  const lead = leads.find((savedLead) => savedLead.id === event.target.dataset.leadId);
  if (!lead) {
    return;
  }

  lead.status = event.target.value;
  lead.updatedAt = new Date().toISOString();
  await persistLeads();
  renderLeadOptions();
  showStatus("Lead status updated.");
}

async function generateMessageDraft() {
  const lead = leads.find((savedLead) => savedLead.id === elements.draftLeadSelect.value);

  if (!lead) {
    showStatus("Select a saved lead first.", true);
    return;
  }

  const firstName = getFirstName(lead.name);
  const location = elements.locationInput.value.trim();
  const industry = elements.industryInput.value.trim();
  const goal = elements.outreachGoalInput.value.trim() || "connect and learn more about your work";
  const contextPieces = [
    industry ? ` in ${industry}` : "",
    location ? ` around ${location}` : ""
  ].join("");
  const headlineSentence = lead.title
    ? ` I noticed your background: ${lead.title}.`
    : "";

  elements.messageDraftInput.value = [
    `Hi ${firstName},`,
    "",
    `I came across your profile while looking for project managers${contextPieces}.${headlineSentence}`,
    `I would like to ${goal}.`,
    "",
    "Would you be open to connecting?"
  ].join("\n");

  lead.status = lead.status === "Saved" ? "Drafted" : lead.status;
  lead.updatedAt = new Date().toISOString();
  await persistLeads();
  renderLeads();
  showStatus("Draft generated. Please review before sending manually.");
}

async function copyMessageDraft() {
  const draft = elements.messageDraftInput.value.trim();

  if (!draft) {
    showStatus("Generate or write a draft first.", true);
    return;
  }

  await copyText(draft);
  showStatus("Draft copied. Paste it into LinkedIn only after reviewing it.");
}

function copyText(text) {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }

  elements.messageDraftInput.focus();
  elements.messageDraftInput.select();
  document.execCommand("copy");
  return Promise.resolve();
}

function exportLeadsAsCsv() {
  if (leads.length === 0) {
    showStatus("Save at least one lead before exporting.", true);
    return;
  }

  const headers = ["Name", "Title", "URL", "Status", "Notes", "Created At", "Updated At"];
  const rows = leads.map((lead) => [
    lead.name,
    lead.title,
    lead.url,
    lead.status,
    lead.notes,
    lead.createdAt,
    lead.updatedAt
  ]);
  const csv = [headers, ...rows]
    .map((row) => row.map(formatCsvCell).join(","))
    .join("\n");
  const blobUrl = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const downloadLink = document.createElement("a");

  downloadLink.href = blobUrl;
  downloadLink.download = `project-manager-leads-${new Date().toISOString().slice(0, 10)}.csv`;
  downloadLink.click();
  URL.revokeObjectURL(blobUrl);
  showStatus("CSV export started.");
}

function formatCsvCell(value = "") {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function getFirstName(name) {
  const firstName = (name || "").trim().split(/\s+/)[0];
  return firstName || "there";
}

function normalizeProfileUrl(value) {
  try {
    const url = new URL(value.trim());
    url.hash = "";
    url.search = "";
    url.pathname = url.pathname.replace(/\/+$/, "");

    return url.toString();
  } catch {
    return value.trim();
  }
}

function isLinkedInProfileUrl(value) {
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase();

    return host === "linkedin.com" || host.endsWith(".linkedin.com")
      ? url.pathname.startsWith("/in/")
      : false;
  } catch {
    return false;
  }
}

function removeEmptyFields(source) {
  return Object.fromEntries(
    Object.entries(source).filter(([, value]) => typeof value === "string" && value.trim())
  );
}

function escapeHtml(value = "") {
  const element = document.createElement("span");
  element.textContent = value;

  return element.innerHTML;
}

function showStatus(message, isError = false) {
  elements.statusMessage.textContent = message;
  elements.statusMessage.style.color = isError ? "#a4262c" : "#107c41";
}
