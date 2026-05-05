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
) -> tuple[str, str]:
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

    if interview_type == "tech":
        cat_instruction = """\n\nВ КОНЦЕ ответа добавь строку:
CATEGORY: <одно из: python, algorithms, system_design, databases, devops, architecture, security, general>"""
    else:
        cat_instruction = """\n\nВ КОНЦЕ ответа добавь строку:
CATEGORY: behavioral"""
    user_content += cat_instruction

    raw = await chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        model=model,
        max_tokens=350,
    )
    # Extract category
    category = "general"
    lines = raw.strip().split("\n")
    question_lines = []
    for line in lines:
        if line.strip().startswith("CATEGORY:"):
            category = line.split(":", 1)[1].strip().lower()
        else:
            question_lines.append(line)
    question_text = "\n".join(question_lines).strip()
    return question_text, category


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

    user_content = f"""Ты — опытный карьерный коуч. Твоя задача — оценить ответ кандидата и вернуть ТОЛЬКО JSON без какого-либо другого текста.
Если ответ кандидата пустой, слишком короткий или не по теме — всё равно верни JSON со score=20 и советом как ответить.

Позиция: {grade} {role}
Тип интервью: {"HR/поведенческое" if interview_type == "hr" else "Техническое"}

Вопрос: {question}

Ответ кандидата: {answer}

Дай разбор в формате JSON (только JSON, без markdown):
{{
  "score": <число от 0 до 100>,
  "feedback": "<{detail_level} коучинговый фидбек на русском: начни с того что было сильным, затем что конкретно можно усилить и как, заверши мотивирующей фразой>",
  "ideal_answer": "<ключевые тезисы которые стоило упомянуть, сформулируй как подсказку а не как правильный ответ>"
}}

Тон: поддерживающий, конкретный, без осуждения. Как опытный ментор после мок-интервью.

Ориентиры по score (используй внутри, не озвучивай как оценку):
- 85-100: Сильный ответ — подчеркни что именно хорошо
- 65-84: Хороший задел — покажи как довести до сильного
- 45-64: Есть основа — помоги структурировать и дополнить
- 25-44: Слабый старт — мягко объясни что упущено и с чего начать
- 0-24: Ответ не по теме или пустой — переформулируй вопрос, предложи попробовать снова"""

    raw = await chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        model=model,
        max_tokens=800 if is_pro else 500,
    )

    import re
    import re as _re
    clean = raw.strip()
    # Extract JSON object with regex — handles ```json fences and extra text
    match = _re.search(r'\{.*\}', clean, _re.DOTALL)
    if match:
        clean = match.group(0)
    # Remove trailing commas before } or ] (common LLM mistake)
    clean = _re.sub(r',\s*([}\]])', r'', clean)

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


CATEGORIES_RU = {
    "python": "Python",
    "algorithms": "Алгоритмы",
    "system_design": "System Design",
    "databases": "Базы данных",
    "devops": "DevOps",
    "architecture": "Архитектура",
    "security": "Безопасность",
    "behavioral": "Поведенческие",
    "general": "Общие",
}


async def generate_final_report(
    role: str,
    grade: str,
    questions_with_scores: list[dict],
    is_pro: bool = False,
) -> str:
    """Generate final session report with category breakdown."""
    model = settings.PRO_MODEL if is_pro else settings.FREE_MODEL

    # Group by category
    by_category: dict[str, list[int]] = {}
    for q in questions_with_scores:
        cat = q.get("category") or "general"
        score = q.get("score", 50)
        by_category.setdefault(cat, []).append(score)

    cat_summary = []
    for cat, scores in by_category.items():
        avg = round(sum(scores) / len(scores))
        cat_ru = CATEGORIES_RU.get(cat, cat)
        cat_summary.append(f"- {cat_ru}: {avg}/100 ({len(scores)} вопр.)")

    summary_str = "\n".join(cat_summary)
    total_avg = round(sum(q.get("score", 50) for q in questions_with_scores) / len(questions_with_scores))

    user_content = f"""Ты карьерный коуч. Дай финальный отчёт по mock-интервью.

Позиция: {grade} {role}
Вопросов пройдено: {len(questions_with_scores)}
Средний балл: {total_avg}/100

Результаты по категориям:
{summary_str}

Напиши финальный отчёт на русском (3-4 абзаца):
1. Общий вывод — как прошло интервью в целом
2. Сильные стороны — где кандидат показал себя хорошо (конкретно)
3. Зоны роста — что нужно проработать (конкретно, с советами)
4. Следующий шаг — 1-2 конкретных действия для улучшения

Тон: как опытный ментор после мок-интервью. Поддерживающий, честный, конкретный."""

    return await chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        model=model,
        max_tokens=600,
    )
