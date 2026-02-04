from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import uuid

def gen_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=True)
    credits = Column(Integer, default=500)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    videos = relationship("VideoJob", back_populates="user")
    transactions = relationship("CreditTransaction", back_populates="user")


class VideoJob(Base):
    __tablename__ = "video_jobs"
    
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Input
    audio_filename = Column(String(255), nullable=False)
    audio_path = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    style = Column(String(50), default="realistic")
    
    # Status
    status = Column(String(50), default="pending")
    progress = Column(Float, default=0.0)
    current_step = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Audio analysis results
    audio_duration = Column(Float, nullable=True)
    audio_bpm = Column(Float, nullable=True)
    audio_key = Column(String(20), nullable=True)
    audio_energy_profile = Column(JSON, nullable=True)
    
    # AI generation results (stored as JSON)
    creative_concept = Column(JSON, nullable=True)
    scenes = Column(JSON, nullable=True)  # Array of scene objects
    segments = Column(JSON, nullable=True)  # Array of video segment URLs
    
    # Final output
    output_file = Column(String(500), nullable=True)
    
    # Metadata
    credits_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="videos")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    transaction_type = Column(String(30), nullable=False)
    job_id = Column(String(36), nullable=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")
