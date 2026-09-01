import { formatDate, formatDuration, formatCost, getSeverityColor, getVerdictColor, getStatusColor } from "@/lib/utils";

describe("Utility Functions", () => {
  describe("formatDate", () => {
    it("formats ISO date string correctly", () => {
      const date = "2024-01-15T10:30:00Z";
      const formatted = formatDate(date);
      expect(formatted).toContain("Jan");
      expect(formatted).toContain("15");
      expect(formatted).toContain("2024");
    });

    it("formats Date object correctly", () => {
      const date = new Date("2024-01-15T10:30:00Z");
      const formatted = formatDate(date);
      expect(formatted).toContain("Jan");
    });
  });

  describe("formatDuration", () => {
    it("formats milliseconds", () => {
      expect(formatDuration(500)).toBe("500ms");
      expect(formatDuration(999)).toBe("999ms");
    });

    it("formats seconds", () => {
      expect(formatDuration(1500)).toBe("1.5s");
      expect(formatDuration(30000)).toBe("30s");
    });

    it("formats minutes", () => {
      expect(formatDuration(90000)).toBe("1.5m");
      expect(formatDuration(300000)).toBe("5m");
    });
  });

  describe("formatCost", () => {
    it("formats cost with 4 decimal places", () => {
      expect(formatCost(0.12345)).toBe("$0.1235");
      expect(formatCost(1.5)).toBe("$1.5000");
      expect(formatCost(0)).toBe("$0.0000");
    });
  });

  describe("getSeverityColor", () => {
    it("returns correct classes for critical", () => {
      const classes = getSeverityColor("critical");
      expect(classes).toContain("text-red-600");
      expect(classes).toContain("bg-red-50");
    });

    it("returns correct classes for high", () => {
      const classes = getSeverityColor("high");
      expect(classes).toContain("text-orange-600");
    });

    it("returns correct classes for medium", () => {
      const classes = getSeverityColor("medium");
      expect(classes).toContain("text-yellow-600");
    });

    it("returns correct classes for low", () => {
      const classes = getSeverityColor("low");
      expect(classes).toContain("text-blue-600");
    });

    it("returns default for unknown", () => {
      const classes = getSeverityColor("unknown");
      expect(classes).toContain("text-gray-600");
    });
  });

  describe("getVerdictColor", () => {
    it("returns correct classes for PASS", () => {
      const classes = getVerdictColor("PASS");
      expect(classes).toContain("text-green-600");
    });

    it("returns correct classes for FAIL", () => {
      const classes = getVerdictColor("FAIL");
      expect(classes).toContain("text-red-600");
    });

    it("returns correct classes for INCONCLUSIVE", () => {
      const classes = getVerdictColor("INCONCLUSIVE");
      expect(classes).toContain("text-yellow-600");
    });
  });

  describe("getStatusColor", () => {
    it("returns correct classes for completed", () => {
      const classes = getStatusColor("completed");
      expect(classes).toContain("text-green-600");
    });

    it("returns correct classes for failed", () => {
      const classes = getStatusColor("failed");
      expect(classes).toContain("text-red-600");
    });

    it("returns correct classes for running", () => {
      const classes = getStatusColor("running");
      expect(classes).toContain("text-blue-600");
    });
  });
});