export class ParseError extends Error {
  input: string;

  constructor(message: string, input: string) {
    super(message);
    this.name = "ParseError";
    this.input = input;
  }
}

export class CommandExecutionError extends Error {
  command: string;
  exitCode: number | null;
  stderr?: string;

  constructor(message: string, command: string, exitCode: number | null, stderr?: string) {
    super(message);
    this.name = "CommandExecutionError";
    this.command = command;
    this.exitCode = exitCode;
    this.stderr = stderr;
  }
}

export class JsonParseError extends Error {
  rawOutput: string;

  constructor(message: string, rawOutput: string) {
    super(message);
    this.name = "JsonParseError";
    this.rawOutput = rawOutput;
  }
}
