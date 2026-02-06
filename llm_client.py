import json
from typing import Optional

import httpx

from models import QuizQuestion
from config import settings

   
SYSTEM_PROMPT = (
    "Ты генератор вопросов викторины.\n"
    "Всегда генерируй ОДИН вопрос с четырьмя вариантами ответа на РУССКОМ ЯЗЫКЕ.\n"
    "Строго соблюдай формат JSON без лишнего текста:\n"
    '{\n'
    '  "question": "текст вопроса",\n'
    '  "options": ["вариант 1", "вариант 2", "вариант 3", "вариант 4"],\n'
    '  "correct_index": 0,\n'
    '  "explanation": "краткое объяснение ответа"\n'
    '}\n'
    "Не добавляй ничего вне JSON, не используй Markdown, комментарии и кодовые блоки."
)


async def generate_question(
    topic: Optional[str] = None,
    level: Optional[str] = None,
    banned_questions: Optional[list[str]] = None,
) -> QuizQuestion:
    topic_part = f"Тема: {topic}.\n" if topic else "Тема: общая эрудиция.\n"
    level_part = f"Уровень сложности: {level}.\n" if level else "Уровень сложности: средний.\n"

    banned_part = ""
    if banned_questions:
        joined = "; ".join(banned_questions[:10])
        banned_part = (
            "Не повторяй вопросы, похожие на следующие (избегай таких же формулировок и фактов): "
            f"{joined}\n"
        )

    user_prompt = (
        f"{topic_part}{level_part}{banned_part}"
        "Сгенерируй новый уникальный вопрос для викторины."
    )

    data = {
        "modelUri": f"gpt://{settings.yandex_folder_id}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.5,
            "maxTokens": 512,
        },
        "messages": [
            {"role": "system", "text": SYSTEM_PROMPT},
            {"role": "user", "text": user_prompt},
        ],
    }
    ...

    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            settings.yandex_endpoint,  # для этого варианта endpoint должен быть /foundationModels/v1/completion
            headers=headers,
            json=data,
        )
        resp.raise_for_status()
        resp_data = resp.json()

    # Структура ответа для /completion — в alternatives лежат варианты текста[page:0][page:1]
    alt = resp_data["result"]["alternatives"][0]
    text = alt["message"]["text"].strip()

    print("YANDEX RAW TEXT >>>", repr(text))

    # Попытка распарсить как чистый JSON
    try:
        quiz_dict = json.loads(text)
    except json.JSONDecodeError:
        # Если модель всё равно добавила что-то лишнее — попробуем вытащить JSON по скобкам
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError(f"Не удалось найти JSON в ответе модели: {text!r}")
        json_str = text[start : end + 1]
        quiz_dict = json.loads(json_str)

    question = QuizQuestion(**quiz_dict)

    if len(question.options) != 4:
        raise RuntimeError("Модель вернула не 4 варианта ответа")
    if not 0 <= question.correct_index < 4:
        raise RuntimeError("Некорректный correct_index в ответе модели")

    return question
