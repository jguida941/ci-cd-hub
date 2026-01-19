import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Box, Text, useApp } from "ink";

import { ErrorBoundary } from "./components/ErrorBoundary.js";
import { Header } from "./components/Header.js";
import { Input } from "./components/Input.js";
import { FirstRunSetup } from "./components/FirstRunSetup.js";
import { Output, type OutputResult } from "./components/Output.js";
import { Spinner } from "./components/Spinner.js";
import { Wizard, type WizardMeta, type WizardResult } from "./components/Wizard.js";
import {
  buildCommandRegistry,
  extractCommandRegistry,
  getHelpTables,
  getGroupHelpTable,
  resolveCommand,
  type CommandRegistry,
  type CommandRegistryEntry
} from "./commands/index.js";
import { runCihub } from "./lib/cihub.js";
import { ParseError, CommandExecutionError, JsonParseError } from "./lib/errors.js";
import { parseInput } from "./lib/parser.js";
import { useConfig } from "./context/ConfigContext.js";
import type { CommandResult } from "./types/command-result.js";
import { setNestedValue, type WizardConfig, type WizardFlow } from "./lib/wizard-steps.js";

export type AppProps = {
  cwd: string;
  version: string;
  pythonVersion: string;
  warnings?: string[];
};

export function App({ cwd, version, pythonVersion, warnings = [] }: AppProps) {
  const { exit } = useApp();
  const {
    config,
    loading: configLoading,
    ready: configReady,
    errors: configErrors,
    hasFileConfig,
    reload
  } = useConfig();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OutputResult | null>(null);
  const [registry, setRegistry] = useState<CommandRegistry | null>(null);
  const [registryError, setRegistryError] = useState<string | null>(null);
  const [setupDismissed, setSetupDismissed] = useState(false);
  const [wizardSession, setWizardSession] = useState<{
    flow: WizardFlow;
    initialConfig: WizardConfig;
    initialMeta: WizardMeta;
  } | null>(null);

  const pythonPath = config.cli?.python_path;
  const defaultTimeoutMs = config.cli?.default_timeout;
  const showSetup = configReady && !configLoading && !hasFileConfig && !setupDismissed;

  useEffect(() => {
    if (!configReady || configLoading || showSetup) {
      return undefined;
    }
    let cancelled = false;
    setRegistryError(null);

    runCihub("commands", ["list"], {
      cwd,
      json: true,
      pythonPath,
      defaultTimeoutMs
    })
      .then((payload) => {
        if (cancelled) {
          return;
        }
        const registryPayload = extractCommandRegistry(payload);
        if (!registryPayload) {
          throw new Error("Command registry missing from CLI output");
        }
        setRegistry(buildCommandRegistry(registryPayload.commands));
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        const message = error instanceof Error ? error.message : String(error);
        setRegistry(null);
        setRegistryError(message);
      });

    return () => {
      cancelled = true;
    };
  }, [configLoading, configReady, cwd, defaultTimeoutMs, pythonPath, showSetup]);

  const helpOutput = useMemo<OutputResult>(() => {
    const tables = getHelpTables(registry);
    const details = registry
      ? []
      : [
          "Command registry unavailable; using fallback meta commands only.",
          "Install/update the Python CLI and rerun."
        ];

    return {
      summary: "Available commands",
      status: registry ? "info" : "warning",
      tables,
      details
    };
  }, [registry]);

  const runtimeWarnings = useMemo(() => {
    const merged = [...warnings];
    if (configErrors.length > 0) {
      merged.push(
        ...configErrors.map((message) => `Config warning: ${message}`)
      );
    }
    if (registryError) {
      merged.push(`Command registry unavailable: ${registryError}`);
    }
    return merged;
  }, [configErrors, registryError, warnings]);

  const toOutputResult = useCallback((payload: CommandResult): OutputResult => {
    const defaultSeverity: OutputResult["status"] =
      payload.exit_code === 0 ? "ok" : "error";

    const status = payload.status === "warning"
      ? "warning"
      : payload.status === "ok"
        ? "ok"
        : defaultSeverity;

    const problems =
      payload.problems?.map((problem) => ({
        severity:
          typeof problem.severity === "string" && problem.severity === "warning"
            ? "warning"
            : typeof problem.severity === "string" && problem.severity === "info"
              ? "info"
              : "error",
        message:
          (problem.message as string | undefined) ??
          (problem.summary as string | undefined) ??
          "Problem reported"
      })) ?? [];

    const suggestions =
      payload.suggestions?.map((suggestion) => {
        return (
          (suggestion.message as string | undefined) ??
          (suggestion.summary as string | undefined) ??
          (suggestion.action as string | undefined) ??
          "Suggestion available"
        );
      }) ?? [];

    const details: string[] = [];
    if (payload.command) {
      details.push(`command: ${payload.command}`);
    }
    if (payload.status) {
      details.push(`status: ${payload.status}`);
    }
    if (typeof payload.duration_ms === "number") {
      details.push(`duration: ${payload.duration_ms}ms`);
    }
    if (payload.data && typeof payload.data.raw_output === "string") {
      const rawLines = payload.data.raw_output.split("\n").filter(Boolean);
      if (rawLines.length > 0) {
        if (details.length > 0) {
          details.push("");
        }
        details.push(...rawLines);
      }
    }

    return {
      summary: payload.summary ?? "Command complete",
      status,
      problems,
      suggestions,
      details
    };
  }, []);

  const resolveWizardFlow = useCallback(
    (entry?: CommandRegistryEntry, command?: string, args?: string[]): WizardFlow | null => {
      if (entry?.command === "new" || command === "new") {
        return "new";
      }
      if (entry?.command === "init" || command === "init") {
        return "init";
      }
      if (entry?.command === "config edit") {
        return "config-edit";
      }
      if (command === "config" && args && args[0] === "edit") {
        return "config-edit";
      }
      return null;
    },
    []
  );

  const getFlagValue = useCallback((args: string[], flag: string): string | null => {
    const index = args.indexOf(flag);
    if (index === -1) {
      return null;
    }
    return args[index + 1] ?? null;
  }, []);

  const buildInitialWizardConfig = useCallback(
    (flow: WizardFlow, args: string[]): WizardConfig => {
      let config: WizardConfig = {};
      const owner = getFlagValue(args, "--owner");
      const name = getFlagValue(args, "--name");
      const language = getFlagValue(args, "--language");

      if (owner) {
        config = setNestedValue(config, "repo.owner", owner);
      }
      if (name) {
        config = setNestedValue(config, "repo.name", name);
      }
      if (language) {
        config = setNestedValue(config, "language", language);
      }

      if (flow === "new" && args.length > 0 && !args[0]?.startsWith("-")) {
        const repoName = args[0];
        const [repoOwner, repoSlug] = repoName.includes("/") ? repoName.split("/", 2) : ["", repoName];
        if (repoOwner) {
          config = setNestedValue(config, "repo.owner", repoOwner);
        }
        if (repoSlug) {
          config = setNestedValue(config, "repo.name", repoSlug);
        }
      }

      return config;
    },
    [getFlagValue]
  );

  const buildInitialWizardMeta = useCallback(
    (flow: WizardFlow, args: string[]): WizardMeta => {
      const meta: WizardMeta = {};
      const dryRun = args.includes("--dry-run");
      const apply = args.includes("--apply");
      if (dryRun) {
        meta.apply = false;
      } else if (apply) {
        meta.apply = true;
      }

      const profile = getFlagValue(args, "--profile");
      if (profile) {
        meta.profileName = profile;
      }

      if (flow === "init") {
        const repoPath = getFlagValue(args, "--repo");
        if (repoPath) {
          meta.repoPath = repoPath;
        }
      }

      if (flow === "config-edit") {
        const repoName = getFlagValue(args, "--repo");
        if (repoName) {
          meta.repoName = repoName;
        }
      }

      if (flow === "new" && args.length > 0 && !args[0]?.startsWith("-")) {
        meta.repoName = args[0];
      }

      return meta;
    },
    [getFlagValue]
  );

  const runWizardCommand = useCallback(
    async (wizardResult: WizardResult) => {
      setWizardSession(null);
      setLoading(true);
      try {
        const json = JSON.stringify(wizardResult.config);
        let command = wizardResult.flow === "config-edit" ? "config" : wizardResult.flow;
        let args: string[] = [];

        if (wizardResult.flow === "new") {
          const repoOwner = (wizardResult.config.repo as { owner?: string } | undefined)?.owner ?? "";
          const repoName = (wizardResult.config.repo as { name?: string } | undefined)?.name ?? "";
          const name = wizardResult.meta.repoName || (repoOwner && repoName ? `${repoOwner}/${repoName}` : repoName);
          if (!name) {
            throw new Error("Repo name is required for /new");
          }
          args = [name, "--config-json", json, "--yes"];
          if (wizardResult.meta.apply === false) {
            args.push("--dry-run");
          }
        } else if (wizardResult.flow === "init") {
          const repoPath = wizardResult.meta.repoPath || ".";
          args = ["--repo", repoPath, "--config-json", json];
          if (wizardResult.meta.apply === false) {
            args.push("--dry-run");
          } else {
            args.push("--apply");
          }
        } else {
          const repoName = wizardResult.meta.repoName;
          if (!repoName) {
            throw new Error("Repo name is required for /config edit");
          }
          args = ["edit", "--repo", repoName, "--config-json", json];
          if (wizardResult.meta.apply === false) {
            args.push("--dry-run");
          }
        }

        const payload = await runCihub(command, args, {
          cwd,
          json: true,
          pythonPath,
          defaultTimeoutMs
        });
        setResult(toOutputResult(payload));
      } catch (error) {
        const message = error instanceof Error ? error.message : "Wizard command failed";
        setResult({
          summary: "Wizard command failed",
          status: "error",
          problems: [{ severity: "error", message }]
        });
      } finally {
        setLoading(false);
      }
    },
    [cwd, defaultTimeoutMs, pythonPath, toOutputResult]
  );

  const handleSubmit = useCallback(
    async (value: string) => {
      const trimmed = value.trim();
      if (!trimmed) {
        return;
      }

      setInput("");

      setLoading(true);
      try {
        const parsed = parseInput(trimmed);
        const resolved = resolveCommand(parsed, registry);

        if (resolved.kind === "meta") {
          if (resolved.name === "exit") {
            exit();
            return;
          }
          if (resolved.name === "clear") {
            setResult(null);
            return;
          }
          if (resolved.name === "help") {
            setResult(helpOutput);
            return;
          }
          return;
        }
        if (resolved.kind === "group") {
          const groupName = resolved.entry.path[0] ?? resolved.command;
          const table = registry ? getGroupHelpTable(registry, groupName) : null;
          setResult({
            summary: `/${groupName} is a command group`,
            status: "info",
            details: ["Select a subcommand to run:"],
            tables: table ? [table] : undefined
          });
          return;
        }

        const entry = resolved.entry;
        const wizardFlow = resolveWizardFlow(entry, resolved.command, resolved.args);
        if (wizardFlow) {
          const effectiveArgs =
            wizardFlow === "config-edit" && resolved.args[0] === "edit"
              ? resolved.args.slice(1)
              : resolved.args;
          const initialConfig = buildInitialWizardConfig(wizardFlow, effectiveArgs);
          const initialMeta = buildInitialWizardMeta(wizardFlow, effectiveArgs);
          setWizardSession({ flow: wizardFlow, initialConfig, initialMeta });
          return;
        }
        const supportsJson = entry?.supports_json ?? true;
        const supportsJsonRuntime = entry?.supports_json_runtime ?? supportsJson;
        const supportsInteractive =
          entry?.supports_interactive ?? entry?.supports_wizard ?? false;
        const interactiveFlags = new Set(["--wizard", "--interactive"]);
        const interactiveRequested = supportsInteractive
          && resolved.args.some((arg) => interactiveFlags.has(arg));

        if (!supportsJsonRuntime) {
          setResult({
            summary: "Command not supported in JSON mode",
            status: "warning",
            details: [
              `/${resolved.command} does not support JSON output.`,
              "Run this command in your terminal using the Python CLI."
            ]
          });
          return;
        }

        if (interactiveRequested) {
          setResult({
            summary: "Interactive commands are not supported here",
            status: "warning",
            details: [
              "This command launches an interactive wizard.",
              "Run it in your terminal without the TypeScript CLI."
            ]
          });
          return;
        }

        const payload = await runCihub(resolved.command, resolved.args, {
          cwd,
          json: supportsJsonRuntime,
          pythonPath,
          defaultTimeoutMs
        });
        setResult(toOutputResult(payload));
      } catch (error) {
        let message = "Command failed";
        if (error instanceof ParseError) {
          message = error.message;
        } else if (error instanceof CommandExecutionError) {
          message = `CLI error: ${error.message}`;
        } else if (error instanceof JsonParseError) {
          message = "Invalid JSON output from Python CLI";
        } else if (error instanceof Error) {
          message = error.message;
        }
        setResult({
          summary: "Command failed",
          status: "error",
          problems: [{ severity: "error", message }]
        });
      } finally {
        setLoading(false);
      }
    },
    [
      buildInitialWizardConfig,
      buildInitialWizardMeta,
      cwd,
      exit,
      helpOutput,
      registry,
      resolveWizardFlow,
      toOutputResult,
      pythonPath,
      defaultTimeoutMs
    ]
  );

  return (
    <ErrorBoundary>
      <Box flexDirection="column" padding={1}>
        <Header
          cwd={cwd}
          version={version}
          pythonVersion={pythonVersion}
          warnings={runtimeWarnings}
        />

        <Box flexDirection="column" marginTop={1}>
          {configLoading && <Spinner label="Loading configuration" />}
          {!configLoading && showSetup && (
            <FirstRunSetup
              cwd={cwd}
              onComplete={() => {
                setSetupDismissed(false);
                void reload();
              }}
              onSkip={() => setSetupDismissed(true)}
            />
          )}
          {!configLoading && !showSetup && loading && <Spinner label="Running" />}
          {!configLoading && !showSetup && !loading && wizardSession && (
            <Wizard
              flow={wizardSession.flow}
              cwd={cwd}
              pythonPath={pythonPath}
              defaultTimeoutMs={defaultTimeoutMs}
              initialConfig={wizardSession.initialConfig}
              initialMeta={wizardSession.initialMeta}
              onCancel={() => setWizardSession(null)}
              onComplete={runWizardCommand}
            />
          )}
          {!configLoading && !showSetup && !loading && !wizardSession && result && (
            <Output result={result} />
          )}
          {!configLoading && !showSetup && !loading && !wizardSession && !result && (
            <Text dimColor>
              Enter a command to begin. Try /help or /exit.
            </Text>
          )}
        </Box>

        <Box marginTop={1}>
          {!configLoading && !showSetup && !wizardSession && (
            <Input
              value={input}
              onChange={setInput}
              onSubmit={handleSubmit}
              placeholder="Type /help or a cihub command..."
              disabled={loading}
            />
          )}
        </Box>
      </Box>
    </ErrorBoundary>
  );
}
