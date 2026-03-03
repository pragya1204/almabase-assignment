from google import genai
from dotenv import load_dotenv
load_dotenv()
import os

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

response = client.models.embed_content(
    model="gemini-embedding-001",
    contents="This is a sample text"
)

vector = response.embeddings[0].values
print(vector)