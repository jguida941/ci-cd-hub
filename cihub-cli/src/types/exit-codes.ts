export const ExitCodes = {
  ok: 0,
  error: 1
} as const;

export type ExitCode = (typeof ExitCodes)[keyof typeof ExitCodes];
