/**
 * Shared DOM Utilities for ERP Adapters
 */

(function () {
  "use strict";

  const DOMUtils = {
    /**
     * Safely dispatches change and input events on a form element.
     */
    triggerChange: function (element) {
      if (!element) return;
      element.dispatchEvent(new Event("change", { bubbles: true }));
      element.dispatchEvent(new Event("input", { bubbles: true }));
    },

    /**
     * Normalizes a student name for matching (removes accents, trims, collapses multiple spaces).
     */
    normalizeName: function (name) {
      if (!name) return "";
      return name
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim();
    },

    /**
     * Strips leading zeros from roll numbers: "001" -> "1".
     */
    stripLeadingZeros: function (str) {
      if (!str) return "";
      return str.replace(/^0+/, "");
    },
  };

  if (typeof window !== "undefined") {
    window.DOMUtils = DOMUtils;
  }
})();
