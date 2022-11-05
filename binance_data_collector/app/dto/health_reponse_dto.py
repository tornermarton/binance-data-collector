# coding=utf-8
import pydantic


class HealthResponseDTO(pydantic.BaseModel):
    status: str
