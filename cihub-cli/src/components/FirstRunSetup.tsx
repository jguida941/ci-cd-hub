import React, { useMemo, useState } from "react";
import { Box, Text } from "ink";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { stringify as stringifyYaml } from "yaml";

import { Input } from "./Input.js";
import { Spinner } from "./Spinner.js";
import { getPreferredConfigPath, type Config } from "../lib/config.js";

type FirstRunSetupProps = {
  cwd: string;
  onComplete: () => void;
  onSkip: () => void;
};

type SetupStep = {
  id: string;
  question: string;
  type: "confirm" | "select" | "text" | "number";
  choices?: string[];
  optional?: boolean;
  defaultValue?: string | number | boolean;
};

const STEPS: SetupStep[] = [
  {
    id: "ai.enabled",
    question: "Enable AI features? (yes/no)",
    type: "confirm",
    defaultValue: true
  },
  {
    id: "ai.provider",
    question: "AI provider",
    type: "select",
    choices: ["anthropic", "openai", "local"],
    defaultValue: "anthropic"
  },
  {
    id: "cli.python_path",
    question: "Python executable path (optional)",
    type: "text",
    optional: true
  },
  {
    id: "cli.default_timeout",
    question: "Default timeout in ms (optional)",
    type: "number",
    optional: true,
    defaultValue: 120000
  }
];

export function FirstRunSetup({ cwd, onComplete, onSkip }: FirstRunSetupProps) {
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [stepIndex, setStepIndex] = useState(0);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const targetPath = useMemo(() => getPreferredConfigPath(cwd), [cwd]);

  const step = STEPS[stepIndex];

  function formatDefault(value: SetupStep["defaultValue"]): string | undefined {
    if (value === undefined) {
      return undefined;
    }
    if (typeof value === "boolean") {
      return value ? "yes" : "no";
    }
    return String(value);
  }

  function parseConfirm(value: string, fallback?: boolean): boolean | null {
    if (!value && typeof fallback === "boolean") {
      return fallback;
    }
    const normalized = value.toLowerCase();
    if (["y", "yes", "true", "1"].includes(normalized)) {
      return true;
    }
    if (["n", "no", "false", "0"].includes(normalized)) {
      return false;
    }
    return null;
  }

  function parseSelect(
    value: string,
    choices: string[],
    fallback?: string
  ): string | null {
    if (!value && fallback) {
      return fallback;
    }
    if (!value) {
      return null;
    }
    const index = Number.parseInt(value, 10);
    if (!Number.isNaN(index) && index >= 1 && index <= choices.length) {
      return choices[index - 1] ?? null;
    }
    const match = choices.find((choice) => choice.toLowerCase() === value.toLowerCase());
    return match ?? null;
  }

  function parseNumber(value: string, fallback?: number): number | null {
    if (!value && typeof fallback === "number") {
      return fallback;
    }
    if (!value) {
      return null;
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  async function handleSubmit(value: string) {
    if (!step) {
      return;
    }
    const trimmed = value.trim();
    setInput("");
    setError(null);

    if (trimmed === "/skip" || trimmed === "/cancel" || trimmed === "/exit") {
      onSkip();
      return;
    }
    if (trimmed === "/back") {
      setStepIndex((index) => Math.max(index - 1, 0));
      return;
    }

    let resolved: unknown;
    if (step.type === "confirm") {
      const parsed = parseConfirm(trimmed, step.defaultValue as boolean | undefined);
      if (parsed === null) {
        setError("Enter yes or no");
        return;
      }
      resolved = parsed;
    } else if (step.type === "select") {
      const choices = step.choices ?? [];
      const parsed = parseSelect(trimmed, choices, step.defaultValue as string | undefined);
      if (!parsed) {
        setError(`Choose one of: ${choices.join(", ")}`);
        return;
      }
      resolved = parsed;
    } else if (step.type === "number") {
      const parsed = parseNumber(trimmed, step.defaultValue as number | undefined);
      if (parsed === null) {
        if (step.optional && !trimmed) {
          resolved = undefined;
        } else {
          setError("Enter a numeric value");
          return;
        }
      } else {
        resolved = parsed;
      }
    } else {
      if (!trimmed) {
        if (step.optional) {
          resolved = undefined;
        } else if (step.defaultValue !== undefined) {
          resolved = step.defaultValue;
        } else {
          setError("Value is required");
          return;
        }
      } else {
        resolved = trimmed;
      }
    }

    let nextConfig = config;
    if (resolved !== undefined) {
      nextConfig = setNestedValue(config, step.id, resolved);
      setConfig(nextConfig);
    }

    const nextIndex = stepIndex + 1;
    if (nextIndex >= STEPS.length) {
      await saveConfig(nextConfig);
      return;
    }
    setStepIndex(nextIndex);
  }

  async function saveConfig(configValue: Record<string, unknown>) {
    setSaving(true);
    try {
      await mkdir(dirname(targetPath), { recursive: true });
      await writeFile(
        targetPath,
        stringifyYaml(configValue as Config, { indent: 2 })
      );
      onComplete();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to write config";
      setError(message);
      setSaving(false);
    }
  }

  const displayDefault = formatDefault(step?.defaultValue);

  return (
    <Box flexDirection="column" marginTop={1}>
      <Text>First-run setup</Text>
      <Text dimColor>Config will be saved to {targetPath}</Text>

      <Box flexDirection="column" marginTop={1}>
        <Text>{step.question}</Text>
        {step.type === "select" && step.choices && (
          <Box flexDirection="column" marginTop={1}>
            {step.choices.map((choice, index) => (
              <Text key={`${choice}-${index}`}>{`${index + 1}. ${choice}`}</Text>
            ))}
          </Box>
        )}
        {displayDefault && <Text dimColor>{`Default: ${displayDefault}`}</Text>}
        {step.optional && <Text dimColor>Optional: press enter to skip.</Text>}
        <Text dimColor>Type /back or /skip anytime.</Text>
      </Box>

      {saving && <Spinner label="Saving configuration" />}
      {error && (
        <Box marginTop={1}>
          <Text color="red">{error}</Text>
        </Box>
      )}

      {!saving && (
        <Box marginTop={1}>
          <Input
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            placeholder="Enter value..."
          />
        </Box>
      )}
    </Box>
  );
}

function setNestedValue(
  config: Record<string, unknown>,
  path: string,
  value: unknown
): Record<string, unknown> {
  const parts = path.split(".").filter(Boolean);
  if (parts.length === 0) {
    return config;
  }
  const root: Record<string, unknown> = { ...config };
  let cursor: Record<string, unknown> = root;
  parts.forEach((part, index) => {
    if (index === parts.length - 1) {
      cursor[part] = value;
      return;
    }
    const next = cursor[part];
    if (typeof next !== "object" || next === null || Array.isArray(next)) {
      cursor[part] = {};
    }
    cursor = cursor[part] as Record<string, unknown>;
  });
  return root;
}
