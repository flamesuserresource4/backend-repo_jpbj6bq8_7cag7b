import os
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from passlib.context import CryptContext
from jose import jwt

from database import db, create_document, get_documents

# App setup
app = FastAPI(title="SaaS Starter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALG = "HS256"
JWT_EXPIRES_MIN = 60 * 24 * 7  # 7 days


# Request/Response models
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: Optional[str] = None
    message: str
    meta: Optional[dict] = None


class BlogItem(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    author: str
    tags: List[str] = []
    published: bool = True
    published_at: Optional[datetime] = None
    cover_image: Optional[str] = None


# Helpers

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRES_MIN))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)
    return encoded_jwt


# Routes
@app.get("/")
def root():
    return {"message": "SaaS Starter Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Auth endpoints
@app.post("/api/auth/register")
def register(payload: RegisterRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    existing = db["user"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_doc = {
        "name": payload.name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "avatar_url": None,
        "plan": "free",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    res = db["user"].insert_one(user_doc)
    token = create_access_token({"sub": str(res.inserted_id), "email": payload.email})
    user_doc.pop("password_hash", None)
    user_doc["_id"] = str(res.inserted_id)
    return {"token": token, "user": user_doc}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    user = db["user"].find_one({"email": payload.email})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.get("_id")), "email": user.get("email")})
    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)
    return {"token": token, "user": user}


# Blog endpoints
@app.get("/api/blogs")
def list_blogs(limit: int = 6):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # Seed a few demo posts if empty
    count = db["blogpost"].count_documents({})
    if count == 0:
        seed_posts = [
            {
                "title": "Designing Trust in Fintech",
                "slug": "designing-trust-in-fintech",
                "excerpt": "How micro-interactions and clear copy build confidence in digital banking.",
                "content": "Long form content...",
                "author": "Team",
                "tags": ["design", "fintech"],
                "published": True,
                "published_at": datetime.utcnow(),
                "cover_image": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "title": "Pricing Psychology 101",
                "slug": "pricing-psychology-101",
                "excerpt": "Make tiers that guide choices without pressure.",
                "content": "Long form content...",
                "author": "Team",
                "tags": ["pricing", "growth"],
                "published": True,
                "published_at": datetime.utcnow(),
                "cover_image": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "title": "Your First 100 Users",
                "slug": "your-first-100-users",
                "excerpt": "Practical channels to get traction for your SaaS.",
                "content": "Long form content...",
                "author": "Team",
                "tags": ["growth"],
                "published": True,
                "published_at": datetime.utcnow(),
                "cover_image": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ]
        if seed_posts:
            db["blogpost"].insert_many(seed_posts)

    docs = get_documents("blogpost", {"published": True}, limit)
    # Convert ObjectId
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return {"items": docs}


# Contact endpoint
@app.post("/api/contact")
def contact(payload: ContactRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    doc = payload.dict()
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    res_id = create_document("contactmessage", doc)
    return {"status": "ok", "id": res_id}


# Schemas endpoint for viewers
@app.get("/schema")
def get_schema():
    try:
        from schemas import User, Blogpost, Contactmessage
        return {
            "user": User.model_json_schema(),
            "blogpost": Blogpost.model_json_schema(),
            "contactmessage": Contactmessage.model_json_schema(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to generate schema: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
