import { z } from "zod";

export const IssueSchema = z
  .object({
    severity: z.string().optional(),
    message: z.string().optional()
  })
  .passthrough();

export const CommandResultSchema = z
  .object({
    command: z.string().optional(),
    status: z.string().optional(),
    exit_code: z.number().int(),
    duration_ms: z.number().int().optional(),
    summary: z.string().optional(),
    artifacts: z.record(z.unknown()).optional(),
    problems: z.array(IssueSchema).optional(),
    suggestions: z.array(IssueSchema).optional(),
    files_generated: z.array(z.string()).optional(),
    files_modified: z.array(z.string()).optional(),
    data: z.record(z.unknown()).optional()
  })
  .passthrough();

export type CommandResult = z.infer<typeof CommandResultSchema>;
