from typing import Any

from pydantic import BaseModel


class CompilationRequest(BaseModel):
    java_code: str
    language: str


class TestCasesRequest(BaseModel):
    test_inputs: list[str]
    expected_outputs: list[str]


class SandboxRequest(BaseModel):
    java_code: str
    language: str
    test_inputs: list[str]
    expected_outputs: list[str]


class CompilationResult(BaseModel):
    success: bool
    outputs: list[str]


class TestCaseResult(BaseModel):
    success: bool
    outputs: list[str]
    expected_outputs: list[str]


class SandboxResult(BaseModel):
    compilation_result: CompilationResult
    test_case_results: list[TestCaseResult]
    assertions_results: dict[str, Any]
