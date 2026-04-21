from datetime import datetime

from pydantic import BaseModel


class RubricCriterion(BaseModel):
    key: str
    label: str
    weight: int


class RubricUpdate(BaseModel):
    criteria: list[RubricCriterion]


class AssignmentBase(BaseModel):
    id: int
    course_id: int
    title: str
    description: str | None = None
    due_date: datetime | None = None
    visible_at: datetime | None = None
    rubric_json: dict | None = None

    model_config = {"from_attributes": True}
