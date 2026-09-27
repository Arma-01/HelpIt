/**
 * Attendance AI Extension - Phase 2 Popup Logic
 * 
 * Implements Phase 2: Student Matching, Confidence & Exception Engine
 * 1. Reads classroom students from active Mock ERP page via content script.
 * 2. Uploads attendance sheet image to backend OCR/Vision extraction.
 * 3. Sends AI detected items + ERP roster to backend matching engine.
 * 4. Displays matching breakdown, resolution states, exceptions, and separate confidences.
 * 
 * CRITICAL SAFETY RULES:
 * - Mock ERP attendance table is NOT modified in this phase.
 * - Missing ERP students are NOT automatically marked absent.
 * - Ambiguous matches are NEVER automatically assigned.
 * - Final ERP submit is NOT triggered.
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
    processingTitle: document.getElementById("processing-title"),
    processingSubtitle: document.getElementById("processing-subtitle"),

    // Result Section
    resultSection: document.getElementById("result-section"),
    resultBadgePhase: document.getElementById("result-badge-phase"),

    // Phase 2.2: Attendance Source of Truth (Uploaded Sheet)
    sourceDetectedCount: document.getElementById("source-detected-count"),
    sourcePresentCount: document.getElementById("source-present-count"),
    sourceAbsentCount: document.getElementById("source-absent-count"),

    // Phase 2.2: ERP Student List Reference
    erpStudentsAvailableCount: document.getElementById("erp-students-available-count"),
    erpRosterStatusBadge: document.getElementById("erp-roster-status-badge"),

    // Phase 2: Matching Stats
    matchCountMatched: document.getElementById("match-count-matched"),
    matchCountReview: document.getElementById("match-count-review"),
    matchCountUnmatched: document.getElementById("match-count-unmatched"),

    // Phase 2: Exceptions
    exceptionsBar: document.getElementById("exceptions-bar"),
    exceptionsCountText: document.getElementById("exceptions-count-text"),
    btnToggleExceptions: document.getElementById("btn-toggle-exceptions"),
    exceptionsDrawer: document.getElementById("exceptions-drawer"),
    exceptionsList: document.getElementById("exceptions-list"),

    // Roster List
    detectedRosterList: document.getElementById("detected-roster-list"),
    btnProcessAgain: document.getElementById("btn-process-again"),
  };

  // State
  let currentTabId = null;
  let isConnected = false;
  let selectedFile = null;
  let detectedStudentCount = 0;
  let cachedErpStudents = [];

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
      if (UI.erpStudentsAvailableCount) {
        UI.erpStudentsAvailableCount.textContent = detectedStudentCount;
      }
      if (UI.erpRosterStatusBadge) {
        UI.erpRosterStatusBadge.textContent = "Classroom Roster";
      }
      isConnected = true;
    } else if (status === "disconnected") {
      UI.connectionText.textContent = "ERP Not Detected";
      UI.erpHintText.textContent = hintText || "Open the Mock ERP Attendance page to begin.";
      if (UI.erpStudentsAvailableCount) {
        UI.erpStudentsAvailableCount.textContent = "0";
      }
      if (UI.erpRosterStatusBadge) {
        UI.erpRosterStatusBadge.textContent = "Not Connected";
      }
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
          setConnectionStatus("connected", `${detectedStudentCount} students detected in classroom`);

          // Preload ERP students for matching
          chrome.tabs.sendMessage(currentTabId, { action: "GET_STUDENTS" }, (stuResp) => {
            if (stuResp && stuResp.success && Array.isArray(stuResp.students)) {
              cachedErpStudents = stuResp.students;
            }
          });
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
   * Fetch latest ERP students directly from active tab
   */
  function fetchErpStudentsAsync() {
    return new Promise((resolve) => {
      if (!currentTabId) {
        resolve(cachedErpStudents);
        return;
      }
      chrome.tabs.sendMessage(currentTabId, { action: "GET_STUDENTS" }, (response) => {
        if (chrome.runtime.lastError || !response || !response.success) {
          resolve(cachedErpStudents);
        } else {
          cachedErpStudents = response.students || [];
          resolve(cachedErpStudents);
        }
      });
    });
  }

  /**
   * Process Attendance Button Click Handler
   * Phase 1 (Vision) + Phase 2 (Student Matching & Exception Engine)
   */
  async function handleProcessAttendance() {
    if (!selectedFile) {
      showBanner("Please select an attendance image first.", "error");
      return;
    }

    hideBanner();

    // Step 1: Transition to Processing State
    UI.uploadSection.classList.add("hidden");
    UI.resultSection.classList.add("hidden");
    UI.processingSection.classList.remove("hidden");
    UI.processingTitle.textContent = "Processing attendance...";
    UI.processingSubtitle.textContent = "Analyzing image via Vision AI...";

    try {
      // Step 2: Fetch active ERP students
      const erpStudents = await fetchErpStudentsAsync();

      // Step 3: Run OCR/Vision Extraction (Phase 1)
      const aiResult = await apiClient.processAttendanceImage(selectedFile);

      if (!aiResult || !aiResult.attendance || aiResult.attendance.length === 0) {
        throw new Error("No attendance information could be detected in the image.");
      }

      // Step 4: Run Student Matching Engine (Phase 2)
      if (erpStudents && erpStudents.length > 0) {
        UI.processingSubtitle.textContent = "Matching students with ERP roster...";
        const matchResponse = await apiClient.matchAttendance(erpStudents, aiResult.attendance);

        // Step 5: Transition to Result View with Full Matching Breakdown
        UI.processingSection.classList.add("hidden");
        displayMatchingResult(matchResponse, aiResult.summary);
      } else {
        // Fallback if ERP not connected
        UI.processingSection.classList.add("hidden");
        displayPhase1Fallback(aiResult);
      }

    } catch (err) {
      console.error("[Attendance AI] Process & Match failed:", err);
      UI.processingSection.classList.add("hidden");
      UI.uploadSection.classList.remove("hidden");

      const message = err.message || "Unable to analyze the attendance image.";
      showBanner(message, "error");
    }
  }

  /**
   * Display Phase 2 Structured Matching Results
   */
  function displayMatchingResult(matchData, aiSummary) {
    const { results, summary, exceptions, erp_students_not_detected } = matchData;

    // 1. Attendance Status Breakdown (Strictly PRESENT and ABSENT)
    let presentCount = 0;
    let absentCount = 0;

    results.forEach((item) => {
      const st = (item.status || "ABSENT").toUpperCase();
      if (st === "PRESENT") presentCount++;
      else absentCount++;
    });

    // 2. Uploaded Sheet Source of Truth stats
    const totalDetected = summary.total_ai_records !== undefined ? summary.total_ai_records : results.length;
    if (UI.sourceDetectedCount) UI.sourceDetectedCount.textContent = totalDetected;
    if (UI.sourcePresentCount) UI.sourcePresentCount.textContent = presentCount;
    if (UI.sourceAbsentCount) UI.sourceAbsentCount.textContent = absentCount;

    // 3. ERP Student List Reference
    const erpCount = summary.total_erp_students !== undefined ? summary.total_erp_students : (cachedErpStudents ? cachedErpStudents.length : 0);
    if (UI.erpStudentsAvailableCount) UI.erpStudentsAvailableCount.textContent = erpCount;
    if (UI.erpRosterStatusBadge) UI.erpRosterStatusBadge.textContent = erpCount > 0 ? "Classroom Roster" : "Not Connected";

    // 4. Matching Breakdown Tallies
    if (UI.resultBadgePhase) UI.resultBadgePhase.textContent = "Matching Complete";
    if (UI.matchCountMatched) UI.matchCountMatched.textContent = summary.matched;
    if (UI.matchCountReview) UI.matchCountReview.textContent = summary.needs_review;
    if (UI.matchCountUnmatched) UI.matchCountUnmatched.textContent = summary.unmatched;

    // 5. Handle Exceptions & Missing ERP Students Drawer
    const totalExceptions = (exceptions ? exceptions.length : 0);
    if (totalExceptions > 0) {
      UI.exceptionsBar.classList.remove("hidden");
      UI.exceptionsCountText.textContent = `${totalExceptions} Exception${totalExceptions > 1 ? "s" : ""} Detected`;
      
      // Populate drawer
      UI.exceptionsList.innerHTML = "";
      exceptions.forEach((exc) => {
        const li = document.createElement("li");
        li.className = "exception-item";

        const badgeClass =
          exc.type === "DUPLICATE_DETECTED" ? "exception-badge-dup" :
          exc.type === "AMBIGUOUS_MATCH" ? "exception-badge-ambig" :
          exc.type === "MISSING_ERP_STUDENT" ? "exception-badge-missing" :
          "exception-badge-unmatched";

        const typeLabel =
          exc.type === "DUPLICATE_DETECTED" ? "Duplicate" :
          exc.type === "AMBIGUOUS_MATCH" ? "Needs Review" :
          exc.type === "MISSING_ERP_STUDENT" ? "Not Detected" :
          "Unmatched";

        li.innerHTML = `
          <div style="display:flex; align-items:center; gap:6px;">
            <span class="exception-badge ${badgeClass}">${typeLabel}</span>
            <span class="exception-msg">${exc.message}</span>
          </div>
        `;
        UI.exceptionsList.appendChild(li);
      });
    } else {
      UI.exceptionsBar.classList.add("hidden");
      UI.exceptionsDrawer.classList.add("hidden");
    }

    // 6. Render Matched Records Roster Review Table (Roll | Student | Raw Mark | Status | Match)
    UI.detectedRosterList.innerHTML = "";

    results.forEach((item) => {
      const container = document.createElement("li");
      container.className = "roster-row-container";

      const row = document.createElement("div");
      row.className = "roster-row";

      // 1. Roll
      const rollCol = document.createElement("span");
      rollCol.className = "row-col col-roll";
      const rollNum = item.matched_roll_number || item.raw_identifier || "-";
      rollCol.textContent = rollNum.startsWith("#") ? rollNum : `#${rollNum}`;
      rollCol.title = `Roll Number: ${rollNum}`;

      // 2. Student Name & OCR context
      const nameCol = document.createElement("span");
      nameCol.className = "row-col col-name";
      const displayName = item.matched_name || item.raw_name || "Unknown Student";
      const subInfo = item.matched_name && item.raw_name && item.matched_name !== item.raw_name
        ? `OCR: "${item.raw_name}"`
        : (item.matched_student_id ? `#${item.matched_student_id}` : (item.raw_student_id ? `#${item.raw_student_id}` : ""));
      nameCol.innerHTML = `
        <span class="student-display-name" title="${displayName}">${displayName}</span>
        ${subInfo ? `<span class="raw-ai-name" title="${subInfo}">${subInfo}</span>` : ""}
      `;

      // 3. Raw Mark
      const rawCol = document.createElement("span");
      rawCol.className = "row-col col-raw";
      const rawMark = item.raw_attendance_mark || (item.status === "PRESENT" ? "P" : "A");
      const isPres = (item.status || "ABSENT").toUpperCase() === "PRESENT";
      rawCol.innerHTML = `
        <span class="raw-mark-pill ${isPres ? 'mark-present' : 'mark-absent'}" title="Raw Sheet Mark: '${rawMark}'">${rawMark}</span>
      `;

      // 4. Status
      const statusCol = document.createElement("span");
      statusCol.className = "row-col col-status";
      statusCol.innerHTML = `
        <span class="roster-badge badge-${isPres ? 'present' : 'absent'}">${isPres ? 'PRESENT' : 'ABSENT'}</span>
      `;

      // 5. Match Resolution & Confidences
      const matchCol = document.createElement("span");
      matchCol.className = "row-col col-match";

      const resBadgeClass =
        item.resolution === "MATCHED" ? "badge-resolution-matched" :
        item.resolution === "NEEDS_REVIEW" ? "badge-resolution-review" :
        "badge-resolution-unmatched";

      const resLabel =
        item.resolution === "MATCHED" ? "MATCH" :
        item.resolution === "NEEDS_REVIEW" ? "REVIEW" :
        "UNMATCH";

      const aiConfPct = Math.round((item.ai_confidence || 0) * 100);
      const matchConfPct = Math.round((item.match_confidence || 0) * 100);
      const tooltip = `Resolution: ${item.resolution}\nMethod: ${item.match_method || 'None'}\nAI Extraction Conf: ${aiConfPct}%\nStudent Match Conf: ${matchConfPct}%`;

      matchCol.innerHTML = `
        <span class="exception-badge ${resBadgeClass}" title="${tooltip}">${resLabel}</span>
      `;

      row.appendChild(rollCol);
      row.appendChild(nameCol);
      row.appendChild(rawCol);
      row.appendChild(statusCol);
      row.appendChild(matchCol);
      container.appendChild(row);

      // Candidate preview drawer for ambiguous matches
      if (item.resolution === "NEEDS_REVIEW" && item.candidates && item.candidates.length > 0) {
        const candBox = document.createElement("div");
        candBox.className = "candidates-preview-box";
        candBox.innerHTML = `<div><strong>Possible matches:</strong></div>`;
        item.candidates.slice(0, 3).forEach((c) => {
          const simText = c.similarity ? ` (${Math.round(c.similarity * 100)}%)` : "";
          candBox.innerHTML += `<div class="candidate-entry"><span>• ${c.student_id} — ${c.name}</span><span>${simText}</span></div>`;
        });
        container.appendChild(candBox);
      }

      UI.detectedRosterList.appendChild(container);
    });

    // Reveal Result Section
    UI.resultSection.classList.remove("hidden");
    showBanner(
      `Extraction & Matching Complete: ${summary.matched} Matched, ${summary.needs_review} Need Review, ${summary.unmatched} Unmatched.`,
      "success"
    );
  }

  /**
   * Fallback if Mock ERP is not connected (shows raw AI results)
   */
  function displayPhase1Fallback(result) {
    const { attendance, summary } = result;
    const total = summary ? summary.total_detected : attendance.length;
    let presentCount = 0;
    let absentCount = 0;

    attendance.forEach((item) => {
      const st = (item.status || "ABSENT").toUpperCase();
      if (st === "PRESENT") presentCount++;
      else absentCount++;
    });

    if (UI.sourceDetectedCount) UI.sourceDetectedCount.textContent = total;
    if (UI.sourcePresentCount) UI.sourcePresentCount.textContent = presentCount;
    if (UI.sourceAbsentCount) UI.sourceAbsentCount.textContent = absentCount;

    if (UI.erpStudentsAvailableCount) UI.erpStudentsAvailableCount.textContent = "0";
    if (UI.erpRosterStatusBadge) UI.erpRosterStatusBadge.textContent = "Not Connected";

    if (UI.resultBadgePhase) UI.resultBadgePhase.textContent = "AI Extracted";
    if (UI.matchCountMatched) UI.matchCountMatched.textContent = "-";
    if (UI.matchCountReview) UI.matchCountReview.textContent = "-";
    if (UI.matchCountUnmatched) UI.matchCountUnmatched.textContent = "-";
    if (UI.exceptionsBar) UI.exceptionsBar.classList.add("hidden");

    UI.detectedRosterList.innerHTML = "";
    attendance.forEach((item) => {
      const container = document.createElement("li");
      container.className = "roster-row-container";

      const row = document.createElement("div");
      row.className = "roster-row";

      const rollCol = document.createElement("span");
      rollCol.className = "row-col col-roll";
      const rollNum = item.raw_identifier || "-";
      rollCol.textContent = rollNum.startsWith("#") ? rollNum : `#${rollNum}`;

      const nameCol = document.createElement("span");
      nameCol.className = "row-col col-name";
      const subInfo = item.raw_student_id ? `#${item.raw_student_id}` : "";
      nameCol.innerHTML = `
        <span class="student-display-name">${item.raw_name || "Unknown"}</span>
        ${subInfo ? `<span class="raw-ai-name" title="${subInfo}">${subInfo}</span>` : ""}
      `;

      const rawCol = document.createElement("span");
      rawCol.className = "row-col col-raw";
      const rawMark = item.raw_attendance_mark || (item.status === "PRESENT" ? "P" : "A");
      const isPres = (item.status || "ABSENT").toUpperCase() === "PRESENT";
      rawCol.innerHTML = `
        <span class="raw-mark-pill ${isPres ? 'mark-present' : 'mark-absent'}">${rawMark}</span>
      `;

      const statusCol = document.createElement("span");
      statusCol.className = "row-col col-status";
      statusCol.innerHTML = `
        <span class="roster-badge badge-${isPres ? 'present' : 'absent'}">${isPres ? 'PRESENT' : 'ABSENT'}</span>
      `;

      const matchCol = document.createElement("span");
      matchCol.className = "row-col col-match";
      const confPct = Math.round((item.confidence || 0) * 100);
      matchCol.innerHTML = `<span class="confidence-pill">${confPct}%</span>`;

      row.appendChild(rollCol);
      row.appendChild(nameCol);
      row.appendChild(rawCol);
      row.appendChild(statusCol);
      row.appendChild(matchCol);
      container.appendChild(row);

      UI.detectedRosterList.appendChild(container);
    });

    UI.resultSection.classList.remove("hidden");
    showBanner("Extracted AI records. Connect Mock ERP to run Student Matching.", "info");
  }

  /**
   * Toggle Exceptions Drawer
   */
  function toggleExceptionsDrawer() {
    UI.exceptionsDrawer.classList.toggle("hidden");
    const isNowVisible = !UI.exceptionsDrawer.classList.contains("hidden");
    UI.btnToggleExceptions.textContent = isNowVisible ? "Hide Exceptions" : "View Exceptions";
  }

  /**
   * Reset back to upload view to process another image
   */
  function handleProcessAgain() {
    UI.resultSection.classList.add("hidden");
    UI.processingSection.classList.add("hidden");
    UI.uploadSection.classList.remove("hidden");
    UI.exceptionsDrawer.classList.add("hidden");
    UI.btnToggleExceptions.textContent = "View Exceptions";
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

    // Toggle Exceptions Drawer
    UI.btnToggleExceptions.addEventListener("click", toggleExceptionsDrawer);

    // Process Again
    UI.btnProcessAgain.addEventListener("click", handleProcessAgain);
  }

  // Initialization on DOM ready
  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    checkActiveTab();
  });
})();
