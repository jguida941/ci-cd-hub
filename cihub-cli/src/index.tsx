import React from "react";
import { render } from "ink";

import { run } from "./cli.js";
import { App } from "./app.js";

run()
  .then((result) => {
    if (!result.context) {
      process.exitCode = result.exitCode;
      return;
    }

    render(
      <App
        cwd={result.context.cwd}
        version={result.context.version}
        pythonVersion={result.context.python.version ?? "unknown"}
        warnings={result.context.warnings}
      />
    );
    process.exitCode = result.exitCode;
  })
  .catch((error) => {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`Unexpected error: ${message}`);
    process.exitCode = 1;
  });
