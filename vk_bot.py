import os
import random
import time

import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkEventType, VkLongPoll

from quiz_utils import WELCOME_MESSAGE, States
from quiz_utils import initialize_bot_environment, get_redis_keys
from quiz_utils import get_user_state, set_user_state
from quiz_utils import (process_give_up, process_new_question, 
                        process_score_request, process_solution_attempt)


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


def handle_start(vk, user_id, redis_client, keys):
    keyboard = create_keyboard()
    send_message(vk, user_id, WELCOME_MESSAGE, keyboard)
    set_user_state(redis_client, keys['state'], States.CHOOSING)


def handle_new_question(vk, user_id, redis_client, questions, keys):
    question = process_new_question(redis_client, keys, questions)
    keyboard = create_keyboard()
    send_message(vk, user_id, f"❓ {question}", keyboard)


def handle_solution_attempt(vk, user_id, message, redis_client, keys):
    is_correct, new_state = process_solution_attempt(redis_client, keys, message)
    keyboard = create_keyboard()
    
    if is_correct:
        send_message(vk, user_id, "Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»", keyboard)
    else:
        send_message(vk, user_id, "Неправильно… Попробуешь ещё раз?", keyboard)


def handle_give_up(vk, user_id, redis_client, questions, keys):
    clean_answer_text, question = process_give_up(redis_client, keys, questions)
    keyboard = create_keyboard()
    send_message(vk, user_id, f"✅ Правильный ответ: {clean_answer_text}", keyboard)
    send_message(vk, user_id, f"❓ {question}", keyboard)


def handle_score(vk, user_id, redis_client, keys):
    current_score, current_state = process_score_request(redis_client, keys)
    keyboard = create_keyboard()
    send_message(vk, user_id, f"📊 Ваш счет: {current_score} правильных ответов", keyboard)


def handle_user_message(vk, user_id, message, redis_client, questions):
    keys = get_redis_keys(user_id)
    user_state = get_user_state(redis_client, keys['state'])
    
    if message.lower() in ['привет', 'hello', 'hi', 'start']:
        handle_start(vk, user_id, redis_client, keys)
        return
    
    if user_state != States.CHOOSING and user_state != States.ANSWERING:
        handle_start(vk, user_id, redis_client, keys)
        return
    
    if message == '📊 Мой счет':
        handle_score(vk, user_id, redis_client, keys)
        return
    
    if message == '🆕 Новый вопрос':
        handle_new_question(vk, user_id, redis_client, questions, keys)
        return
    
    if user_state == States.CHOOSING:
        handle_start(vk, user_id, redis_client, keys)
        return
    
    if user_state == States.ANSWERING and message == '🏳️ Сдаться':
        handle_give_up(vk, user_id, redis_client, questions, keys)
        return
    
    if user_state == States.ANSWERING:
        handle_solution_attempt(vk, user_id, message, redis_client, keys)
        return


def main():
    vk_token = os.environ["VK_GROUP_TOKEN"]
    redis_client, questions = initialize_bot_environment()
    
    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()
    
    longpoll = VkLongPoll(vk_session)
    
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    user_id = event.user_id
                    message = event.text.strip()
                    
                    handle_user_message(vk, user_id, message, redis_client, questions)
        except Exception as e:
            time.sleep(5)


if __name__ == "__main__":
    main() 