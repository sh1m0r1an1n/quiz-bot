from enum import Enum
import json
from pathlib import Path
import random


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