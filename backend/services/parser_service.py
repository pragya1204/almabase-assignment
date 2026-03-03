import io
import os
import json
import re
import PyPDF2
import openpyxl
from typing import List, Dict
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq client using your existing API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY not found. LLM parsing will fail.")

client = Groq(api_key=GROQ_API_KEY)

class DocumentParser:
    """Extracts text and parses questions from uploaded files using LLM."""
    
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        """Extracts plain text from a PDF file."""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    @staticmethod
    def extract_text_from_spreadsheet(file_bytes: bytes) -> str:
        """Extracts text from an Excel spreadsheet."""
        try:
            workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            text = ""
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    row_values = [str(cell) for cell in row if cell is not None]
                    if row_values:
                        text += " | ".join(row_values) + "\n"
            return text
        except Exception as e:
            print(f"Error reading Spreadsheet: {e}")
            return ""

    @staticmethod
    def _clean_json_string(json_str: str) -> str:
        """Helper to clean LLM output if it includes markdown code blocks."""
        # Remove ```json and ``` markers often added by LLMs
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        return json_str.strip()

    @staticmethod
    def extract_questions(content: str, format: str) -> List[Dict]:
        """
        Parses text content into individual questions using LLM with smart merging.
        Falls back to a 'stateful' regex parser that handles multi-line questions.
        """
        # 1. Try LLM Parsing (Updated Prompt)
        try:
            # Truncate content to avoid token limits
            truncated_content = content[:25000] 
            
            prompt = f"""
            You are a data extraction assistant. Extract all questions from the following text.
            
            CRITICAL RULES:
            1. MERGE multi-line questions into a single string. Do not split them.
            2. If a question spans multiple lines (e.g., has instructions or sub-questions below it), keep it as ONE item.
            3. Preserve the original numbering (e.g., "1. Question...").
            4. Ignore page headers (e.g., "--- PAGE 1 ---") or footers.
            5. Return ONLY a valid JSON array of strings.
            
            Text to parse:
            {truncated_content}
            """

            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a precise data extractor that outputs only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.0,
            )

            response_content = chat_completion.choices[0].message.content
            cleaned_json = DocumentParser._clean_json_string(response_content)
            parsed_data = json.loads(cleaned_json)
            
            question_texts = []
            if isinstance(parsed_data, list):
                question_texts = parsed_data
            elif isinstance(parsed_data, dict):
                for key in ["questions", "items", "data"]:
                    if key in parsed_data and isinstance(parsed_data[key], list):
                        question_texts = parsed_data[key]
                        break
            
            if question_texts:
                return [
                    {
                        "text": q_text,
                        "order_index": i,
                        "original_format": {"type": "llm_extracted"}
                    }
                    for i, q_text in enumerate(question_texts)
                ]

        except Exception as e:
            print(f"LLM Parsing failed: {e}. Falling back to heuristic.")
        
        # 2. Fallback Heuristic: Stateful Merging
        # Instead of treating every line as a question, we look for "Starters" (1., 2.)
        # and merge subsequent lines into that question.
        print("Using stateful fallback parser...")
        
        questions = []
        lines = content.split('\n')
        
        current_question_text = ""
        current_order = 0
        
        # Regex to find lines that definitely START a question (e.g., "1.", "12)", "Q1:")
        start_pattern = re.compile(r'^(\d+[\.\)]|Q\d+[:\.]?)\s+')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # If line starts with a number, it's a NEW question
            if start_pattern.match(line):
                # Save the PREVIOUS question if it exists
                if current_question_text:
                    questions.append({
                        "text": current_question_text,
                        "order_index": current_order,
                        "original_format": {"type": "heuristic_fallback"}
                    })
                    current_order += 1
                
                # Start the NEW question
                current_question_text = line
            
            # If line does NOT start with a number, it's a CONTINUATION
            else:
                if current_question_text:
                    current_question_text += " " + line
                # If we haven't found a number yet, we might skip intro text or handle it separately
        
        # Don't forget to append the very last question found
        if current_question_text:
            questions.append({
                "text": current_question_text,
                "order_index": current_order,
                "original_format": {"type": "heuristic_fallback"}
            })

        # Edge Case: If the document had NO numbering, the above logic returns nothing.
        # In that case, revert to the "ends with ?" logic.
        if not questions:
            print("No numbering found, falling back to simple line splitter.")
            for i, line in enumerate(lines):
                if line.strip().endswith('?') and len(line) > 5:
                    questions.append({
                        "text": line.strip(),
                        "order_index": i,
                        "original_format": {"type": "simple_fallback"}
                    })

        return questions