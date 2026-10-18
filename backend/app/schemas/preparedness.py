from pydantic import BaseModel, ConfigDict


class PreparednessItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hazard: str
    stage: str
    audience: str
    title: str
    body: str
    source_url: str | None = None
    lang: str
