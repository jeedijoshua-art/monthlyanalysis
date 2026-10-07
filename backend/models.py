import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text, LargeBinary
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    datasets = relationship("Dataset", back_populates="owner")
    analyses = relationship("AnalysisHistory", back_populates="user")

class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    
    # Store the actual dataframe (e.g. as parquet or csv bytes)
    file_data = Column(LargeBinary, nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    owner = relationship("User", back_populates="datasets")
    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")

class DatasetColumn(Base):
    __tablename__ = "dataset_columns"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    column_name = Column(String(255), nullable=False)
    data_type = Column(String(100), nullable=False)
    nullable = Column(Boolean, default=True)
    unique_count = Column(Integer, default=0)
    missing_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    dataset = relationship("Dataset", back_populates="columns")

class AnalysisHistory(Base):
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    dataset_ids = Column(String(255), nullable=False) # Comma separated IDs or JSON string
    answer = Column(Text, nullable=True) # JSON serialized answer
    status = Column(String(50), nullable=False)
    generated_code = Column(Text, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="analyses")
