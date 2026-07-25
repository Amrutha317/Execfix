export type HistoryEntry = {
  attempt?: number;
  code?: string;
  success?: boolean;
  error?: string;
  exception_type?: string | null;
  duration_ms?: number;
  rejected?: boolean;
  llm_output?: string | null;
};

export type DebugResponse = {
  success: boolean;
  attempts_used: number;
  final_code: string;
  original_code: string;
  final_error: string;
  final_exception_type?: string | null;
  history: HistoryEntry[];
};

export type EvalProblemResult = {
  name: string;
  passed: boolean;
  attempts_used: number;
  fixed_on_first_run: boolean;
  final_exception_type?: string | null;
  duration_ms: number;
  final_code: string;
  error_excerpt: string;
  skipped_reason?: string | null;
};

export type EvalResponse = {
  model: string;
  max_attempts: number;
  summary: {
    total: number;
    evaluated: number;
    skipped: number;
    passed: number;
    pass_rate: number;
    avg_attempts_when_passed: number;
  };
  results: EvalProblemResult[];
};

