# LinkedIn Project Manager Finder

A small Chrome extension that helps you find project managers, save promising LinkedIn profiles, draft outreach, and track follow-up status.

## What this extension does

- Builds LinkedIn people-search URLs from role, location, industry, and keyword inputs.
- Builds Google profile-search URLs for public LinkedIn profile discovery.
- Saves the current LinkedIn profile as a lead when you choose to save it.
- Drafts a short, personalized connection message that you can review and copy.
- Tracks each lead's status: `Saved`, `Drafted`, `Messaged`, `Replied`, `Follow-up`, or `Closed`.
- Exports saved leads to CSV.

## What this extension does not do

- It does not log in to LinkedIn for you.
- It does not scrape LinkedIn search results.
- It does not click LinkedIn buttons or send messages automatically.
- It does not bypass LinkedIn permissions, rate limits, or account protections.

The final send action stays manual so you can review every message and use LinkedIn responsibly.

## Load it in Chrome

1. Open Chrome and go to `chrome://extensions`.
2. Turn on **Developer mode**.
3. Click **Load unpacked**.
4. Select this repository folder.
5. Pin the **Project Manager Finder** extension if you want quick access.

## Basic workflow

1. Open the extension popup.
2. Enter a role, location, industry, and optional keywords.
3. Open a LinkedIn or Google search from the popup.
4. Visit a LinkedIn profile that looks relevant.
5. Click **Save PM lead** on the LinkedIn profile page, or use **Load current LinkedIn profile** in the popup.
6. Generate a draft message.
7. Review the draft, copy it, paste it into LinkedIn, and send it yourself if it looks appropriate.

## Files

- `manifest.json` - Chrome extension configuration.
- `src/popup.html` - Popup layout.
- `src/popup.css` - Popup styling.
- `src/popup.js` - Search builder, lead storage, CSV export, and message drafting.
- `src/content.js` - LinkedIn profile-page helper button and profile metadata reader.