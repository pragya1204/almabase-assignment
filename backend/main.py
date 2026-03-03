from fastapi import FastAPI, Depends
from services.auth_service import get_current_user, User
from api import documents, answers
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from the .env file we created in Task 1
load_dotenv()


app = FastAPI(title="Structured Questionnaire Answering Tool")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"], # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"], # Allow all headers (Authorization, Content-Type, etc.)
)
app.include_router(documents.router)
app.include_router(answers.router)


@app.get("/")
def read_root():
    return {"status": "API is running"}

# Create a protected endpoint using our auth middleware
@app.get("/api/me", response_model=User)
def get_user_profile(current_user: User = Depends(get_current_user)):
    """
    This endpoint requires a valid Supabase JWT. 
    If missing or invalid, the request is denied.
    """
    return current_user