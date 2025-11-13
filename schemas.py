"""
Database Schemas for the SaaS starter

Each Pydantic model corresponds to a MongoDB collection with the
collection name equal to the lowercase class name.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password_hash: str = Field(..., description="Hashed password (server-side computed)")
    avatar_url: Optional[str] = Field(None, description="Profile image URL")
    plan: str = Field("free", description="Current plan: free, pro, business")
    is_active: bool = Field(True, description="Active account flag")


class Blogpost(BaseModel):
    """
    Blog posts collection (collection name: blogpost)
    """
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    author: str
    tags: List[str] = []
    published: bool = True
    published_at: Optional[datetime] = None
    cover_image: Optional[str] = None


class Contactmessage(BaseModel):
    """
    Contact messages collection (collection name: contactmessage)
    """
    name: str
    email: EmailStr
    subject: Optional[str] = None
    message: str
    meta: Optional[dict] = None
