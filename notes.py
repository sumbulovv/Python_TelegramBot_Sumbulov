import re
import os
import os.path

NOTES_PATH = "notes"  # Путь к папке, где будут храниться заметки

# Создайте функцию, которая создает заметку по запросу пользователя
def build_note(note_text, note_name):
    # Проверьте, существует ли файл, название которого указывает пользователь.
    # Если нет, создайте новый файл. Если да, замените существующий файл на новый.
    try:
        try:
            file = open(f"{NOTES_PATH}/{note_name}.txt", "r+", encoding="utf-8")
            print("Такой файл существует")
        except IOError:
            file = open(f"{NOTES_PATH}/{note_name}.txt", "w+", encoding="utf-8")
            print("Файл создан")
        file.write(note_text)
        print(f"Заметка {note_name} создана.")
    except:
        print("Что-то пошло не так. Попробуйте еще раз.")


# Напишите функцию, которая запрашивает название и текст заметки, а затем создает ее
def create_note(note_name, note_text):
    # Создайте файл с заметкой
    try:
        # Запросите название заметки и проверьте его на наличие запрещенных символов
        forbidden_symbols = "\\|/*<>?:"  # набор запрещенных символов для Windows
        pattern = "[{0}]".format(forbidden_symbols)
        if re.search(pattern, note_name):
            return f"Вы ввели недопустимые символы в названии файла. Переименуйте заметку."
        # Запросите текст заметки и создайте заметку
        else:
            print("Название заметки создано.")
            build_note(note_text, note_name)
    except:
        return f"Что-то пошло не так. Попробуйте еще раз."


# Напишите функцию, которая прочитает заметку и выведет ее текст
def read_note(note_name):
    # Запросите у пользователя название заметки, которую он хочет вывести на экран
    try:
        path = f"{NOTES_PATH}/{note_name}.txt"
        # Выведите заметку, если она существует. Если такой заметки нет, сообщите об этом пользователю
        if os.path.isfile(path):
            with open(path, "r") as file:
                lines = file.read()
            return "Текст заметки: " + lines
        else:
            return "Такой заметки не существует. Введите другой запрос."
    except:
        return "Что-то пошло не так. Попробуйте еще раз."


# Напишите функцию, которая редактирует заметку
def edit_note(note_name, note_text):
    # Запросите у пользователя название заметки, которую он хочет отредактировать
    try:
        path = f"{NOTES_PATH}/{note_name}.txt"
        # Проверьте, есть ли такая заметка. Если да, обновите ее содержание. Если нет, сообщите об этом пользователю.
        if os.path.isfile(path):
            note_text_new = open(path, "w+")
            note_text_new.write(note_text)
            return f"Заметка {note_name} обновлена."
        else:
            return "Такой заметки не существует. Введите другой запрос."
    except:
        return "Что-то пошло не так. Попробуйте еще раз."


# Напишите функцию, которая удаляет заметку
def delete_note(note_name):
    # Запросите у пользователя название заметки, которую он хочет удалить
    try:
        path = f"{NOTES_PATH}/{note_name}.txt"
        # Проверьте, есть ли такая заметка. Если да, удалите ее. Если нет, сообщите об этом пользователю.
        if os.path.isfile(path):
            os.remove(path)
            return "Заметка удалена!"
        else:
            return "Такой заметки не существует. Введите другой запрос."
    except:
        return "Что-то пошло не так. Попробуйте еще раз."


# Напишите функцию, которая выведет все заметки пользователя в порядке от самой короткой до самой длинной
def display_notes():
    try:
        notes = [note for note in os.listdir(NOTES_PATH) if note.endswith(".txt")]
        sorted_notes = sorted(notes, key=len, reverse=True)
        return sorted_notes
    except:
        return "Что-то пошло не так. Попробуйте еще раз."


# Напишите функцию, которая выведет все заметки пользователя в порядке от самой длинной до самой короткой
def display_sorted_notes():
    try:
        notes = [note for note in os.listdir(NOTES_PATH) if note.endswith(".txt")]
        sorted_list = sorted(notes, key=len)
        return sorted_list
    except:
        return "Что-то пошло не так. Попробуйте еще раз."


# Создайте функцию, которая управляет всеми операциями с заметками
def main():
    # Создайте бесконечный цикл работы с заметками и настройте меню для пользователя
    while True:
        action = input(
            "Нажмите цифру, чтобы выбрать действие, которое хотите выполнить с заметками: "
            "\n"
            "Введите 1, чтобы создать заметку с определенным названием и текстом."
            "\n"
            "Введите 2, чтобы вывести на экран нужную вам заметку."
            "\n"
            "Введите 3, чтобы отредактировать нужную вам заметку."
            "\n"
            "Введите 4, чтобы удалить заметку."
            "\n"
            "Введите 5, чтобы вывести все заметки в порядке от самой короткой до самой длинной."
            "\n"
            "Введите 6, чтобы вывести все заметки в порядке от самой длинной до самой короткой."
            "\n"
            "Введите n, чтобы выйти из приложения."
            "\n"
            "Что вы хотите сделать?"
        ).lower()
        # Проверьте символ, который ввел пользователь. Если он некорректный, сообщите об этом.
        allowed_symbols = "123456n"
        pattern1 = "[{0}]".format(allowed_symbols)
        if re.search(pattern1, action):
            print("Вы ввели корректный запрос. Действие сейчас выполнится.")
            if action == "1":
                create_note()
            if action == "2":
                read_note()
            if action == "3":
                edit_note()
            if action == "4":
                delete_note()
            if action == "5":
                display_notes()
            if action == "6":
                display_sorted_notes()
            if action == "n":
                break
        else:
            print(
                "Вы ввели некорректный символ. Пожалуйста, введите цифры от 1 до 6 или n."
            )

        # Предложите пользователю продолжить работу с приложением
        print("Чтобы продолжить работать с заметками, нажмите y/n")
        answer = input().lower()
        if answer != "y":
            break
