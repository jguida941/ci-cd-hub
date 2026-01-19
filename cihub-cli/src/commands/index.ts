import type { ParsedInput } from "../lib/parser.js";
import type { CommandResult } from "../types/command-result.js";

type MetaCommand = "help" | "clear" | "exit";

type MetaCommandEntry = {
  name: MetaCommand;
  description: string;
};

export type CommandRegistryEntry = {
  path: string[];
  command: string;
  help?: string;
  options?: { flags: string[]; help?: string; dest?: string }[];
  supports_json?: boolean;
  supports_json_runtime?: boolean;
  supports_wizard?: boolean;
  supports_interactive?: boolean;
  is_group?: boolean;
};

export type CommandRegistryPayload = {
  commands: CommandRegistryEntry[];
  schema?: Record<string, unknown>;
  wizard?: Record<string, unknown>;
  cli_version?: string;
};

export type HelpTable = {
  title: string;
  headers: string[];
  rows: string[][];
};

export type CommandRegistry = {
  entries: CommandRegistryEntry[];
  commandMap: Map<string, CommandRegistryEntry>;
  groupMap: Map<string, CommandRegistryEntry>;
  maxTokens: number;
  helpTables: HelpTable[];
};

const META_COMMANDS: MetaCommandEntry[] = [
  { name: "help", description: "Show help" },
  { name: "clear", description: "Clear current output" },
  { name: "exit", description: "Exit the interactive CLI" }
];

const HELP_HEADERS = ["Command", "Description"] as const;

export type ResolvedCommand =
  | { kind: "meta"; name: MetaCommand }
  | { kind: "group"; command: string; entry: CommandRegistryEntry }
  | { kind: "python"; command: string; args: string[]; entry?: CommandRegistryEntry };

function normalizeEntry(entry: CommandRegistryEntry): CommandRegistryEntry {
  const path = entry.path?.length ? entry.path : entry.command.split(" ");
  return {
    ...entry,
    path,
    command: entry.command ?? path.join(" ")
  };
}

function buildHelpTables(entries: CommandRegistryEntry[]): HelpTable[] {
  const leafEntries = entries.filter((entry) => !entry.is_group);
  const grouped = new Map<string, CommandRegistryEntry[]>();

  leafEntries.forEach((entry) => {
    const key = entry.path.length === 1 ? "Top-level" : entry.path[0];
    const existing = grouped.get(key) ?? [];
    existing.push(entry);
    grouped.set(key, existing);
  });

  const tables: HelpTable[] = [
    {
      title: "Meta commands",
      headers: [...HELP_HEADERS],
      rows: META_COMMANDS.map((command) => [
        `/${command.name}`,
        command.description
      ])
    }
  ];

  Array.from(grouped.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .forEach(([group, items]) => {
      const rows = items
        .slice()
        .sort((a, b) => a.command.localeCompare(b.command))
        .map((entry) => [
          `/${entry.command}`,
          entry.help ?? ""
        ]);

      tables.push({
        title: `${group} commands`,
        headers: [...HELP_HEADERS],
        rows
      });
    });

  return tables;
}

export function extractCommandRegistry(result: CommandResult): CommandRegistryPayload | null {
  const data = result.data as Record<string, unknown> | undefined;
  if (!data) {
    return null;
  }

  const commands = data.commands;
  if (!Array.isArray(commands)) {
    return null;
  }

  return {
    commands: commands as CommandRegistryEntry[],
    schema: (data.schema as Record<string, unknown> | undefined) ?? undefined,
    wizard: (data.wizard as Record<string, unknown> | undefined) ?? undefined,
    cli_version: (data.cli_version as string | undefined) ?? undefined
  };
}

export function buildCommandRegistry(entries: CommandRegistryEntry[]): CommandRegistry {
  const normalized = entries.map(normalizeEntry);
  const groupEntries = normalized.filter((entry) => entry.is_group);
  const leafEntries = normalized.filter((entry) => !entry.is_group);
  const commandMap = new Map<string, CommandRegistryEntry>(
    leafEntries.map((entry) => [entry.command, entry])
  );
  const groupMap = new Map<string, CommandRegistryEntry>(
    groupEntries.map((entry) => [entry.command, entry])
  );

  const maxTokens = normalized
    .map((entry) => entry.path.length)
    .reduce((max, count) => Math.max(max, count), 1);

  return {
    entries: normalized,
    commandMap,
    groupMap,
    maxTokens,
    helpTables: buildHelpTables(normalized)
  };
}

export function getHelpTables(registry: CommandRegistry | null): HelpTable[] {
  if (!registry) {
    return [
      {
        title: "Meta commands",
        headers: [...HELP_HEADERS],
        rows: META_COMMANDS.map((command) => [
          `/${command.name}`,
          command.description
        ])
      }
    ];
  }

  return registry.helpTables;
}

export function getGroupHelpTable(
  registry: CommandRegistry,
  group: string
): HelpTable | null {
  const entries = registry.entries.filter(
    (entry) => !entry.is_group && entry.path[0] === group
  );
  if (!entries.length) {
    return null;
  }

  const rows = entries
    .slice()
    .sort((a, b) => a.command.localeCompare(b.command))
    .map((entry) => [
      `/${entry.command}`,
      entry.help ?? ""
    ]);

  return {
    title: `${group} commands`,
    headers: [...HELP_HEADERS],
    rows
  };
}

function splitCommand(command: string) {
  const tokens = command.split(" ");
  return {
    command: tokens[0] ?? "",
    args: tokens.slice(1)
  };
}

export function resolveCommand(
  parsed: ParsedInput,
  registry: CommandRegistry | null
): ResolvedCommand {
  if (parsed.isSlash && registry) {
    const match = META_COMMANDS.find((command) => command.name === parsed.command);
    if (match) {
      return { kind: "meta", name: match.name };
    }

    const tokens = [parsed.command, ...parsed.args];
    const maxDepth = Math.min(tokens.length, registry.maxTokens);
    for (let depth = maxDepth; depth > 0; depth -= 1) {
      const key = tokens.slice(0, depth).join(" ");
      const remaining = tokens.slice(depth);
      const definition = registry.commandMap.get(key);
      if (definition) {
        const python = splitCommand(definition.command);
        return {
          kind: "python",
          command: python.command,
          args: [...python.args, ...remaining],
          entry: definition
        };
      }

      const groupEntry = registry.groupMap.get(key);
      if (groupEntry && remaining.length === 0) {
        return {
          kind: "group",
          command: key,
          entry: groupEntry
        };
      }
    }
  }

  if (parsed.isSlash) {
    const match = META_COMMANDS.find((command) => command.name === parsed.command);
    if (match) {
      return { kind: "meta", name: match.name };
    }
  }

  return {
    kind: "python",
    command: parsed.command,
    args: parsed.args
  };
}
