from typing import Optional, List

from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db import AsyncSessionLocal
from models_db import User, Answer


async def get_or_create_user(
    telegram_id: int,
    username: Optional[str],
    first_name: Optional[str],
) -> User:
    async with AsyncSessionLocal() as session:
        user = await _get_user_by_telegram_id(session, telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def _get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    res = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return res.scalar_one_or_none()


async def update_score(
    telegram_id: int,
    username: Optional[str],
    first_name: Optional[str],
    question_text: str,
    topic: Optional[str],
    is_correct: bool,
):
    async with AsyncSessionLocal() as session:
        user = await _get_user_by_telegram_id(session, telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            session.add(user)
            await session.flush()  # чтобы появился id

        user.total_questions += 1
        if is_correct:
            user.score += 1

        ans = Answer(
            user_id=user.id,
            question_text=question_text,
            is_correct=is_correct,
            topic=topic,
        )
        session.add(ans)

        await session.commit()


async def get_stats(telegram_id: int) -> tuple[int, int, float]:
    async with AsyncSessionLocal() as session:
        user = await _get_user_by_telegram_id(session, telegram_id)
        if user is None or user.total_questions == 0:
            return 0, 0, 0.0
        accuracy = user.score / user.total_questions * 100.0
        return user.total_questions, user.score, accuracy


async def get_leaderboard(limit: int = 10) -> List[User]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User)
            .where(User.total_questions >= 5)
            .order_by(desc(User.score))
            .limit(limit)
        )
        return list(res.scalars().all())
