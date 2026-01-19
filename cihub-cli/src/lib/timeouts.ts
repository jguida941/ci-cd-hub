const DEFAULT_TIMEOUT_MS = 60_000;

const COMMAND_TIMEOUTS: Record<string, number> = {
  check: 180_000,
  ci: 300_000,
  report: 180_000,
  triage: 180_000,
  smoke: 180_000
};

export function resolveTimeout(command: string) {
  return COMMAND_TIMEOUTS[command] ?? DEFAULT_TIMEOUT_MS;
}
