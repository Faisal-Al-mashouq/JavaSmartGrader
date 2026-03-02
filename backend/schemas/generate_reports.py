from pydantic import BaseModel


class GenerateReportBase(BaseModel):
    id: int
    assignment_id: int
    report_text: str | None = None

    model_config = {"from_attributes": True}
