import os
import json
import random
import redis
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler, 
    Filters, 
    CallbackContext,
    ConversationHandler
)


class States(Enum):
    CHOOSING = 1
    ANSWERING = 2


def create_keyboard():
    keyboard = [
        [KeyboardButton("🆕 Новый вопрос"), KeyboardButton("🏳️ Сдаться")],
        [KeyboardButton("📊 Мой счет"), KeyboardButton("🔄 Начать заново")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_random_question(quiz_data_path):
    quiz_directory = Path(quiz_data_path)
    json_files = list(quiz_directory.glob("*.json"))
    
    random_file = random.choice(json_files)
    
    with open(random_file, 'r', encoding='utf-8') as file:
        questions_data = json.load(file)
    
    random_question = random.choice(list(questions_data.keys()))
    answer = questions_data[random_question]
    
    return random_question, answer


def clean_answer(answer):
    """Очищает ответ от пояснений в скобках и после точки"""
    if '(' in answer:
        answer = answer.split('(')[0]
    
    if '.' in answer:
        answer = answer.split('.')[0]
    
    return answer.strip()


def check_answer(user_answer, correct_answer):
    cleaned_correct = clean_answer(correct_answer)
    
    user_answer = user_answer.strip().lower()
    cleaned_correct = cleaned_correct.strip().lower()
    
    return user_answer == cleaned_correct


def get_user_context(update, context):
    user_id = update.effective_user.id
    redis_client = context.bot_data['redis_client']
    user_key = f"user:{user_id}:current_question"
    quiz_data_path = os.getenv("QUIZ_DATA_PATH", "quiz-json")
    
    return user_id, redis_client, user_key, quiz_data_path


def get_current_question_data(redis_client, user_key):
    stored_data = redis_client.get(user_key)
    return json.loads(stored_data)


def load_and_send_question(update, redis_client, user_key, quiz_data_path):
    question, answer = get_random_question(quiz_data_path)
    
    question_data = {
        "question": question,
        "answer": answer
    }
    
    redis_client.set(user_key, json.dumps(question_data, ensure_ascii=False))
    update.message.reply_text(f"❓ {question}")


def start(update, context):
    reply_markup = create_keyboard()
    welcome_message = (
        "🎯 Добро пожаловать в игру «Викторина»!\n\n"
        "Я задам вам вопросы из различных областей знаний. "
        "Попробуйте ответить правильно!\n\n"
        "Управление:\n"
        "🆕 Новый вопрос — получить случайный вопрос\n"
        "🏳️ Сдаться — показать правильный ответ\n"
        "📊 Мой счет — посмотреть статистику\n"
        "🔄 Начать заново — перезапустить бота\n\n"
        "Нажмите «Новый вопрос» для начала!"
    )
    update.message.reply_text(welcome_message, reply_markup=reply_markup)
    return States.CHOOSING


def handle_new_question_request(update, context):
    user_id, redis_client, user_key, quiz_data_path = get_user_context(update, context)
    
    load_and_send_question(update, redis_client, user_key, quiz_data_path)
    return States.ANSWERING


def handle_solution_attempt(update, context):
    user_id, redis_client, user_key, quiz_data_path = get_user_context(update, context)
    
    question_data = get_current_question_data(redis_client, user_key)
    correct_answer = question_data['answer']
    user_answer = update.message.text
    
    if check_answer(user_answer, correct_answer):
        update.message.reply_text("Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»")
        redis_client.delete(user_key)
        return States.CHOOSING
    else:
        update.message.reply_text("Неправильно… Попробуешь ещё раз?")
        return States.ANSWERING


def handle_give_up(update, context):
    user_id, redis_client, user_key, quiz_data_path = get_user_context(update, context)
    
    question_data = get_current_question_data(redis_client, user_key)
    answer = question_data['answer']
    
    clean_answer_text = clean_answer(answer)
    update.message.reply_text(f"✅ Правильный ответ: {clean_answer_text}")
    
    load_and_send_question(update, redis_client, user_key, quiz_data_path)
    return States.ANSWERING


def handle_score(update, context):
    update.message.reply_text("Функция 'Мой счет' пока не реализована")
    return States.CHOOSING


def handle_restart(update, context):
    return start(update, context)


def main():
    load_dotenv()
    bot_token = os.environ["TG_BOT_TOKEN"]
    redis_url = os.environ["REDIS_URL"]
    
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    updater = Updater(token=bot_token)
    dispatcher = updater.dispatcher
    
    dispatcher.bot_data['redis_client'] = redis_client
    
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            States.CHOOSING: [
                MessageHandler(Filters.regex("^🆕 Новый вопрос$"), handle_new_question_request),
                MessageHandler(Filters.regex("^📊 Мой счет$"), handle_score),
                MessageHandler(Filters.regex("^🔄 Начать заново$"), handle_restart),
            ],
            States.ANSWERING: [
                MessageHandler(Filters.regex("^🏳️ Сдаться$"), handle_give_up),
                MessageHandler(Filters.regex("^🔄 Начать заново$"), handle_restart),
                MessageHandler(Filters.text & ~Filters.command, handle_solution_attempt),
            ],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    dispatcher.add_handler(conversation_handler)
    
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main() 