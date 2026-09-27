/**
 * AI Attendance Backend API Client
 * 
 * Handles communication between Chrome Extension and FastAPI backend.
 * Uses HTTP (localhost:8000) for local development and HTTPS in production.
 * Ensures zero secrets or API keys are embedded in the extension.
 */

class AttendanceApiClient {
  constructor(baseUrl = "http://127.0.0.1:8000/api/v1") {
    this.baseUrl = baseUrl;
  }

  /**
   * Verifies backend connectivity and health.
   * @returns {Promise<Object>}
   */
  async checkHealth() {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(`Backend returned HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      console.warn("[AttendanceApiClient] Health check failed:", err.message);
      throw new Error("AI service is currently unavailable.");
    }
  }

  /**
   * Uploads an attendance register image to the AI backend for OCR/Vision extraction.
   * @param {File|Blob} imageFile 
   * @returns {Promise<{ success: boolean, attendance: Array, summary: Object }>}
   */
  async processAttendanceImage(imageFile) {
    if (!imageFile) {
      throw new Error("Please select an attendance image to process.");
    }

    const formData = new FormData();
    formData.append("file", imageFile, imageFile.name || "attendance.jpg");

    let response;
    try {
      response = await fetch(`${this.baseUrl}/attendance/process`, {
        method: "POST",
        body: formData,
      });
    } catch (networkErr) {
      console.error("[AttendanceApiClient] Network error connecting to backend:", networkErr);
      throw new Error("AI service is currently unavailable. Please verify the backend is running on http://127.0.0.1:8000.");
    }

    let data;
    try {
      data = await response.json();
    } catch (jsonErr) {
      throw new Error("Unable to analyze the attendance image.");
    }

    if (!response.ok || !data || data.success === false) {
      const message = data?.error?.message || "Unable to analyze the attendance image.";
      const err = new Error(message);
      err.code = data?.error?.code || "PROCESSING_ERROR";
      throw err;
    }

    return data;
  }

  /**
   * Sends ERP students and AI attendance records to backend matching engine.
   * @param {Array} erpStudents
   * @param {Array} aiRecords
   * @returns {Promise<Object>}
   */
  async matchAttendance(erpStudents, aiRecords) {
    if (!erpStudents || !Array.isArray(erpStudents)) {
      throw new Error("ERP students list is required for matching.");
    }
    if (!aiRecords || !Array.isArray(aiRecords)) {
      throw new Error("AI attendance records are required for matching.");
    }

    let response;
    try {
      response = await fetch(`${this.baseUrl}/attendance/match`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          erp_students: erpStudents,
          ai_records: aiRecords,
        }),
      });
    } catch (networkErr) {
      console.error("[AttendanceApiClient] Network error connecting to matching engine:", networkErr);
      throw new Error("AI service is currently unavailable. Please verify backend is running on http://127.0.0.1:8000.");
    }

    let data;
    try {
      data = await response.json();
    } catch (jsonErr) {
      throw new Error("Unable to parse student matching response.");
    }

    if (!response.ok || !data || data.success === false) {
      const message = data?.error?.message || "Student matching failed.";
      const err = new Error(message);
      err.code = data?.error?.code || "MATCHING_ERROR";
      throw err;
    }

    return data;
  }
}

if (typeof window !== "undefined") {
  window.AttendanceApiClient = AttendanceApiClient;
}
