from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    build_time: str | None = None


class MessageResponse(BaseModel):
    msg: str
