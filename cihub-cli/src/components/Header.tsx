import React from "react";
import { Box, Text } from "ink";

type HeaderProps = {
  cwd: string;
  version: string;
  pythonVersion: string;
  warnings?: string[];
};

export function Header({
  cwd,
  version,
  pythonVersion,
  warnings = []
}: HeaderProps) {
  return (
    <Box flexDirection="column">
      <Box>
        <Text color="cyan">CIHub Interactive</Text>
        <Text>  ts {version} / py {pythonVersion}</Text>
      </Box>
      <Text dimColor>cwd: {cwd}</Text>
      {warnings.length > 0 && (
        <Box flexDirection="column" marginTop={1}>
          <Text color="yellow">Warnings:</Text>
          {warnings.map((warning, index) => (
            <Text key={`${warning}-${index}`}>- {warning}</Text>
          ))}
        </Box>
      )}
      <Text>{"-".repeat(64)}</Text>
    </Box>
  );
}
