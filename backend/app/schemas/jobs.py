from pydantic import BaseModel


class JobTriggerResponse(BaseModel):
    job_name: str
    status: str
    rows_written: int
    message: str
