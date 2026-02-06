# models.py

from pydantic import BaseModel
from typing import List, Optional


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    explanation: str


class UserState(BaseModel):
    current_question: Optional[QuizQuestion] = None
    score: int = 0
    total_questions: int = 0
    topic: str = "Общая эрудиция"
    level: str = "средний"
    last_questions: List[str] = []
