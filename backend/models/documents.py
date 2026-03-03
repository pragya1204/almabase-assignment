from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Questionnaire(Base):
    __tablename__ = 'questionnaires'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False) # Maps to Supabase Auth User ID
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    format = Column(String, nullable=False) # 'PDF' or 'SPREADSHEET'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    questions = relationship("Question", back_populates="questionnaire", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = 'questions'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    questionnaire_id = Column(String, ForeignKey('questionnaires.id'), nullable=False)
    text = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False) # Preserves original structure
    original_format = Column(JSON, nullable=True) 
    
    questionnaire = relationship("Questionnaire", back_populates="questions")

class ReferenceDocument(Base):
    __tablename__ = 'reference_documents'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    content = Column(String, nullable=False)
    indexed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    embeddings = relationship("DocumentEmbedding", back_populates="reference_document", cascade="all, delete-orphan")

class DocumentEmbedding(Base):
    __tablename__ = 'document_embeddings'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    reference_document_id = Column(String, ForeignKey('reference_documents.id'), nullable=False)
    chunk_text = Column(String, nullable=False)
    # Gemini embeddings typically have 768 dimensions
    embedding = Column(Vector(768), nullable=False) 
    chunk_index = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    reference_document = relationship("ReferenceDocument", back_populates="embeddings")