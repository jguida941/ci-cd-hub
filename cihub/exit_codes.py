"""Exit code registry for cihub CLI."""

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_DECLINED = 3
EXIT_INTERNAL_ERROR = 4
EXIT_INTERRUPTED = 130

EXIT_CODE_DESCRIPTIONS = {
    EXIT_SUCCESS: "success",
    EXIT_FAILURE: "command failed",
    EXIT_USAGE: "invalid usage or precondition",
    EXIT_DECLINED: "user declined confirmation",
    EXIT_INTERNAL_ERROR: "internal error",
    EXIT_INTERRUPTED: "interrupted by user",
}
