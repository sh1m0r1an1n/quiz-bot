import json
import re
from pathlib import Path


def read_koi8r_file(file_path):
    """Читает файл с кодировкой KOI8-R."""
    with open(file_path, 'r', encoding='koi8-r') as file:
        return file.read()


def clean_text(text):
    """Очищает текст от лишних пробелов и переносов."""
    return re.sub(r'\s+', ' ', text.strip())


def parse_questions_and_answers(file_content):
    """Парсит содержимое файла и извлекает пары вопрос-ответ."""
    questions_and_answers = {}
    all_lines = file_content.split('\n')
    
    question_line_numbers = []
    for line_number, line in enumerate(all_lines):
        if re.match(r'^Вопрос\s+\d+:', line.strip()):
            question_line_numbers.append(line_number)
    
    for question_index, current_question_line in enumerate(question_line_numbers):
        next_question_line = question_line_numbers[question_index + 1] if question_index + 1 < len(question_line_numbers) else len(all_lines)
        current_question_block = all_lines[current_question_line:next_question_line]
        
        answer_line_index = None
        for block_line_index, block_line in enumerate(current_question_block):
            if block_line.strip() == 'Ответ:':
                answer_line_index = block_line_index
                break
        
        if answer_line_index is None:
            continue
        
        question_text_lines = current_question_block[1:answer_line_index]
        clean_question_text = '\n'.join(line for line in question_text_lines if line.strip())
        clean_question_text = clean_text(clean_question_text)
        
        answer_text_lines = []
        for block_line in current_question_block[answer_line_index + 1:]:
            if block_line.strip().startswith(('Комментарий:', 'Источник:', 'Автор:', 'Зачет:')):
                break
            if block_line.strip():
                answer_text_lines.append(block_line)
        
        clean_answer_text = '\n'.join(answer_text_lines)
        clean_answer_text = clean_text(clean_answer_text)
        
        if clean_question_text and clean_answer_text:
            questions_and_answers[clean_question_text] = clean_answer_text
    
    return questions_and_answers


def save_json_file(questions_dict, output_file_path):
    """Сохраняет словарь вопросов-ответов в JSON файл."""
    with open(output_file_path, 'w', encoding='utf-8') as file:
        json.dump(questions_dict, file, ensure_ascii=False, indent=2)


def process_single_txt_file(input_txt_file, output_json_directory):
    """Обрабатывает один txt файл и сохраняет результат в JSON."""
    file_content = read_koi8r_file(input_txt_file)
    parsed_questions = parse_questions_and_answers(file_content)
    
    output_json_filename = input_txt_file.stem + '.json'
    output_json_path = output_json_directory / output_json_filename
    
    save_json_file(parsed_questions, output_json_path)
    return len(parsed_questions)


def main():
    """Основная функция программы."""
    quiz_questions_directory = Path("quiz-questions")
    quiz_json_directory = Path("quiz-json")
    quiz_json_directory.mkdir(exist_ok=True)
    
    all_txt_files = list(quiz_questions_directory.glob("*.txt"))
    print(f"Найдено файлов для обработки: {len(all_txt_files)}")
    
    total_questions_processed = 0
    files_processed = 0
    
    for txt_file in all_txt_files:
        questions_count = process_single_txt_file(txt_file, quiz_json_directory)
        total_questions_processed += questions_count
        files_processed += 1
    
    print(f"Обработано файлов: {files_processed}, вопросов: {total_questions_processed}")


if __name__ == "__main__":
    main() 