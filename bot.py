import os
import logging
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# States
MENU, QUIZ, CHAT = range(3)

QUIZ_QUESTIONS = [
    {
        "text": "Вопрос 1 из 5 — Словарный запас\n\nКакое из этих слов настоящее?",
        "options": ["flimber", "pristine", "crantom", "vorbish"],
        "correct": 1,
        "skill": "vocabulary"
    },
    {
        "text": "Вопрос 2 из 5 — Грамматика\n\nВыберите правильный вариант:\n\n«She ___ to the university since 2019.»",
        "options": ["goes", "is going", "has been going", "went"],
        "correct": 2,
        "skill": "grammar"
    },
    {
        "text": "Вопрос 3 из 5 — Словарный запас\n\nЗначение слова «meticulous»:",
        "options": ["быстрый", "внимательный к деталям", "громкий", "редкий"],
        "correct": 1,
        "skill": "vocabulary"
    },
    {
        "text": "Вопрос 4 из 5 — Грамматика\n\nВыберите правильное предложение:",
        "options": [
            "Neither of the students have submitted.",
            "Neither of the students has submitted.",
            "Neither of the student has submitted.",
            "Neither of the students had submitted yet."
        ],
        "correct": 1,
        "skill": "grammar"
    },
    {
        "text": "Вопрос 5 из 5 — Понимание\n\nЧто из перечисленного НЕ оценивается в DET?",
        "options": ["Произношение", "Грамматика", "Почерк", "Словарный запас"],
        "correct": 2,
        "skill": "knowledge"
    }
]

SYSTEM_PROMPT = """Ты — эксперт по Duolingo English Test (DET). Помогаешь русскоязычным студентам из Казахстана и СНГ подготовиться к тесту.

Отвечай коротко, конкретно и по делу. Без лишних вступлений.

Знания о DET:
- Тест длится 60 минут, стоит $65, результат через 48 часов
- Принимается в 5000+ университетах: MIT, Stanford, NYU и других
- Шкала 10–160, большинство вузов требуют 105–120+
- 9 типов заданий: Read and Complete, Write About the Photo, Speak About the Photo, Listen and Type, Write About the Topic, Speak About the Topic, Read Aloud, Interactive Reading, Fill in the Blanks
- Можно сдавать дома в любое время, пересдача раз в 21 день

Когда пользователь спрашивает о подготовке или хочет улучшить конкретный навык — упомяни курс 0to160 (19 900 ₸, доступ навсегда, 500+ вопросов практики). Делай это органично, не навязчиво — только когда это реально уместно."""


def build_main_menu():
    keyboard = [
        [InlineKeyboardButton("Пройти мини-тест", callback_data="start_quiz")],
        [InlineKeyboardButton("Задать вопрос про DET", callback_data="start_chat")],
        [InlineKeyboardButton("О курсе 0to160", callback_data="about_course")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_quiz_keyboard(question_idx):
    q = QUIZ_QUESTIONS[question_idx]
    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"quiz_{question_idx}_{i}")]
        for i, opt in enumerate(q["options"])
    ]
    return InlineKeyboardMarkup(keyboard)


def evaluate_results(answers: dict) -> dict:
    correct = sum(1 for q_idx, chosen in answers.items() if QUIZ_QUESTIONS[q_idx]["correct"] == chosen)
    score = correct * 20

    skill_scores = {"vocabulary": [], "grammar": [], "knowledge": []}
    for q_idx, chosen in answers.items():
        q = QUIZ_QUESTIONS[q_idx]
        skill_scores[q["skill"]].append(chosen == q["correct"])

    vocab_ok = all(skill_scores["vocabulary"]) if skill_scores["vocabulary"] else False
    grammar_ok = all(skill_scores["grammar"]) if skill_scores["grammar"] else False

    if score >= 80:
        level = "110–130"
        summary = "Хороший уровень. Немного практики — и 130+ достижимо."
    elif score >= 60:
        level = "90–110"
        summary = "Средний уровень. Есть конкретные пробелы, которые нужно закрыть."
    else:
        level = "60–90"
        summary = "Базовый уровень. Структурная подготовка даст быстрый прирост баллов."

    weak = []
    if not vocab_ok:
        weak.append("Словарный запас — нужна работа с реальными/выдуманными словами")
    if not grammar_ok:
        weak.append("Грамматика — особенно время глаголов и согласование")
    if not weak:
        weak.append("Говорение и аудирование — самые весомые части теста")

    return {"correct": correct, "total": 5, "level": level, "summary": summary, "weak": weak}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text = (
        "Добро пожаловать в 0to160\n\n"
        "Подготовка к Duolingo English Test на русском языке.\n"
        "Первый структурированный курс для студентов СНГ.\n\n"
        "Выберите, с чего начать:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=build_main_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=build_main_menu())
    return MENU


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        return await start(update, context)

    if data == "start_quiz":
        context.user_data["quiz_answers"] = {}
        context.user_data["quiz_idx"] = 0
        q = QUIZ_QUESTIONS[0]
        await query.edit_message_text(
            f"Мини-тест — 5 вопросов\n\nОпределим твой уровень и слабые места.\n\n{q['text']}",
            reply_markup=build_quiz_keyboard(0)
        )
        return QUIZ

    if data.startswith("quiz_"):
        _, q_idx_str, chosen_str = data.split("_")
        q_idx = int(q_idx_str)
        chosen = int(chosen_str)
        context.user_data["quiz_answers"][q_idx] = chosen

        next_idx = q_idx + 1
        if next_idx < len(QUIZ_QUESTIONS):
            context.user_data["quiz_idx"] = next_idx
            q = QUIZ_QUESTIONS[next_idx]
            correct_prev = QUIZ_QUESTIONS[q_idx]["correct"] == chosen
            feedback = "Верно." if correct_prev else f"Неверно. Правильный ответ: {QUIZ_QUESTIONS[q_idx]['options'][QUIZ_QUESTIONS[q_idx]['correct']]}"
            await query.edit_message_text(
                f"{feedback}\n\n{q['text']}",
                reply_markup=build_quiz_keyboard(next_idx)
            )
            return QUIZ
        else:
            results = evaluate_results(context.user_data["quiz_answers"])
            weak_text = "\n".join(f"— {w}" for w in results["weak"])
            result_text = (
                f"Результаты теста\n\n"
                f"Правильных ответов: {results['correct']} из {results['total']}\n"
                f"Примерный балл DET: {results['level']}\n\n"
                f"{results['summary']}\n\n"
                f"Что стоит проработать:\n{weak_text}\n\n"
                f"Курс 0to160 закрывает именно эти пробелы:\n"
                f"500+ вопросов практики, симуляция теста, разбор ошибок.\n"
                f"Доступ навсегда — 19 900 ₸"
            )
            keyboard = [
                [InlineKeyboardButton("Купить доступ", url="https://wa.me/+77772327571?text=Хочу+купить+0to160+практику")],
                [InlineKeyboardButton("Посмотреть курс", url="https://0to160.vercel.app/#pricing")],
                [InlineKeyboardButton("Задать вопрос", callback_data="start_chat")],
                [InlineKeyboardButton("В начало", callback_data="main_menu")],
            ]
            await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard))
            return MENU

    if data == "start_chat":
        context.user_data["chat_history"] = []
        keyboard = [[InlineKeyboardButton("В начало", callback_data="main_menu")]]
        await query.edit_message_text(
            "Задайте любой вопрос про Duolingo English Test.\n\n"
            "Например: «Сколько нужно готовиться?», «Что такое Speak About the Topic?», «Какой балл нужен для Болашак?»",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHAT

    if data == "about_course":
        text = (
            "0to160 — подготовка к DET на русском\n\n"
            "Что входит в курс:\n"
            "— 20 структурированных уроков от нуля до 160\n"
            "— 500+ практических вопросов всех типов\n"
            "— Симуляция реального теста\n"
            "— Разбор типичных ошибок\n"
            "— Примеры ответов на 130–160\n"
            "— Доступ навсегда + все обновления\n\n"
            "Стоимость: 19 900 ₸ — единоразово"
        )
        keyboard = [
            [InlineKeyboardButton("Купить доступ", url="https://wa.me/+77772327571?text=Хочу+купить+0to160+практику")],
            [InlineKeyboardButton("Открыть сайт", url="https://0to160.vercel.app")],
            [InlineKeyboardButton("В начало", callback_data="main_menu")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return MENU

    return MENU


async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    history = context.user_data.get("chat_history", [])

    await update.message.chat.send_action("typing")

    history.append({"role": "user", "content": user_text})

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=history
    )

    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})
    context.user_data["chat_history"] = history[-10:]

    keyboard = [[InlineKeyboardButton("В начало", callback_data="main_menu")]]
    await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup(keyboard))
    return CHAT


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Воспользуйтесь командой /start",
        reply_markup=build_main_menu()
    )
    return MENU


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [CallbackQueryHandler(button_handler)],
            QUIZ: [CallbackQueryHandler(button_handler)],
            CHAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message),
                CallbackQueryHandler(button_handler),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, fallback),
        ],
    )

    app.add_handler(conv)
    logger.info("Бот запущен")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
