import { Command } from "commander";
import { execa } from "execa";
import { readFileSync } from "node:fs";

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

export function parsePythonVersion(output: string): string | null {
  const match = output.match(/cihub\s+([0-9A-Za-z.+-]+)/);
  return match ? match[1] : null;
}

export function resolvePythonCliCommand(): ResolvedCli {
  const explicit = process.env.CIHUB_PATH;
  if (explicit) {
    return { command: explicit, args: [] };
  }

  const pythonPath = process.env.CIHUB_PYTHON_PATH ?? process.env.PYTHON_PATH;
  if (pythonPath) {
    return { command: pythonPath, args: ["-m", "cihub"] };
  }

  return { command: "cihub", args: [] };
}

export async function getPythonCliVersion(): Promise<PythonCliCheck> {
  try {
    const resolved = resolvePythonCliCommand();
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

export async function run(argv: string[] = process.argv): Promise<RunResult> {
  const program = new Command();
  program
    .name("cihub-interactive")
    .description("Interactive CLI for CIHub")
    .version(pkg.version, "-v, --version", "Show CLI version")
    .option("-d, --dir <path>", "Working directory", process.cwd())
    .parse(argv);

  const options = program.opts<{ dir: string }>();
  const python = await getPythonCliVersion();
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
