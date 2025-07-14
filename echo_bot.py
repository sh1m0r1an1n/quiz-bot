import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext


def create_keyboard():
    keyboard = [
        [KeyboardButton("🆕 Новый вопрос"), KeyboardButton("🏳️ Сдаться")],
        [KeyboardButton("📊 Мой счет")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def start_command(update, context):
    reply_markup = create_keyboard()
    update.message.reply_text("Здравствуйте", reply_markup=reply_markup)


def handle_buttons(update, context):
    text = update.message.text
    
    if text == "🆕 Новый вопрос":
        update.message.reply_text("Функция 'Новый вопрос' пока не реализована")
    elif text == "🏳️ Сдаться":
        update.message.reply_text("Функция 'Сдаться' пока не реализована")
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