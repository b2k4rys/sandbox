from pydantic import BaseModel, field_validator
from pydantic_core.core_schema import ValidationInfo


class CodeResponse(BaseModel):
    stdout: str | None = None
    stderr: str | None = None

class TaskEnqueueResponse(BaseModel):
    task_id: str

class CeleryTaskResponse(BaseModel):
    task_id: str
    task_status: str
    task_result: dict | str

    @field_validator('task_result', mode='after')
    @classmethod
    def check_task_result(cls, value: str, info: ValidationInfo) -> str:
        if info.data['task_status'] == "SUCCESS":
            return value
        else:
            return str(value)