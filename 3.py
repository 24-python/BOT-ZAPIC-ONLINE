import telebot
import sqlite3
from telebot import types
from datetime import datetime, timedelta

# Инициализация бота
TOKEN = '8095038946:AAF-j8fR2g1f_zkVlshE4eYvqIkgOFQUN10'
bot = telebot.TeleBot(TOKEN)

# Пример данных для хранения информации о мастерах и услугах
services = ['Мужская стрижка', 'Женская стрижка', 'Окрашивание']
masters = ['Вера', 'Надежда', 'Любовь']

# Админ-данные для входа
ADMIN_LOGIN = 'admin'
ADMIN_PASSWORD = 'admin'

# Словарь для хранения промежуточных данных о записи
user_appointments = {}


# Подключение к базе данных SQLite
def init_db():
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    # Создание таблицы users, если она не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY, 
                        username TEXT, 
                        full_name TEXT, 
                        is_admin INTEGER DEFAULT 0)''')  # Поле is_admin: 0 - пользователь, 1 - админ

    # Проверяем, есть ли колонка full_name (если таблица была создана ранее без этой колонки)
    try:
        cursor.execute('SELECT full_name FROM users LIMIT 1')
    except sqlite3.OperationalError:
        # Если колонки нет, добавляем ее
        cursor.execute('ALTER TABLE users ADD COLUMN full_name TEXT')

    # Создание таблицы appointments, если она не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        user_id INTEGER, 
                        service TEXT, 
                        master TEXT, 
                        date TEXT, 
                        time TEXT,
                        UNIQUE(user_id, date, time))''')

    conn.commit()
    conn.close()


# Добавление записи в базу данных
def add_appointment(user_id, service, master, date, time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''INSERT INTO appointments (user_id, service, master, date, time) 
                          VALUES (?, ?, ?, ?, ?)''', (user_id, service, master, date, time))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # Запись уже существует
        success = False

    conn.close()
    return success


# Получение списка записей для пользователя
def get_user_appointments(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT service, master, date, time FROM appointments WHERE user_id = ?''', (user_id,))
    appointments = cursor.fetchall()

    conn.close()
    return appointments


# Удаление записи
def delete_appointment(user_id, date, time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''DELETE FROM appointments WHERE user_id = ? AND date = ? AND time = ?''', (user_id, date, time))
    conn.commit()
    conn.close()


# Получение всех администраторов
def get_admins():
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT user_id FROM users WHERE is_admin = 1''')
    admins = cursor.fetchall()

    conn.close()
    return [admin[0] for admin in admins]


# Отправка уведомления администраторам
def notify_admins(message):
    admins = get_admins()
    for admin_id in admins:
        bot.send_message(admin_id, message)


# Проверка, является ли пользователь администратором
def is_admin(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT is_admin FROM users WHERE user_id = ?''', (user_id,))
    result = cursor.fetchone()

    conn.close()

    return result and result[0] == 1


# Назначение пользователя администратором
def set_admin(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''UPDATE users SET is_admin = 1 WHERE user_id = ?''', (user_id,))
    conn.commit()
    conn.close()


# Снятие прав администратора
def remove_admin(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''UPDATE users SET is_admin = 0 WHERE user_id = ?''', (user_id,))
    conn.commit()
    conn.close()


# Главное меню
def main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Записаться на стрижку')
    btn2 = types.KeyboardButton('Отменить запись')
    btn3 = types.KeyboardButton('Просмотреть записи')
    btn4 = types.KeyboardButton('Контакты')
    btn5 = types.KeyboardButton('Помощь')
    markup.add(btn1, btn2, btn3, btn4, btn5)

    if is_admin:
        btn_admin = types.KeyboardButton('Админ-панель')
        btn_exit_admin = types.KeyboardButton('Выйти из админ-режима')
        markup.add(btn_admin, btn_exit_admin)

    return markup


# Приветственное сообщение для новых пользователей с запросом имени
@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.chat.id
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    # Проверяем, есть ли пользователь в базе, если нет — добавляем
    cursor.execute('SELECT full_name FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()

    if user is None:
        # Запрашиваем у пользователя его имя
        msg = bot.send_message(user_id, "Добро пожаловать! Как вас зовут?")
        bot.register_next_step_handler(msg, save_user_name)
    else:
        full_name = user[0]
        bot.send_message(user_id, f"Добро пожаловать, {full_name}! Чем могу помочь?",
                         reply_markup=main_menu(is_admin(user_id)))

    conn.close()


# Сохранение имени пользователя и приветствие
def save_user_name(message):
    full_name = message.text
    user_id = message.chat.id

    # Сохраняем имя пользователя в базу данных
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''INSERT OR REPLACE INTO users (user_id, username, full_name) 
                      VALUES (?, ?, ?)''', (user_id, message.from_user.username, full_name))
    conn.commit()
    conn.close()

    # Приветственное сообщение
    bot.send_message(user_id, f"Приятно познакомиться, {full_name}! Чем могу помочь?",
                     reply_markup=main_menu(is_admin(user_id)))


# Админ режим - вход по логину/паролю
@bot.message_handler(commands=['admin'])
def admin_login(message):
    msg = bot.send_message(message.chat.id, "Введите логин:")
    bot.register_next_step_handler(msg, process_admin_login)


def process_admin_login(message):
    if message.text == ADMIN_LOGIN:
        msg = bot.send_message(message.chat.id, "Введите пароль:")
        bot.register_next_step_handler(msg, process_admin_password)
    else:
        bot.send_message(message.chat.id, "Неверный логин. Попробуйте снова.")
        return


def process_admin_password(message):
    if message.text == ADMIN_PASSWORD:
        set_admin(message.chat.id)
        bot.send_message(message.chat.id, "Вы вошли в админ-режим.", reply_markup=main_menu(True))
    else:
        bot.send_message(message.chat.id, "Неверный пароль. Попробуйте снова.")
        return


# Выход из админ-режима
@bot.message_handler(func=lambda message: message.text == 'Выйти из админ-режима')
def exit_admin(message):
    remove_admin(message.chat.id)
    bot.send_message(message.chat.id, "Вы вышли из админ-режима.", reply_markup=main_menu(False))


# Информация о функциях бота
@bot.message_handler(commands=['info'])
def bot_info(message):
    info_message = (
        "/start - Начать работу с ботом\n"
        "/admin - Вход в административный режим (требуются логин и пароль)\n"
        "/info - Информация о функциях бота\n"
        "Записаться на стрижку - Оформить запись на услугу\n"
        "Отменить запись - Отмена существующей записи\n"
        "Просмотреть записи - Просмотр всех ваших записей\n"
        "Контакты - Контактная информация о салоне\n"
        "Помощь - Краткое описание доступных возможностей\n"
        "Админ-панель - Доступно для администраторов, управление расписанием и записями\n"
        "Выйти из админ-режима - Выход из режима администратора"
    )
    bot.send_message(message.chat.id, info_message)


# Запись на стрижку
@bot.message_handler(func=lambda message: message.text == 'Записаться на стрижку')
def book_appointment(message):
    user_appointments[message.chat.id] = {}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for service in services:
        markup.add(types.KeyboardButton(service))

    bot.send_message(message.chat.id, "Выберите услугу:", reply_markup=markup)
    bot.register_next_step_handler(message, select_master)


from datetime import datetime, timedelta


# Обработчик выбора мастера
def select_master(message):
    user_appointments[message.chat.id]['service'] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for master in masters:
        markup.add(types.KeyboardButton(master))

    bot.send_message(message.chat.id, "Выберите мастера:", reply_markup=markup)
    bot.register_next_step_handler(message, select_date)


# Обработчик выбора даты
def select_date(message):
    user_appointments[message.chat.id]['master'] = message.text
    selected_master = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    today = datetime.now().date()

    # Доступные даты для записи - на неделю вперед
    dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    for date in dates:
        markup.add(types.KeyboardButton(date))

    bot.send_message(message.chat.id, f"Выберите дату для мастера {selected_master}:", reply_markup=markup)
    bot.register_next_step_handler(message, select_time)


# Обработчик выбора времени
def select_time(message):
    user_appointments[message.chat.id]['date'] = message.text
    selected_date = message.text
    selected_master = user_appointments[message.chat.id]['master']

    # Получаем текущее время
    now = datetime.now()

    # Доступное время для записи (например, с 10:00 до 18:00 с шагом в час)
    available_times = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']

    # Если выбрана текущая дата, исключаем прошедшие временные слоты
    if selected_date == now.strftime('%Y-%m-%d'):
        available_times = [time for time in available_times if time > now.strftime('%H:%M')]

    # Получаем занятые временные слоты для выбранного мастера и даты
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT time FROM appointments WHERE date = ? AND master = ?', (selected_date, selected_master))
    booked_times = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Исключаем занятые временные слоты
    free_times = [time for time in available_times if time not in booked_times]

    # Проверяем, есть ли свободное время
    if free_times:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for time in free_times:
            markup.add(types.KeyboardButton(time))

        bot.send_message(message.chat.id, f"Выберите время для мастера {selected_master}:", reply_markup=markup)
        bot.register_next_step_handler(message, confirm_appointment)
    else:
        bot.send_message(message.chat.id,
                         f"Нет доступного времени для мастера {selected_master} на выбранную дату. Попробуйте выбрать другую дату.")
        bot.register_next_step_handler(message, select_date)


# Подтверждение записи
def confirm_appointment(message):
    user_appointments[message.chat.id]['time'] = message.text
    user_data = user_appointments[message.chat.id]

    # Проверка на занятость только для выбранного мастера
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    # Проверяем, есть ли уже запись на это время у этого мастера
    cursor.execute('SELECT * FROM appointments WHERE date = ? AND time = ? AND master = ?',
                   (user_data['date'], user_data['time'], user_data['master']))
    existing_appointment = cursor.fetchone()

    if existing_appointment:
        # Если запись уже существует, сообщаем пользователю и просим выбрать другое время
        bot.send_message(message.chat.id,
                         "Ошибка: на это время у выбранного мастера уже есть запись. Пожалуйста, выберите другое время.")
        bot.register_next_step_handler(message, select_time)
    else:
        # Если запись не существует, добавляем новую запись
        success = add_appointment(
            message.chat.id,
            user_data['service'],
            user_data['master'],
            user_data['date'],
            user_data['time']
        )

        if success:
            bot.send_message(message.chat.id, "Ваша запись успешно создана!")
            notify_admins(
                f"Новая запись: {user_data['service']} к {user_data['master']} на {user_data['date']} {user_data['time']}.")
        else:
            bot.send_message(message.chat.id, "Произошла ошибка при создании записи. Попробуйте снова.")

        bot.send_message(message.chat.id, "Возвращаю вас в главное меню.",
                         reply_markup=main_menu(is_admin(message.chat.id)))
        user_appointments.pop(message.chat.id, None)

    conn.close()


# Функция для добавления записи
def add_appointment(user_id, service, master, date, time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''INSERT INTO appointments (user_id, service, master, date, time)
                          VALUES (?, ?, ?, ?, ?)''', (user_id, service, master, date, time))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


# Отмена записи
@bot.message_handler(func=lambda message: message.text == 'Отменить запись')
def cancel_appointment(message):
    appointments = get_user_appointments(message.chat.id)

    if not appointments:
        bot.send_message(message.chat.id, "У вас нет активных записей.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for appointment in appointments:
        markup.add(types.KeyboardButton(f"{appointment[2]} {appointment[3]}"))

    bot.send_message(message.chat.id, "Выберите запись для отмены (дата и время):", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_cancel)


def confirm_cancel(message):
    date_time = message.text.split()
    if len(date_time) == 2:
        delete_appointment(message.chat.id, date_time[0], date_time[1])
        bot.send_message(message.chat.id, "Запись успешно отменена.")
        notify_admins(f"Запись отменена пользователем {message.from_user.full_name}: {date_time[0]} {date_time[1]}")
    else:
        bot.send_message(message.chat.id, "Неверный формат. Попробуйте снова.")

    bot.send_message(message.chat.id, "Возвращаю вас в главное меню.",
                     reply_markup=main_menu(is_admin(message.chat.id)))


# Просмотр записей
@bot.message_handler(func=lambda message: message.text == 'Просмотреть записи')
def view_appointments(message):
    appointments = get_user_appointments(message.chat.id)

    if not appointments:
        bot.send_message(message.chat.id, "У вас нет активных записей.")
    else:
        response = "Ваши записи:\n"
        for appointment in appointments:
            response += f"{appointment[0]} к {appointment[1]} на {appointment[2]} {appointment[3]}\n"

        bot.send_message(message.chat.id, response)

    bot.send_message(message.chat.id, "Возвращаю вас в главное меню.",
                     reply_markup=main_menu(is_admin(message.chat.id)))


# Инициализация базы данных при старте
init_db()

# Запуск бота
bot.polling(none_stop=True)
