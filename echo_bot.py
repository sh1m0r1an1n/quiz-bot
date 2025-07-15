import os
import json
import random
import redis
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext


def create_keyboard():
    keyboard = [
        [KeyboardButton("🆕 Новый вопрос"), KeyboardButton("🏳️ Сдаться")],
        [KeyboardButton("📊 Мой счет")]
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


def start_command(update, context):
    reply_markup = create_keyboard()
    update.message.reply_text("Здравствуйте", reply_markup=reply_markup)


def handle_buttons(update, context):
    text = update.message.text
    user_id = update.effective_user.id
    redis_client = context.bot_data['redis_client']
    quiz_data_path = os.getenv("QUIZ_DATA_PATH", "quiz-json")
    
    user_key = f"user:{user_id}:current_question"
    
    if text == "🆕 Новый вопрос":
        question, answer = get_random_question(quiz_data_path)
        
        question_data = {
            "question": question,
            "answer": answer
        }
        redis_client.set(user_key, json.dumps(question_data, ensure_ascii=False))
        
        update.message.reply_text(f"❓ {question}")

    elif text == "🏳️ Сдаться":
        stored_data = redis_client.get(user_key)
        question_data = json.loads(stored_data)
        answer = question_data['answer']
        update.message.reply_text(f"✅ Правильный ответ: {answer}")
        redis_client.delete(user_key)
            
    elif text == "📊 Мой счет":
        update.message.reply_text("Функция 'Мой счет' пока не реализована")
    else:
        handle_answer(update, context)


def handle_answer(update, context):
    """Обрабатывает ответ пользователя на вопрос"""
    user_id = update.effective_user.id
    redis_client = context.bot_data['redis_client']
    user_key = f"user:{user_id}:current_question"
    
    stored_data = redis_client.get(user_key)
    
    question_data = json.loads(stored_data)
    correct_answer = question_data['answer']
    user_answer = update.message.text
    
    if check_answer(user_answer, correct_answer):
        update.message.reply_text("Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»")
        redis_client.delete(user_key)
    else:
        update.message.reply_text("Неправильно… Попробуешь ещё раз?")


def main():
    load_dotenv()
    bot_token = os.environ["TG_BOT_TOKEN"]
    redis_url = os.environ["REDIS_URL"]
    
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    updater = Updater(token=bot_token)
    dispatcher = updater.dispatcher
    
    dispatcher.bot_data['redis_client'] = redis_client
    
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_buttons))
    
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main() 