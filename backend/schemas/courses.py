from pydantic import BaseModel


class CourseBase(BaseModel):
    id: int
    name: str
    description: str | None = None
    instructor_id: int

    model_config = {"from_attributes": True}
