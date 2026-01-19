import React from "react";
import { Box, Text } from "ink";

type ErrorBoundaryProps = {
  children: React.ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
  message?: string;
  stack?: string;
};

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, message: error.message, stack: error.stack };
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box flexDirection="column">
          <Text color="red">Application error</Text>
          {this.state.message && <Text>{this.state.message}</Text>}
          {this.state.stack && <Text dimColor>{this.state.stack}</Text>}
        </Box>
      );
    }

    return this.props.children;
  }
}
