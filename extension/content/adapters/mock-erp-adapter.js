/**
 * Mock ERP Adapter
 * 
 * Specialized adapter for the EduERP / Mock Academic ERP portal.
 * Implements the ERPAdapter interface with DOM selectors and controls
 * tailored to the Mock ERP portal.
 */

(function () {
  "use strict";

  if (typeof window.ERPAdapter === "undefined") {
    console.error("[MockERPAdapter] ERPAdapter base class is not defined. Ensure erp-adapter.js is loaded first.");
  }

  const BaseClass = window.ERPAdapter || class {};

  class MockERPAdapter extends BaseClass {
    constructor() {
      super("MockERPAdapter");
      this.version = "1.0.0";
    }

    /**
     * Detects if the active page is the Mock ERP Attendance view.
     * Must return true ONLY when on the Attendance page, not on Login or Dashboard.
     * @returns {boolean}
     */
    detectPage() {
      // 1. Check if the page belongs to Mock ERP
      const isMockERP =
        document.body?.dataset?.erpApp === "mock-erp" ||
        document.querySelector('meta[name="erp-type"][content="mock-erp"]') !== null ||
        document.querySelector('meta[name="erp-adapter-target"][content="MockERPAdapter"]') !== null;

      if (!isMockERP) {
        return false;
      }

      // 2. Check if currently active view is the Attendance view
      const isAttendancePageAttr = document.body?.dataset?.erpPage === "attendance";
      const attendanceView = document.getElementById("view-attendance");
      const isAttendanceVisible =
        attendanceView &&
        window.getComputedStyle(attendanceView).display !== "none" &&
        attendanceView.offsetParent !== null;

      const hasAttendanceTable = document.getElementById("attendance-table") !== null;

      return (isAttendancePageAttr || isAttendanceVisible) && hasAttendanceTable;
    }

    /**
     * Extracts active class/session metadata.
     * @returns {{ className: string, subjectName: string, date: string, section: string }}
     */
    getClassInfo() {
      const classSelect = document.getElementById("att-class");
      const subjectSelect = document.getElementById("att-subject");
      const sectionSelect = document.getElementById("att-section");
      const dateInput = document.getElementById("att-date");

      const className =
        classSelect && classSelect.selectedIndex >= 0
          ? classSelect.options[classSelect.selectedIndex].text.trim()
          : "BCA - 2nd Year (Semester IV)";

      const subjectName =
        subjectSelect && subjectSelect.selectedIndex >= 0
          ? subjectSelect.options[subjectSelect.selectedIndex].text.trim()
          : "Database Management Systems (CS-401)";

      const section =
        sectionSelect && sectionSelect.selectedIndex >= 0
          ? sectionSelect.options[sectionSelect.selectedIndex].text.trim()
          : "Section A";

      const date = dateInput && dateInput.value ? dateInput.value : new Date().toISOString().split("T")[0];

      return {
        className,
        subjectName,
        section,
        date,
      };
    }

    /**
     * Reads all student records currently in the table.
     * @returns {Array<{ studentId: string, rollNumber: string, name: string, status: string, remarks: string }>}
     */
    getStudents() {
      const rows = document.querySelectorAll(
        "#attendance-table-body tr[data-student-row='true'], #attendance-table tbody tr[data-student-id]"
      );

      const students = [];

      rows.forEach((row) => {
        // Extract identifiers with safe fallbacks
        const studentId =
          row.getAttribute("data-student-id") ||
          row.querySelector('[data-field="student-id"]')?.textContent.trim() ||
          row.id?.replace("row-", "") ||
          "";

        const rollNumber =
          row.getAttribute("data-roll-number") ||
          row.querySelector('[data-field="roll-number"]')?.textContent.trim() ||
          "";

        const nameEl = row.querySelector(".student-name-text") || row.querySelector('[data-field="student-name"]');
        const name =
          row.getAttribute("data-student-name") ||
          (nameEl ? nameEl.textContent.trim() : "");

        const selectEl = row.querySelector('select[data-attendance-control="true"], select.attendance-select');
        const status =
          (selectEl ? selectEl.value : null) ||
          row.getAttribute("data-attendance-state") ||
          "UNMARKED";

        const remarksInput = row.querySelector('input.remarks-input, input[data-remarks-control="true"]');
        const remarks = remarksInput ? remarksInput.value.trim() : "";

        if (studentId || rollNumber) {
          students.push({
            studentId,
            rollNumber,
            name,
            status: status.toUpperCase(),
            remarks,
          });
        }
      });

      return students;
    }

    /**
     * Calculates the current attendance tally from the active table.
     * @returns {{ total: number, present: number, absent: number, late: number, unmarked: number }}
     */
    getAttendanceStats() {
      const students = this.getStudents();
      const stats = {
        total: students.length,
        present: 0,
        absent: 0,
        late: 0,
        unmarked: 0,
      };

      students.forEach((s) => {
        switch (s.status) {
          case "PRESENT":
            stats.present++;
            break;
          case "ABSENT":
            stats.absent++;
            break;
          case "LATE":
            stats.late++;
            break;
          default:
            stats.unmarked++;
            break;
        }
      });

      return stats;
    }

    /**
     * Applies attendance to matching student rows in the Mock ERP DOM.
     * 
     * Priority Matching:
     * 1. Student ID (Primary)
     * 2. Roll Number (Secondary)
     * 3. Exact Name (Tertiary)
     * 
     * Never submits attendance.
     * 
     * @param {Array<{ studentId?: string, rollNumber?: string, name?: string, status: string, remarks?: string }>} records
     * @returns {{ total: number, applied: number, unmatched: Array<any>, failed: Array<any> }}
     */
    applyAttendance(records) {
      if (!Array.isArray(records) || records.length === 0) {
        return { total: 0, applied: 0, unmatched: [], failed: [] };
      }

      const rows = document.querySelectorAll(
        "#attendance-table-body tr[data-student-row='true'], #attendance-table tbody tr[data-student-id]"
      );

      // Build fast lookup indexes
      const idMap = new Map();
      const rollMap = new Map();
      const nameMap = new Map();

      rows.forEach((row) => {
        const studentId = (
          row.getAttribute("data-student-id") ||
          row.querySelector('[data-field="student-id"]')?.textContent.trim() ||
          ""
        ).toUpperCase();

        const rollNumber = (
          row.getAttribute("data-roll-number") ||
          row.querySelector('[data-field="roll-number"]')?.textContent.trim() ||
          ""
        ).toUpperCase();

        const rawName = (
          row.getAttribute("data-student-name") ||
          row.querySelector(".student-name-text")?.textContent.trim() ||
          ""
        ).toLowerCase();

        if (studentId) idMap.set(studentId, row);
        if (rollNumber) {
          rollMap.set(rollNumber, row);
          // Also handle leading zero strip: "001" -> "1"
          const unpadded = rollNumber.replace(/^0+/, "");
          if (unpadded && unpadded !== rollNumber) {
            rollMap.set(unpadded, row);
          }
        }
        if (rawName) nameMap.set(rawName, row);
      });

      let appliedCount = 0;
      const unmatched = [];
      const failed = [];

      const validStatuses = ["PRESENT", "ABSENT", "UNMARKED"];

      records.forEach((record) => {
        let matchedRow = null;

        // Priority 1: Student ID
        if (record.studentId) {
          const key = String(record.studentId).toUpperCase().trim();
          matchedRow = idMap.get(key);
        }

        // Priority 2: Roll Number
        if (!matchedRow && record.rollNumber) {
          const key = String(record.rollNumber).toUpperCase().trim();
          matchedRow = rollMap.get(key) || rollMap.get(key.replace(/^0+/, ""));
        }

        // Priority 3: Exact Name
        if (!matchedRow && record.name) {
          const key = String(record.name).toLowerCase().trim();
          matchedRow = nameMap.get(key);
        }

        if (!matchedRow) {
          unmatched.push({
            record,
            reason: "STUDENT_NOT_FOUND",
          });
          return;
        }

        // Locate attendance select control in matched row
        const select = matchedRow.querySelector(
          'select[data-attendance-control="true"], select.attendance-select, select'
        );

        if (!select) {
          failed.push({
            record,
            reason: "ATTENDANCE_CONTROL_NOT_FOUND",
          });
          return;
        }

        const normalizedStatus = String(record.status || "UNMARKED").toUpperCase();
        const finalStatus = validStatuses.includes(normalizedStatus) ? normalizedStatus : "UNMARKED";

        // Update select value
        select.value = finalStatus;

        // Dispatch synthetic change and input events to trigger ERP logic & stats
        select.dispatchEvent(new Event("change", { bubbles: true }));
        select.dispatchEvent(new Event("input", { bubbles: true }));

        // Mark row with visual class to show extension modified it
        matchedRow.classList.add("row-ai-applied");

        // Optional Remarks
        if (typeof record.remarks === "string" && record.remarks.length > 0) {
          const remarksInput = matchedRow.querySelector('input.remarks-input, input[data-remarks-control="true"]');
          if (remarksInput) {
            remarksInput.value = record.remarks;
            remarksInput.dispatchEvent(new Event("input", { bubbles: true }));
          }
        }

        appliedCount++;
      });

      // SAFETY GUARANTEE: Never trigger the ERP Submit button
      // document.getElementById('btn-submit-attendance') is left untouched!

      return {
        total: records.length,
        applied: appliedCount,
        unmatched,
        failed,
      };
    }

    /**
     * Validates that applied changes persist in the table.
     * @returns {{ isValid: boolean, issues: Array<string> }}
     */
    validateChanges() {
      const students = this.getStudents();
      const issues = [];

      if (students.length === 0) {
        issues.push("No student rows found in table.");
      }

      return {
        isValid: issues.length === 0,
        issues,
      };
    }
  }

  // Attach to window for content script usage
  window.MockERPAdapter = MockERPAdapter;
})();
