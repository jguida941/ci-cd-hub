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

export function parsePythonVersion(output: string): string | null {
  const match = output.match(/cihub\s+([0-9A-Za-z.+-]+)/);
  return match ? match[1] : null;
}

export async function getPythonCliVersion(): Promise<PythonCliCheck> {
  try {
    const { stdout } = await execa("cihub", ["--version"]);
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
