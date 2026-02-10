class CompilationResult:
    def __init__(self, success: bool, output: str):
        self.success = success
        self.output = output


class TestCaseResult:
    def __init__(self, success: bool, output: str, expected_output: str):
        self.success = success
        self.output = output
        self.expected_output = expected_output


class SandboxResult:
    def __init__(
        self,
        compilation_result: CompilationResult,
        test_case_results: list[TestCaseResult],
    ):
        self.compilation_result = compilation_result
        self.test_case_results = test_case_results


if __name__ == "__main__":
    print("Hello from the sandbox worker!")
