from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # e.g., "openai", "anthropic"
    model_name = Column(String, nullable=False) # e.g., "gpt-4o"
    is_active = Column(Boolean, default=True)
    is_healthy = Column(Boolean, default=True)
    last_checked = Column(DateTime, default=datetime.utcnow)
    latency_ms = Column(Float, nullable=True)

class HealthCheck(Base):
    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"))
    status = Column(String, nullable=False) # "UP", "DOWN"
    error_message = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(String, nullable=False)
    response = Column(String, nullable=True)
    provider_id = Column(Integer, ForeignKey("providers.id"))
    duration_ms = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    was_fallback = Column(Boolean, default=False)
