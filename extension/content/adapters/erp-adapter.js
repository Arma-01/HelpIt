/**
 * Base ERP Adapter Interface
 * 
 * Standard abstraction layer for educational ERP systems.
 * All ERP-specific integrations (Mock ERP, VMEDULife, SAP, etc.) must extend this class
 * to ensure that content scripts, AI processors, and UI components remain agnostic
 * to underlying DOM structure and ERP quirks.
 */

(function () {
  "use strict";

  class ERPAdapter {
    constructor(adapterName = "BaseERPAdapter") {
      this.adapterName = adapterName;
    }

    /**
     * Determines whether the current active page is the ERP's attendance marking view.
     * @returns {boolean} True if on attendance page, false otherwise.
     */
    detectPage() {
      throw new Error(`[${this.adapterName}] detectPage() must be implemented.`);
    }

    /**
     * Extracts active class/session metadata from the ERP page.
     * @returns {{ className: string, subjectName: string, date: string, section: string }}
     */
    getClassInfo() {
      throw new Error(`[${this.adapterName}] getClassInfo() must be implemented.`);
    }

    /**
     * Reads all student records currently rendered in the ERP attendance roster.
     * @returns {Array<{ studentId: string, rollNumber: string, name: string, status: string, remarks: string }>}
     */
    getStudents() {
      throw new Error(`[${this.adapterName}] getStudents() must be implemented.`);
    }

    /**
     * Calculates the current attendance tally from the ERP roster.
     * @returns {{ total: number, present: number, absent: number, late: number, unmarked: number }}
     */
    getAttendanceStats() {
      throw new Error(`[${this.adapterName}] getAttendanceStats() must be implemented.`);
    }

    /**
     * Applies attendance statuses to matching student rows in the ERP DOM.
     * 
     * Matching Priority:
     * 1. Student ID
     * 2. Roll Number
     * 3. Exact Name
     * 
     * SAFETY RULE: This method MUST NEVER click the final Submit button.
     * 
     * @param {Array<{ studentId?: string, rollNumber?: string, name?: string, status: string, remarks?: string }>} records
     * @returns {{ total: number, applied: number, unmatched: Array<any>, failed: Array<any> }}
     */
    applyAttendance(records) {
      throw new Error(`[${this.adapterName}] applyAttendance() must be implemented.`);
    }

    /**
     * Validates that the applied attendance matches the intended values in the DOM.
     * @returns {{ isValid: boolean, issues: Array<string> }}
     */
    validateChanges() {
      throw new Error(`[${this.adapterName}] validateChanges() must be implemented.`);
    }
  }

  // Attach to window for content script usage
  window.ERPAdapter = ERPAdapter;
})();
