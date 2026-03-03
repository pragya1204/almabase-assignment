import os
from groq import Groq
from typing import List, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env file.")

client = Groq(api_key=GROQ_API_KEY)

class AnswerGenerator:
    """Generates answers using Groq API and calculates a hybrid confidence score."""

    @staticmethod
    def calculate_confidence_score(relevance_scores: List[float], answer_text: str) -> float:
        """
        Calculates a smarter confidence score.
        1. If LLM says 'not found', score is 0.0.
        2. Weighted average: 70% Top Score + 30% Mean Score.
        3. Penalty: If top score is low (< 0.5), penalize heavily.
        """
        if not relevance_scores:
            return 0.0

        # 1. LLM Verification Override
        # Check if the LLM explicitly stated it couldn't find the answer
        negative_phrases = [
            "not found in references", 
            "cannot be determined", 
            "no information provided", 
            "does not mention",
            "not mentioned"
        ]
        if any(phrase in answer_text.lower() for phrase in negative_phrases):
            return 0.0

        # 2. Weighted Scoring (Favor the best match)
        top_score = max(relevance_scores)
        avg_score = sum(relevance_scores) / len(relevance_scores)
        
        # We give 70% weight to the single best chunk, 30% to the overall context quality
        weighted_score = (0.7 * top_score) + (0.3 * avg_score)

        # 3. Low Similarity Penalty
        # If even the best chunk is weak (e.g., < 0.5), the model is likely hallucinating or guessing.
        if top_score < 0.5:
            weighted_score *= 0.5  # Slash the score in half

        return round(weighted_score, 2)

    @staticmethod
    def format_prompt(question: str, context_chunks: List[str]) -> str:
        """Structures the input for the LLM."""
        context_text = "\n\n---\n\n".join(context_chunks)
        # --- REFINED PROMPT START ---
        prompt = f"""You are a professional representative of the company answering a due diligence questionnaire.
                    Use the provided internal documents (Context) to answer the question below.

                    Context:
                    {context_text}

                    Question: {question}

                    Guidelines:
                    1. **Voice:** Use "We", "Our", or "The Company". Act as if you are the company.
                    2. **Strict Source Control:** Answer ONLY based on the Context. Do not use outside knowledge.
                    3. **Missing Information:** - If the Context does NOT contain the answer, you must output exactly: "Not found in references."
                    - Do NOT attempt to answer "No" or "We do not..." unless the Context explicitly states that you do not.
                    - Do NOT write "We do not provide... in the provided context." Just "Not found in references."
                    4. **Tone:** Be direct and professional. 
                    - NEVER say "According to the documents...", "In the provided context...", or "Based on the text...".
                    - Just state the fact. (e.g., "We encrypt data usi
                     Answer:"""
        return prompt

    @staticmethod
    def generate_answer(question: str, retrieved_chunks: List[Dict]) -> Tuple[str, bool, float]:
        """
        Coordinates the LLM call and returns (answer, is_not_found, confidence_score).
        """
        # Handle cases with no relevant content
        if not retrieved_chunks:
            return "Not found in references.", True, 0.0

        context_texts = [chunk['chunk_text'] for chunk in retrieved_chunks]
        scores = [chunk['similarity'] for chunk in retrieved_chunks]
        
        prompt = AnswerGenerator.format_prompt(question, context_texts)

        try:
            # Call Groq API
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a precise, professional assistant."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.0, # Zero temp for strict adherence to context
            )
            
            answer_text = chat_completion.choices[0].message.content.strip()
            
            # Calculate the improved confidence score using the GENERATED text
            confidence_score = AnswerGenerator.calculate_confidence_score(scores, answer_text)
            
            # Determine is_not_found based on the score override or text
            is_not_found = (confidence_score == 0.0)

            return answer_text, is_not_found, confidence_score
            
        except Exception as e:
            print(f"Groq API Error: {e}")
            return "Error generating answer.", True, 0.0