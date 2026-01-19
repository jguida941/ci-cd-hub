import { ParseError } from "./errors.js";

export type ParsedInput = {
  raw: string;
  command: string;
  args: string[];
  isSlash: boolean;
};

function splitArgs(input: string) {
  const tokens: string[] = [];
  let current = "";
  let inQuotes: "\"" | "'" | null = null;
  let escaped = false;

  for (const char of input) {
    if (escaped) {
      current += char;
      escaped = false;
      continue;
    }

    if (char === "\\") {
      escaped = true;
      continue;
    }

    if (inQuotes) {
      if (char === inQuotes) {
        inQuotes = null;
        continue;
      }
      current += char;
      continue;
    }

    if (char === "\"" || char === "'") {
      inQuotes = char as "\"" | "'";
      continue;
    }

    if (char.trim() === "") {
      if (current) {
        tokens.push(current);
        current = "";
      }
      continue;
    }

    current += char;
  }

  if (current) {
    tokens.push(current);
  }

  if (inQuotes) {
    throw new ParseError("Unterminated quote in command", input);
  }

  return tokens;
}

export function parseInput(input: string): ParsedInput {
  const raw = input.trim();
  if (!raw) {
    throw new ParseError("No command provided", input);
  }

  if (raw === "?") {
    return {
      raw,
      command: "help",
      args: [],
      isSlash: true
    };
  }

  let tokens = splitArgs(raw);
  if (tokens[0] === "cihub") {
    tokens = tokens.slice(1);
    if (tokens.length === 0) {
      throw new ParseError("Expected a subcommand after 'cihub'", input);
    }
  }
  const [first, ...rest] = tokens;
  if (!first) {
    throw new ParseError("No command token provided", input);
  }

  const isSlash = first.startsWith("/");
  const command = isSlash ? first.slice(1) : first;

  if (!command) {
    throw new ParseError("Slash command requires a name", input);
  }

  return {
    raw,
    command,
    args: rest,
    isSlash
  };
}
