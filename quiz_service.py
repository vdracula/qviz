from typing import Dict

# llm_client.py
from models import QuizQuestion
from config import settings

# quiz_service.py
from models import UserState, QuizQuestion
import llm_client

# Простое in-memory хранилище (на проде заменить на БД)
_user_states: Dict[int, UserState] = {}


def get_or_create_state(user_id: int) -> UserState:
    if user_id not in _user_states:
        _user_states[user_id] = UserState()
    return _user_states[user_id]


async def new_question(user_id: int) -> QuizQuestion:
    state = get_or_create_state(user_id)

    question = await llm_client.generate_question(
        topic=state.topic,
        level=state.level,
        banned_questions=state.last_questions,
    )

    state.current_question = question
    state.total_questions += 1

    # обновляем список последних вопросов для анти-повторов
    state.last_questions.append(question.question)
    if len(state.last_questions) > 5:  # храним последние 5
        state.last_questions = state.last_questions[-5:]

    return question


def check_answer(user_id: int, answer_index: int) -> tuple[bool, QuizQuestion, UserState]:
    state = get_or_create_state(user_id)

    if not state.current_question:
        raise RuntimeError("Нет активного вопроса для пользователя")

    q = state.current_question
    is_correct = (answer_index == q.correct_index)

    if is_correct:
        state.score += 1

    # После ответа можно сбросить current_question,
    # если не нужно возвращаться к нему
    state.current_question = None

    return is_correct, q, state
