import { Command } from "commander";
import { execa } from "execa";
import { readFileSync } from "node:fs";

import { loadConfig } from "./lib/config.js";

const pkg = JSON.parse(
  readFileSync(new URL("../package.json", import.meta.url), "utf-8")
) as { name?: string; version: string };

export type PythonCliCheck = {
  version?: string;
  raw?: string;
  error?: string;
};

export type CliContext = {
  cwd: string;
  version: string;
  python: PythonCliCheck;
  warnings: string[];
};

export type RunResult = {
  exitCode: number;
  context?: CliContext;
};

type ResolvedCli = {
  command: string;
  args: string[];
};

type ParsedCliArgs = {
  cwd: string;
  passthrough: string[];
  hasCommand: boolean;
};

export function parsePythonVersion(output: string): string | null {
  const match = output.match(/cihub\s+([0-9A-Za-z.+-]+)/);
  return match ? match[1] : null;
}

export function resolvePythonCliCommand(pythonPath?: string): ResolvedCli {
  const explicit = process.env.CIHUB_PATH;
  if (explicit) {
    return { command: explicit, args: [] };
  }

  const envPythonPath = process.env.CIHUB_PYTHON_PATH ?? process.env.PYTHON_PATH;
  const resolvedPythonPath = envPythonPath ?? pythonPath;
  if (resolvedPythonPath) {
    return { command: resolvedPythonPath, args: ["-m", "cihub"] };
  }

  return { command: "cihub", args: [] };
}

function parseCliArgs(argv: string[]): ParsedCliArgs {
  const rawArgs = argv.slice(2);
  let cwd = process.cwd();
  const passthrough: string[] = [];

  for (let i = 0; i < rawArgs.length; i += 1) {
    const arg = rawArgs[i];
    if (arg === "-d" || arg === "--dir") {
      const next = rawArgs[i + 1];
      if (next) {
        cwd = next;
        i += 1;
        continue;
      }
    }
    passthrough.push(arg);
  }

  const hasCommand = passthrough.some((arg) => arg && !arg.startsWith("-"));
  return { cwd, passthrough, hasCommand };
}

export async function getPythonCliVersion(pythonPath?: string): Promise<PythonCliCheck> {
  try {
    const resolved = resolvePythonCliCommand(pythonPath);
    const { stdout } = await execa(resolved.command, [...resolved.args, "--version"]);
    const version = parsePythonVersion(stdout);
    return {
      version: version ?? undefined,
      raw: stdout.trim()
    };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Unknown error"
    };
  }
}

async function runPythonCliCommand(args: string[], cwd: string): Promise<number> {
  let pythonPath: string | undefined;
  try {
    const { config } = await loadConfig(cwd);
    pythonPath = config.cli?.python_path;
  } catch {
    pythonPath = undefined;
  }

  const resolved = resolvePythonCliCommand(pythonPath);
  try {
    const result = await execa(resolved.command, [...resolved.args, ...args], {
      cwd,
      reject: false,
      stdio: "inherit"
    });
    return typeof result.exitCode === "number" ? result.exitCode : 1;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error(`Failed to run Python CLI: ${message}`);
    return 1;
  }
}

export async function run(argv: string[] = process.argv): Promise<RunResult> {
  const parsedArgs = parseCliArgs(argv);
  if (parsedArgs.hasCommand) {
    const exitCode = await runPythonCliCommand(parsedArgs.passthrough, parsedArgs.cwd);
    return { exitCode };
  }

  const program = new Command();
  program
    .name("cihub-interactive")
    .description("Interactive CLI for CIHub")
    .version(pkg.version, "-v, --version", "Show CLI version")
    .option("-d, --dir <path>", "Working directory", process.cwd())
    .parse(argv);

  const options = program.opts<{ dir: string }>();
  const passthroughArgs = program.args;
  if (passthroughArgs.length > 0) {
    const exitCode = await runPythonCliCommand(passthroughArgs, options.dir);
    return { exitCode };
  }

  let pythonPath: string | undefined;
  try {
    const { config } = await loadConfig(options.dir);
    pythonPath = config.cli?.python_path;
  } catch {
    pythonPath = undefined;
  }

  const python = await getPythonCliVersion(pythonPath);
  if (!python.version) {
    const detail = python.error ? ` (${python.error})` : "";
    console.error(
      `Python CLI not available. Install cihub before running the interactive CLI.${detail}`
    );
    return { exitCode: 1 };
  }

  const warnings: string[] = [];
  if (python.version !== pkg.version) {
    warnings.push(
      `Version mismatch: TypeScript CLI ${pkg.version} vs Python CLI ${python.version}.`
    );
  }

  return {
    exitCode: 0,
    context: {
      cwd: options.dir,
      version: pkg.version,
      python,
      warnings
    }
  };
}
