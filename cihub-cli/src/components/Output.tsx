import React from "react";
import { Box, Text } from "ink";

import { Problems, type ProblemItem } from "./Problems.js";
import { Suggestions } from "./Suggestions.js";
import { Table } from "./Table.js";

type OutputStatus = "ok" | "warning" | "error" | "info";

type TableData = {
  title?: string;
  headers: string[];
  rows: string[][];
};

export type OutputResult = {
  summary: string;
  status?: OutputStatus;
  problems?: ProblemItem[];
  suggestions?: string[];
  tables?: TableData[];
  details?: string[];
};

type OutputProps = {
  result: OutputResult;
};

const statusColor: Record<OutputStatus, "green" | "yellow" | "red" | "blue"> = {
  ok: "green",
  warning: "yellow",
  error: "red",
  info: "blue"
};

function statusPrefix(status?: OutputStatus) {
  if (!status) {
    return "";
  }
  return `[${status.toUpperCase()}] `;
}

export function Output({ result }: OutputProps) {
  const problems = result.problems ?? [];
  const suggestions = result.suggestions ?? [];
  const tables = result.tables ?? [];
  const details = result.details ?? [];

  return (
    <Box flexDirection="column">
      <Text color={result.status ? statusColor[result.status] : undefined}>
        {statusPrefix(result.status)}{result.summary}
      </Text>

      {details.length > 0 && (
        <Box flexDirection="column" marginTop={1}>
          {details.map((line, index) => (
            <Text key={`${line}-${index}`} dimColor>
              {line}
            </Text>
          ))}
        </Box>
      )}

      <Problems items={problems} />
      <Suggestions items={suggestions} />

      {tables.map((table, index) => (
        <Table
          key={`${table.title ?? "table"}-${index}`}
          title={table.title}
          headers={table.headers}
          rows={table.rows}
        />
      ))}
    </Box>
  );
}
