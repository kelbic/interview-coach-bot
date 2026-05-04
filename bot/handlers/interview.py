"""Main interview flow: setup → questions → evaluation → results."""
from __future__ import annotations

import logging
from typing import Optional

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import (
    interview_type_kb, grade_kb,
    after_answer_kb, confirm_finish_kb, main_menu_kb,
)
from config import settings
from core.question_gen import generate_question, evaluate_answer
from db.models import User
from db.repositories import users as user_repo
from db.repositories import sessions as session_repo
from db.repositories.achievements import check_and_grant, grant_achievement

logger = logging.getLogger(__name__)

router = Router()


class InterviewSetup(StatesGroup):
    waiting_role = State()
    waiting_grade = State()
    waiting_company = State()
    waiting_type = State()
    waiting_jd = State()


class InterviewActive(StatesGroup):
    waiting_answer = State()


# ─── Setup flow ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "start_interview")
async def cb_start_interview(callback: CallbackQuery, db_user: User, state: FSMContext) -> None:
    await state.clear()

    hint = ""
    if db_user.last_role:
        hint = f"\n\n💡 Последний раз: <b>{db_user.last_grade} {db_user.last_role}</b>"

    await callback.message.edit_text(
        f"🎯 <b>Настройка собеседования</b>{hint}\n\n"
        "Напиши свою желаемую роль.\n"
        "Например: <code>Python Backend Developer</code>, <code>Fullstack Engineer</code>, "
        "<code>DevOps Engineer</code>",
        parse_mode="HTML",
    )
    await state.set_state(InterviewSetup.waiting_role)
    await callback.answer()


@router.message(InterviewSetup.waiting_role)
async def got_role(message: Message, db_user: User, state: FSMContext) -> None:
    role = message.text.strip()[:100]
    await state.update_data(role=role)

    last_grade = db_user.last_grade or "Middle"
    await message.answer(
        f"✅ Роль: <b>{role}</b>\n\nВыбери грейд:",
        reply_markup=grade_kb(),
        parse_mode="HTML",
    )
    await state.set_state(InterviewSetup.waiting_grade)


@router.callback_query(F.data.startswith("grade_"), InterviewSetup.waiting_grade)
async def got_grade(callback: CallbackQuery, state: FSMContext) -> None:
    grade = callback.data.removeprefix("grade_")
    await state.update_data(grade=grade)

    await callback.message.edit_text(
        f"✅ Грейд: <b>{grade}</b>\n\n"
        "Напиши название компании (или нажми /skip чтобы пропустить):",
        parse_mode="HTML",
    )
    await state.set_state(InterviewSetup.waiting_company)
    await callback.answer()


@router.message(InterviewSetup.waiting_company)
async def got_company(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    company = None if text.lower() in ("/skip", "skip", "-", "нет", "пропустить") else text[:100]
    await state.update_data(company=company)

    company_str = f"<b>{company}</b>" if company else "без конкретной компании"
    await message.answer(
        f"✅ Компания: {company_str}\n\nВыбери тип интервью:",
        reply_markup=interview_type_kb(),
        parse_mode="HTML",
    )
    await state.set_state(InterviewSetup.waiting_type)


@router.callback_query(
    F.data.in_({"type_hr", "type_tech", "type_mixed"}),
    InterviewSetup.waiting_type,
)
async def got_type(callback: CallbackQuery, state: FSMContext) -> None:
    type_map = {"type_hr": "hr", "type_tech": "tech", "type_mixed": "mixed"}
    itype = type_map[callback.data]
    await state.update_data(interview_type=itype)

    await callback.message.edit_text(
        "📋 Хочешь добавить описание вакансии для точных вопросов?\n\n"
        "Вставь текст вакансии или нажми /skip:",
        parse_mode="HTML",
    )
    await state.set_state(InterviewSetup.waiting_jd)
    await callback.answer()


@router.message(InterviewSetup.waiting_jd)
async def got_jd(
    message: Message,
    db_user: User,
    db_session,
    state: FSMContext,
) -> None:
    text = message.text.strip()
    jd = None if text.lower() in ("/skip", "skip", "-", "нет", "пропустить") else text[:3000]
    data = await state.get_data()
    await state.clear()

    await _launch_session(message, db_user, db_session, state, data, jd)


async def _launch_session(
    message: Message,
    db_user: User,
    db_session,
    state: FSMContext,
    data: dict,
    jd: Optional[str],
) -> None:
    role = data["role"]
    grade = data["grade"]
    company = data.get("company")
    itype = data["interview_type"]

    # Save preferences
    db_user.last_role = role
    db_user.last_grade = grade
    db_user.last_company = company
    await db_session.commit()

    # Check daily limit for free users
    if not db_user.is_pro:
        used = await user_repo.get_questions_used_today(db_session, db_user.id)
        if used >= settings.FREE_QUESTIONS_PER_DAY:
            await message.answer(
                f"⚠️ Ты использовал все <b>{settings.FREE_QUESTIONS_PER_DAY} бесплатных вопросов</b> на сегодня.\n\n"
                "💎 Переходи на <b>Pro</b> для безлимитной практики и детальных разборов!",
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
            return

    # Create DB session
    interview = await session_repo.create_session(
        db_session, db_user.id, role, grade, company, itype, jd
    )
    await state.update_data(session_id=interview.id, interview_type=itype)

    type_label = {"hr": "HR-интервью 🤝", "tech": "Техническое 💻", "mixed": "Смешанное 🔀"}[itype]
    company_str = f" в {company}" if company else ""

    loading_msg = await message.answer(
        f"🚀 <b>Начинаем!</b>\n\n"
        f"<b>Роль:</b> {grade} {role}{company_str}\n"
        f"<b>Тип:</b> {type_label}\n\n"
        "⏳ Генерирую вопрос...",
        parse_mode="HTML",
    )

    await _ask_next_question(loading_msg, db_user, db_session, state, interview, edit=True)


# ─── Active interview ─────────────────────────────────────────────────────────

async def _ask_next_question(
    message: Message,
    db_user: User,
    db_session,
    state: FSMContext,
    interview,
    edit: bool = False,
) -> None:
    data = await state.get_data()
    prev_questions = [q.question_text for q in interview.questions]

    try:
        # Alternate type for "mixed"
        itype = interview.interview_type
        if itype == "mixed":
            itype = "hr" if len(prev_questions) % 2 == 0 else "tech"

        question_text = await generate_question(
            role=interview.role,
            grade=interview.grade,
            company=interview.company,
            interview_type=itype,
            previous_questions=prev_questions,
            job_description=interview.job_description,
            is_pro=db_user.is_pro,
        )
    except Exception as e:
        logger.error("Question generation failed: %s", e)
        question_text = "Расскажи о своём самом сложном техническом проекте."

    question = await session_repo.add_question(db_session, interview, question_text)
    await state.update_data(question_id=question.id)

    q_num = interview.questions_count
    progress = _progress_bar(db_user.readiness_pct)

    text = (
        f"❓ <b>Вопрос #{q_num}</b>\n\n"
        f"{question_text}\n\n"
        f"📊 Готовность: {progress} {db_user.readiness_pct}%\n\n"
        "<i>Напиши свой ответ в чат ↓</i>"
    )

    if edit:
        await message.edit_text(text, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

    await state.set_state(InterviewActive.waiting_answer)


@router.message(InterviewActive.waiting_answer)
async def got_answer(
    message: Message,
    db_user: User,
    db_session,
    state: FSMContext,
) -> None:
    answer_text = message.text.strip()
    if not answer_text:
        await message.answer("Напиши свой ответ текстом 👇")
        return

    data = await state.get_data()
    session_id = data.get("session_id")
    question_id = data.get("question_id")

    if not session_id or not question_id:
        await message.answer("Что-то пошло не так. Начни новое интервью: /start")
        await state.clear()
        return

    # Check daily limit
    if not db_user.is_pro:
        used = await user_repo.get_questions_used_today(db_session, db_user.id)
        if used >= settings.FREE_QUESTIONS_PER_DAY:
            await message.answer(
                f"⚠️ Лимит исчерпан ({settings.FREE_QUESTIONS_PER_DAY} вопросов/день).\n"
                "Возвращайся завтра или подключи 💎 Pro!",
                reply_markup=main_menu_kb(),
            )
            await state.clear()
            return

    interview = await session_repo.get_session_by_id(db_session, session_id)
    if not interview:
        await message.answer("Сессия не найдена. Начни заново: /start")
        await state.clear()
        return

    # Find question
    question = next((q for q in interview.questions if q.id == question_id), None)
    if not question:
        await message.answer("Вопрос не найден. Начни заново: /start")
        await state.clear()
        return

    # Show typing indicator
    await message.answer("🔍 Оцениваю ответ...")

    # Determine effective interview type
    itype = interview.interview_type
    if itype == "mixed":
        q_index = next(i for i, q in enumerate(interview.questions) if q.id == question_id)
        itype = "hr" if q_index % 2 == 0 else "tech"

    try:
        evaluation = await evaluate_answer(
            question=question.question_text,
            answer=answer_text,
            role=interview.role,
            grade=interview.grade,
            interview_type=itype,
            is_pro=db_user.is_pro,
        )
    except Exception as e:
        logger.error("Evaluation failed: %s", e)
        evaluation = {
            "score": 50,
            "feedback": "Не удалось оценить автоматически. Продолжай практиковаться!",
            "ideal_answer": "",
        }

    score = evaluation["score"]
    feedback = evaluation.get("feedback", "")
    ideal = evaluation.get("ideal_answer", "")

    # Save to DB
    await session_repo.save_answer(
        db_session, question, answer_text, score, feedback, ideal, interview
    )
    await user_repo.increment_daily_usage(db_session, db_user.id)
    await user_repo.add_score(db_session, db_user, score)
    await user_repo.update_streak(db_session, db_user)

    # Refresh user
    await db_session.refresh(db_user)

    # Check achievements
    if score == 100:
        await grant_achievement(db_session, db_user, "perfect_score")

    # HR/tech counters for achievements
    hr_count = sum(1 for q in interview.questions if q.answer_text)
    if itype == "hr" and hr_count >= 20:
        await grant_achievement(db_session, db_user, "hr_master")
    if itype == "tech" and hr_count >= 20:
        await grant_achievement(db_session, db_user, "tech_master")

    new_achievements = await check_and_grant(db_session, db_user)

    # Format score emoji
    score_emoji = _score_emoji(score)
    progress = _progress_bar(db_user.readiness_pct)

    text = (
        f"{score_emoji} <b>Оценка: {score}/100</b>\n\n"
        f"💬 <b>Фидбек:</b>\n{feedback}"
    )

    if ideal and db_user.is_pro:
        text += f"\n\n✨ <b>Эталонный ответ:</b>\n<i>{ideal}</i>"
    elif not db_user.is_pro:
        text += "\n\n💎 <i>Эталонный ответ доступен в Pro</i>"

    text += (
        f"\n\n📊 <b>Прогресс:</b>\n"
        f"• Вопросов: {db_user.total_questions} | Ср.балл: {db_user.average_score}\n"
        f"• Стрик: {db_user.streak_days} 🔥\n"
        f"• Готовность: {progress} {db_user.readiness_pct}%"
    )

    if new_achievements:
        text += "\n\n🏆 <b>Новые достижения!</b>\n"
        text += "\n".join(f"{e} <b>{t}</b> — {d}" for e, t, d in new_achievements)

    await message.answer(text, reply_markup=after_answer_kb(db_user.is_pro), parse_mode="HTML")


@router.callback_query(F.data == "next_question")
async def cb_next_question(
    callback: CallbackQuery,
    db_user: User,
    db_session,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    session_id = data.get("session_id")

    if not session_id:
        await callback.message.edit_text(
            "Сессия истекла. Начни новое интервью:",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    # Check limit
    if not db_user.is_pro:
        used = await user_repo.get_questions_used_today(db_session, db_user.id)
        if used >= settings.FREE_QUESTIONS_PER_DAY:
            await callback.message.answer(
                f"⚠️ Лимит {settings.FREE_QUESTIONS_PER_DAY} вопросов/день исчерпан.\n"
                "💎 Pro — безлимитная практика!",
                reply_markup=main_menu_kb(),
            )
            await callback.answer()
            return

    interview = await session_repo.get_session_by_id(db_session, session_id)
    if not interview:
        await callback.answer("Сессия не найдена")
        return

    loading = await callback.message.answer("⏳ Генерирую следующий вопрос...")
    await _ask_next_question(loading, db_user, db_session, state, interview, edit=True)
    await callback.answer()


@router.callback_query(F.data == "finish_interview")
async def cb_finish_interview(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "Точно хочешь завершить сессию?",
        reply_markup=confirm_finish_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "continue_interview")
async def cb_continue(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.answer("Продолжаем! 💪")


@router.callback_query(F.data == "confirm_finish")
async def cb_confirm_finish(
    callback: CallbackQuery,
    db_user: User,
    db_session,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    session_id = data.get("session_id")
    await state.clear()

    if session_id:
        interview = await session_repo.get_session_by_id(db_session, session_id)
        if interview and interview.status == "active":
            await session_repo.finish_session(db_session, interview)

            avg = (
                round(interview.session_score / interview.questions_count)
                if interview.questions_count > 0 else 0
            )
            progress = _progress_bar(db_user.readiness_pct)

            await callback.message.edit_text(
                f"🏁 <b>Сессия завершена!</b>\n\n"
                f"📋 Вопросов в сессии: {interview.questions_count}\n"
                f"⭐ Балл сессии: {avg}/100\n\n"
                f"📊 <b>Общий прогресс:</b>\n"
                f"• Всего вопросов: {db_user.total_questions}\n"
                f"• Средний балл: {db_user.average_score}\n"
                f"• Стрик: {db_user.streak_days} 🔥\n"
                f"• Готовность: {progress} {db_user.readiness_pct}%\n\n"
                "Хочешь ещё потренироваться?",
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
    else:
        await callback.message.edit_text(
            "Возвращаемся в меню:",
            reply_markup=main_menu_kb(),
        )

    await callback.answer()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _score_emoji(score: int) -> str:
    if score >= 90:
        return "🌟"
    elif score >= 75:
        return "✅"
    elif score >= 55:
        return "🟡"
    elif score >= 35:
        return "🟠"
    else:
        return "❌"


def _progress_bar(pct: int, length: int = 10) -> str:
    filled = round(pct / 100 * length)
    return "█" * filled + "░" * (length - filled)
