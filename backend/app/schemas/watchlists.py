from pydantic import BaseModel, Field


class SavedListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    symbols: list[str] = Field(default_factory=list)


class SavedListRead(BaseModel):
    id: int
    owner_id: int
    name: str
    symbols: list[str]

    model_config = {"from_attributes": True}
