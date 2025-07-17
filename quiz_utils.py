import json
import os
from pathlib import Path
import random
from enum import Enum

from dotenv import load_dotenv
import redis


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


def load_all_questions(quiz_directory_path):
    quiz_directory = Path(quiz_directory_path)
    json_files = list(quiz_directory.glob("*.json"))
    
    all_questions = {}
    
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as file:
            questions = json.load(file)
            all_questions.update(questions)
    
    return all_questions


def get_random_question(questions_dict):
    random_question = random.choice(list(questions_dict.keys()))
    answer = questions_dict[random_question]
    
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


def get_current_question(redis_client, question_key):
    stored_json = redis_client.get(question_key)
    return json.loads(stored_json)


def get_redis_keys(user_id):
    return {
        'question': f"user:{user_id}:current_question",
        'state': f"user:{user_id}:state",
        'score': f"user:{user_id}:score"
    }


def save_question_to_redis(redis_client, question_key, question, answer):
    question_entry = {
        "question": question,
        "answer": answer
    }
    redis_client.set(question_key, json.dumps(question_entry, ensure_ascii=False))
    return question_entry


def get_user_score(redis_client, score_key):
    return int(redis_client.get(score_key) or 0)


def increment_user_score(redis_client, score_key, current_score):
    new_score = current_score + 1
    redis_client.set(score_key, new_score)
    return new_score


def get_user_state(redis_client, state_key):
    state = redis_client.get(state_key)
    if state:
        return States(int(state))
    return States.CHOOSING


def set_user_state(redis_client, state_key, state):
    redis_client.set(state_key, state.value)
    return state


def initialize_bot_environment():
    load_dotenv()
    redis_url = os.environ["REDIS_URL"]
    quiz_data_path = os.environ["QUIZ_DATA_PATH"]
    
    redis_client = redis.from_url(redis_url, decode_responses=True)
    questions_dict = load_all_questions(quiz_data_path)
    
    return redis_client, questions_dict


def process_new_question(redis_client, keys, questions_dict):
    question, answer = get_random_question(questions_dict)
    save_question_to_redis(redis_client, keys['question'], question, answer)
    set_user_state(redis_client, keys['state'], States.ANSWERING)
    return question


def process_solution_attempt(redis_client, keys, user_answer):
    question_data = get_current_question(redis_client, keys['question'])
    correct_answer = question_data['answer']
    is_correct = check_answer(user_answer, correct_answer)
    
    if is_correct:
        current_score = get_user_score(redis_client, keys['score'])
        increment_user_score(redis_client, keys['score'], current_score)
        redis_client.delete(keys['question'])
        set_user_state(redis_client, keys['state'], States.CHOOSING)
        return True, States.CHOOSING
    else:
        return False, States.ANSWERING


def process_give_up(redis_client, keys, questions_dict):
    question_data = get_current_question(redis_client, keys['question'])
    answer = question_data['answer']
    clean_answer_text = clean_answer(answer)
    
    question, answer = get_random_question(questions_dict)
    save_question_to_redis(redis_client, keys['question'], question, answer)
    set_user_state(redis_client, keys['state'], States.ANSWERING)
    
    return clean_answer_text, question


def process_score_request(redis_client, keys):
    current_score = get_user_score(redis_client, keys['score'])
    current_state = get_user_state(redis_client, keys['state'])
    return current_score, current_state 