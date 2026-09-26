/**
 * Mock ERP Application Logic
 * Implements the core faculty workflow: login, dashboard, attendance management,
 * history tracking, and student roster.
 *
 * Specially designed as a stable, predictable DOM target for the AI Attendance
 * Chrome Extension (Manifest V3) integration testing.
 */

(function () {
  "use strict";

  // Application State
  const AppState = {
    isAuthenticated: false,
    currentUser: null,
    currentView: "login", // 'login', 'dashboard', 'attendance', 'history', 'students', 'subjects'
    currentSession: {
      date: "2026-09-26",
      classId: "BCA-2",
      section: "Section A",
      subjectCode: "CS-401",
      isSubmitted: false,
    },
    // Map of studentId -> { status: 'UNMARKED' | 'PRESENT' | 'ABSENT' | 'LATE', remarks: '', modified: false }
    attendanceRecords: new Map(),
  };

  // DOM Elements Cache
  const DOM = {};

  /**
   * Initialize DOM references
   */
  function cacheDOM() {
    DOM.body = document.body;
    DOM.appShell = document.getElementById("app-shell");
    DOM.viewLogin = document.getElementById("view-login");
    DOM.viewDashboard = document.getElementById("view-dashboard");
    DOM.viewAttendance = document.getElementById("view-attendance");
    DOM.viewHistory = document.getElementById("view-history");
    DOM.viewStudents = document.getElementById("view-students");
    DOM.viewSubjects = document.getElementById("view-subjects");

    // Login
    DOM.loginForm = document.getElementById("login-form");
    DOM.usernameInput = document.getElementById("username");
    DOM.passwordInput = document.getElementById("password");
    DOM.btnQuickDemo = document.getElementById("btn-quick-demo-login");

    // Header & User
    DOM.headerUserName = document.getElementById("header-user-name");
    DOM.headerUserRole = document.getElementById("header-user-role");
    DOM.userAvatar = document.getElementById("user-avatar");
    DOM.btnLogout = document.getElementById("btn-logout");

    // Navigation
    DOM.navItems = document.querySelectorAll(".nav-item");

    // Attendance View Controls
    DOM.attDate = document.getElementById("att-date");
    DOM.attClass = document.getElementById("att-class");
    DOM.attSection = document.getElementById("att-section");
    DOM.attSubject = document.getElementById("att-subject");
    DOM.btnLoadSession = document.getElementById("btn-load-session");
    DOM.attSessionStatusTag = document.getElementById("attendance-session-status-tag");

    // Stat Pills
    DOM.statTotal = document.getElementById("stat-pill-total");
    DOM.statPresent = document.getElementById("stat-pill-present");
    DOM.statAbsent = document.getElementById("stat-pill-absent");
    DOM.statLate = document.getElementById("stat-pill-late");
    DOM.statUnmarked = document.getElementById("stat-pill-unmarked");

    // Table
    DOM.attendanceTable = document.getElementById("attendance-table");
    DOM.attendanceTableBody = document.getElementById("attendance-table-body");
    DOM.searchStudentsInput = document.getElementById("search-students-input");

    // Bulk buttons
    DOM.btnMarkAllPresent = document.getElementById("btn-mark-all-present");
    DOM.btnMarkAllAbsent = document.getElementById("btn-mark-all-absent");
    DOM.btnClearAttendance = document.getElementById("btn-clear-attendance");
    DOM.btnResetBar = document.getElementById("btn-reset-attendance-bar");
    DOM.btnSubmitAttendance = document.getElementById("btn-submit-attendance");

    // Modal
    DOM.modalOverlay = document.getElementById("submit-confirm-modal");
    DOM.btnModalClose = document.getElementById("btn-modal-close");
    DOM.btnModalCancel = document.getElementById("btn-modal-cancel");
    DOM.btnModalConfirm = document.getElementById("btn-modal-confirm-submit");
    DOM.modalSummaryDate = document.getElementById("modal-summary-date");
    DOM.modalSummaryClass = document.getElementById("modal-summary-class");
    DOM.modalSummarySubject = document.getElementById("modal-summary-subject");
    DOM.modalSummaryTotal = document.getElementById("modal-summary-total");
    DOM.modalSummaryPresent = document.getElementById("modal-summary-present");
    DOM.modalSummaryAbsent = document.getElementById("modal-summary-absent");
    DOM.modalSummaryLate = document.getElementById("modal-summary-late");
    DOM.modalSummaryUnmarked = document.getElementById("modal-summary-unmarked");
    DOM.modalUnmarkedWarning = document.getElementById("modal-unmarked-warning");
    DOM.modalUnmarkedWarningText = document.getElementById("modal-unmarked-warning-text");

    // Toast Container
    DOM.toastContainer = document.getElementById("toast-container");

    // Secondary views
    DOM.historyTableBody = document.getElementById("history-table-body");
    DOM.rosterTableBody = document.getElementById("roster-table-body");
    DOM.rosterSearchInput = document.getElementById("roster-search-input");
    DOM.subjectsTableBody = document.getElementById("subjects-table-body");

    // Dashboard shortcuts
    DOM.btnDashTakeAtt = document.getElementById("btn-dash-take-att");
    DOM.btnGotoAttendanceCard1 = document.getElementById("btn-goto-attendance-card1");
    DOM.btnGotoAttendanceCard2 = document.getElementById("btn-goto-attendance-card2");
    DOM.dashPendingCount = document.getElementById("dash-pending-count");
    DOM.dashCard1Badge = document.getElementById("dash-card1-badge");

    // Drawer
    DOM.drawerHeader = document.getElementById("drawer-toggle-header");
    DOM.drawerBody = document.getElementById("drawer-body");
    DOM.drawerToggleIcon = document.getElementById("drawer-toggle-icon");
    DOM.btnScenarioAllPresent = document.getElementById("scenario-all-present");
    DOM.btnScenarioSomeAbsent = document.getElementById("scenario-some-absent");
    DOM.btnScenarioSomeLate = document.getElementById("scenario-some-late");
    DOM.btnScenarioMixed = document.getElementById("scenario-mixed");
    DOM.btnScenarioInspectDom = document.getElementById("scenario-inspect-dom");
    DOM.btnScenarioReset = document.getElementById("scenario-reset");
  }

  /**
   * Initialize Attendance Record Map
   */
  function initAttendanceRecords() {
    AppState.attendanceRecords.clear();
    if (!window.MOCK_DATA || !window.MOCK_DATA.students) {
      console.error("MOCK_DATA not loaded properly.");
      return;
    }

    window.MOCK_DATA.students.forEach((student) => {
      AppState.attendanceRecords.set(student.studentId, {
        rollNumber: student.rollNumber,
        studentId: student.studentId,
        name: student.name,
        status: "UNMARKED",
        remarks: "",
        modified: false,
      });
    });
  }

  /**
   * Switch View
   */
  function navigateTo(viewName) {
    AppState.currentView = viewName;
    DOM.body.dataset.erpPage = viewName;

    const views = [
      { name: "login", el: DOM.viewLogin },
      { name: "dashboard", el: DOM.viewDashboard },
      { name: "attendance", el: DOM.viewAttendance },
      { name: "history", el: DOM.viewHistory },
      { name: "students", el: DOM.viewStudents },
      { name: "subjects", el: DOM.viewSubjects },
    ];

    if (viewName === "login") {
      DOM.viewLogin.style.display = "flex";
      DOM.appShell.style.display = "none";
    } else {
      DOM.viewLogin.style.display = "none";
      DOM.appShell.style.display = "flex";

      views.forEach((v) => {
        if (v.name !== "login" && v.el) {
          v.el.style.display = v.name === viewName ? "block" : "none";
        }
      });

      // Update sidebar active status
      DOM.navItems.forEach((item) => {
        if (item.dataset.nav === viewName) {
          item.classList.add("active");
        } else {
          item.classList.remove("active");
        }
      });
    }

    // View specific refreshes
    if (viewName === "attendance") {
      renderAttendanceTable();
      updateAttendanceStats();
    } else if (viewName === "history") {
      renderHistoryTable();
    } else if (viewName === "students") {
      renderStudentsRoster();
    } else if (viewName === "subjects") {
      renderSubjectsTable();
    }

    window.scrollTo(0, 0);
  }

  /**
   * Perform Login
   */
  function login(user) {
    AppState.isAuthenticated = true;
    AppState.currentUser = user || window.MOCK_DATA.currentUser;

    if (DOM.headerUserName) DOM.headerUserName.textContent = AppState.currentUser.name;
    if (DOM.headerUserRole) DOM.headerUserRole.textContent = `${AppState.currentUser.designation} (${AppState.currentUser.department})`;
    if (DOM.userAvatar) DOM.userAvatar.textContent = AppState.currentUser.avatar;

    navigateTo("attendance");
    showToast(`Welcome back, ${AppState.currentUser.name}! Logged into Academic ERP.`, "success");
  }

  /**
   * Perform Logout
   */
  function logout() {
    AppState.isAuthenticated = false;
    AppState.currentUser = null;
    navigateTo("login");
    showToast("You have been signed out.", "info");
  }

  /**
   * Render Attendance Table (60 Students)
   * Ensures crystal-clear, standard DOM structure for Chrome Extension extraction.
   */
  function renderAttendanceTable(filterQuery = "") {
    if (!DOM.attendanceTableBody) return;

    const query = filterQuery.trim().toLowerCase();
    DOM.attendanceTableBody.innerHTML = "";

    window.MOCK_DATA.students.forEach((student) => {
      const record = AppState.attendanceRecords.get(student.studentId) || {
        status: "UNMARKED",
        remarks: "",
      };

      // Search filtering
      if (query) {
        const matchesName = student.name.toLowerCase().includes(query);
        const matchesRoll = student.rollNumber.toLowerCase().includes(query);
        const matchesId = student.studentId.toLowerCase().includes(query);
        if (!matchesName && !matchesRoll && !matchesId) {
          return;
        }
      }

      const tr = document.createElement("tr");
      tr.setAttribute("data-student-row", "true");
      tr.setAttribute("data-student-id", student.studentId);
      tr.setAttribute("data-roll-number", student.rollNumber);
      tr.setAttribute("data-student-name", student.name);
      tr.setAttribute("data-attendance-state", record.status);
      tr.id = `row-${student.studentId}`;

      // Column 1: Roll Number
      const tdRoll = document.createElement("td");
      tdRoll.className = "col-roll";
      tdRoll.setAttribute("data-field", "roll-number");
      tdRoll.textContent = student.rollNumber;
      tr.appendChild(tdRoll);

      // Column 2: Student ID
      const tdId = document.createElement("td");
      tdId.className = "col-id";
      tdId.setAttribute("data-field", "student-id");
      tdId.textContent = student.studentId;
      tr.appendChild(tdId);

      // Column 3: Student Name
      const tdName = document.createElement("td");
      tdName.className = "col-name";
      tdName.setAttribute("data-field", "student-name");
      tdName.innerHTML = `
        <span class="student-name-text">${escapeHtml(student.name)}</span>
        <span class="student-email-sub">${escapeHtml(student.email)}</span>
      `;
      tr.appendChild(tdName);

      // Column 4: Attendance Select Control
      const tdControl = document.createElement("td");
      tdControl.className = "col-status-control";
      tdControl.setAttribute("data-field", "attendance-control");

      const select = document.createElement("select");
      select.className = "attendance-select";
      select.setAttribute("data-attendance-control", "true");
      select.setAttribute("data-student-id", student.studentId);
      select.setAttribute("data-roll-number", student.rollNumber);
      select.setAttribute("name", `attendance_${student.studentId}`);
      select.id = `attendance-select-${student.studentId}`;
      select.setAttribute("data-selected-state", record.status);

      const options = [
        { value: "PRESENT", label: "Present" },
        { value: "ABSENT", label: "Absent" },
        { value: "LATE", label: "Late" },
        { value: "UNMARKED", label: "Unmarked" },
      ];

      options.forEach((opt) => {
        const optionEl = document.createElement("option");
        optionEl.value = opt.value;
        optionEl.textContent = opt.label;
        if (record.status === opt.value) {
          optionEl.selected = true;
        }
        select.appendChild(optionEl);
      });

      // Event listener for teacher or extension modification
      select.addEventListener("change", function (e) {
        handleAttendanceChange(student.studentId, e.target.value, false);
      });

      tdControl.appendChild(select);
      tr.appendChild(tdControl);

      // Column 5: Status Indicator Badge
      const tdBadge = document.createElement("td");
      tdBadge.className = "col-badge";
      tdBadge.setAttribute("data-field", "status-badge");
      tdBadge.innerHTML = getStatusBadgeHtml(record.status);
      tr.appendChild(tdBadge);

      // Column 6: Remarks Input
      const tdRemarks = document.createElement("td");
      tdRemarks.className = "col-remarks";
      tdRemarks.setAttribute("data-field", "remarks");

      const remarksInput = document.createElement("input");
      remarksInput.type = "text";
      remarksInput.className = "remarks-input";
      remarksInput.placeholder = "Optional note...";
      remarksInput.value = record.remarks || "";
      remarksInput.setAttribute("data-remarks-control", "true");
      remarksInput.setAttribute("data-student-id", student.studentId);
      remarksInput.addEventListener("input", function (e) {
        const rec = AppState.attendanceRecords.get(student.studentId);
        if (rec) rec.remarks = e.target.value;
      });

      tdRemarks.appendChild(remarksInput);
      tr.appendChild(tdRemarks);

      DOM.attendanceTableBody.appendChild(tr);
    });
  }

  /**
   * Return HTML for status badge
   */
  function getStatusBadgeHtml(status) {
    const s = (status || "UNMARKED").toUpperCase();
    const classMap = {
      PRESENT: "status-present",
      ABSENT: "status-absent",
      LATE: "status-late",
      UNMARKED: "status-unmarked",
    };
    const labelMap = {
      PRESENT: "Present",
      ABSENT: "Absent",
      LATE: "Late",
      UNMARKED: "Unmarked",
    };

    const cssClass = classMap[s] || "status-unmarked";
    const label = labelMap[s] || "Unmarked";
    return `<span class="status-badge ${cssClass}" data-status-indicator="true">${label}</span>`;
  }

  /**
   * Handle attendance change for a student (both manual or via Chrome Extension)
   */
  function handleAttendanceChange(studentId, newStatus, isProgrammatic = false) {
    const validStatuses = ["PRESENT", "ABSENT", "LATE", "UNMARKED"];
    const status = validStatuses.includes(newStatus) ? newStatus : "UNMARKED";

    const record = AppState.attendanceRecords.get(studentId);
    if (!record) return;

    record.status = status;
    record.modified = true;

    // Update row DOM
    const row = document.getElementById(`row-${studentId}`);
    if (row) {
      row.setAttribute("data-attendance-state", status);

      // If programmatically updated (e.g. by AI extension or test scenario)
      if (isProgrammatic) {
        row.classList.add("row-ai-applied");
      }

      // Update select value if not already matching
      const select = row.querySelector(`select[data-attendance-control="true"]`);
      if (select && select.value !== status) {
        select.value = status;
      }
      if (select) {
        select.setAttribute("data-selected-state", status);
      }

      // Update badge cell
      const badgeCell = row.querySelector('[data-field="status-badge"]');
      if (badgeCell) {
        badgeCell.innerHTML = getStatusBadgeHtml(status);
      }
    }

    updateAttendanceStats();
  }

  /**
   * Recalculate and update the stats pills
   */
  function updateAttendanceStats() {
    let present = 0;
    let absent = 0;
    let late = 0;
    let unmarked = 0;

    AppState.attendanceRecords.forEach((record) => {
      switch (record.status) {
        case "PRESENT":
          present++;
          break;
        case "ABSENT":
          absent++;
          break;
        case "LATE":
          late++;
          break;
        default:
          unmarked++;
          break;
      }
    });

    const total = AppState.attendanceRecords.size;

    if (DOM.statTotal) DOM.statTotal.textContent = `Total: ${total}`;
    if (DOM.statPresent) DOM.statPresent.textContent = `Present: ${present}`;
    if (DOM.statAbsent) DOM.statAbsent.textContent = `Absent: ${absent}`;
    if (DOM.statLate) DOM.statLate.textContent = `Late: ${late}`;
    if (DOM.statUnmarked) DOM.statUnmarked.textContent = `Unmarked: ${unmarked}`;

    return { total, present, absent, late, unmarked };
  }

  /**
   * Mark All Students with a given status
   */
  function setAllAttendance(status) {
    AppState.attendanceRecords.forEach((record, studentId) => {
      handleAttendanceChange(studentId, status, false);
    });
    showToast(`All 60 students marked as ${status.toLowerCase()}.`, "info");
  }

  /**
   * Open Submission Confirmation Modal
   */
  function openSubmissionModal() {
    const stats = updateAttendanceStats();

    const dateVal = DOM.attDate ? DOM.attDate.value : AppState.currentSession.date;
    const formattedDate = formatDateDisplay(dateVal);

    if (DOM.modalSummaryDate) DOM.modalSummaryDate.textContent = formattedDate;
    if (DOM.modalSummaryClass) DOM.modalSummaryClass.textContent = "BCA - 2nd Year (Sec A)";
    if (DOM.modalSummarySubject) DOM.modalSummarySubject.textContent = "Database Management Systems (CS-401)";
    if (DOM.modalSummaryTotal) DOM.modalSummaryTotal.textContent = stats.total;
    if (DOM.modalSummaryPresent) DOM.modalSummaryPresent.textContent = stats.present;
    if (DOM.modalSummaryAbsent) DOM.modalSummaryAbsent.textContent = stats.absent;
    if (DOM.modalSummaryLate) DOM.modalSummaryLate.textContent = stats.late;
    if (DOM.modalSummaryUnmarked) DOM.modalSummaryUnmarked.textContent = stats.unmarked;

    if (stats.unmarked > 0) {
      if (DOM.modalUnmarkedWarning) DOM.modalUnmarkedWarning.style.display = "flex";
      if (DOM.modalUnmarkedWarningText) {
        DOM.modalUnmarkedWarningText.textContent = `Caution: ${stats.unmarked} student(s) remain Unmarked. Are you sure you want to proceed?`;
      }
    } else {
      if (DOM.modalUnmarkedWarning) DOM.modalUnmarkedWarning.style.display = "none";
    }

    if (DOM.modalOverlay) {
      DOM.modalOverlay.classList.add("active");
    }
  }

  /**
   * Close Submission Modal
   */
  function closeSubmissionModal() {
    if (DOM.modalOverlay) {
      DOM.modalOverlay.classList.remove("active");
    }
  }

  /**
   * Commit Official Attendance Submission (Safety Rule: Manual confirmation only)
   */
  function commitAttendanceSubmission() {
    closeSubmissionModal();

    const stats = updateAttendanceStats();
    const dateVal = DOM.attDate ? DOM.attDate.value : AppState.currentSession.date;
    const formattedDate = formatDateDisplay(dateVal);

    // Create session history record
    const newSession = {
      id: `ATT-${Date.now().toString().slice(-6)}`,
      date: dateVal,
      dateFormatted: formattedDate,
      classId: "BCA-2",
      className: "BCA - 2nd Year (Sec A)",
      subjectCode: "CS-401",
      subjectName: "Database Management Systems",
      totalStudents: stats.total,
      present: stats.present,
      absent: stats.absent,
      late: stats.late,
      unmarked: stats.unmarked,
      submittedBy: AppState.currentUser ? AppState.currentUser.name : "Prof. Rajesh Sharma",
      submittedAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      status: "Submitted",
    };

    // Prepend to history
    window.MOCK_DATA.attendanceHistory.unshift(newSession);

    // Update status in UI
    AppState.currentSession.isSubmitted = true;
    if (DOM.attSessionStatusTag) {
      DOM.attSessionStatusTag.className = "status-badge status-present";
      DOM.attSessionStatusTag.textContent = "Status: Submitted to ERP";
    }
    if (DOM.dashPendingCount) {
      DOM.dashPendingCount.textContent = "0";
    }
    if (DOM.dashCard1Badge) {
      DOM.dashCard1Badge.className = "status-badge status-present";
      DOM.dashCard1Badge.textContent = "Submitted";
    }

    showToast("Attendance submitted successfully. 60 student records recorded for BCA 2nd Year - DBMS.", "success");
  }

  /**
   * Render Attendance History
   */
  function renderHistoryTable() {
    if (!DOM.historyTableBody) return;
    DOM.historyTableBody.innerHTML = "";

    window.MOCK_DATA.attendanceHistory.forEach((item) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-family: monospace; font-size: 12px; color: var(--color-primary); font-weight: 600;">${item.id}</td>
        <td><strong>${item.dateFormatted}</strong></td>
        <td>${escapeHtml(item.className)}</td>
        <td>${escapeHtml(item.subjectName)} (${item.subjectCode})</td>
        <td>${item.totalStudents}</td>
        <td><span class="status-badge status-present" style="min-width: 40px;">${item.present}</span></td>
        <td><span class="status-badge status-absent" style="min-width: 40px;">${item.absent}</span></td>
        <td><span class="status-badge status-present">${item.status}</span></td>
        <td style="font-size: 12px; color: var(--color-text-light);">${item.submittedAt || "11:00 AM"}</td>
      `;
      DOM.historyTableBody.appendChild(tr);
    });
  }

  /**
   * Render Students Roster
   */
  function renderStudentsRoster(filterQuery = "") {
    if (!DOM.rosterTableBody) return;
    const query = filterQuery.trim().toLowerCase();
    DOM.rosterTableBody.innerHTML = "";

    window.MOCK_DATA.students.forEach((student) => {
      if (query) {
        const match =
          student.name.toLowerCase().includes(query) ||
          student.rollNumber.toLowerCase().includes(query) ||
          student.studentId.toLowerCase().includes(query);
        if (!match) return;
      }

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-weight: 700; color: var(--color-primary);">${student.rollNumber}</td>
        <td style="font-family: monospace; font-size: 12px;">${student.studentId}</td>
        <td><strong>${escapeHtml(student.name)}</strong></td>
        <td>${student.gender}</td>
        <td style="color: var(--color-text-light); font-size: 12px;">${escapeHtml(student.email)}</td>
        <td>BCA - 2nd Year (Sec A)</td>
        <td><span class="status-badge status-present">Enrolled / Active</span></td>
      `;
      DOM.rosterTableBody.appendChild(tr);
    });
  }

  /**
   * Render Subjects Table
   */
  function renderSubjectsTable() {
    if (!DOM.subjectsTableBody) return;
    DOM.subjectsTableBody.innerHTML = "";

    window.MOCK_DATA.subjects.forEach((sub) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-family: monospace; font-weight: 700; color: var(--color-primary);">${sub.code}</td>
        <td><strong>${escapeHtml(sub.name)}</strong></td>
        <td>BCA 2nd Year</td>
        <td>${sub.credits} Credits</td>
        <td><span class="status-badge status-unmarked">${sub.type}</span></td>
        <td>
          <button type="button" class="btn btn-secondary btn-sm" onclick="MockERP.openSubjectAttendance('${sub.code}')">
            Attendance Sheet
          </button>
        </td>
      `;
      DOM.subjectsTableBody.appendChild(tr);
    });
  }

  /**
   * Toast notification helper
   */
  function showToast(message, type = "info") {
    if (!DOM.toastContainer) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div style="flex: 1;">${escapeHtml(message)}</div>
      <button style="background: none; border: none; cursor: pointer; color: #94a3b8; font-size: 16px;" onclick="this.parentElement.remove();">&times;</button>
    `;

    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
      if (toast.parentElement) {
        toast.remove();
      }
    }, 4500);
  }

  /**
   * Date formatting utility (YYYY-MM-DD -> DD Mon YYYY)
   */
  function formatDateDisplay(isoDateString) {
    if (!isoDateString) return "26 Sep 2026";
    try {
      const [year, month, day] = isoDateString.split("-");
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const mIdx = parseInt(month, 10) - 1;
      return `${parseInt(day, 10)} ${months[mIdx] || "Sep"} ${year}`;
    } catch (e) {
      return isoDateString;
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>"']/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
    });
  }

  /**
   * Set up all Event Listeners
   */
  function setupEventListeners() {
    // 1. Login Form Submit
    if (DOM.loginForm) {
      DOM.loginForm.addEventListener("submit", function (e) {
        e.preventDefault();
        login();
      });
    }

    // 2. Quick Demo Login Button
    if (DOM.btnQuickDemo) {
      DOM.btnQuickDemo.addEventListener("click", function () {
        if (DOM.usernameInput) DOM.usernameInput.value = "teacher@college.edu";
        if (DOM.passwordInput) DOM.passwordInput.value = "demo123";
        login();
      });
    }

    // 3. Logout
    if (DOM.btnLogout) {
      DOM.btnLogout.addEventListener("click", logout);
    }

    // 4. Sidebar Navigation
    DOM.navItems.forEach((item) => {
      item.addEventListener("click", function (e) {
        e.preventDefault();
        const targetView = this.dataset.nav;
        if (targetView) navigateTo(targetView);
      });
    });

    // 5. Dashboard Shortcut Buttons
    if (DOM.btnDashTakeAtt) {
      DOM.btnDashTakeAtt.addEventListener("click", () => navigateTo("attendance"));
    }
    if (DOM.btnGotoAttendanceCard1) {
      DOM.btnGotoAttendanceCard1.addEventListener("click", () => navigateTo("attendance"));
    }
    if (DOM.btnGotoAttendanceCard2) {
      DOM.btnGotoAttendanceCard2.addEventListener("click", () => navigateTo("attendance"));
    }

    // 6. Attendance Table Search
    if (DOM.searchStudentsInput) {
      DOM.searchStudentsInput.addEventListener("input", function (e) {
        renderAttendanceTable(e.target.value);
      });
    }

    // 7. Roster Search
    if (DOM.rosterSearchInput) {
      DOM.rosterSearchInput.addEventListener("input", function (e) {
        renderStudentsRoster(e.target.value);
      });
    }

    // 8. Bulk Attendance Actions
    if (DOM.btnMarkAllPresent) {
      DOM.btnMarkAllPresent.addEventListener("click", () => setAllAttendance("PRESENT"));
    }
    if (DOM.btnMarkAllAbsent) {
      DOM.btnMarkAllAbsent.addEventListener("click", () => setAllAttendance("ABSENT"));
    }
    if (DOM.btnClearAttendance) {
      DOM.btnClearAttendance.addEventListener("click", () => setAllAttendance("UNMARKED"));
    }
    if (DOM.btnResetBar) {
      DOM.btnResetBar.addEventListener("click", () => setAllAttendance("UNMARKED"));
    }

    // 9. Submit Attendance Button
    if (DOM.btnSubmitAttendance) {
      DOM.btnSubmitAttendance.addEventListener("click", openSubmissionModal);
    }

    // 10. Modal controls
    if (DOM.btnModalClose) {
      DOM.btnModalClose.addEventListener("click", closeSubmissionModal);
    }
    if (DOM.btnModalCancel) {
      DOM.btnModalCancel.addEventListener("click", closeSubmissionModal);
    }
    if (DOM.btnModalConfirm) {
      DOM.btnModalConfirm.addEventListener("click", commitAttendanceSubmission);
    }

    // Close modal on click outside
    if (DOM.modalOverlay) {
      DOM.modalOverlay.addEventListener("click", function (e) {
        if (e.target === DOM.modalOverlay) closeSubmissionModal();
      });
    }

    // 11. Testing Drawer Scenarios
    if (DOM.drawerHeader) {
      DOM.drawerHeader.addEventListener("click", function () {
        DOM.drawerBody.classList.toggle("collapsed");
        DOM.drawerToggleIcon.textContent = DOM.drawerBody.classList.contains("collapsed") ? "[Expand]" : "[Collapse]";
      });
    }

    // Scenario 1: All Present
    if (DOM.btnScenarioAllPresent) {
      DOM.btnScenarioAllPresent.addEventListener("click", function () {
        navigateTo("attendance");
        setAllAttendance("PRESENT");
      });
    }

    // Scenario 2: Some Absent
    if (DOM.btnScenarioSomeAbsent) {
      DOM.btnScenarioSomeAbsent.addEventListener("click", function () {
        navigateTo("attendance");
        setAllAttendance("PRESENT");
        const absentees = ["STU003", "STU007", "STU015", "STU023", "STU040"];
        absentees.forEach((id) => handleAttendanceChange(id, "ABSENT", true));
        showToast("Scenario 2: Set 5 students ABSENT (STU003, STU007, STU015, STU023, STU040)", "warning");
      });
    }

    // Scenario 3: Some Late
    if (DOM.btnScenarioSomeLate) {
      DOM.btnScenarioSomeLate.addEventListener("click", function () {
        navigateTo("attendance");
        setAllAttendance("PRESENT");
        const lateStudents = ["STU004", "STU020", "STU041"];
        lateStudents.forEach((id) => handleAttendanceChange(id, "LATE", true));
        showToast("Scenario 3: Set 3 students LATE (STU004, STU020, STU041)", "warning");
      });
    }

    // Scenario 4: Mixed Attendance
    if (DOM.btnScenarioMixed) {
      DOM.btnScenarioMixed.addEventListener("click", function () {
        navigateTo("attendance");
        setAllAttendance("PRESENT");
        const absentees = ["STU003", "STU007", "STU015", "STU023", "STU040"];
        const lateStudents = ["STU004", "STU020", "STU041"];
        absentees.forEach((id) => handleAttendanceChange(id, "ABSENT", true));
        lateStudents.forEach((id) => handleAttendanceChange(id, "LATE", true));
        showToast("Scenario 4: Mixed batch applied (52 Present, 5 Absent, 3 Late)", "info");
      });
    }

    // Scenario: Test DOM Inspection
    if (DOM.btnScenarioInspectDom) {
      DOM.btnScenarioInspectDom.addEventListener("click", function () {
        navigateTo("attendance");
        const extracted = MockERP.extractStudents();
        console.group("Mock ERP - Extracted Student DOM Data (for Chrome Extension):");
        console.table(extracted.map((s) => ({ roll: s.rollNumber, id: s.id, name: s.name, status: s.currentStatus })));
        console.groupEnd();
        showToast(`Extracted ${extracted.length} students. Check Browser DevTools Console!`, "success");
      });
    }

    // Scenario: Reset
    if (DOM.btnScenarioReset) {
      DOM.btnScenarioReset.addEventListener("click", function () {
        navigateTo("attendance");
        setAllAttendance("UNMARKED");
      });
    }
  }

  // =========================================================================
  // GLOBAL ERP ADAPTER INTERFACE
  // Matches the project's ERP Adapter specification in docs/erp_integration.md
  // =========================================================================
  window.MockERP = {
    /**
     * Check if currently on attendance page
     */
    detectPage: function () {
      return (
        document.body.dataset.erpPage === "attendance" ||
        document.getElementById("attendance-table") !== null
      );
    },

    /**
     * Extract students from the DOM in the exact standard structure:
     * Student { id, rollNumber, name, attendanceControl, currentStatus }
     */
    extractStudents: function () {
      const rows = document.querySelectorAll('#attendance-table tbody tr[data-student-row="true"]');
      const students = [];

      rows.forEach((row) => {
        const studentId = row.dataset.studentId || row.getAttribute("data-student-id");
        const rollNumber = row.dataset.rollNumber || row.getAttribute("data-roll-number");
        const name = row.dataset.studentName || row.getAttribute("data-student-name");
        const control = row.querySelector('select[data-attendance-control="true"]');
        const currentStatus = control ? control.value : "UNMARKED";

        students.push({
          id: studentId,
          rollNumber: rollNumber,
          name: name,
          attendanceControl: control,
          currentStatus: currentStatus,
          rowElement: row,
        });
      });

      return students;
    },

    /**
     * Apply attendance result to the ERP controls
     * @param {Array<{ studentId: string, status: string }>} results
     */
    applyAttendance: function (results) {
      if (!Array.isArray(results)) return 0;
      let appliedCount = 0;

      results.forEach((item) => {
        const studentId = item.studentId || item.id;
        const status = (item.status || "").toUpperCase();

        if (studentId && ["PRESENT", "ABSENT", "LATE", "UNMARKED"].includes(status)) {
          // Find the select control in the DOM
          const select = document.querySelector(
            `select[data-attendance-control="true"][data-student-id="${studentId}"]`
          );
          if (select) {
            select.value = status;
            // Dispatch standard change event so ERP listener reacts
            select.dispatchEvent(new Event("change", { bubbles: true }));
            appliedCount++;
          } else {
            handleAttendanceChange(studentId, status, true);
            appliedCount++;
          }
        }
      });

      showToast(`Applied attendance to ${appliedCount} students via MockERPAdapter interface.`, "success");
      return appliedCount;
    },

    /**
     * Get live statistics
     */
    getCurrentStats: function () {
      return updateAttendanceStats();
    },

    /**
     * Programmatic submission
     */
    submitAttendance: function () {
      commitAttendanceSubmission();
    },

    /**
     * Subject navigation shortcut
     */
    openSubjectAttendance: function (subjectCode) {
      if (DOM.attSubject) DOM.attSubject.value = subjectCode;
      navigateTo("attendance");
    },
  };

  /**
   * Bootstrapping on DOMContentLoaded
   */
  document.addEventListener("DOMContentLoaded", function () {
    cacheDOM();
    initAttendanceRecords();
    setupEventListeners();

    // Start with Login view or auto-load if demo requested
    navigateTo("login");
  });
})();
