/**
 * Service Worker (Manifest V3)
 * Handles background extension lifecycle and coordinates messages between popup and content scripts.
 */

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    console.log("[Attendance AI Service Worker] Extension installed successfully (v1.0.0).");
  } else if (details.reason === "update") {
    console.log("[Attendance AI Service Worker] Extension updated to new version.");
  }
});

// Listener for background messages if needed
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "BACKGROUND_PING") {
    sendResponse({ status: "OK", timestamp: Date.now() });
    return true;
  }
});
