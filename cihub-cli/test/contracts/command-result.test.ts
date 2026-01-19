import { describe, expect, it } from "vitest";

import { CommandResultSchema } from "../../src/types/command-result.js";

describe("CommandResultSchema", () => {
  it("accepts a minimal payload", () => {
    const payload = {
      command: "check",
      status: "ok",
      exit_code: 0,
      duration_ms: 10,
      summary: "All good",
      artifacts: {},
      problems: [],
      suggestions: [],
      files_generated: [],
      files_modified: []
    };

    expect(() => CommandResultSchema.parse(payload)).not.toThrow();
  });

  it("accepts additional fields", () => {
    const payload = {
      command: "triage",
      status: "warning",
      exit_code: 0,
      summary: "Warnings found",
      artifacts: { report: "report.json" },
      problems: [{ severity: "warning", message: "Something" }],
      suggestions: [{ message: "Try again" }],
      files_generated: ["report.json"],
      files_modified: [],
      data: { key: "value" }
    };

    const parsed = CommandResultSchema.parse(payload);
    expect(parsed.exit_code).toBe(0);
    expect(parsed.command).toBe("triage");
  });
});
