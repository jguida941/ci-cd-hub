import { describe, expect, it } from "vitest";

import { parseInput } from "../src/lib/parser.js";

const base = (input: string) => parseInput(input);

describe("parseInput", () => {
  it("parses slash commands", () => {
    const parsed = base("/check --json");
    expect(parsed.command).toBe("check");
    expect(parsed.args).toEqual(["--json"]);
    expect(parsed.isSlash).toBe(true);
  });

  it("parses question mark as help", () => {
    const parsed = base("?");
    expect(parsed.command).toBe("help");
    expect(parsed.isSlash).toBe(true);
  });

  it("strips cihub prefix", () => {
    const parsed = base("cihub report summary --json");
    expect(parsed.command).toBe("report");
    expect(parsed.args).toEqual(["summary", "--json"]);
  });

  it("handles quoted values", () => {
    const parsed = base("/run --output-dir 'build artifacts'");
    expect(parsed.args).toEqual(["--output-dir", "build artifacts"]);
  });
});
