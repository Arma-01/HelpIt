/**
 * Content Script - AI Attendance ERP Assistant
 * 
 * Injected into matching web pages. Discovers the appropriate ERPAdapter,
 * reads student records, and coordinates with the popup to apply attendance.
 */

(function () {
  "use strict";

  // Prevent multiple injections
  if (window.__ATTENDANCE_AI_CONTENT_SCRIPT_LOADED__) {
    return;
  }
  window.__ATTENDANCE_AI_CONTENT_SCRIPT_LOADED__ = true;

  console.log("[Attendance AI] Content script initialized.");

  // Adapter Registry: Supports plug-and-play ERP adapters
  const registeredAdapters = [];

  if (typeof window.MockERPAdapter === "function") {
    registeredAdapters.push(new window.MockERPAdapter());
  }

  /**
   * Discovers which adapter recognizes the current page as an attendance view.
   * @returns {ERPAdapter|null}
   */
  function getActiveAdapter() {
    for (const adapter of registeredAdapters) {
      try {
        if (adapter.detectPage()) {
          return adapter;
        }
      } catch (err) {
        console.warn(`[Attendance AI] Error running detectPage on ${adapter.adapterName}:`, err);
      }
    }
    return null;
  }

  // Chrome Message Listener
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    const action = request.action || request.type;

    try {
      if (action === "PING") {
        sendResponse({ status: "PONG" });
        return true;
      }

      if (action === "DETECT_PAGE") {
        const adapter = getActiveAdapter();
        if (adapter) {
          const stats = adapter.getAttendanceStats();
          const classInfo = adapter.getClassInfo();
          sendResponse({
            isDetected: true,
            adapterName: adapter.adapterName,
            classInfo,
            stats,
            studentCount: stats.total,
          });
        } else {
          sendResponse({
            isDetected: false,
            message: "Mock ERP Attendance page not detected. Please navigate to the Attendance view.",
          });
        }
        return true;
      }

      if (action === "GET_STUDENTS") {
        const adapter = getActiveAdapter();
        if (!adapter) {
          sendResponse({
            success: false,
            error: "ERP Attendance page not active.",
          });
          return true;
        }

        const students = adapter.getStudents();
        const stats = adapter.getAttendanceStats();
        const classInfo = adapter.getClassInfo();

        sendResponse({
          success: true,
          students,
          stats,
          classInfo,
        });
        return true;
      }

      if (action === "APPLY_ATTENDANCE") {
        const adapter = getActiveAdapter();
        if (!adapter) {
          sendResponse({
            success: false,
            error: "ERP Attendance page not active. Please ensure you are on the Attendance page.",
          });
          return true;
        }

        const records = request.records || [];
        const result = adapter.applyAttendance(records);
        const updatedStats = adapter.getAttendanceStats();

        sendResponse({
          success: true,
          result,
          stats: updatedStats,
        });
        return true;
      }

      // Unknown action
      sendResponse({ success: false, error: `Unknown action: ${action}` });
      return true;
    } catch (error) {
      console.error("[Attendance AI] Error processing message:", error);
      sendResponse({ success: false, error: error.message || "An unexpected error occurred in content script." });
      return true;
    }
  });
})();
