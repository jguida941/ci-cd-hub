export type WizardConfig = Record<string, unknown>;

export type WizardFlow = "new" | "init" | "config-edit";

export type WizardStepType = "text" | "select" | "confirm";

export type WizardStepScope = "config" | "meta";

export type WizardStep = {
  id: string;
  type: WizardStepType;
  question: string;
  key: string;
  scope?: WizardStepScope;
  default?: string | boolean;
  choices?: string[];
  condition?: (config: WizardConfig) => boolean;
  parse?: (value: string) => unknown;
};

export const BASE_CONFIG_STEPS: WizardStep[] = [
  { id: "repo.owner", type: "text", question: "Repo owner (org/user):", key: "repo.owner" },
  { id: "repo.name", type: "text", question: "Repo name:", key: "repo.name" },
  {
    id: "repo.use_central",
    type: "confirm",
    question: "Use central runner?",
    key: "repo.use_central_runner",
    default: true
  },
  {
    id: "repo.repo_side",
    type: "confirm",
    question: "Enable repo-side execution?",
    key: "repo.repo_side_execution",
    default: false
  },
  {
    id: "language",
    type: "select",
    question: "Select language:",
    key: "language",
    choices: ["java", "python"]
  },
  {
    id: "python.version",
    type: "select",
    question: "Python version:",
    key: "python.version",
    choices: ["3.12", "3.11", "3.10", "3.9"],
    default: "3.12",
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.pytest",
    type: "confirm",
    question: "Enable pytest?",
    key: "python.tools.pytest.enabled",
    default: true,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.ruff",
    type: "confirm",
    question: "Enable ruff (linter)?",
    key: "python.tools.ruff.enabled",
    default: true,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.black",
    type: "confirm",
    question: "Enable black (formatter)?",
    key: "python.tools.black.enabled",
    default: true,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.isort",
    type: "confirm",
    question: "Enable isort (import sorter)?",
    key: "python.tools.isort.enabled",
    default: false,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.mypy",
    type: "confirm",
    question: "Enable mypy (type checker)?",
    key: "python.tools.mypy.enabled",
    default: false,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.bandit",
    type: "confirm",
    question: "Enable bandit (security)?",
    key: "python.tools.bandit.enabled",
    default: true,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.pip_audit",
    type: "confirm",
    question: "Enable pip-audit (dependency audit)?",
    key: "python.tools.pip_audit.enabled",
    default: true,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.mutmut",
    type: "confirm",
    question: "Enable mutmut (mutation testing)?",
    key: "python.tools.mutmut.enabled",
    default: false,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.hypothesis",
    type: "confirm",
    question: "Enable hypothesis (property testing)?",
    key: "python.tools.hypothesis.enabled",
    default: false,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.semgrep",
    type: "confirm",
    question: "Enable semgrep (SAST)?",
    key: "python.tools.semgrep.enabled",
    default: false,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.trivy",
    type: "confirm",
    question: "Enable trivy (container scanner)?",
    key: "python.tools.trivy.enabled",
    default: true,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.codeql",
    type: "confirm",
    question: "Enable codeql (code analysis)?",
    key: "python.tools.codeql.enabled",
    default: false,
    condition: (c) => c.language === "python"
  },
  {
    id: "python.tools.docker",
    type: "confirm",
    question: "Enable docker builds?",
    key: "python.tools.docker.enabled",
    default: false,
    condition: (c) => c.language === "python"
  },
  {
    id: "java.build_tool",
    type: "select",
    question: "Build tool:",
    key: "java.build_tool",
    choices: ["maven", "gradle"],
    default: "maven",
    condition: (c) => c.language === "java"
  },
  {
    id: "java.version",
    type: "select",
    question: "Java version:",
    key: "java.version",
    choices: ["21", "17", "11", "8"],
    default: "17",
    condition: (c) => c.language === "java"
  },
  {
    id: "java.tools.junit",
    type: "confirm",
    question: "Enable JUnit tests?",
    key: "java.tools.junit.enabled",
    default: true,
    condition: (c) => c.language === "java"
  },
  {
    id: "java.tools.jacoco",
    type: "confirm",
    question: "Enable JaCoCo coverage?",
    key: "java.tools.jacoco.enabled",
    default: true,
    condition: (c) => c.language === "java"
  },
  {
    id: "java.tools.pitest",
    type: "confirm",
    question: "Enable PITest mutation testing?",
    key: "java.tools.pitest.enabled",
    default: true,
    condition: (c) => c.language === "java"
  },
  {
    id: "java.tools.pitest.timeout_multiplier",
    type: "text",
    question: "PITest timeout multiplier (default 2):",
    key: "java.tools.pitest.timeout_multiplier",
    default: "2",
    parse: (value) => {
      const parsed = Number.parseInt(value, 10);
      if (Number.isNaN(parsed) || parsed < 1) {
        throw new Error("Enter a whole number >= 1");
      }
      return parsed;
    },
    condition: (c) =>
      c.language === "java" &&
      getNestedValue(c, "java.tools.pitest.enabled") !== false
  },
  {
    id: "java.tools.checkstyle",
    type: "confirm",
    question: "Enable Checkstyle?",
    key: "java.tools.checkstyle.enabled",
    default: true,
    condition: (c) => c.language === "java"
  },
  {
    id: "java.tools.spotbugs",
    type: "confirm",
    question: "Enable SpotBugs?",
    key: "java.tools.spotbugs.enabled",
    default: false,
    condition: (c) => c.language === "java"
  },
  {
    id: "java.tools.owasp",
    type: "confirm",
    question: "Enable OWASP dependency check?",
    key: "java.tools.owasp.enabled",
    default: true,
    condition: (c) => c.language === "java"
  },
  {
    id: "java.tools.owasp.timeout_seconds",
    type: "text",
    question: "OWASP timeout in seconds (default 1800):",
    key: "java.tools.owasp.timeout_seconds",
    default: "1800",
    parse: (value) => {
      const parsed = Number.parseInt(value, 10);
      if (Number.isNaN(parsed) || parsed < 60) {
        throw new Error("Enter a whole number >= 60");
      }
      return parsed;
    },
    condition: (c) =>
      c.language === "java" &&
      getNestedValue(c, "java.tools.owasp.enabled") !== false
  },
  {
    id: "security.gitleaks",
    type: "confirm",
    question: "Enable gitleaks (secret scanning)?",
    key: "security.gitleaks.enabled",
    default: true
  },
  {
    id: "thresholds.coverage",
    type: "text",
    question: "Coverage threshold (%):",
    key: "thresholds.coverage_min",
    default: "80",
    parse: (value) => {
      const parsed = Number.parseFloat(value);
      if (Number.isNaN(parsed)) {
        throw new Error("Enter a valid number");
      }
      return parsed;
    }
  },
  {
    id: "thresholds.max_critical",
    type: "text",
    question: "Max critical vulnerabilities allowed:",
    key: "thresholds.max_critical_vulns",
    default: "0",
    parse: (value) => {
      const parsed = Number.parseInt(value, 10);
      if (Number.isNaN(parsed)) {
        throw new Error("Enter a valid integer");
      }
      return parsed;
    }
  }
];

export function getWizardSteps(flow: WizardFlow, profiles: string[] = []): WizardStep[] {
  const steps: WizardStep[] = [];

  if (flow === "new" && profiles.length > 0) {
    steps.push({
      id: "meta.profile",
      scope: "meta",
      type: "select",
      question: "Apply a profile?",
      key: "profileName",
      choices: ["none", ...profiles],
      default: "none"
    });
  }

  if (flow === "init") {
    steps.push({
      id: "meta.repo_path",
      scope: "meta",
      type: "text",
      question: "Repo path:",
      key: "repoPath",
      default: "."
    });
  }

  if (flow === "config-edit") {
    steps.push({
      id: "meta.repo_name",
      scope: "meta",
      type: "text",
      question: "Repo config name:",
      key: "repoName"
    });
  }

  steps.push(...BASE_CONFIG_STEPS);

  steps.push({
    id: "meta.apply",
    scope: "meta",
    type: "confirm",
    question: "Write files now?",
    key: "apply",
    default: true
  });

  return steps;
}

export function getActiveSteps(steps: WizardStep[], config: WizardConfig): WizardStep[] {
  return steps.filter((step) => {
    if (!step.condition) {
      return true;
    }
    return step.condition(config);
  });
}

export function getNestedValue(config: WizardConfig, path: string): unknown {
  const parts = path.split(".").filter(Boolean);
  let cursor: unknown = config;
  for (const key of parts) {
    if (typeof cursor !== "object" || cursor === null) {
      return undefined;
    }
    const next = (cursor as Record<string, unknown>)[key];
    if (next === undefined) {
      return undefined;
    }
    cursor = next;
  }
  return cursor;
}

export function setNestedValue(config: WizardConfig, path: string, value: unknown): WizardConfig {
  const parts = path.split(".").filter(Boolean);
  if (parts.length === 0) {
    return config;
  }
  const root: WizardConfig = { ...config };
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

export function deepMerge(base: WizardConfig, override: WizardConfig): WizardConfig {
  const result: WizardConfig = { ...base };
  Object.entries(override).forEach(([key, value]) => {
    if (
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      typeof result[key] === "object" &&
      result[key] !== null &&
      !Array.isArray(result[key])
    ) {
      result[key] = deepMerge(
        result[key] as WizardConfig,
        value as WizardConfig
      );
    } else {
      result[key] = value;
    }
  });
  return result;
}
