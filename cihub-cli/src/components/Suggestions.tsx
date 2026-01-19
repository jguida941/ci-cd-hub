import React from "react";
import { Box, Text } from "ink";

type SuggestionsProps = {
  items: string[];
};

export function Suggestions({ items }: SuggestionsProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <Box flexDirection="column" marginTop={1}>
      <Text color="green">Suggestions</Text>
      {items.map((item, index) => (
        <Text key={`${item}-${index}`}>- {item}</Text>
      ))}
    </Box>
  );
}
