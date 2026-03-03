import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from services.auth_service import get_current_user, User, supabase
from services.parser_service import DocumentParser
from services.rag_service import RAGService # Import RAGService

router = APIRouter(prefix="/api", tags=["Documents"])

def upload_to_storage(bucket_name: str, file_bytes: bytes, filename: str, user_id: str) -> str:
    file_path = f"{user_id}/{uuid.uuid4()}_{filename}"
    supabase.storage.from_(bucket_name).upload(
        path=file_path, 
        file=file_bytes, 
        file_options={"content-type": "application/octet-stream"}
    )
    return file_path

@router.post("/questionnaires/upload")
async def upload_questionnaire(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Uploads, parses, and stores the questionnaire and its questions in the DB."""
    if not file.filename.endswith(('.pdf', '.xlsx')):
        raise HTTPException(status_code=400, detail="Unsupported file format.")
        
    file_bytes = await file.read()
    
    # 1. Parse Document
    if file.filename.endswith('.pdf'):
        content = DocumentParser.extract_text_from_pdf(file_bytes)
        doc_format = "PDF"
    else:
        content = DocumentParser.extract_text_from_spreadsheet(file_bytes)
        doc_format = "SPREADSHEET"
        
    questions = DocumentParser.extract_questions(content, doc_format)
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found.")

    # 2. Upload to Storage
    file_path = upload_to_storage("questionnaires", file_bytes, file.filename, current_user.id)
    
    # 3. Save to Database
    questionnaire_id = str(uuid.uuid4())
    supabase.table("questionnaires").insert({
        "id": questionnaire_id,
        "user_id": current_user.id,
        "filename": file.filename,
        "file_path": file_path,
        "format": doc_format
    }).execute()
    
    # 4. Save Parsed Questions
    for q in questions:
        supabase.table("questions").insert({
            "id": str(uuid.uuid4()),
            "questionnaire_id": questionnaire_id,
            "text": q["text"],
            "order_index": q["order_index"],
            "original_format": q["original_format"]
        }).execute()
    
    return {
        "message": "Questionnaire processed",
        "questionnaire_id": questionnaire_id,
        "questions_found": len(questions)
    }

@router.post("/references/upload")
async def upload_reference(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Uploads a reference document and triggers the Gemini RAG indexing."""
    if not file.filename.endswith(('.pdf', '.txt', '.json', '.csv')):
        raise HTTPException(status_code=400, detail="Unsupported format.")
        
    file_bytes = await file.read()
    
    # Extract text
    content = ""
    if file.filename.endswith('.pdf'):
        content = DocumentParser.extract_text_from_pdf(file_bytes)
    else:
        content = file_bytes.decode('utf-8')
    
    file_path = upload_to_storage("references", file_bytes, file.filename, current_user.id)
    
    # Save to Database
    doc_id = str(uuid.uuid4())
    supabase.table("reference_documents").insert({
        "id": doc_id,
        "user_id": current_user.id,
        "filename": file.filename,
        "file_path": file_path,
        "content": content,
        "indexed": True
    }).execute()
    
    # Trigger RAG Indexing (Gemini Embeddings -> pgvector)
    RAGService.index_document(doc_id, content)
    
    return {"message": "Reference document indexed successfully", "doc_id": doc_id}

@router.get("/questionnaires")
def list_questionnaires(current_user: User = Depends(get_current_user)):
    """Fetches all questionnaires belonging to the user."""
    res = supabase.table("questionnaires").select("*").eq("user_id", current_user.id).order('created_at', desc=True).execute()
    return res.data

@router.get("/references")
def list_references(current_user: User = Depends(get_current_user)):
    """Fetches all reference documents belonging to the user."""
    res = supabase.table("reference_documents").select("*").eq("user_id", current_user.id).order('created_at', desc=True).execute()
    return res.data