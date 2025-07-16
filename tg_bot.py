import os
import time
import redis
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
from quiz_utils import (
    States, 
    WELCOME_MESSAGE, 
    get_random_question, 
    clean_answer, 
    check_answer,
    get_current_question_data,
    get_redis_keys,
    save_question_to_redis,
    get_user_score,
    increment_user_score,
    clear_user_data,
    get_user_state,
    set_user_state
)


def create_keyboard():
    keyboard = [
        [KeyboardButton("🆕 Новый вопрос"), KeyboardButton("🏳️ Сдаться")],
        [KeyboardButton("📊 Мой счет"), KeyboardButton("🔄 Начать заново")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_user_context(update, context):
    user_id = update.effective_user.id
    redis_client = context.bot_data['redis_client']
    keys = get_redis_keys(user_id)
    quiz_data_path = os.getenv("QUIZ_DATA_PATH", "quiz-json")
    
    return user_id, redis_client, keys, quiz_data_path


def load_and_send_question(update, redis_client, user_key, quiz_data_path):
    question, answer = get_random_question(quiz_data_path)
    save_question_to_redis(redis_client, user_key, question, answer)
    update.message.reply_text(f"❓ {question}")


def start(update, context):
    user_id = update.effective_user.id
    redis_client = context.bot_data['redis_client']
    
    reply_markup = create_keyboard()
    update.message.reply_text(WELCOME_MESSAGE, reply_markup=reply_markup)
    set_user_state(redis_client, user_id, States.CHOOSING)
    return States.CHOOSING


def handle_new_question_request(update, context):
    user_id, redis_client, keys, quiz_data_path = get_user_context(update, context)
    
    load_and_send_question(update, redis_client, keys['question'], quiz_data_path)
    set_user_state(redis_client, user_id, States.ANSWERING)
    return States.ANSWERING


def handle_solution_attempt(update, context):
    user_id, redis_client, keys, quiz_data_path = get_user_context(update, context)
    
    question_data = get_current_question_data(redis_client, keys['question'])
    correct_answer = question_data['answer']
    user_answer = update.message.text
    
    if check_answer(user_answer, correct_answer):
        increment_user_score(redis_client, user_id)
        update.message.reply_text("Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»")
        redis_client.delete(keys['question'])
        set_user_state(redis_client, user_id, States.CHOOSING)
        return States.CHOOSING
    else:
        update.message.reply_text("Неправильно… Попробуешь ещё раз?")
        return States.ANSWERING


def handle_give_up(update, context):
    user_id, redis_client, keys, quiz_data_path = get_user_context(update, context)
    
    question_data = get_current_question_data(redis_client, keys['question'])
    answer = question_data['answer']
    
    clean_answer_text = clean_answer(answer)
    update.message.reply_text(f"✅ Правильный ответ: {clean_answer_text}")
    
    load_and_send_question(update, redis_client, keys['question'], quiz_data_path)
    set_user_state(redis_client, user_id, States.ANSWERING)
    return States.ANSWERING


def handle_score(update, context):
    user_id, redis_client, keys, quiz_data_path = get_user_context(update, context)
    current_score = get_user_score(redis_client, user_id)
    update.message.reply_text(f"📊 Ваш счет: {current_score} правильных ответов")
    
    current_state = get_user_state(redis_client, user_id)
    return current_state


def handle_restart(update, context):
    user_id, redis_client, keys, quiz_data_path = get_user_context(update, context)
    clear_user_data(redis_client, user_id)
    return start(update, context)


def run_bot():
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
                MessageHandler(Filters.regex("^📊 Мой счет$"), handle_score),
                MessageHandler(Filters.regex("^🔄 Начать заново$"), handle_restart),
                MessageHandler(Filters.text & ~Filters.command, handle_solution_attempt),
            ],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    
    dispatcher.add_handler(conversation_handler)
    
    updater.start_polling()
    updater.idle()


def main():
    while True:
        try:
            run_bot()
        except Exception as e:
            time.sleep(5)


if __name__ == "__main__":
    main() 