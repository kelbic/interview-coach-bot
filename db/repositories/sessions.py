from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import InterviewSession, Question


async def create_session(
    session: AsyncSession,
    user_id: int,
    role: str,
    grade: str,
    company: Optional[str],
    interview_type: str,
    job_description: Optional[str] = None,
) -> InterviewSession:
    interview = InterviewSession(
        user_id=user_id,
        role=role,
        grade=grade,
        company=company,
        interview_type=interview_type,
        job_description=job_description,
    )
    session.add(interview)
    await session.commit()
    await session.refresh(interview)
    return interview


async def get_active_session(
    session: AsyncSession, user_id: int
) -> Optional[InterviewSession]:
    result = await session.execute(
        select(InterviewSession)
        .where(
            InterviewSession.user_id == user_id,
            InterviewSession.status == "active",
        )
        .order_by(InterviewSession.created_at.desc())
    )
    return result.scalar_one_or_none()


async def get_session_by_id(
    session: AsyncSession, session_id: int
) -> Optional[InterviewSession]:
    result = await session.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def finish_session(session: AsyncSession, interview: InterviewSession) -> None:
    interview.status = "finished"
    interview.finished_at = datetime.utcnow()
    await session.commit()


async def add_question(
    session: AsyncSession,
    interview: InterviewSession,
    question_text: str,
) -> Question:
    q = Question(session_id=interview.id, question_text=question_text)
    session.add(q)
    interview.questions_count += 1
    await session.commit()
    await session.refresh(q)
    return q


async def save_answer(
    session: AsyncSession,
    question: Question,
    answer_text: str,
    score: int,
    feedback: str,
    ideal_answer: str,
    interview: InterviewSession,
) -> None:
    question.answer_text = answer_text
    question.score = score
    question.feedback = feedback
    question.ideal_answer = ideal_answer
    question.answered_at = datetime.utcnow()

    interview.session_score += score
    await session.commit()


async def get_current_question(
    session: AsyncSession, interview: InterviewSession
) -> Optional[Question]:
    """Return the last unanswered question in the session."""
    result = await session.execute(
        select(Question)
        .where(
            Question.session_id == interview.id,
            Question.answer_text.is_(None),
        )
        .order_by(Question.asked_at.desc())
    )
    return result.scalar_one_or_none()
