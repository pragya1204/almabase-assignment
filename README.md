# Structured Questionnaire Answering Tool 🤖

**Submitted for:** GTM Engineering Internship Assignment

## 1. What I Built
I built a full-stack **RAG (Retrieval-Augmented Generation)** application designed to automate the completion of due diligence questionnaires.

The tool allows a user to:
1.  **Upload** a blank questionnaire (PDF/Excel) and internal reference documents (policies, SOPs).
2.  **Parse** the questionnaire automatically into individual questions.
3.  **Generate** answers using an LLM (Llama-3 via Groq) grounded in the uploaded references.
4.  **Review** answers with citations and confidence scores.
5.  **Export** a completed PDF report that preserves the original question structure and coverage summary.

### Fictional Context (LinguaPlay)
* **Industry:** EdTech (Children's Language Learning)
* **Company:** **LinguaPlay**, an AI-tutor platform for kids aged 3-12.
* **Use Case:** Because LinguaPlay handles child data (COPPA/GDPR), the security team is overwhelmed with compliance forms from school districts. This tool automates answering those forms using LinguaPlay's "Information Security Policy" and "Privacy Standards."

---

## 2. Assumptions I Made
To scope this project within the timeframe, I made the following assumptions:
* **Text-Readable Files:** I assumed all uploaded PDFs are text-based (selectable text), not scanned images. OCR (Optical Character Recognition) was out of scope.
* **Single-Turn Logic:** I assumed questions are standalone and do not require memory of previous questions (e.g., "See answer to Q1").
* **English Language:** The system is optimized for English documents.
* **Sequential Structure:** I assumed questionnaires generally follow a linear flow (1, 2, 3...) rather than complex branching logic (e.g., "If Yes, go to Q10").

---

## 3. Trade-offs
In building this system, I had to balance performance, cost, and complexity:

* **Gemini Embeddings (`embedding-001`):**
    * *Trade-off:* I chose Google's Gemini embeddings over OpenAI or local BERT models.
    * *Why:* Gemini offers a larger context window and excellent retrieval performance for free/low-cost tiers, making it ideal for a prototype. The downside is adding a dependency on Google Cloud Platform (GCP) alongside Groq.

* **Heuristic vs. Model-Based Confidence:**
    * *Trade-off:* I implemented a confidence score based on **vector similarity** and **keyword checks** (e.g., forcing 0% if "not found").
    * *Why:* Training a custom classifier model or using LLM-as-a-judge for every answer would have doubled the latency and cost. The heuristic approach provides a "good enough" signal for human review without the overhead.

* **Hybrid Parsing (LLM + Regex):**
    * *Trade-off:* I use an LLM to identify questions but fall back to Regex.
    * *Why:* Using an LLM for parsing is more accurate but costs tokens. Regex is free but brittle. The hybrid approach balances reliability with cost.

* **Llama-3-8b Model:**
    * *Trade-off:* I chose `llama-3.1-8b-instant` via Groq.
    * *Why:* It offers near-instant inference speeds, which is crucial for a good UX when generating 15 answers at once. Larger models (GPT-4) would be smarter but significantly slower and more expensive.

---

## 4. What I Would Improve With More Time
If I had another week to work on this, I would prioritize:

1.  **Excel/Word Export:** Currently, I only export to PDF. In the real world, teams usually need to return the questionnaire in the original format (Excel or Word) to the requester.
2.  **Multi-Modal RAG:** Integrate vision capabilities to read charts, tables, and diagrams in the policy documents, which are often missed by standard text extraction.
3.  **Source Highlighting:** Instead of just citing the document name, I would implement a UI that highlights the exact paragraph in the source PDF when a user clicks a citation.

---

## 5. Project Structure & Setup

```text
├── .streamlit/             # Secrets & Config
├── backend/                # FastAPI Backend
│   ├── api/                # API Routes (Documents, Answers)
│   ├── models/             # Database Models (SQLAlchemy)
│   ├── services/           # Business Logic (RAG, Parsing, Auth)
│   └── main.py             # Application Entry Point
├── mock_data/              # Sample Policies & Questionnaires
├── app.py                  # Streamlit Frontend Application
└── README.md
```
---
### Tech Stack
* **Frontend:** Streamlit
* **Backend:** FastAPI
* **Database:** Supabase (PostgreSQL + pgvector)
* **AI:** Groq (Llama-3), Google Gemini (Embeddings)
