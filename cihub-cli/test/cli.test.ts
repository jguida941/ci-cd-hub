import { describe, expect, test } from "vitest";
import { parsePythonVersion } from "../src/cli.js";

describe("parsePythonVersion", () => {
  test("extracts version from cihub --version output", () => {
    const version = parsePythonVersion("cihub 1.2.3");
    expect(version).toBe("1.2.3");
  });

  test("returns null on unexpected output", () => {
    const version = parsePythonVersion("unknown");
    expect(version).toBeNull();
  });
});
