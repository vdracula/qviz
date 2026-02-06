import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command

from quiz_service import get_or_create_state
from services_db import update_score, get_stats
from db import init_db
from config import settings
import quiz_service


bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher()


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Новый вопрос", callback_data="quiz:new")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="quiz:stats")],
        [InlineKeyboardButton(text="🎯 Тема", callback_data="quiz:topics")],
    ])

def topics_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💻 IT", callback_data="quiz:topic:it"),
            InlineKeyboardButton(text="🎬 Кино", callback_data="quiz:topic:movie"),
        ],
        [
            InlineKeyboardButton(text="🎵 Музыка", callback_data="quiz:topic:music"),
            InlineKeyboardButton(text="🌍 Эрудиция", callback_data="quiz:topic:general"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="quiz:menu"),
        ],
    ])


def question_kb(options: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for idx, option in enumerate(options):
        rows.append([
            InlineKeyboardButton(
                text=option,
                callback_data=f"quiz:answer:{idx}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "Привет! Это викторина с вопросами от ИИ.\n\n"
        "Нажми кнопку ниже, чтобы получить новый вопрос."
    )
    await message.answer(text, reply_markup=main_menu_kb())

@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    user_id = message.from_user.id
    question = await quiz_service.new_question(user_id)

    text = (
        "Привет! Это викторина с вопросами от ИИ.\n\n"
        "Нажми кнопку ниже, чтобы получить новый вопрос."
    )
    await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "quiz:new")
async def cb_new_question(callback: CallbackQuery):
    user_id = callback.from_user.id
    question = await quiz_service.new_question(user_id)

    text = f"❓ <b>{question.question}</b>"
    kb = question_kb(question.options)

    # Редактируем сообщение, если есть, иначе отвечаем
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb)
    else:
        await callback.message.answer(text, reply_markup=kb)

    await callback.answer()  # закрыть "часики"

@dp.callback_query(F.data == "quiz:topics")
async def cb_topics(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выбери тему викторины:",
        reply_markup=topics_kb(),
    )
    await callback.answer()
from quiz_service import get_or_create_state  # вверху файла

@dp.callback_query(F.data == "quiz:finish")
async def cb_finish(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = get_or_create_state(user_id)
    # сбрасываем текущий вопрос
    state.current_question = None

    text = (
        "Квиз завершён.\n\n"
        "Можешь вернуться в главное меню и начать заново в любой момент."
    )
    await callback.message.edit_text(text, reply_markup=main_menu_kb())
    await callback.answer()

@dp.callback_query(F.data.startswith("quiz:topic:"))
async def cb_set_topic(callback: CallbackQuery):
    user_id = callback.from_user.id
    _, _, topic_key = callback.data.split(":")

    state = get_or_create_state(user_id)

    if topic_key == "it":
        state.topic = "IT и программирование"
        title = "💻 Тема установлена: IT и программирование"
    elif topic_key == "movie":
        state.topic = "Кино, сериалы, режиссёры и актёры"
        title = "🎬 Тема установлена: Кино"
    elif topic_key == "music":
        state.topic = "Музыка, исполнители, альбомы"
        title = "🎵 Тема установлена: Музыка"
    else:
        state.topic = "Общая эрудиция"
        title = "🌍 Тема установлена: Общая эрудиция"

    await callback.message.edit_text(
        f"{title}\n\nТеперь жми «Новый вопрос».",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()

@dp.callback_query(F.data == "quiz:menu")
async def cb_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню викторины:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()

def question_kb(options: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for idx, option in enumerate(options):
        rows.append([
            InlineKeyboardButton(
                text=option,
                callback_data=f"quiz:answer:{idx}",
            )
        ])
    # добавляем кнопку завершения квиза
    rows.append([
        InlineKeyboardButton(
            text="🚪 Закончить квиз",
            callback_data="quiz:finish",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.callback_query(F.data == "quiz:stats")
async def cb_stats(callback: CallbackQuery):
    total, score, accuracy = await get_stats(callback.from_user.id)

    text = (
        "📊 <b>Твоя статистика</b>\n\n"
        f"Всего вопросов: {total}\n"
        f"Правильных ответов: {score}\n"
        f"Точность: {accuracy:.1f}%"
    )

    await callback.message.edit_text(text, reply_markup=main_menu_kb())
    await callback.answer()


@dp.callback_query(F.data.startswith("quiz:answer:"))
async def cb_answer(callback: CallbackQuery):
    user = callback.from_user
    user_id = user.id

    try:
        _, _, idx_str = callback.data.split(":")
        answer_index = int(idx_str)
    except Exception:
        await callback.answer("Ошибка данных ответа", show_alert=True)
        return

    try:
        is_correct, question, state = quiz_service.check_answer(user_id, answer_index)
    except RuntimeError:
        await callback.answer("Нет активного вопроса. Нажми «Новый вопрос».", show_alert=True)
        return

    # обновляем БД
    await update_score(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        question_text=question.question,
        topic=state.topic,
        is_correct=is_correct,
    )

    total, score, accuracy = await get_stats(user.id)

    result_text = "✅ Правильно!" if is_correct else "❌ Неправильно."
    correct_option = question.options[question.correct_index]

    text = (
        f"{result_text}\n\n"
        f"Правильный ответ: <b>{correct_option}</b>\n\n"
        f"{question.explanation}\n\n"
        f"Твой счёт: {score}/{total} ({accuracy:.1f}%)"
    )

    await callback.message.edit_text(text, reply_markup=main_menu_kb())
    await callback.answer()


async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
