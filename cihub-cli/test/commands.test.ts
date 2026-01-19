import { describe, expect, it } from "vitest";

import { parseInput } from "../src/lib/parser.js";
import { buildCommandRegistry, resolveCommand } from "../src/commands/index.js";

const registry = buildCommandRegistry([
  { command: "config-outputs", path: ["config-outputs"], is_group: false },
  { command: "report build", path: ["report", "build"], is_group: false },
  { command: "hub-ci ruff", path: ["hub-ci", "ruff"], is_group: false }
]);

describe("resolveCommand", () => {
  it("maps config-outputs", () => {
    const parsed = parseInput("/config-outputs --json");
    const resolved = resolveCommand(parsed, registry);
    expect(resolved).toEqual({
      kind: "python",
      command: "config-outputs",
      args: ["--json"]
    });
  });

  it("maps report subcommands", () => {
    const parsed = parseInput("/report build");
    const resolved = resolveCommand(parsed, registry);
    expect(resolved).toEqual({
      kind: "python",
      command: "report",
      args: ["build"]
    });
  });

  it("maps hub-ci subcommands", () => {
    const parsed = parseInput("/hub-ci ruff --path .");
    const resolved = resolveCommand(parsed, registry);
    expect(resolved).toEqual({
      kind: "python",
      command: "hub-ci",
      args: ["ruff", "--path", "."]
    });
  });

  it("returns meta commands", () => {
    const parsed = parseInput("/help");
    const resolved = resolveCommand(parsed, registry);
    expect(resolved).toEqual({ kind: "meta", name: "help" });
  });

  it("passes through raw commands", () => {
    const parsed = parseInput("check --json");
    const resolved = resolveCommand(parsed, registry);
    expect(resolved).toEqual({
      kind: "python",
      command: "check",
      args: ["--json"]
    });
  });
});
