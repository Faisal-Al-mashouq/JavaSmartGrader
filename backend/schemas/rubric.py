from __future__ import annotations

from pydantic import BaseModel, model_validator

STANDARD_CRITERIA_KEYS = ["correctness", "edge_cases", "code_quality", "efficiency"]

DEFAULT_RUBRIC: dict = {
    "criteria": {
        "correctness": {
            "label": "Correctness",
            "weight": 40,
            "description": "Does the solution produce"
            " correct output for all given test cases?",
            "is_standard": True,
        },
        "edge_cases": {
            "label": "Edge Cases",
            "weight": 20,
            "description": "Does the solution handle boundary and edge cases properly?",
            "is_standard": True,
        },
        "code_quality": {
            "label": "Code Quality",
            "weight": 20,
            "description": "Is the code clean,"
            " readable, and following good programming practices?",
            "is_standard": True,
        },
        "efficiency": {
            "label": "Efficiency",
            "weight": 20,
            "description": "Does the solution use appropriate "
            "algorithms and data structures to minimize time and space complexity?",
            "is_standard": True,
        },
    }
}


class RubricCriterion(BaseModel):
    label: str
    weight: float
    description: str
    is_standard: bool = False


class RubricSchema(BaseModel):
    criteria: dict[str, RubricCriterion]

    @model_validator(mode="after")
    def validate_rubric(self) -> RubricSchema:
        criteria = self.criteria

        # All 4 standard criteria must be present
        for key in STANDARD_CRITERIA_KEYS:
            if key not in criteria:
                raise ValueError(f"Standard criterion '{key}' is required")
            if not criteria[key].is_standard:
                raise ValueError(f"Criterion '{key}' must have is_standard=true")

        # At most 2 custom criteria
        custom_keys = [k for k in criteria if k not in STANDARD_CRITERIA_KEYS]
        if len(custom_keys) > 2:
            raise ValueError(
                f"At most 2 custom criteria are allowed, got {len(custom_keys)}"
            )

        # Weights must sum to 100
        total = sum(c.weight for c in criteria.values())
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Rubric weights must sum to 100, got {total:.2f}")

        # Each weight must be non-negative
        for key, criterion in criteria.items():
            if criterion.weight < 0:
                raise ValueError(f"Weight for '{key}' must be non-negative")

        return self
