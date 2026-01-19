import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Box, Text, useApp } from "ink";

import { ErrorBoundary } from "./components/ErrorBoundary.js";
import { Header } from "./components/Header.js";
import { Input } from "./components/Input.js";
import { Output, type OutputResult } from "./components/Output.js";
import { Spinner } from "./components/Spinner.js";
import {
  buildCommandRegistry,
  extractCommandRegistry,
  getHelpTables,
  getGroupHelpTable,
  resolveCommand,
  type CommandRegistry
} from "./commands/index.js";
import { runCihub } from "./lib/cihub.js";
import { ParseError, CommandExecutionError, JsonParseError } from "./lib/errors.js";
import { parseInput } from "./lib/parser.js";
import { resolveTimeout } from "./lib/timeouts.js";
import type { CommandResult } from "./types/command-result.js";

export type AppProps = {
  cwd: string;
  version: string;
  pythonVersion: string;
  warnings?: string[];
};

export function App({ cwd, version, pythonVersion, warnings = [] }: AppProps) {
  const { exit } = useApp();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OutputResult | null>(null);
  const [registry, setRegistry] = useState<CommandRegistry | null>(null);
  const [registryError, setRegistryError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setRegistryError(null);

    runCihub("commands", ["list"], {
      cwd,
      timeoutMs: resolveTimeout("commands"),
      json: true
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
  }, [cwd]);

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
    if (registryError) {
      return [...warnings, `Command registry unavailable: ${registryError}`];
    }
    return warnings;
  }, [registryError, warnings]);

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

        const timeoutMs = resolveTimeout(resolved.command);
        const payload = await runCihub(resolved.command, resolved.args, {
          cwd,
          timeoutMs,
          json: supportsJsonRuntime
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
    [cwd, exit, helpOutput, registry, toOutputResult]
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
          {loading && <Spinner label="Running" />}
          {!loading && result && <Output result={result} />}
          {!loading && !result && (
            <Text dimColor>
              Enter a command to begin. Try /help or /exit.
            </Text>
          )}
        </Box>

        <Box marginTop={1}>
          <Input
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            placeholder="Type /help or a cihub command..."
            disabled={loading}
          />
        </Box>
      </Box>
    </ErrorBoundary>
  );
}
