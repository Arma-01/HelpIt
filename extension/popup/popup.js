/**
 * Attendance AI Extension - Phase 1 Popup Logic
 * 
 * Implements Phase 1 Image Processing Workflow:
 * Teacher uploads attendance sheet -> Backend processes via OCR/Vision -> Result displayed in popup.
 * ERP DOM is NOT modified in this phase.
 */

(function () {
  "use strict";

  // Initialize API Client pointing to backend
  const apiClient = new (window.AttendanceApiClient || class {
    constructor() { this.baseUrl = "http://127.0.0.1:8000/api/v1"; }
  })();

  // DOM Elements Cache
  const UI = {
    // Banner
    statusBanner: document.getElementById("status-banner"),
    bannerIcon: document.getElementById("banner-icon"),
    bannerMessage: document.getElementById("banner-message"),

    // ERP Status Section
    connectionPill: document.getElementById("connection-pill"),
    connectionText: document.getElementById("connection-text"),
    erpDetailsBox: document.getElementById("erp-details-box"),
    erpHintText: document.getElementById("erp-hint-text"),

    // Upload Section
    uploadSection: document.getElementById("upload-section"),
    fileInput: document.getElementById("file-input"),
    dropzoneBox: document.getElementById("dropzone-box"),
    btnUploadTrigger: document.getElementById("btn-upload-trigger"),
    previewBox: document.getElementById("preview-box"),
    previewImage: document.getElementById("preview-image"),
    previewFilename: document.getElementById("preview-filename"),
    btnChangeImage: document.getElementById("btn-change-image"),
    btnProcessAttendance: document.getElementById("btn-process-attendance"),

    // Processing Section
    processingSection: document.getElementById("processing-section"),

    // Result Section
    resultSection: document.getElementById("result-section"),
    resultRecordsCount: document.getElementById("result-records-count"),
    resPresent: document.getElementById("res-present"),
    resAbsent: document.getElementById("res-absent"),
    resLate: document.getElementById("res-late"),
    resUnknown: document.getElementById("res-unknown"),
    detectedRosterList: document.getElementById("detected-roster-list"),
    btnProcessAgain: document.getElementById("btn-process-again"),
  };

  // State
  let currentTabId = null;
  let isConnected = false;
  let selectedFile = null;
  let detectedStudentCount = 0;

  /**
   * Display a status toast banner (success, error, or info)
   */
  function showBanner(message, type = "info") {
    UI.statusBanner.className = `status-banner banner-${type}`;
    UI.bannerIcon.textContent = type === "success" ? "✓" : type === "error" ? "⚠" : "ℹ";
    UI.bannerMessage.textContent = message;
    UI.statusBanner.classList.remove("hidden");
  }

  function hideBanner() {
    UI.statusBanner.classList.add("hidden");
  }

  /**
   * Set the ERP connection UI state
   */
  function setConnectionStatus(status, hintText) {
    UI.connectionPill.className = `status-pill status-${status}`;

    if (status === "connected") {
      UI.connectionText.textContent = "ERP Connected";
      UI.erpHintText.textContent = hintText || `${detectedStudentCount} students detected`;
      isConnected = true;
    } else if (status === "disconnected") {
      UI.connectionText.textContent = "ERP Not Detected";
      UI.erpHintText.textContent = hintText || "Open the Mock ERP Attendance page to begin.";
      isConnected = false;
    } else {
      UI.connectionText.textContent = "Checking ERP...";
      UI.erpHintText.textContent = hintText || "Detecting active classroom ERP page...";
      isConnected = false;
    }
  }

  /**
   * Query active tab and check page status with content script
   */
  async function checkActiveTab() {
    setConnectionStatus("checking", "Connecting to active tab...");
    hideBanner();

    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tabs || tabs.length === 0) {
        setConnectionStatus("disconnected", "No active browser tab found.");
        return;
      }

      currentTabId = tabs[0].id;
      const tabUrl = tabs[0].url || "";

      // Verify host is localhost or 127.0.0.1
      if (!tabUrl.startsWith("http://localhost") && !tabUrl.startsWith("http://127.0.0.1")) {
        setConnectionStatus(
          "disconnected",
          "Open the Mock ERP attendance page (e.g. http://localhost:3000)."
        );
        return;
      }

      // Send DETECT_PAGE message to content script
      chrome.tabs.sendMessage(currentTabId, { action: "DETECT_PAGE" }, (response) => {
        if (chrome.runtime.lastError) {
          setConnectionStatus(
            "disconnected",
            "Please refresh the ERP page and reopen the extension."
          );
          return;
        }

        if (response && response.isDetected) {
          detectedStudentCount = response.studentCount || (response.stats && response.stats.total) || 60;
          setConnectionStatus("connected", `${detectedStudentCount} students detected`);
        } else {
          setConnectionStatus(
            "disconnected",
            (response && response.message) || "Open the Mock ERP Attendance page first."
          );
        }
      });
    } catch (err) {
      console.error("[Attendance AI] Error inspecting active tab:", err);
      setConnectionStatus("disconnected", "Unable to inspect active tab.");
    }
  }

  /**
   * Handle image selection via file input
   */
  function handleFileSelected(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ["image/jpeg", "image/png", "image/jpg", "image/webp"];
    if (!validTypes.includes(file.type.toLowerCase())) {
      showBanner("Please upload a valid attendance image (JPG, PNG, or WebP).", "error");
      return;
    }

    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      showBanner("Image is too large. Maximum size is 10MB.", "error");
      return;
    }

    selectedFile = file;
    hideBanner();

    // Show Image Preview
    const reader = new FileReader();
    reader.onload = function (e) {
      UI.previewImage.src = e.target.result;
      UI.previewFilename.textContent = file.name;
      UI.dropzoneBox.classList.add("hidden");
      UI.previewBox.classList.remove("hidden");
      UI.btnProcessAttendance.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  /**
   * Reset file selection back to initial dropzone state
   */
  function resetFileSelection() {
    selectedFile = null;
    UI.fileInput.value = "";
    UI.previewImage.src = "";
    UI.previewFilename.textContent = "";
    UI.previewBox.classList.add("hidden");
    UI.dropzoneBox.classList.remove("hidden");
    UI.btnProcessAttendance.disabled = true;
  }

  /**
   * Process Attendance Button Click Handler
   * Sends image to backend and displays structured result.
   */
  async function handleProcessAttendance() {
    if (!selectedFile) {
      showBanner("Please select an attendance image first.", "error");
      return;
    }

    hideBanner();

    // Step 1: Transition to Processing State (non-blocking)
    UI.uploadSection.classList.add("hidden");
    UI.resultSection.classList.add("hidden");
    UI.processingSection.classList.remove("hidden");

    try {
      // Step 2: Call FastAPI Backend
      const result = await apiClient.processAttendanceImage(selectedFile);

      // Step 3: Transition to Result View
      UI.processingSection.classList.add("hidden");
      displayAttendanceResult(result);

    } catch (err) {
      console.error("[Attendance AI] Process Attendance failed:", err);
      // Return to upload view and show error message
      UI.processingSection.classList.add("hidden");
      UI.uploadSection.classList.remove("hidden");

      const message = err.message || "Unable to analyze the attendance image.";
      showBanner(message, "error");
    }
  }

  /**
   * Display structured attendance results returned by AI
   */
  function displayAttendanceResult(result) {
    if (!result || !result.success || !Array.isArray(result.attendance)) {
      UI.uploadSection.classList.remove("hidden");
      showBanner("No attendance information could be detected.", "error");
      return;
    }

    const { attendance, summary } = result;

    // 1. Update records count tag
    const total = summary ? summary.total_detected : attendance.length;
    UI.resultRecordsCount.textContent = `${total} records detected`;

    // 2. Update Breakdown Numbers
    UI.resPresent.textContent = summary ? summary.present : 0;
    UI.resAbsent.textContent = summary ? summary.absent : 0;
    UI.resLate.textContent = summary ? summary.late : 0;
    UI.resUnknown.textContent = summary ? summary.unknown : 0;

    // 3. Render Detected Student Items List
    UI.detectedRosterList.innerHTML = "";

    if (attendance.length === 0) {
      const emptyLi = document.createElement("li");
      emptyLi.className = "detected-item";
      emptyLi.style.justifyContent = "center";
      emptyLi.style.color = "var(--color-text-muted)";
      emptyLi.textContent = "No attendance rows extracted.";
      UI.detectedRosterList.appendChild(emptyLi);
    } else {
      attendance.forEach((item) => {
        const li = document.createElement("li");
        li.className = "detected-item";

        // Info container (identifier + name)
        const infoDiv = document.createElement("div");
        infoDiv.className = "detected-student-info";

        if (item.raw_identifier) {
          const rollSpan = document.createElement("span");
          rollSpan.className = "detected-roll";
          rollSpan.textContent = `#${item.raw_identifier}`;
          infoDiv.appendChild(rollSpan);
        }

        const nameSpan = document.createElement("span");
        nameSpan.className = "detected-name";
        nameSpan.textContent = item.raw_name || "Unknown Student";
        infoDiv.appendChild(nameSpan);

        // Badges container (Status badge + Confidence pill)
        const badgesDiv = document.createElement("div");
        badgesDiv.className = "detected-badges";

        const badge = document.createElement("span");
        const statusLower = (item.status || "UNKNOWN").toLowerCase();
        badge.className = `roster-badge badge-${statusLower}`;
        badge.textContent = item.status || "UNKNOWN";

        const confPill = document.createElement("span");
        confPill.className = "confidence-pill";
        const confPercent = Math.round((item.confidence || 0) * 100);
        confPill.textContent = `${confPercent}%`;
        confPill.title = `AI Confidence: ${item.confidence}`;

        badgesDiv.appendChild(badge);
        badgesDiv.appendChild(confPill);

        li.appendChild(infoDiv);
        li.appendChild(badgesDiv);
        UI.detectedRosterList.appendChild(li);
      });
    }

    // Reveal Result Section
    UI.resultSection.classList.remove("hidden");
    showBanner(`Successfully extracted ${total} attendance records.`, "success");
  }

  /**
   * Reset back to upload view to process another image
   */
  function handleProcessAgain() {
    UI.resultSection.classList.add("hidden");
    UI.processingSection.classList.add("hidden");
    UI.uploadSection.classList.remove("hidden");
    resetFileSelection();
    hideBanner();
  }

  /**
   * Event Listeners
   */
  function bindEvents() {
    // File input trigger
    UI.btnUploadTrigger.addEventListener("click", () => {
      UI.fileInput.click();
    });

    UI.fileInput.addEventListener("change", handleFileSelected);

    // Change image action
    UI.btnChangeImage.addEventListener("click", () => {
      UI.fileInput.click();
    });

    // Process Attendance
    UI.btnProcessAttendance.addEventListener("click", handleProcessAttendance);

    // Process Again
    UI.btnProcessAgain.addEventListener("click", handleProcessAgain);
  }

  // Initialization on DOM ready
  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    checkActiveTab();
  });
})();
