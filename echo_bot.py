import os
import json
import random
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


def start_command(update, context):
    reply_markup = create_keyboard()
    update.message.reply_text("Здравствуйте", reply_markup=reply_markup)


def handle_buttons(update, context):
    text = update.message.text
    quiz_data_path = os.getenv("QUIZ_DATA_PATH", "quiz-json")
    
    if text == "🆕 Новый вопрос":
        question, answer = get_random_question(quiz_data_path)
        context.user_data['current_answer'] = answer
        update.message.reply_text(f"❓ {question}")

    elif text == "🏳️ Сдаться":
        current_answer = context.user_data.get('current_answer')
        update.message.reply_text(f"✅ Правильный ответ: {current_answer}")
        context.user_data['current_answer'] = None
    elif text == "📊 Мой счет":
        update.message.reply_text("Функция 'Мой счет' пока не реализована")
    else:
        echo_message(update, context)


def echo_message(update, context):
    user_message = update.message.text
    update.message.reply_text(user_message)


def main():
    load_dotenv()
    bot_token = os.environ["TG_BOT_TOKEN"]
    
    updater = Updater(token=bot_token)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_buttons))
    
    print("Бот запущен...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main() 