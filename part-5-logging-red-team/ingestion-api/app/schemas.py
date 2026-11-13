"""
schemas.py: request validation.

extra="forbid" rejects any field the API does not expect. That matters for
security: a client cannot sneak in a "tenant" field to write into another
tenant's data, because the field is refused before any code runs.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ArticleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title:          str = Field(default="", max_length=200)
    url:            str = Field(default="", max_length=2048)
    source:         str = Field(default="", max_length=200)
    published_date: str = Field(default="", max_length=30)
    text:           str = Field(min_length=1, max_length=30000)
    tags:           List[str] = Field(default_factory=list, max_length=20)


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=2, max_length=2000)
    detail_level: Optional[Literal["basic", "standard", "advanced"]] = "standard"
