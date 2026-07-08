from pydantic import BaseModel, Field, computed_field


class SavedListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    symbols: list[str] = Field(default_factory=list)


class SavedListRead(BaseModel):
    id: int
    owner_id: int
    name: str
    tickers: list[str] = Field(default_factory=list, exclude=True)

    @computed_field
    @property
    def symbols(self) -> list[str]:
        return self.tickers

    model_config = {"from_attributes": True}
