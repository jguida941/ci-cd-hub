import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.tsx"],
  format: ["esm"],
  target: "node20",
  clean: true,
  minify: true,
  bundle: true,
  external: ["react", "ink"]
});
