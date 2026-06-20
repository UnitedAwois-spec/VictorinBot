from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random
import os
import threading
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.environ.get("BOT_TOKEN")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")


def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def get_db():
    conn = sqlite3.connect("quiz.db")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            score INTEGER,
            question INTEGER,
            total_games INTEGER DEFAULT 0,
            best_score INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def get_or_create_user(user_id, name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute(
            "INSERT INTO users (user_id, name, score, question, total_games, best_score) VALUES (?, ?, 0, 0, 0, 0)",
            (user_id, name)
        )
        conn.commit()
    conn.close()


def update_progress(user_id, score, question):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET score = ?, question = ? WHERE user_id = ?",
        (score, question, user_id)
    )
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT score, question, name, total_games, best_score FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"score": row[0], "question": row[1], "name": row[2], "total_games": row[3], "best_score": row[4]}
    return None


def finish_game(user_id, final_score):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT best_score, total_games FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    best = max(row[0], final_score)
    games = row[1] + 1
    cursor.execute(
        "UPDATE users SET best_score = ?, total_games = ?, score = 0, question = 0 WHERE user_id = ?",
        (best, games, user_id)
    )
    conn.commit()
    conn.close()


def get_top_players(limit=10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, best_score FROM users ORDER BY best_score DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


ALL_QUESTIONS = [
    {"q": "Что означает CPU?", "o": ["Центральный процессор", "Видеокарта", "Память", "Монитор"], "a": 0, "cat": "IT"},
    {"q": "Сколько бит в байте?", "o": ["4", "8", "16", "32"], "a": 1, "cat": "IT"},
    {"q": "Что такое RAM?", "o": ["Процессор", "Видеокарта", "Оперативная память", "Диск"], "a": 2, "cat": "IT"},
    {"q": "Какой язык для внешнего вида сайтов?", "o": ["Python", "SQL", "CSS", "Java"], "a": 2, "cat": "IT"},
    {"q": "Что делает print() в Python?", "o": ["Печатает", "Выводит на экран", "Создаёт файл", "Удаляет"], "a": 1, "cat": "IT"},
    {"q": "Что такое баг?", "o": ["Функция", "Ошибка в коде", "Тип данных", "Команда"], "a": 1, "cat": "IT"},
    {"q": "Какой язык чаще для AI?", "o": ["HTML", "CSS", "Python", "SQL"], "a": 2, "cat": "IT"},
    {"q": "Что такое алгоритм?", "o": ["Язык", "Компьютер", "Пошаговая инструкция", "База данных"], "a": 2, "cat": "IT"},
    {"q": "Расшифруй HTTP", "o": ["HyperText Transfer Protocol", "High Tech Transfer Protocol", "Home Tool Transfer", "Hyper Tool Text"], "a": 0, "cat": "IT"},
    {"q": "Что такое IP-адрес?", "o": ["Название сайта", "Адрес устройства в сети", "Тип кабеля", "Браузер"], "a": 1, "cat": "IT"},
    {"q": "Что делает Google Chrome?", "o": ["Редактор кода", "Браузер", "Операционная система", "Антивирус"], "a": 1, "cat": "IT"},
    {"q": "Что такое HTML?", "o": ["Язык разметки страниц", "Язык программирования", "База данных", "Операционная система"], "a": 0, "cat": "IT"},
    {"q": "Что такое SQL?", "o": ["Язык для работы с базами данных", "Язык для сайтов", "Операционная система", "Браузер"], "a": 0, "cat": "IT"},
    {"q": "Кто создал Python?", "o": ["Билл Гейтс", "Гвидо ван Россум", "Стив Джобс", "Линус Торвальдс"], "a": 1, "cat": "IT"},
    {"q": "Что такое Git?", "o": ["Браузер", "Система контроля версий кода", "База данных", "Язык программирования"], "a": 1, "cat": "IT"},
    {"q": "Что такое API?", "o": ["Тип компьютера", "Интерфейс для общения программ", "Браузер", "База данных"], "a": 1, "cat": "IT"},
    {"q": "Что такое VPN?", "o": ["Браузер", "Антивирус", "Защищённое соединение", "Поисковик"], "a": 2, "cat": "IT"},
    {"q": "Какая компания сделала Android?", "o": ["Apple", "Microsoft", "Google", "Samsung"], "a": 2, "cat": "IT"},
    {"q": "Что такое open source?", "o": ["Платный софт", "Программы с открытым кодом", "Операционная система", "Браузер"], "a": 1, "cat": "IT"},
    {"q": "Что такое SSD?", "o": ["Оперативная память", "Быстрый тип накопителя", "Видеокарта", "Процессор"], "a": 1, "cat": "IT"},
    {"q": "Что такое JavaScript?", "o": ["Язык для интерактивности сайтов", "База данных", "Операционная система", "Антивирус"], "a": 0, "cat": "IT"},
    {"q": "Что означает URL?", "o": ["Адрес страницы в интернете", "Тип файла", "Браузер", "Протокол"], "a": 0, "cat": "IT"},
    {"q": "Что такое облачное хранилище?", "o": ["Флешка", "Хранение данных на удалённых серверах", "Жёсткий диск", "Оперативная память"], "a": 1, "cat": "IT"},
    {"q": "Какой символ начинает комментарий в Python?", "o": ["//", "/*", "#", "--"], "a": 2, "cat": "IT"},
    {"q": "Что такое loop (цикл)?", "o": ["Ошибка", "Повторение действий", "Функция", "Переменная"], "a": 1, "cat": "IT"},
    {"q": "Что такое переменная в программировании?", "o": ["Команда", "Контейнер для данных", "Ошибка", "Цикл"], "a": 1, "cat": "IT"},
    {"q": "Что делает функция в коде?", "o": ["Хранит данные", "Выполняет набор команд", "Создаёт ошибку", "Удаляет файлы"], "a": 1, "cat": "IT"},
    {"q": "Что такое if/else?", "o": ["Цикл", "Условие — если/иначе", "Функция", "Переменная"], "a": 1, "cat": "IT"},
    {"q": "Что означает Wi-Fi?", "o": ["Wireless Fidelity", "Wide Fidelity", "Wire First", "Просто бренд"], "a": 3, "cat": "IT"},
    {"q": "Что такое Telegram Bot API?", "o": ["Браузер", "Интерфейс для создания ботов", "Антивирус", "Операционная система"], "a": 1, "cat": "IT"},
    {"q": "Что такое сервер?", "o": ["Мощный компьютер который обслуживает запросы", "Браузер", "Вид кабеля", "Антивирус"], "a": 0, "cat": "IT"},
    {"q": "Что такое хостинг?", "o": ["Браузер", "Место где хранится сайт/бот", "Антивирус", "Поисковик"], "a": 1, "cat": "IT"},
    {"q": "Какой из этих языков — язык разметки, а не программирования?", "o": ["Python", "Java", "HTML", "C++"], "a": 2, "cat": "IT"},
    {"q": "Сколько планет в Солнечной системе?", "o": ["7", "8", "9", "10"], "a": 1, "cat": "Общее"},
    {"q": "Столица Японии?", "o": ["Osaka", "Kyoto", "Tokyo", "Hiroshima"], "a": 2, "cat": "Общее"},
    {"q": "Сколько continents на Земле?", "o": ["5", "6", "7", "8"], "a": 2, "cat": "Общее"},
    {"q": "Самая длинная река в мире?", "o": ["Амазонка", "Нил", "Янцзы", "Миссисипи"], "a": 1, "cat": "Общее"},
    {"q": "Самая высокая гора в мире?", "o": ["К2", "Эверест", "Килиманджаро", "Эльбрус"], "a": 1, "cat": "Общее"},
    {"q": "Из скольки цветов состоит радуга?", "o": ["5", "6", "7", "8"], "a": 2, "cat": "Общее"},
    {"q": "Сколько часов в сутках?", "o": ["12", "24", "48", "36"], "a": 1, "cat": "Общее"},
    {"q": "Самый большой океан?", "o": ["Атлантический", "Индийский", "Тихий", "Северный Ледовитый"], "a": 2, "cat": "Общее"},
    {"q": "Столица России?", "o": ["Санкт-Петербург", "Казань", "Москва", "Новосибирск"], "a": 2, "cat": "Общее"},
    {"q": "Сколько минут в часе?", "o": ["30", "45", "60", "100"], "a": 2, "cat": "Общее"},
    {"q": "Какая планета ближайшая к Солнцу?", "o": ["Венера", "Земля", "Меркурий", "Марс"], "a": 2, "cat": "Общее"},
    {"q": "Из чего состоит вода?", "o": ["HO", "H2O", "CO2", "O2"], "a": 1, "cat": "Общее"},
    {"q": "Сколько дней в невисокосном году?", "o": ["364", "365", "366", "360"], "a": 1, "cat": "Общее"},
    {"q": "Самая большая страна по площади?", "o": ["США", "Китай", "Россия", "Канада"], "a": 2, "cat": "Общее"},
    {"q": "Скорость света примерно?", "o": ["100 000 км/с", "300 000 км/с", "500 000 км/с", "1 000 000 км/с"], "a": 1, "cat": "Общее"},
    {"q": "Сколько букв в русском алфавите?", "o": ["30", "31", "32", "33"], "a": 3, "cat": "Общее"},
    {"q": "Какой газ мы вдыхаем для жизни?", "o": ["CO2", "Азот", "Кислород", "Водород"], "a": 2, "cat": "Общее"},
    {"q": "Столица Франции?", "o": ["Лондон", "Берлин", "Рим", "Париж"], "a": 3, "cat": "Общее"},
    {"q": "Сколько сторон у треугольника?", "o": ["2", "3", "4", "5"], "a": 1, "cat": "Общее"},
    {"q": "Какое животное самое быстрое на суше?", "o": ["Лев", "Гепард", "Лошадь", "Страус"], "a": 1, "cat": "Общее"},
    {"q": "Сколько секунд в минуте?", "o": ["30", "45", "60", "100"], "a": 2, "cat": "Общее"},
    {"q": "Столица США?", "o": ["Нью-Йорк", "Лос-Анджелес", "Вашингтон", "Чикаго"], "a": 2, "cat": "Общее"},
    {"q": "Какой металл самый распространённый на Земле?", "o": ["Железо", "Золото", "Алюминий", "Медь"], "a": 2, "cat": "Общее"},
    {"q": "Сколько недель в году?", "o": ["48", "50", "52", "54"], "a": 2, "cat": "Общее"},
    {"q": "Самое большое животное на планете?", "o": ["Слон", "Жираф", "Синий кит", "Акула"], "a": 2, "cat": "Общее"},
    {"q": "Из чего сделан карандаш внутри?", "o": ["Свинец", "Уголь", "Графит", "Чернила"], "a": 2, "cat": "Общее"},
    {"q": "Сколько цветов у шахматной доски?", "o": ["1", "2", "3", "4"], "a": 1, "cat": "Общее"},
    {"q": "Столица Германии?", "o": ["Мюнхен", "Берлин", "Гамбург", "Франкфурт"], "a": 1, "cat": "Общее"},
    {"q": "Какая нота идёт после До?", "o": ["Ми", "Ре", "Фа", "Соль"], "a": 1, "cat": "Общее"},
    {"q": "Сколько игроков в футбольной команде на поле?", "o": ["9", "10", "11", "12"], "a": 2, "cat": "Общее"},
    {"q": "Какой орган перекачивает кровь?", "o": ["Мозг", "Лёгкие", "Сердце", "Печень"], "a": 2, "cat": "Общее"},
    {"q": "Самый холодный континент?", "o": ["Арктика", "Антарктида", "Северная Америка", "Азия"], "a": 1, "cat": "Общее"},
    {"q": "Сколько будет 15 × 15?", "o": ["175", "200", "225", "250"], "a": 2, "cat": "Математика"},
    {"q": "Квадратный корень из 144?", "o": ["10", "11", "12", "13"], "a": 2, "cat": "Математика"},
    {"q": "Сколько будет 2 в степени 10?", "o": ["512", "1024", "2048", "256"], "a": 1, "cat": "Математика"},
    {"q": "Простое число?", "o": ["4", "6", "9", "7"], "a": 3, "cat": "Математика"},
    {"q": "Сколько градусов в прямом угле?", "o": ["45", "90", "180", "360"], "a": 1, "cat": "Математика"},
    {"q": "Чему равно Пи (π) приближённо?", "o": ["3.14", "2.71", "1.41", "1.73"], "a": 0, "cat": "Математика"},
    {"q": "Сколько будет 100 ÷ 4?", "o": ["20", "25", "30", "40"], "a": 1, "cat": "Математика"},
    {"q": "Следующее простое число после 7?", "o": ["8", "9", "10", "11"], "a": 3, "cat": "Математика"},
    {"q": "Сколько будет 7 × 8?", "o": ["54", "56", "58", "60"], "a": 1, "cat": "Математика"},
    {"q": "Сколько градусов в круге?", "o": ["180", "270", "360", "90"], "a": 2, "cat": "Математика"},
    {"q": "Сколько будет 12²?", "o": ["124", "134", "144", "154"], "a": 2, "cat": "Математика"},
    {"q": "Что такое периметр?", "o": ["Площадь фигуры", "Сумма всех сторон", "Высота фигуры", "Объём"], "a": 1, "cat": "Математика"},
    {"q": "Сколько будет 1000 - 337?", "o": ["663", "673", "653", "643"], "a": 0, "cat": "Математика"},
    {"q": "Чему равна сумма углов треугольника?", "o": ["90°", "180°", "270°", "360°"], "a": 1, "cat": "Математика"},
    {"q": "Сколько будет 25% от 200?", "o": ["25", "40", "50", "75"], "a": 2, "cat": "Математика"},
    {"q": "Какое число не является натуральным?", "o": ["1", "5", "0", "100"], "a": 2, "cat": "Математика"},
    {"q": "Сколько будет 3³?", "o": ["9", "18", "27", "81"], "a": 2, "cat": "Математика"},
    {"q": "Сколько нулей в числе миллион?", "o": ["5", "6", "7", "8"], "a": 1, "cat": "Математика"},
    {"q": "Сколько будет 999 + 1?", "o": ["999", "1000", "1001", "1010"], "a": 1, "cat": "Математика"},
    {"q": "Площадь прямоугольника 5×8?", "o": ["30", "35", "40", "45"], "a": 2, "cat": "Математика"},
    {"q": "Что такое дробь 1/2 в процентах?", "o": ["25%", "40%", "50%", "75%"], "a": 2, "cat": "Математика"},
    {"q": "Сколько будет 6! (факториал)?", "o": ["120", "360", "720", "5040"], "a": 2, "cat": "Математика"},
    {"q": "Какое число чётное?", "o": ["7", "13", "17", "18"], "a": 3, "cat": "Математика"},
    {"q": "Сколько будет √256?", "o": ["14", "16", "18", "20"], "a": 1, "cat": "Математика"},
    {"q": "Сколько будет 15% от 300?", "o": ["35", "40", "45", "50"], "a": 2, "cat": "Математика"},
    {"q": "Как называется результат сложения?", "o": ["Разность", "Произведение", "Сумма", "Частное"], "a": 2, "cat": "Математика"},
    {"q": "Как называется результат умножения?", "o": ["Сумма", "Разность", "Произведение", "Частное"], "a": 2, "cat": "Математика"},
    {"q": "Сколько будет 2⁸?", "o": ["128", "256", "512", "64"], "a": 1, "cat": "Математика"},
    {"q": "Что меньше: 2/3 или 3/4?", "o": ["2/3", "3/4", "Они равны", "Нельзя сравнить"], "a": 0, "cat": "Математика"},
    {"q": "Сколько будет 1001 × 0?", "o": ["1001", "1", "0", "1000"], "a": 2, "cat": "Математика"},
    {"q": "Чему равен модуль числа -15?", "o": ["-15", "0", "15", "150"], "a": 2, "cat": "Математика"},
    {"q": "Сколько будет 50% от 50?", "o": ["10", "20", "25", "50"], "a": 2, "cat": "Математика"},
    {"q": "Как называется результат деления?", "o": ["Сумма", "Разность", "Произведение", "Частное"], "a": 3, "cat": "Математика"},
]


def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎮 Случайная (10 вопросов)", callback_data="mode_random")],
        [InlineKeyboardButton("💻 IT", callback_data="mode_it"),
         InlineKeyboardButton("🌍 Общее", callback_data="mode_general")],
        [InlineKeyboardButton("🔢 Математика", callback_data="mode_math")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats"),
         InlineKeyboardButton("🏆 Топ игроков", callback_data="show_leaderboard")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name

    get_or_create_user(user_id, name)

    await update.message.reply_text(
        f"👋 Привет, {name}!\n\n"
        f"🧠 <b>IT-Викторина</b>\n\n"
        f"📚 Вопросов в базе: {len(ALL_QUESTIONS)}\n"
        f"Выбери раздел:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back_to_menu":
        await query.edit_message_text(
            "🧠 <b>IT-Викторина</b>\n\nВыбери раздел:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        return

    if data == "my_stats":
        u = get_user(user_id)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]])
        await query.edit_message_text(
            f"📊 <b>Твоя статистика</b>\n\n"
            f"Игр сыграно: {u['total_games']}\n"
            f"Лучший результат: {u['best_score']}\n",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    if data == "show_leaderboard":
        top = get_top_players()
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]])
        if not top:
            await query.edit_message_text("🏆 Рейтинг пока пуст!", reply_markup=keyboard)
            return
        text = "🏆 <b>Топ игроков:</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (name, best) in enumerate(top):
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} {name} — {best}\n"
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        return

    if data.startswith("mode_"):
        if data == "mode_random":
            pool = ALL_QUESTIONS.copy()
            random.shuffle(pool)
            selected = pool[:10]
        elif data == "mode_it":
            selected = [q for q in ALL_QUESTIONS if q["cat"] == "IT"]
        elif data == "mode_general":
            selected = [q for q in ALL_QUESTIONS if q["cat"] == "Общее"]
        elif data == "mode_math":
            selected = [q for q in ALL_QUESTIONS if q["cat"] == "Математика"]

        context.user_data["questions"] = selected
        update_progress(user_id, 0, 0)

        await query.edit_message_text(f"🚀 Начинаем! Вопросов: {len(selected)}")
        await send_question(context, user_id)
        return

    if ":" in data:
        parts = data.split(":")
        q_index = int(parts[0])
        answer_index = int(parts[1])

        u = get_user(user_id)
        if u is None or u["question"] != q_index:
            return

        questions = context.user_data.get("questions")
        if questions is None:
            await query.edit_message_text("Сессия истекла. Напиши /start")
            return

        correct = questions[q_index]["a"]
        correct_text = questions[q_index]["o"][correct]
        new_score = u["score"]

        if answer_index == correct:
            new_score += 1
            await query.edit_message_text("✅ <b>Правильно!</b>", parse_mode="HTML")
        else:
            await query.edit_message_text(
                f"❌ <b>Неверно!</b>\nПравильный ответ: <b>{correct_text}</b>",
                parse_mode="HTML"
            )

        update_progress(user_id, new_score, q_index + 1)
        await send_question(context, user_id)


async def send_question(context, user_id):
    u = get_user(user_id)
    q_index = u["question"]
    questions = context.user_data.get("questions")

    if questions is None or q_index >= len(questions):
        final_score = u["score"]
        total = len(questions) if questions else 0
        finish_game(user_id, final_score)

        percent = final_score / total if total else 0
        if percent == 1.0:
            emoji, comment = "🏆", "Идеальный результат!"
        elif percent >= 0.7:
            emoji, comment = "🎯", "Отличный результат!"
        elif percent >= 0.4:
            emoji, comment = "📚", "Неплохо, есть куда расти!"
        else:
            emoji, comment = "💪", "Продолжай учиться!"

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu")]])
        await context.bot.send_message(
            chat_id=user_id,
            text=f"{emoji} <b>Готово!</b>\n\nРезультат: {final_score} из {total}\n{comment}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    q = questions[q_index]
    keyboard = []
    for i, option in enumerate(q["o"]):
        keyboard.append([InlineKeyboardButton(option, callback_data=f"{q_index}:{i}")])
    markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=f"<b>{q['cat']}</b> | Вопрос {q_index + 1}/{len(questions)}\n\n❓ {q['q']}",
        reply_markup=markup,
        parse_mode="HTML"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 /start — открыть меню\n/help — помощь",
    )


def main():
    init_db()
    threading.Thread(target=run_web_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(handle_button))

    print("Бот запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
