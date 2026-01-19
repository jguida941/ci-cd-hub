import React, { useEffect, useState } from "react";
import { Box, Text } from "ink";

type SpinnerProps = {
  label?: string;
  active?: boolean;
  intervalMs?: number;
};

const frames = ["-", "\\", "|", "/"];

export function Spinner({
  label = "Running",
  active = true,
  intervalMs = 80
}: SpinnerProps) {
  const [frameIndex, setFrameIndex] = useState(0);

  useEffect(() => {
    if (!active) {
      return;
    }

    const timer = setInterval(() => {
      setFrameIndex((current) => (current + 1) % frames.length);
    }, intervalMs);

    return () => clearInterval(timer);
  }, [active, intervalMs]);

  if (!active) {
    return null;
  }

  return (
    <Box>
      <Text>{frames[frameIndex]}</Text>
      <Text> {label}...</Text>
    </Box>
  );
}
