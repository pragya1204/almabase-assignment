import uuid
from typing import Dict, List
from services.auth_service import supabase
from services.rag_service import RAGService
from services.answer_generator import AnswerGenerator

class AnswerService:
    """Orchestrates the RAG retrieval and answer generation pipeline."""

    @staticmethod
    def process_question(question_text: str, question_id: str, answer_set_id: str) -> Dict:
        """Coordinates RAG retrieval, generation, and database storage for a single question."""
        
        # 1. Retrieve relevant content from pgvector
        retrieved_chunks = RAGService.retrieve_relevant_content(question_text)
        
        # Fetch actual filenames for the retrieved chunks
        doc_ids = list(set([chunk['reference_document_id'] for chunk in retrieved_chunks]))
        filename_map = {}
        
        if doc_ids:
            try:
                res = supabase.table("reference_documents").select("id, filename").in_("id", doc_ids).execute()
                for doc in res.data:
                    filename_map[doc['id']] = doc['filename']
            except Exception as e:
                print(f"Error fetching filenames: {e}")

        # 2. Generate answer using Groq
        answer_text, is_not_found, conf_score = AnswerGenerator.generate_answer(
            question=question_text, 
            retrieved_chunks=retrieved_chunks
        )
        
        # 3. Save the Answer to Supabase
        answer_id = str(uuid.uuid4())
        answer_data = {
            "id": answer_id,
            "question_id": question_id,
            "answer_set_id": answer_set_id,
            "text": answer_text,
            "confidence_score": conf_score,
            "is_not_found": is_not_found
        }
        supabase.table("answers").insert(answer_data).execute()
        
        # 4. Save the Citations to Supabase
        if not is_not_found and retrieved_chunks:
            for chunk in retrieved_chunks:
                doc_id = chunk.get("reference_document_id", "unknown")
                real_filename = filename_map.get(doc_id, "Unknown Document")
                
                citation_data = {
                    "id": str(uuid.uuid4()),
                    "answer_id": answer_id,
                    "reference_document_id": doc_id,
                    "reference_document_name": real_filename,
                    "chunk_text": chunk.get("chunk_text", ""),
                    "relevance_score": chunk.get("similarity", 0.0)
                }
                supabase.table("citations").insert(citation_data).execute()
                
        return answer_data

    @staticmethod
    def generate_answers(questionnaire_id: str, user_id: str) -> Dict:
        """Processes all questions in a questionnaire."""
        
        questions_res = supabase.table("questions").select("*").eq("questionnaire_id", questionnaire_id).execute()
        questions = questions_res.data
        
        if not questions:
            raise ValueError("No questions found for this questionnaire.")

        answer_set_id = str(uuid.uuid4())
        answer_set_data = {
            "id": answer_set_id,
            "questionnaire_id": questionnaire_id,
            "user_id": user_id,
            "status": "COMPLETED"
        }
        supabase.table("answer_sets").insert(answer_set_data).execute()
        
        for q in questions:
            AnswerService.process_question(q["text"], q["id"], answer_set_id)
            
        return {"answer_set_id": answer_set_id, "status": "COMPLETED"}

    @staticmethod
    def get_answer_set(answer_set_id: str) -> Dict:
        """Retrieves an answer set AND injects the original question text + Coverage Summary."""
        
        # 1. Fetch Answers and Citations
        res = supabase.table("answer_sets").select("*, answers(*, citations(*))").eq("id", answer_set_id).execute()
        if not res.data:
            return None
            
        answer_set = res.data[0]
        
        # 2. Fetch Questions to map the text back to the answers
        questionnaire_id = answer_set.get("questionnaire_id")
        if questionnaire_id:
            q_res = supabase.table("questions").select("id, text, order_index").eq("questionnaire_id", questionnaire_id).execute()
            
            # Map ID -> Text and ID -> Order
            q_map = {q['id']: q['text'] for q in q_res.data}
            order_map = {q['id']: q['order_index'] for q in q_res.data}
            
            # Inject into answers
            for ans in answer_set['answers']:
                ans['question_text'] = q_map.get(ans['question_id'], "Question Text Not Found")
                ans['order_index'] = order_map.get(ans['question_id'], 999)
            
            # Sort answers by the original question order
            answer_set['answers'].sort(key=lambda x: x.get('order_index', 999))

        # 3. --- NEW: Calculate Coverage Summary ---
        total = len(answer_set['answers'])
        not_found = sum(1 for a in answer_set['answers'] if a.get('is_not_found', False))
        covered = total - not_found
        
        answer_set['summary'] = {
            "total": total,
            "covered": covered,
            "not_found": not_found,
            "percentage": round((covered / total * 100), 1) if total > 0 else 0.0
        }
        # ---------------------------------------
            
        return answer_set

    @staticmethod
    def update_answer(answer_id: str, new_text: str) -> Dict:
        res = supabase.table("answers").update({"text": new_text}).eq("id", answer_id).execute()
        return res.data[0] if res.data else None