from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Date, Float, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user_id
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), default="")

    is_pro: Mapped[bool] = mapped_column(Boolean, default=False)
    pro_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Gamification
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Interview preferences (saved from last session)
    last_role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_grade: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    sessions: Mapped[list[InterviewSession]] = relationship(back_populates="user", lazy="selectin")
    achievements: Mapped[list[Achievement]] = relationship(back_populates="user", lazy="selectin")

    @property
    def average_score(self) -> float:
        if self.total_questions == 0:
            return 0.0
        return round(self.total_score / self.total_questions, 1)

    @property
    def readiness_pct(self) -> int:
        """0-100 readiness bar based on questions count and avg score."""
        if self.total_questions == 0:
            return 0
        qty_factor = min(self.total_questions / 50, 1.0)  # 50 questions = full
        score_factor = self.average_score / 100
        return int((qty_factor * 0.4 + score_factor * 0.6) * 100)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))

    role: Mapped[str] = mapped_column(String(128))
    grade: Mapped[str] = mapped_column(String(64))
    company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    interview_type: Mapped[str] = mapped_column(String(16))  # "hr" | "tech"
    job_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="active")  # active | finished
    questions_count: Mapped[int] = mapped_column(Integer, default=0)
    session_score: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    questions: Mapped[list[Question]] = relationship(back_populates="session", lazy="selectin")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("interview_sessions.id"))

    question_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ideal_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    asked_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    session: Mapped[InterviewSession] = relationship(back_populates="questions")


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(String(64))
    earned_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped[User] = relationship(back_populates="achievements")


class DailyUsage(Base):
    """Track free-tier question usage per day."""
    __tablename__ = "daily_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    usage_date: Mapped[date] = mapped_column(Date)
    questions_used: Mapped[int] = mapped_column(Integer, default=0)
