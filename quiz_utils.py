import json
import random
from enum import Enum
from pathlib import Path


class States(Enum):
    CHOOSING = 1
    ANSWERING = 2


WELCOME_MESSAGE = (
    "🎯 Добро пожаловать в игру «Викторина»!\n\n"
    "Я задам вам вопросы из различных областей знаний. "
    "Попробуйте ответить правильно!\n\n"
    "Управление:\n"
    "🆕 Новый вопрос — получить случайный вопрос\n"
    "🏳️ Сдаться — показать правильный ответ\n"
    "📊 Мой счет — посмотреть статистику\n\n"
    "Нажмите «Новый вопрос» для начала!"
)


def get_random_question(quiz_directory_path):
    quiz_directory = Path(quiz_directory_path)
    json_files = list(quiz_directory.glob("*.json"))
    
    question_file = random.choice(json_files)
    
    with open(question_file, 'r', encoding='utf-8') as file:
        questions = json.load(file)
    
    random_question = random.choice(list(questions.keys()))
    answer = questions[random_question]
    
    return random_question, answer


def clean_answer(answer):
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


def get_current_question_data(redis_client, user_key):
    stored_json = redis_client.get(user_key)
    return json.loads(stored_json)


def get_redis_keys(user_id):
    return {
        'question': f"user:{user_id}:current_question",
        'state': f"user:{user_id}:state",
        'score': f"user:{user_id}:score"
    }


def save_question_to_redis(redis_client, user_key, question, answer):
    question_entry = {
        "question": question,
        "answer": answer
    }
    redis_client.set(user_key, json.dumps(question_entry, ensure_ascii=False))


def get_user_score(redis_client, user_id):
    keys = get_redis_keys(user_id)
    return int(redis_client.get(keys['score']) or 0)


def increment_user_score(redis_client, user_id):
    keys = get_redis_keys(user_id)
    current_score = get_user_score(redis_client, user_id)
    redis_client.set(keys['score'], current_score + 1)


def clear_user_data(redis_client, user_id):
    keys = get_redis_keys(user_id)
    redis_client.delete(keys['question'])
    redis_client.delete(keys['state'])
    redis_client.delete(keys['score'])


def get_user_state(redis_client, user_id):
    keys = get_redis_keys(user_id)
    state = redis_client.get(keys['state'])
    if state:
        return States(int(state))
    return States.CHOOSING


def set_user_state(redis_client, user_id, state):
    keys = get_redis_keys(user_id)
    redis_client.set(keys['state'], state.value) 