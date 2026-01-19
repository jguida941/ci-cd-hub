import React from "react";
import { Box, Text } from "ink";
import TextInput from "ink-text-input";

type InputProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
};

export function Input({
  value,
  onChange,
  onSubmit,
  placeholder,
  disabled = false
}: InputProps) {
  return (
    <Box>
      <Text color={disabled ? "gray" : "green"}>{"> "}</Text>
      <TextInput
        value={value}
        onChange={onChange}
        onSubmit={onSubmit}
        placeholder={placeholder}
        focus={!disabled}
      />
    </Box>
  );
}
