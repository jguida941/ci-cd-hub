import React from "react";
import { Box, Text } from "ink";

type TableProps = {
  title?: string;
  headers: string[];
  rows: string[][];
};

function padRight(value: string, width: number) {
  return value.padEnd(width, " ");
}

function normalizeRow(row: string[], width: number) {
  const result = row.slice(0, width);
  while (result.length < width) {
    result.push("");
  }
  return result;
}

function computeWidths(headers: string[], rows: string[][]) {
  const widths = headers.map((header) => header.length);
  rows.forEach((row) => {
    row.forEach((cell, index) => {
      widths[index] = Math.max(widths[index] ?? 0, cell.length);
    });
  });
  return widths;
}

function buildDivider(widths: number[]) {
  return `+-${widths.map((width) => "-".repeat(width)).join("-+-")}-+`;
}

function buildRow(cells: string[], widths: number[]) {
  const padded = cells.map((cell, index) => padRight(cell, widths[index]));
  return `| ${padded.join(" | ")} |`;
}

export function Table({ title, headers, rows }: TableProps) {
  const normalizedRows = rows.map((row) => normalizeRow(row, headers.length));
  const widths = computeWidths(headers, normalizedRows);
  const divider = buildDivider(widths);
  const lines = [divider, buildRow(headers, widths), divider];

  normalizedRows.forEach((row) => {
    lines.push(buildRow(row, widths));
  });
  lines.push(divider);

  return (
    <Box flexDirection="column" marginTop={1}>
      {title && <Text color="cyan">{title}</Text>}
      {lines.map((line, index) => (
        <Text key={`${line}-${index}`}>{line}</Text>
      ))}
    </Box>
  );
}
