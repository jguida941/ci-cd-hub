import { runCihub } from "./cihub.js";
import { deepMerge, type WizardConfig } from "./wizard-steps.js";

export type ProfileSummary = {
  name: string;
  description?: string;
  type?: string;
  language?: string | null;
  config?: WizardConfig;
};

export type ProfileOptions = {
  pythonPath?: string;
  defaultTimeoutMs?: number;
};

export const FALLBACK_PROFILES: ProfileSummary[] = [
  {
    name: "python-strict",
    description: "Strict Python config: full linting, typing, mutation testing",
    config: {
      language: "python",
      python: {
        version: "3.12",
        tools: {
          pytest: { enabled: true },
          ruff: { enabled: true },
          black: { enabled: true },
          isort: { enabled: true },
          mypy: { enabled: true },
          bandit: { enabled: true },
          pip_audit: { enabled: true },
          mutmut: { enabled: true },
          trivy: { enabled: true }
        }
      },
      thresholds: {
        coverage_min: 90,
        mutation_score_min: 80
      }
    }
  },
  {
    name: "python-minimal",
    description: "Minimal Python config: basic tests and linting",
    config: {
      language: "python",
      python: {
        version: "3.12",
        tools: {
          pytest: { enabled: true },
          ruff: { enabled: true }
        }
      },
      thresholds: {
        coverage_min: 60
      }
    }
  },
  {
    name: "java-enterprise",
    description: "Enterprise Java: full security suite, strict coverage",
    config: {
      language: "java",
      java: {
        build_tool: "maven",
        version: "17",
        tools: {
          junit: { enabled: true },
          jacoco: { enabled: true },
          checkstyle: { enabled: true },
          spotbugs: { enabled: true },
          owasp: { enabled: true }
        }
      },
      security: {
        gitleaks: { enabled: true }
      },
      thresholds: {
        coverage_min: 85,
        max_critical_vulns: 0
      }
    }
  }
];

export async function listProfiles(
  cwd: string,
  options: ProfileOptions = {}
): Promise<ProfileSummary[]> {
  try {
    const result = await runCihub("profile", ["list"], {
      cwd,
      json: true,
      pythonPath: options.pythonPath,
      defaultTimeoutMs: options.defaultTimeoutMs
    });
    const profiles = (result.data?.profiles as ProfileSummary[] | undefined) ?? [];
    if (profiles.length > 0) {
      return profiles;
    }
  } catch {
    // Fall back to static profiles.
  }
  return FALLBACK_PROFILES;
}

export async function loadProfileConfig(
  cwd: string,
  name: string,
  options: ProfileOptions = {}
): Promise<WizardConfig | null> {
  try {
    const result = await runCihub("profile", ["show", name], {
      cwd,
      json: true,
      pythonPath: options.pythonPath,
      defaultTimeoutMs: options.defaultTimeoutMs
    });
    const profile = result.data?.profile as WizardConfig | undefined;
    if (profile) {
      return profile;
    }
  } catch {
    // Fall back to static profiles.
  }
  const fallback = FALLBACK_PROFILES.find((profile) => profile.name === name);
  return fallback?.config ?? null;
}

export function applyProfileConfig(
  base: WizardConfig,
  profile: WizardConfig | null
): WizardConfig {
  if (!profile) {
    return base;
  }
  return deepMerge(base, profile);
}
