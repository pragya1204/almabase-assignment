from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.auth_service import get_current_user, User
from services.answer_service import AnswerService

router = APIRouter(prefix="/api", tags=["Answers"])

class AnswerUpdate(BaseModel):
    text: str

@router.post("/questionnaires/{id}/generate")
def generate_answers(id: str, current_user: User = Depends(get_current_user)):
    """Starts the RAG and LLM generation process for a questionnaire."""
    try:
        result = AnswerService.generate_answers(id, current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.get("/answer-sets/{id}")
def get_answer_set(id: str, current_user: User = Depends(get_current_user)):
    """Retrieves the generated results for display."""
    answer_set = AnswerService.get_answer_set(id)
    if not answer_set:
        raise HTTPException(status_code=404, detail="Answer set not found")
        
    # Security check: Ensure the answer set belongs to the logged-in user
    if answer_set.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view these results")
        
    return answer_set

@router.put("/answers/{id}")
def edit_answer(id: str, update_data: AnswerUpdate, current_user: User = Depends(get_current_user)):
    """Updates the text of a specific answer."""
    updated = AnswerService.update_answer(id, update_data.text)
    if not updated:
        raise HTTPException(status_code=404, detail="Answer not found")
    return {"message": "Answer updated successfully", "answer": updated}