"""Generate interview questions tailored to role, grade, company, and type."""
from __future__ import annotations

import json
import logging
from typing import Optional

from core.llm_client import chat_completion
from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — опытный технический интервьюер и HR-специалист в IT-компании.
Твоя задача — задавать точные, релевантные вопросы для собеседований.
Отвечай ТОЛЬКО на русском языке. Будь конкретным и профессиональным."""


async def generate_question(
    role: str,
    grade: str,
    company: Optional[str],
    interview_type: str,  # "hr" | "tech"
    previous_questions: list[str],
    job_description: Optional[str] = None,
    is_pro: bool = False,
) -> str:
    model = settings.PRO_MODEL if is_pro else settings.FREE_MODEL

    prev_str = ""
    if previous_questions:
        prev_list = "\n".join(f"- {q}" for q in previous_questions[-5:])
        prev_str = f"\n\nУже заданные вопросы (не повторяй):\n{prev_list}"

    jd_str = ""
    if job_description:
        jd_str = f"\n\nОписание вакансии:\n{job_description[:1500]}"

    company_str = f" в компании {company}" if company else ""

    if interview_type == "hr":
        type_instruction = """Задай ОДИН HR/поведенческий вопрос.
Темы: мотивация, конфликты, teamwork, работа под давлением, карьерные цели, 
сильные/слабые стороны, почему эта компания, ожидания от работы, фейлы и выводы.
Используй STAR-метод-ориентированные вопросы. Вопрос должен быть открытым и конкретным."""
    else:
        type_instruction = f"""Задай ОДИН технический вопрос для позиции {role} ({grade}).
Чередуй категории: алгоритмы, системный дизайн, конкретные технологии стека, 
архитектура, отладка, code review, производительность, безопасность, базы данных.
Для Senior/Lead — больше вопросов про архитектуру и leadership.
Для Junior/Middle — больше про базовые концепции и практику.
Вопрос должен быть реалистичным и проверять реальный опыт."""

    user_content = f"""Позиция: {grade} {role}{company_str}
Тип интервью: {"HR/поведенческое" if interview_type == "hr" else "Техническое"}{jd_str}{prev_str}

{type_instruction}

Верни ТОЛЬКО сам вопрос, без нумерации, пояснений и вводных фраз."""

    return await chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        model=model,
        max_tokens=300,
    )


async def evaluate_answer(
    question: str,
    answer: str,
    role: str,
    grade: str,
    interview_type: str,
    is_pro: bool = False,
) -> dict:
    """Returns {"score": int, "feedback": str, "ideal_answer": str}"""
    model = settings.PRO_MODEL if is_pro else settings.FREE_MODEL

    detail_level = "детальный" if is_pro else "краткий"

    user_content = f"""Оцени ответ кандидата на собеседование.

Позиция: {grade} {role}
Тип интервью: {"HR/поведенческое" if interview_type == "hr" else "Техническое"}

Вопрос: {question}

Ответ кандидата: {answer}

Дай оценку в формате JSON (только JSON, без markdown):
{{
  "score": <число от 0 до 100>,
  "feedback": "<{detail_level} фидбек на русском: что хорошо, что можно улучшить, конкретные советы>",
  "ideal_answer": "<краткий эталонный ответ или ключевые тезисы, которые стоило упомянуть>"
}}

Критерии оценки:
- 90-100: Отличный ответ, полный и структурированный
- 70-89: Хороший ответ, есть небольшие пробелы
- 50-69: Средний ответ, основное есть но много упущено
- 30-49: Слабый ответ, много неточностей
- 0-29: Неудовлетворительный ответ или отказ отвечать"""

    raw = await chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        model=model,
        max_tokens=800 if is_pro else 500,
    )

    # Strip markdown fences if present
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean

    try:
        result = json.loads(clean)
        result["score"] = max(0, min(100, int(result.get("score", 50))))
        return result
    except Exception as e:
        logger.error("Failed to parse evaluation JSON: %s | raw: %s", e, raw)
        return {
            "score": 50,
            "feedback": "Не удалось автоматически оценить ответ. Попробуй ещё раз.",
            "ideal_answer": "",
        }
