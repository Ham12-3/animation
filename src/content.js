(() => {
  const STORAGE_KEY = "projectManagerFinderLeads";
  const BUTTON_ID = "project-manager-finder-save-button";
  const TOAST_ID = "project-manager-finder-toast";

  if (window.projectManagerFinderInjected) {
    return;
  }

  window.projectManagerFinderInjected = true;

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "GET_LINKEDIN_PROFILE") {
      return false;
    }

    sendResponse(readProfileFromPage());
    return true;
  });

  addSaveButton();

  function addSaveButton() {
    if (document.getElementById(BUTTON_ID)) {
      return;
    }

    const button = document.createElement("button");
    button.id = BUTTON_ID;
    button.type = "button";
    button.textContent = "Save PM lead";
    button.setAttribute("aria-label", "Save this LinkedIn profile as a project manager lead");
    Object.assign(button.style, {
      position: "fixed",
      right: "18px",
      bottom: "18px",
      zIndex: "2147483647",
      border: "0",
      borderRadius: "999px",
      padding: "12px 16px",
      background: "#0a66c2",
      color: "#ffffff",
      cursor: "pointer",
      font: "700 14px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
      boxShadow: "0 10px 30px rgba(0, 0, 0, 0.24)"
    });

    button.addEventListener("click", saveCurrentProfile);
    document.body.appendChild(button);
  }

  function readProfileFromPage() {
    const name = getText("main h1") || getNameFromDocumentTitle();
    const title = getText(".text-body-medium.break-words") || getHeadlineNearName() || "";
    const url = normalizeProfileUrl(window.location.href);

    return { name, title, url };
  }

  async function saveCurrentProfile() {
    const profile = readProfileFromPage();

    if (!profile.url.startsWith("https://www.linkedin.com/in/")) {
      showToast("Open a LinkedIn profile page before saving.");
      return;
    }

    const now = new Date().toISOString();
    const lead = {
      id: profile.url,
      name: profile.name || "Unnamed lead",
      title: profile.title,
      url: profile.url,
      notes: "Saved from LinkedIn profile page.",
      status: "Saved",
      createdAt: now,
      updatedAt: now
    };

    const leads = await loadLeads();
    const existingIndex = leads.findIndex((savedLead) => savedLead.id === lead.id);

    if (existingIndex >= 0) {
      leads[existingIndex] = {
        ...leads[existingIndex],
        ...lead,
        notes: leads[existingIndex].notes || lead.notes,
        createdAt: leads[existingIndex].createdAt || lead.createdAt
      };
    } else {
      leads.unshift(lead);
    }

    await saveLeads(leads);
    showToast("Lead saved. Open the extension popup to draft a message.");
  }

  function loadLeads() {
    return new Promise((resolve) => {
      chrome.storage.local.get({ [STORAGE_KEY]: [] }, (result) => {
        resolve(Array.isArray(result[STORAGE_KEY]) ? result[STORAGE_KEY] : []);
      });
    });
  }

  function saveLeads(leads) {
    return new Promise((resolve) => {
      chrome.storage.local.set({ [STORAGE_KEY]: leads }, resolve);
    });
  }

  function getText(selector) {
    return document.querySelector(selector)?.textContent?.trim() || "";
  }

  function getHeadlineNearName() {
    const nameHeading = document.querySelector("main h1");
    const profileSection = nameHeading?.closest("section");
    const possibleHeadlines = Array.from(profileSection?.querySelectorAll("div, span") || [])
      .map((element) => element.textContent.trim())
      .filter((text) => text.length > 20 && !text.includes("\n"));

    return possibleHeadlines[0] || "";
  }

  function getNameFromDocumentTitle() {
    return document.title.replace(/\s*\|\s*LinkedIn\s*$/i, "").split(/\s+-\s+/)[0].trim();
  }

  function normalizeProfileUrl(value) {
    const url = new URL(value);
    url.hash = "";
    url.search = "";
    url.pathname = url.pathname.replace(/\/+$/, "");

    return url.toString();
  }

  function showToast(message) {
    document.getElementById(TOAST_ID)?.remove();

    const toast = document.createElement("div");
    toast.id = TOAST_ID;
    toast.textContent = message;
    Object.assign(toast.style, {
      position: "fixed",
      right: "18px",
      bottom: "72px",
      zIndex: "2147483647",
      maxWidth: "320px",
      borderRadius: "14px",
      padding: "12px 14px",
      background: "#162033",
      color: "#ffffff",
      font: "600 14px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
      boxShadow: "0 10px 30px rgba(0, 0, 0, 0.24)"
    });

    document.body.appendChild(toast);
    window.setTimeout(() => toast.remove(), 3600);
  }
})();
