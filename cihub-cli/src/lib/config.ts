import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { isAbsolute, join, resolve } from "node:path";
import { z } from "zod";
import { parse as parseYaml } from "yaml";

const DEFAULT_TIMEOUT_MS = 120_000;

export const ConfigSchema = z
  .object({
    cli: z
      .object({
        python_path: z.string().optional(),
        default_timeout: z.number().default(DEFAULT_TIMEOUT_MS),
        verbose: z.boolean().default(false)
      })
      .default({}),
    ai: z
      .object({
        enabled: z.boolean().default(true),
        provider: z.enum(["anthropic", "openai", "local"]).default("anthropic"),
        model: z.string().default("claude-sonnet-4-20250514"),
        max_tokens: z.number().default(4096),
        temperature: z.number().min(0).max(1).default(0.3),
        api_key: z.string().optional()
      })
      .default({}),
    ui: z
      .object({
        theme: z.enum(["auto", "dark", "light", "none"]).default("auto"),
        show_duration: z.boolean().default(true),
        unicode_icons: z.boolean().default(true),
        max_width: z.number().default(0),
        spinner: z.enum(["dots", "line", "simple"]).default("dots")
      })
      .default({}),
    aliases: z.record(z.string()).default({}),
    defaults: z.record(z.array(z.string())).default({}),
    shortcuts: z.record(z.string()).default({})
  })
  .default({});

export type Config = z.infer<typeof ConfigSchema>;

export type ConfigSource = {
  label: string;
  path: string;
  loaded: boolean;
  error?: string;
};

export type ConfigLoadResult = {
  config: Config;
  sources: ConfigSource[];
  errors: string[];
  hasFileConfig: boolean;
};

type PartialConfig = z.input<typeof ConfigSchema>;

export type ConfigPaths = {
  globalPath: string;
  xdgPath: string;
  projectPath: string;
  envPath?: string;
};

export function resolveConfigPaths(cwd: string): ConfigPaths {
  const globalPath = join(homedir(), ".cihubrc");
  const xdgPath = join(homedir(), ".config", "cihub", "config.yaml");
  const projectPath = join(cwd, ".cihubrc");
  const envPathRaw = process.env.CIHUB_CONFIG;
  const envPath = envPathRaw
    ? isAbsolute(envPathRaw)
      ? envPathRaw
      : resolve(cwd, envPathRaw)
    : undefined;

  return {
    globalPath,
    xdgPath,
    projectPath,
    envPath
  };
}

export function getPreferredConfigPath(cwd: string): string {
  const paths = resolveConfigPaths(cwd);
  return paths.envPath ?? paths.globalPath;
}

export async function loadConfig(cwd: string): Promise<ConfigLoadResult> {
  const paths = resolveConfigPaths(cwd);
  const sources: ConfigSource[] = [];
  const errors: string[] = [];
  let merged: PartialConfig = {};
  let explicitAiEnabled: boolean | undefined;

  const orderedSources = [
    { label: "global", path: paths.globalPath },
    { label: "xdg", path: paths.xdgPath },
    { label: "project", path: paths.projectPath }
  ];
  if (paths.envPath) {
    orderedSources.push({ label: "env", path: paths.envPath });
  }

  for (const source of orderedSources) {
    const result = await readConfigFile(source.path);
    if (result.loaded && result.data && isRecord(result.data)) {
      merged = deepMerge(merged, result.data as PartialConfig);
      const candidate = (result.data as Record<string, unknown>).ai;
      if (isRecord(candidate) && typeof candidate.enabled === "boolean") {
        explicitAiEnabled = candidate.enabled;
      }
    }
    if (result.error) {
      errors.push(`${source.path}: ${result.error}`);
    }
    sources.push({
      label: source.label,
      path: source.path,
      loaded: result.loaded,
      error: result.error
    });
  }

  merged = applyEnvOverrides(merged);

  const hasApiKey = Boolean(
    (merged.ai as Record<string, unknown> | undefined)?.api_key
      ?? process.env.ANTHROPIC_API_KEY
      ?? process.env.OPENAI_API_KEY
  );
  if (explicitAiEnabled === undefined && !hasApiKey) {
    merged.ai = { ...(merged.ai ?? {}), enabled: false };
  }

  try {
    return {
      config: ConfigSchema.parse(merged),
      sources,
      errors,
      hasFileConfig: sources.some((source) => source.loaded)
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Invalid configuration";
    errors.push(message);
    return {
      config: ConfigSchema.parse({}),
      sources,
      errors,
      hasFileConfig: sources.some((source) => source.loaded)
    };
  }
}

type ReadResult = {
  loaded: boolean;
  data?: unknown;
  error?: string;
};

async function readConfigFile(path: string): Promise<ReadResult> {
  try {
    const raw = await readFile(path, "utf-8");
    try {
      const parsed = parseYaml(raw);
      return { loaded: true, data: parsed };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Invalid YAML";
      return { loaded: true, error: message };
    }
  } catch (error) {
    const code = (error as { code?: string }).code;
    if (code === "ENOENT") {
      return { loaded: false };
    }
    const message = error instanceof Error ? error.message : "Failed to read config";
    return { loaded: false, error: message };
  }
}

function applyEnvOverrides(config: PartialConfig): PartialConfig {
  let updated = { ...config };

  if (process.env.CIHUB_PYTHON_PATH) {
    updated = {
      ...updated,
      cli: { ...(updated.cli ?? {}), python_path: process.env.CIHUB_PYTHON_PATH }
    };
  }

  if (process.env.CIHUB_DEBUG) {
    updated = {
      ...updated,
      cli: { ...(updated.cli ?? {}), verbose: true }
    };
  }

  if (process.env.CIHUB_NO_COLOR) {
    updated = {
      ...updated,
      ui: { ...(updated.ui ?? {}), theme: "none" }
    };
  }

  const provider = isRecord(updated.ai) && typeof updated.ai.provider === "string"
    ? updated.ai.provider
    : undefined;
  const anthropicKey = process.env.ANTHROPIC_API_KEY;
  const openaiKey = process.env.OPENAI_API_KEY;
  let apiKey = updated.ai && isRecord(updated.ai)
    ? (updated.ai.api_key as string | undefined)
    : undefined;

  if (provider === "openai" && openaiKey) {
    apiKey = openaiKey;
  } else if (provider === "anthropic" && anthropicKey) {
    apiKey = anthropicKey;
  } else if (!apiKey) {
    apiKey = anthropicKey ?? openaiKey ?? apiKey;
  }

  if (apiKey) {
    updated = {
      ...updated,
      ai: { ...(updated.ai ?? {}), api_key: apiKey }
    };
  }

  return updated;
}

function deepMerge<T extends Record<string, unknown>>(
  base: T,
  override: Partial<T>
): T {
  const result = { ...base } as Record<string, unknown>;
  Object.entries(override).forEach(([key, value]) => {
    const existing = result[key];
    if (isRecord(existing) && isRecord(value)) {
      result[key] = deepMerge(existing, value);
    } else if (value !== undefined) {
      result[key] = value;
    }
  });
  return result as T;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
