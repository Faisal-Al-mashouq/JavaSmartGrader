from pydantic import BaseModel


class QuestionBase(BaseModel):
    id: int
    assignment_id: int
    question_text: str

    model_config = {"from_attributes": True}


class TestcaseBase(BaseModel):
    id: int
    question_id: int
    assignment_id: int
    input: str
    expected_output: str

    model_config = {"from_attributes": True}
