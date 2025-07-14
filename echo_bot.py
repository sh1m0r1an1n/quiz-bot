import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext


def start_command(update, context):
    update.message.reply_text("Здравствуйте")


def echo_message(update, context):
    user_message = update.message.text
    update.message.reply_text(user_message)


def main():
    load_dotenv()
    bot_token = os.environ["TG_BOT_TOKEN"]
    
    updater = Updater(token=bot_token)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo_message))
    
    print("Бот запущен...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main() 