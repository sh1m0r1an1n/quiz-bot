import os
import random
import time

import redis
import vk_api
from dotenv import load_dotenv
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from quiz_utils import (
    States, WELCOME_MESSAGE, get_random_question, clean_answer, check_answer,
    get_current_question_data, get_redis_keys, save_question_to_redis,
    get_user_score, increment_user_score, get_user_state, set_user_state
)


def create_keyboard():
    keyboard = VkKeyboard(one_time=True)
    
    keyboard.add_button('🆕 Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('🏳️ Сдаться', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('📊 Мой счет', color=VkKeyboardColor.SECONDARY)
    
    return keyboard.get_keyboard()


def send_message(vk, user_id, message, keyboard=None):
    vk.messages.send(
        user_id=user_id,
        message=message,
        random_id=random.randint(1, 10000),
        keyboard=keyboard
    )


def load_and_send_question(vk, user_id, redis_client, user_key, quiz_data_path):
    question, answer = get_random_question(quiz_data_path)
    save_question_to_redis(redis_client, user_key, question, answer)
    keyboard = create_keyboard()
    send_message(vk, user_id, f"❓ {question}", keyboard)


def handle_start(vk, user_id, redis_client):
    keyboard = create_keyboard()
    send_message(vk, user_id, WELCOME_MESSAGE, keyboard)
    set_user_state(redis_client, user_id, States.CHOOSING)


def handle_new_question(vk, user_id, redis_client, quiz_data_path):
    keys = get_redis_keys(user_id)
    
    load_and_send_question(vk, user_id, redis_client, keys['question'], quiz_data_path)
    set_user_state(redis_client, user_id, States.ANSWERING)


def handle_solution_attempt(vk, user_id, message, redis_client):
    keys = get_redis_keys(user_id)
    
    question_data = get_current_question_data(redis_client, keys['question'])
    correct_answer = question_data['answer']
    
    if check_answer(message, correct_answer):
        increment_user_score(redis_client, user_id)
        keyboard = create_keyboard()
        send_message(vk, user_id, "Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»", keyboard)
        redis_client.delete(keys['question'])
        set_user_state(redis_client, user_id, States.CHOOSING)
    else:
        keyboard = create_keyboard()
        send_message(vk, user_id, "Неправильно… Попробуешь ещё раз?", keyboard)


def handle_give_up(vk, user_id, redis_client, quiz_data_path):
    keys = get_redis_keys(user_id)
    
    question_data = get_current_question_data(redis_client, keys['question'])
    answer = question_data['answer']
    clean_answer_text = clean_answer(answer)
    keyboard = create_keyboard()
    send_message(vk, user_id, f"✅ Правильный ответ: {clean_answer_text}", keyboard)
    
    load_and_send_question(vk, user_id, redis_client, keys['question'], quiz_data_path)
    set_user_state(redis_client, user_id, States.ANSWERING)


def handle_score(vk, user_id, redis_client):
    current_score = get_user_score(redis_client, user_id)
    keyboard = create_keyboard()
    send_message(vk, user_id, f"📊 Ваш счет: {current_score} правильных ответов", keyboard)


def run_bot():
    load_dotenv()
    
    vk_token = os.environ["VK_GROUP_TOKEN"]
    redis_url = os.environ["REDIS_URL"]
    quiz_data_path = os.environ["QUIZ_DATA_PATH"]
    
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()
    
    longpoll = VkLongPoll(vk_session)
    
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            message = event.text.strip()
            
            user_state = get_user_state(redis_client, user_id)
            
            if message.lower() in ['привет', 'hello', 'hi', 'start']:
                handle_start(vk, user_id, redis_client)
            elif user_state == States.CHOOSING:
                if message == '🆕 Новый вопрос':
                    handle_new_question(vk, user_id, redis_client, quiz_data_path)
                elif message == '📊 Мой счет':
                    handle_score(vk, user_id, redis_client)
                else:
                    handle_start(vk, user_id, redis_client)
            elif user_state == States.ANSWERING:
                if message == '🏳️ Сдаться':
                    handle_give_up(vk, user_id, redis_client, quiz_data_path)
                elif message == '📊 Мой счет':
                    handle_score(vk, user_id, redis_client)
                elif message == '🆕 Новый вопрос':
                    handle_new_question(vk, user_id, redis_client, quiz_data_path)
                else:
                    handle_solution_attempt(vk, user_id, message, redis_client)


if __name__ == "__main__":
    while True:
        try:
            run_bot()
        except Exception as e:
            time.sleep(5) 