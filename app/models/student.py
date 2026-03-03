"""
Database models for Lead tracking, Call logs, and Conversation history.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    APPLIED = "applied"
    ENROLLED = "enrolled"
    LOST = "lost"


class Lead(Base):
    """A prospective student captured via voice call or web."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    course_interest = Column(String(255), nullable=True)
    budget = Column(String(100), nullable=True)
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.NEW, nullable=False)
    source = Column(String(50), default="voice_call")  # voice_call, web, whatsapp
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    calls = relationship("CallLog", back_populates="lead", cascade="all, delete-orphan")


class CallLog(Base):
    """Record of each voice call made to/from a lead."""
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    twilio_call_sid = Column(String(64), nullable=True, unique=True)
    direction = Column(String(10), default="outbound")  # inbound / outbound
    duration_seconds = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)  # AI-generated call summary
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)

    # Relationships
    lead = relationship("Lead", back_populates="calls")
    messages = relationship("ConversationMessage", back_populates="call",
                            cascade="all, delete-orphan")


class ConversationMessage(Base):
    """Individual message in a call conversation (for long-term memory)."""
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("call_logs.id"), nullable=False, index=True)
    role = Column(String(10), nullable=False)  # "user" or "ai"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    call = relationship("CallLog", back_populates="messages")
