import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  ConfigSchema,
  loadConfig,
  type Config,
  type ConfigLoadResult,
  type ConfigSource
} from "../lib/config.js";

export type ConfigState = {
  config: Config;
  sources: ConfigSource[];
  errors: string[];
  hasFileConfig: boolean;
  loading: boolean;
  ready: boolean;
  reload: () => Promise<void>;
};

const ConfigContext = createContext<ConfigState | null>(null);

type ConfigProviderProps = {
  cwd: string;
  children: React.ReactNode;
};

export function ConfigProvider({ cwd, children }: ConfigProviderProps) {
  const [state, setState] = useState<ConfigLoadResult & { loading: boolean; ready: boolean }>(() => ({
    config: ConfigSchema.parse({}),
    sources: [],
    errors: [],
    hasFileConfig: false,
    loading: true,
    ready: false
  }));

  const reload = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true }));
    const result = await loadConfig(cwd);
    setState({
      ...result,
      loading: false,
      ready: true
    });
  }, [cwd]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const value = useMemo<ConfigState>(
    () => ({
      config: state.config,
      sources: state.sources,
      errors: state.errors,
      hasFileConfig: state.hasFileConfig,
      loading: state.loading,
      ready: state.ready,
      reload
    }),
    [reload, state]
  );

  return <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>;
}

export function useConfig(): ConfigState {
  const ctx = useContext(ConfigContext);
  if (!ctx) {
    throw new Error("useConfig must be used within ConfigProvider");
  }
  return ctx;
}
