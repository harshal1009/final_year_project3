from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from jose import jwt
from datetime import datetime, timedelta
from fastapi import Depends, Header, UploadFile, File, Form
from jose import JWTError
import requests
import os
import sys
from pathlib import Path


# print("GROQ_API_KEY loaded:", bool(GROQ_API_KEY))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Add model folder to path for lazy import
sys.path.insert(0, str(Path(__file__).parent / "model"))

import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

# ---------------- CONFIG ----------------

DATABASE_URL = "sqlite:///arogyaai.db"
SECRET_KEY = "arogyaai_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Optional: Remove old database on startup to recreate with new schema
if os.path.exists("arogyaai.db"):
    print("✅ Database found at: arogyaai.db")

# ---------------- APP ----------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DB SETUP ----------------

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ---------------- JWT ----------------
def get_current_user_id(authorization: str = Header(...)):
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return user_id

    except (JWTError, IndexError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ============= H5 MODEL PROCESSING =============
async def process_image_with_h5(image_file: UploadFile) -> str:
    """Process image with H5 model and return prediction"""
    try:
        # Lazy import to avoid circular imports
        from predictor import predict_from_image
        
        print(f"\n[H5 MODEL] Processing image: {image_file.filename}")
        image_bytes = await image_file.read()
        print(f"[H5 MODEL] Image size: {len(image_bytes)} bytes")
        
        image_file.file.seek(0)  # Reset file pointer
        
        print(f"[H5 MODEL] Calling predict_from_image...")
        prediction = predict_from_image(image_bytes)
        print(f"[H5 MODEL] Prediction result: {prediction}")
        print(f"[H5 MODEL] Prediction type: {type(prediction)}")
        
        if not prediction:
            print("[H5 MODEL] ⚠️ Model returned empty prediction")
            return "Unable to identify the issue from image"
            
        return str(prediction)
    except ImportError as e:
        print(f"[H5 MODEL] ❌ Import error: {str(e)}")
        raise Exception(f"Failed to import H5 model: {str(e)}")
    except Exception as e:
        print(f"[H5 MODEL] ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Image processing failed: {str(e)}")


def identify_issue(message: str, image_prediction: str = None) -> str:
    """Identify health issue from message and/or image prediction"""
    
    # If image prediction available, use it
    if image_prediction:
        print(f"[IDENTIFY] Using image prediction: {image_prediction}")
        return f"Image analysis detected: {image_prediction}"
    
    msg = message.lower() if message else ""

    if "burn" in msg:
        return "The issue appears to be a minor burn."
    if "cut" in msg or "wound" in msg:
        return "The issue appears to be a minor cut or wound."
    if "fever" in msg:
        return "The issue appears to be fever-related."

    return "A general health concern was reported."


def generate_first_aid(issue: str, user_message: str = None) -> str:
    """Generate first aid guidance using Groq API"""
    
    if not GROQ_API_KEY:
        return "Please consult a healthcare professional if symptoms persist."

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # Combine issue and user message for better context
    context = f"Issue: {issue}"
    if user_message:
        context += f"\nUser details: {user_message}"

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a healthcare guidance assistant. "
                    "Provide only general first-aid advice. "
                    "Do not diagnose diseases. "
                    "Keep responses short and safe. Always end with: 'Seek professional medical help if symptoms worsen.'"
                ),
            },
            {
                "role": "user",
                "content": f"{context}. Suggest basic first-aid steps.",
            },
        ],
        "temperature": 0.2,
        "max_tokens": 300,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        print(f"[GROQ] Response Status: {response.status_code}")

        if response.status_code != 200:
            print(f"[GROQ] ❌ Error: {response.text}")
            return "Unable to generate AI guidance at the moment. Please try again."

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print(f"[GROQ] ❌ Exception: {e}")
        return "Unable to generate AI guidance at the moment."


# ============= MODELS ================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)


from sqlalchemy import Text, ForeignKey

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user_message = Column(Text)
    ai_response = Column(Text)
    image_path = Column(String, nullable=True)
    image_prediction = Column(String, nullable=True)
    timestamp = Column(String, default=str(datetime.utcnow()))


Base.metadata.create_all(bind=engine)


# ============= SCHEMAS ================

class SignupRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str


# ============= AUTH APIs ================

@app.post("/auth/signup")
def signup(data: SignupRequest):
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")

        user = User(
            email=data.email,
            password_hash=hash_password(data.password)
        )
        db.add(user)
        db.commit()
        return {"message": "User registered successfully"}
    finally:
        db.close()


@app.post("/auth/login")
def login(data: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token({"user_id": user.id})

        return {
            "access_token": token,
            "token_type": "bearer"
        }
    finally:
        db.close()


# ============= CHAT API WITH H5 MODEL ================

@app.post("/chat/send")
async def chat_send(
    user_id: int = Depends(get_current_user_id),
    message: str = Form(default=""),
    image: UploadFile = File(default=None),
):
    """
    Route handler for different input combinations:
    - Text only → Identify issue from text → Generate first aid
    - Image only → H5 model prediction → Generate first aid from prediction
    - Both → H5 model prediction + text → Generate first aid with both
    """
    
    db = SessionLocal()
    try:
        print(f"\n{'='*50}")
        print(f"[CHAT] New request from User ID: {user_id}")
        print(f"[CHAT] Message: '{message}' (length: {len(message)})")
        print(f"[CHAT] Image: {image.filename if image else None}")
        
        # Clean up message - convert empty string to None
        message = message.strip() if message else None
        
        # Validate input
        if not message and not image:
            raise HTTPException(status_code=400, detail="Please provide either text or image or both")

        image_prediction = None
        image_path = None

        # ===== CASE 1: Only text =====
        if message and not image:
            print("[CHAT] 📝 Route: TEXT ONLY")
            issue = identify_issue(message)
            first_aid = generate_first_aid(issue, message)
            final_reply = f"{issue}\n\nFirst Aid:\n{first_aid}"
            route = "text_only"

        # ===== CASE 2: Only image =====
        elif image and not message:
            print("[CHAT] 🖼️ Route: IMAGE ONLY")
            image_path = image.filename
            try:
                image_prediction = await process_image_with_h5(image)
                print(f"[CHAT] ✅ Image prediction received: {image_prediction}")
            except Exception as e:
                print(f"[CHAT] ❌ Image processing error: {str(e)}")
                raise
            
            issue = identify_issue("", image_prediction)
            first_aid = generate_first_aid(issue)
            final_reply = f"{issue}\n\nFirst Aid:\n{first_aid}"
            route = "image_only"

        # ===== CASE 3: Both image and text =====
        else:  # both image and message
            print("[CHAT] 📝🖼️ Route: IMAGE AND TEXT")
            image_path = image.filename
            try:
                image_prediction = await process_image_with_h5(image)
                print(f"[CHAT] ✅ Image prediction received: {image_prediction}")
            except Exception as e:
                print(f"[CHAT] ❌ Image processing error: {str(e)}")
                raise
            
            issue = identify_issue(message, image_prediction)
            first_aid = generate_first_aid(issue, message)
            final_reply = f"{issue}\n\nFirst Aid:\n{first_aid}"
            route = "image_and_text"

        # Save to database
        chat = ChatMessage(
            user_id=user_id,
            user_message=message or "",
            ai_response=final_reply,
            image_path=image_path,
            image_prediction=image_prediction
        )

        db.add(chat)
        db.commit()

        print(f"[CHAT] ✅ Response saved to database")
        print(f"{'='*50}\n")

        return {
            "reply": final_reply,
            "route": route,
            "image_prediction": image_prediction
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[CHAT] ❌ Error in chat_send: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============= HEALTH CHECK =================

@app.get("/health")
async def health():
    return {"status": "ok"}