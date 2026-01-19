import React from "react";
import { Box, Text } from "ink";

export type ProblemItem = {
  severity: "error" | "warning" | "info";
  message: string;
};

type ProblemsProps = {
  items: ProblemItem[];
};

const severityColor: Record<ProblemItem["severity"], "red" | "yellow" | "blue"> = {
  error: "red",
  warning: "yellow",
  info: "blue"
};

const severityLabel: Record<ProblemItem["severity"], string> = {
  error: "!",
  warning: "!",
  info: "i"
};

export function Problems({ items }: ProblemsProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <Box flexDirection="column" marginTop={1}>
      <Text color="red">Problems</Text>
      {items.map((item, index) => (
        <Text key={`${item.message}-${index}`}>
          <Text color={severityColor[item.severity]}>{severityLabel[item.severity]}</Text>
          <Text> {item.message}</Text>
        </Text>
      ))}
    </Box>
  );
}
