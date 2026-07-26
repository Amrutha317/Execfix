import type { DebugResponse } from "@/lib/types";

export const EXAMPLE_CODE = `def get_item(items, index):
    return items[index]

get_item([1, 2, 3], 10)
`;

const FIRST_ATTEMPT_CODE = EXAMPLE_CODE;

const PATCHED_CODE = `def get_item(items, index):
    if index >= len(items):
        raise IndexError(f"index {index} out of range for {len(items)} items")
    return items[index]

get_item([1, 2, 3], 10)
`;

const TRACEBACK = `Traceback (most recent call last):
  File "candidate.py", line 4, in <module>
    get_item([1, 2, 3], 10)
  File "candidate.py", line 2, in get_item
    return items[index]
           ~~~~~^^^^^^^
IndexError: list index out of range
`;

export const EXAMPLE_RESULT: DebugResponse = {
  success: true,
  attempts_used: 2,
  final_code: PATCHED_CODE,
  original_code: FIRST_ATTEMPT_CODE,
  final_error: "",
  final_exception_type: null,
  history: [
    {
      attempt: 1,
      code: FIRST_ATTEMPT_CODE,
      success: false,
      error: TRACEBACK,
      exception_type: "IndexError",
      duration_ms: 180,
      rejected: false,
      llm_output: PATCHED_CODE
    },
    {
      attempt: 2,
      code: PATCHED_CODE,
      success: true,
      error: "",
      exception_type: null,
      duration_ms: 210,
      rejected: false,
      llm_output: null
    }
  ]
};
