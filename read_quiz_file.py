from pathlib import Path


def read_koi8r_file(file_path):
    with open(file_path, 'r', encoding='koi8-r') as file:
        return file.read()


def main():
    file_name = "120br.txt"
    file_path = Path("quiz-questions") / file_name
    content = read_koi8r_file(file_path)
    print(content)


if __name__ == "__main__":
    main() 