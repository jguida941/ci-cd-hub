import React, { useEffect, useMemo, useState } from "react";
import { Box, Text } from "ink";

import { Input } from "./Input.js";
import { Spinner } from "./Spinner.js";
import { runCihub } from "../lib/cihub.js";
import {
  applyProfileConfig,
  FALLBACK_PROFILES,
  listProfiles,
  loadProfileConfig,
  type ProfileSummary
} from "../lib/profiles.js";
import {
  getActiveSteps,
  getNestedValue,
  getWizardSteps,
  setNestedValue,
  type WizardConfig,
  type WizardFlow,
  type WizardStep
} from "../lib/wizard-steps.js";

export type WizardMeta = {
  repoPath?: string;
  repoName?: string;
  apply?: boolean;
  profileName?: string;
};

export type WizardResult = {
  flow: WizardFlow;
  config: WizardConfig;
  meta: WizardMeta;
};

type WizardProps = {
  flow: WizardFlow;
  cwd: string;
  pythonPath?: string;
  defaultTimeoutMs?: number;
  initialConfig?: WizardConfig;
  initialMeta?: WizardMeta;
  onCancel: () => void;
  onComplete: (result: WizardResult) => void;
};

function formatDefault(value: unknown): string | undefined {
  if (value === undefined || value === null) {
    return undefined;
  }
  if (typeof value === "boolean") {
    return value ? "yes" : "no";
  }
  return String(value);
}

function parseConfirm(input: string, fallback?: boolean): boolean | null {
  if (!input && typeof fallback === "boolean") {
    return fallback;
  }
  const normalized = input.toLowerCase();
  if (["y", "yes", "true", "1"].includes(normalized)) {
    return true;
  }
  if (["n", "no", "false", "0"].includes(normalized)) {
    return false;
  }
  return null;
}

function parseSelect(
  input: string,
  choices: string[],
  fallback?: string
): string | null {
  if (!input && fallback) {
    return fallback;
  }
  if (!input) {
    return null;
  }
  const index = Number.parseInt(input, 10);
  if (!Number.isNaN(index) && index >= 1 && index <= choices.length) {
    return choices[index - 1] ?? null;
  }
  const match = choices.find((choice) => choice.toLowerCase() === input.toLowerCase());
  return match ?? null;
}

function resolveStepValue(
  step: WizardStep,
  input: string,
  defaultValue: unknown
): { value?: unknown; error?: string } {
  if (step.type === "confirm") {
    const resolved = parseConfirm(input, defaultValue as boolean | undefined);
    if (resolved === null) {
      return { error: "Enter yes or no" };
    }
    return { value: resolved };
  }

  if (step.type === "select") {
    const choices = step.choices ?? [];
    const resolved = parseSelect(input, choices, defaultValue as string | undefined);
    if (!resolved) {
      return {
        error: `Choose one of: ${choices.join(", ")}`
      };
    }
    return { value: resolved };
  }

  const resolved = input || (defaultValue !== undefined ? String(defaultValue) : "");
  if (!resolved) {
    return { error: "Value is required" };
  }
  if (step.parse) {
    try {
      return { value: step.parse(resolved) };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Invalid value";
      return { error: message };
    }
  }
  return { value: resolved };
}

function stepLabel(flow: WizardFlow) {
  if (flow === "new") {
    return "New Repo";
  }
  if (flow === "init") {
    return "Init";
  }
  return "Config Edit";
}

export function Wizard({
  flow,
  cwd,
  pythonPath,
  defaultTimeoutMs,
  initialConfig = {},
  initialMeta = {},
  onCancel,
  onComplete
}: WizardProps) {
  const [config, setConfig] = useState<WizardConfig>(initialConfig);
  const [meta, setMeta] = useState<WizardMeta>(initialMeta);
  const [profiles, setProfiles] = useState<ProfileSummary[]>(
    flow === "new" ? FALLBACK_PROFILES : []
  );
  const [input, setInput] = useState("");
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (flow !== "new") {
      return undefined;
    }
    listProfiles(cwd, { pythonPath, defaultTimeoutMs })
      .then((items) => {
        if (cancelled) {
          return;
        }
        setProfiles(items);
      })
      .catch(() => {
        if (!cancelled) {
          setProfiles([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [cwd, defaultTimeoutMs, flow, pythonPath]);

  const profileNames = useMemo(
    () => profiles.map((profile) => profile.name),
    [profiles]
  );

  const steps = useMemo(
    () => getWizardSteps(flow, profileNames),
    [flow, profileNames]
  );
  const activeSteps = useMemo(
    () => getActiveSteps(steps, config),
    [steps, config]
  );

  const currentStep = activeSteps[stepIndex];
  const progressLabel = currentStep
    ? `Step ${stepIndex + 1} of ${activeSteps.length}`
    : "Wizard";

  const defaultValue = currentStep
    ? currentStep.scope === "meta"
      ? (meta as Record<string, unknown>)[currentStep.key]
      : getNestedValue(config, currentStep.key)
    : undefined;

  const displayDefault = formatDefault(defaultValue ?? currentStep?.default);

  async function handleSubmit(value: string) {
    if (!currentStep) {
      return;
    }
    const trimmed = value.trim();
    setInput("");
    setError(null);

    if (trimmed === "/cancel" || trimmed === "/exit") {
      onCancel();
      return;
    }
    if (trimmed === "/back") {
      setStepIndex((index) => Math.max(index - 1, 0));
      return;
    }

    const resolved = resolveStepValue(
      currentStep,
      trimmed,
      defaultValue ?? currentStep.default
    );
    if (resolved.error) {
      setError(resolved.error);
      return;
    }

    let nextConfig = config;
    let nextMeta = meta;
    if (currentStep.scope === "meta") {
      nextMeta = { ...meta, [currentStep.key]: resolved.value };
      setMeta(nextMeta);
    } else {
      nextConfig = setNestedValue(config, currentStep.key, resolved.value);
      setConfig(nextConfig);
    }

    if (currentStep.id === "meta.profile") {
      const profileName = String(resolved.value ?? "");
      if (profileName && profileName !== "none") {
        setLoading(true);
        const profileConfig = await loadProfileConfig(cwd, profileName, {
          pythonPath,
          defaultTimeoutMs
        });
        nextConfig = applyProfileConfig(nextConfig, profileConfig);
        setConfig(nextConfig);
        setMeta({ ...nextMeta, profileName });
        setLoading(false);
      }
    }

    if (currentStep.id === "meta.repo_name" && flow === "config-edit") {
      const repoName = String(resolved.value ?? "");
      if (!repoName) {
        setError("Repo name is required");
        return;
      }
      setLoading(true);
      try {
        const payload = await runCihub("config", ["show", "--repo", repoName], {
          cwd,
          json: true,
          pythonPath,
          defaultTimeoutMs
        });
        const existing = (payload.data?.config as WizardConfig | undefined) ?? {};
        nextConfig = existing;
        setConfig(existing);
        setMeta({ ...nextMeta, repoName });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load config";
        setError(message);
        setLoading(false);
        return;
      }
      setLoading(false);
    }

    const updatedSteps = getActiveSteps(steps, nextConfig);
    const currentId = currentStep.id;
    const currentIndex = updatedSteps.findIndex((step) => step.id === currentId);
    const nextIndex = currentIndex + 1;

    if (nextIndex >= updatedSteps.length) {
      onComplete({ flow, config: nextConfig, meta: nextMeta });
      return;
    }
    setStepIndex(nextIndex);
  }

  return (
    <Box flexDirection="column" marginTop={1}>
      <Text>{`Wizard: ${stepLabel(flow)}`}</Text>
      <Text dimColor>{progressLabel}</Text>

      {currentStep ? (
        <Box flexDirection="column" marginTop={1}>
          <Text>{currentStep.question}</Text>
          {currentStep.type === "select" && currentStep.choices && (
            <Box flexDirection="column" marginTop={1}>
              {currentStep.choices.map((choice, index) => (
                <Text key={`${choice}-${index}`}>{`${index + 1}. ${choice}`}</Text>
              ))}
            </Box>
          )}
          {displayDefault && (
            <Text dimColor>{`Default: ${displayDefault}`}</Text>
          )}
          <Text dimColor>Type /back or /cancel anytime.</Text>
        </Box>
      ) : (
        <Text>No steps available.</Text>
      )}

      {loading && <Spinner label="Loading" />}
      {error && (
        <Box marginTop={1}>
          <Text color="red">{error}</Text>
        </Box>
      )}

      {currentStep && (
        <Box marginTop={1}>
          <Input
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            placeholder="Enter value..."
            disabled={loading}
          />
        </Box>
      )}
    </Box>
  );
}
