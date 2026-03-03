from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class AnswerSet(Base):
    """Groups all answers generated for a specific questionnaire."""
    __tablename__ = 'answer_sets'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    questionnaire_id = Column(String, nullable=False) # References Questionnaire.id
    user_id = Column(String, nullable=False)
    status = Column(String, default="GENERATING") # GENERATING, COMPLETED, EXPORTED
    created_at = Column(DateTime, default=datetime.utcnow)
    
    answers = relationship("Answer", back_populates="answer_set", cascade="all, delete-orphan")

class Answer(Base):
    """Stores the generated AI response for a specific question."""
    __tablename__ = 'answers'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, nullable=False) # References Question.id
    answer_set_id = Column(String, ForeignKey('answer_sets.id'), nullable=False)
    text = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=True) # Optional feature metric
    is_not_found = Column(Boolean, default=False) # True if "Not found in references."
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    answer_set = relationship("AnswerSet", back_populates="answers")
    citations = relationship("Citation", back_populates="answer", cascade="all, delete-orphan")

class Citation(Base):
    """Links an answer to the specific reference document chunk used to generate it."""
    __tablename__ = 'citations'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    answer_id = Column(String, ForeignKey('answers.id'), nullable=False)
    reference_document_id = Column(String, nullable=False)
    reference_document_name = Column(String, nullable=False)
    chunk_text = Column(String, nullable=False)
    relevance_score = Column(Float, nullable=False)
    
    answer = relationship("Answer", back_populates="citations")