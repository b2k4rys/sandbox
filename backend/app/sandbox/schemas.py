from pydantic import BaseModel

class CodeResponse(BaseModel):
    stdout: str | None = None
    stderr: str | None = None