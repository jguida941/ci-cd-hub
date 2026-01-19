import { execa } from "execa";

import { CommandResultSchema, type CommandResult } from "../types/command-result.js";
import { CommandExecutionError, JsonParseError } from "./errors.js";
import { resolveTimeout } from "./timeouts.js";

type RunOptions = {
  cwd: string;
  timeoutMs?: number;
  json?: boolean;
};

type ResolvedCihub = {
  command: string;
  baseArgs: string[];
};

function resolveCihubCommand(): ResolvedCihub {
  const explicit = process.env.CIHUB_PATH;
  if (explicit) {
    return { command: explicit, baseArgs: [] };
  }

  const pythonPath = process.env.PYTHON_PATH;
  if (pythonPath) {
    return { command: pythonPath, baseArgs: ["-m", "cihub"] };
  }

  return { command: "cihub", baseArgs: [] };
}

function ensureJsonFlag(args: string[], enabled: boolean) {
  if (!enabled) {
    return;
  }
  if (!args.includes("--json")) {
    args.push("--json");
  }
}

export async function runCihub(
  command: string,
  args: string[],
  options: RunOptions
): Promise<CommandResult> {
  const resolved = resolveCihubCommand();
  const runArgs = [...resolved.baseArgs, command, ...args];
  const jsonEnabled = options.json ?? true;
  ensureJsonFlag(runArgs, jsonEnabled);

  const timeoutMs = options.timeoutMs ?? resolveTimeout(command);

  try {
    const result = await execa(resolved.command, runArgs, {
      cwd: options.cwd,
      reject: false,
      timeout: timeoutMs
    });

    const stdout = result.stdout.trim();
    if (!stdout) {
      throw new JsonParseError("No JSON output from Python CLI", result.stdout);
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(stdout);
    } catch (error) {
      throw new JsonParseError("Invalid JSON output from Python CLI", stdout);
    }

    const validated = CommandResultSchema.safeParse(parsed);
    if (!validated.success) {
      throw new JsonParseError("CommandResult schema validation failed", stdout);
    }

    return validated.data;
  } catch (error) {
    if (error instanceof JsonParseError) {
      throw error;
    }

    const message = error instanceof Error ? error.message : "Unknown error";
    const exitCode = typeof (error as { exitCode?: number }).exitCode === "number"
      ? (error as { exitCode: number }).exitCode
      : null;

    throw new CommandExecutionError(
      message,
      `${resolved.command} ${runArgs.join(" ")}`,
      exitCode
    );
  }
}
