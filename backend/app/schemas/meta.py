from pydantic import BaseModel, Field


class SourceAttribution(BaseModel):
    name: str
    category: str
    license: str
    attribution_text: str
    url: str


class SourcesMetaResponse(BaseModel):
    sources: list[SourceAttribution] = Field(default_factory=list)


class DisclaimerResponse(BaseModel):
    disclaimer: str
    academic_mandate: str
    official_authorities: list[str] = Field(default_factory=list)
    guidance: str
