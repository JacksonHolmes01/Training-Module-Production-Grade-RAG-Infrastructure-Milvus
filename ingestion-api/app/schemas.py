"""
schemas.py — Pydantic request/response models for the ingestion API.

These are intentionally simple so students can focus on the infrastructure
rather than complex validation logic. Fields match the Milvus collection
schema defined in milvus_client.py.
"""

from typing import Optional, Literal, List
from pydantic import BaseModel, Field


class ArticleIn(BaseModel):
    """Schema for documents submitted to POST /ingest."""
    title:          str  = Field(default="",  max_length=200)
    url:            str  = Field(default="",  max_length=2048)
    source:         str  = Field(default="",  max_length=200)
    published_date: str  = Field(default="",  max_length=30)
    text:           str  = Field(min_length=1, max_length=30000)
    tags:           List[str] = Field(default_factory=list)


class ChatIn(BaseModel):
    """Schema for POST /chat and debug endpoints."""
    message: str = Field(min_length=2, max_length=2000)

    # Controls response verbosity:
    #   basic    -> short, beginner-friendly
    #   standard -> normal depth (default)
    #   advanced -> technical, precise
    detail_level: Optional[Literal["basic", "standard", "advanced"]] = "standard"
