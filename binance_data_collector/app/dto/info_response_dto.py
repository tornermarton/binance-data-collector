# coding=utf-8
import datetime

import pydantic


class InfoResponseDTO(pydantic.BaseModel):
    time: datetime.datetime
    timezone: str
