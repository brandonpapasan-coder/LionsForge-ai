from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CompanyBase(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16)
    name: str = Field(..., min_length=1, max_length=255)
    exchange: str | None = Field(default=None, max_length=64)
    sector: str | None = Field(default=None, max_length=128)
    industry: str | None = Field(default=None, max_length=128)
    country: str | None = Field(default=None, max_length=64)
    website: str | None = Field(default=None, max_length=255)
    description: str | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    exchange: str | None = Field(default=None, max_length=64)
    sector: str | None = Field(default=None, max_length=128)
    industry: str | None = Field(default=None, max_length=128)
    country: str | None = Field(default=None, max_length=64)
    website: str | None = Field(default=None, max_length=255)
    description: str | None = None


class CompanyRead(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
