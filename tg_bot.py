import os
import time

from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

from quiz_utils import (WELCOME_MESSAGE, States, get_current_question,
                        get_redis_keys, get_user_state, initialize_bot_environment,
                        process_give_up, process_new_question, process_score_request,
                        process_solution_attempt, set_user_state)


def create_keyboard():
    keyboard = [
        [KeyboardButton("🆕 Новый вопрос"), KeyboardButton("🏳️ Сдаться")],
        [KeyboardButton("📊 Мой счет")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_user_context(update, context):
    user_id = update.effective_user.id
    redis_client = context.bot_data['redis_client']
    keys = get_redis_keys(user_id)
    questions = context.bot_data['questions']
    
    return user_id, redis_client, keys, questions


def smart_entry_handler(update, context):
    user_id, redis_client, keys, questions = get_user_context(update, context)
    
    current_state = get_user_state(redis_client, keys['state'])
    
    if current_state == States.ANSWERING:
        question_data = get_current_question(redis_client, keys['question'])
        if question_data:
            reply_markup = create_keyboard()
            update.message.reply_text(
                f"🔄 Добро пожаловать обратно!\n\n❓ {question_data['question']}", 
                reply_markup=reply_markup
            )
            return States.ANSWERING
    
    reply_markup = create_keyboard()
    update.message.reply_text(WELCOME_MESSAGE, reply_markup=reply_markup)
    set_user_state(redis_client, keys['state'], States.CHOOSING)
    return States.CHOOSING


def handle_new_question_request(update, context):
    user_id, redis_client, keys, questions = get_user_context(update, context)
    
    question = process_new_question(redis_client, keys, questions)
    update.message.reply_text(f"❓ {question}")
    return States.ANSWERING


def handle_solution_attempt(update, context):
    user_id, redis_client, keys, questions = get_user_context(update, context)
    
    user_answer = update.message.text
    is_correct, new_state = process_solution_attempt(redis_client, keys, user_answer)
    
    if is_correct:
        update.message.reply_text("Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»")
        return new_state
    else:
        update.message.reply_text("Неправильно… Попробуешь ещё раз?")
        return new_state


def handle_give_up(update, context):
    user_id, redis_client, keys, questions = get_user_context(update, context)
    
    clean_answer_text, question = process_give_up(redis_client, keys, questions)
    
    update.message.reply_text(f"✅ Правильный ответ: {clean_answer_text}")
    update.message.reply_text(f"❓ {question}")
    return States.ANSWERING


def handle_score(update, context):
    user_id, redis_client, keys, questions = get_user_context(update, context)
    
    current_score, current_state = process_score_request(redis_client, keys)
    update.message.reply_text(f"📊 Ваш счет: {current_score} правильных ответов")
    
    return current_state


def handle_fallback(update, context):
    user_id, redis_client, keys, questions = get_user_context(update, context)
    
    current_state = get_user_state(redis_client, keys['state'])
    
    if current_state == States.ANSWERING:
        question_data = get_current_question(redis_client, keys['question'])
        if question_data:
            reply_markup = create_keyboard()
            update.message.reply_text(
                f"❓ {question_data['question']}\n\n💡 Используйте кнопки для управления ботом", 
                reply_markup=reply_markup
            )
            return States.ANSWERING
    
    reply_markup = create_keyboard()
    update.message.reply_text(
        "💡 Используйте кнопки для управления ботом",
        reply_markup=reply_markup
    )
    set_user_state(redis_client, keys['state'], States.CHOOSING)
    return States.CHOOSING


def main():
    bot_token = os.environ["TG_BOT_TOKEN"]
    redis_client, questions = initialize_bot_environment()
    
    updater = Updater(token=bot_token)
    dispatcher = updater.dispatcher
    
    dispatcher.bot_data['redis_client'] = redis_client
    dispatcher.bot_data['questions'] = questions
    
    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", smart_entry_handler),
            MessageHandler(Filters.all, smart_entry_handler)
        ],
        states={
            States.CHOOSING: [
                MessageHandler(Filters.regex("^🆕 Новый вопрос$"), handle_new_question_request),
                MessageHandler(Filters.regex("^📊 Мой счет$"), handle_score),
            ],
            States.ANSWERING: [
                MessageHandler(Filters.regex("^🏳️ Сдаться$"), handle_give_up),
                MessageHandler(Filters.regex("^📊 Мой счет$"), handle_score),
                MessageHandler(Filters.text & ~Filters.command, handle_solution_attempt),
            ],
        },
        fallbacks=[
            CommandHandler("start", smart_entry_handler),
            MessageHandler(Filters.all, handle_fallback)
        ]
    )
    
    dispatcher.add_handler(conversation_handler)
    
    while True:
        try:
            updater.start_polling()
            updater.idle()
        except Exception as e:
            time.sleep(5)


if __name__ == "__main__":
    main() 