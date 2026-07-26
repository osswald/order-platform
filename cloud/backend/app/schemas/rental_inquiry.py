from pydantic import BaseModel, EmailStr, Field, field_validator


class RentalInquiryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    organisation: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(None, max_length=80)
    timeframe: str = Field(..., min_length=1, max_length=500)
    message: str = Field(..., min_length=1, max_length=5000)
    # Honeypot — browsers leave this empty; bots often fill it.
    website: str = Field(default="", max_length=500)

    @field_validator("name", "organisation", "timeframe", "message", mode="before")
    @classmethod
    def strip_required(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def strip_optional_phone(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value
