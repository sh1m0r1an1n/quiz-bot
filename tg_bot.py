import os
import time

from dotenv import load_dotenv
import redis
from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

from quiz_utils import (WELCOME_MESSAGE, States, check_answer, clean_answer,
                        get_current_question, get_random_question,
                        get_redis_keys, get_user_score, get_user_state,
                        increment_user_score, load_all_questions,
                        save_question_to_redis, set_user_state)


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
    questions_dict = context.bot_data['questions_dict']
    
    return user_id, redis_client, keys, questions_dict


def smart_entry_handler(update, context):
    user_id, redis_client, keys, questions_dict = get_user_context(update, context)
    
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
    user_id, redis_client, keys, questions_dict = get_user_context(update, context)
    
    question, answer = get_random_question(questions_dict)
    save_question_to_redis(redis_client, keys['question'], question, answer)
    update.message.reply_text(f"❓ {question}")
    set_user_state(redis_client, keys['state'], States.ANSWERING)
    return States.ANSWERING


def handle_solution_attempt(update, context):
    user_id, redis_client, keys, questions_dict = get_user_context(update, context)
    
    question_data = get_current_question(redis_client, keys['question'])
    correct_answer = question_data['answer']
    user_answer = update.message.text
    
    is_correct = check_answer(user_answer, correct_answer)
    
    if is_correct:
        current_score = get_user_score(redis_client, keys['score'])
        increment_user_score(redis_client, keys['score'], current_score)
        update.message.reply_text("Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»")
        redis_client.delete(keys['question'])
        set_user_state(redis_client, keys['state'], States.CHOOSING)
        return States.CHOOSING
    else:
        update.message.reply_text("Неправильно… Попробуешь ещё раз?")
        return States.ANSWERING


def handle_give_up(update, context):
    user_id, redis_client, keys, questions_dict = get_user_context(update, context)
    
    question_data = get_current_question(redis_client, keys['question'])
    answer = question_data['answer']
    
    clean_answer_text = clean_answer(answer)
    update.message.reply_text(f"✅ Правильный ответ: {clean_answer_text}")
    
    question, answer = get_random_question(questions_dict)
    save_question_to_redis(redis_client, keys['question'], question, answer)
    update.message.reply_text(f"❓ {question}")
    set_user_state(redis_client, keys['state'], States.ANSWERING)
    return States.ANSWERING


def handle_score(update, context):
    user_id, redis_client, keys, questions_dict = get_user_context(update, context)
    
    current_score = get_user_score(redis_client, keys['score'])
    update.message.reply_text(f"📊 Ваш счет: {current_score} правильных ответов")
    
    current_state = get_user_state(redis_client, keys['state'])
    return current_state


def handle_fallback(update, context):
    user_id, redis_client, keys, questions_dict = get_user_context(update, context)
    
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
    load_dotenv()
    bot_token = os.environ["TG_BOT_TOKEN"]
    redis_url = os.environ["REDIS_URL"]
    quiz_data_path = os.environ["QUIZ_DATA_PATH"]
    
    redis_client = redis.from_url(redis_url, decode_responses=True)
    questions_dict = load_all_questions(quiz_data_path)
    
    updater = Updater(token=bot_token)
    dispatcher = updater.dispatcher
    
    dispatcher.bot_data['redis_client'] = redis_client
    dispatcher.bot_data['questions_dict'] = questions_dict
    
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