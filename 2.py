import telebot
import sqlite3
from telebot import types
from datetime import datetime, timedelta

# Инициализация бота
TOKEN = '8095038946:AAF-j8fR2g1f_zkVlshE4eYvqIkgOFQUN10'
bot = telebot.TeleBot(TOKEN)

# Пример данных для хранения информации о мастерах и услугах
services = ['Мужская стрижка', 'Женская стрижка', 'Окрашивание']

# Список мастеров для каждой услуги
service_masters = {
    'Мужская стрижка': ['Андрей', 'Иван'],
    'Женская стрижка': ['Мария', 'Екатерина'],
    'Окрашивание': ['Анна', 'Ольга']
}

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
                        is_admin INTEGER DEFAULT 0)''')

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
def notify_admins(message, username=None, full_name=None):
    admins = get_admins()
    for admin_id in admins:
        full_message = message
        if username and full_name:
            full_message += f"\nПользователь: {full_name} (@{username})"
        bot.send_message(admin_id, full_message)


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
        "/info - Информация о функциях бота"
    )
    bot.send_message(message.chat.id, info_message)


# Запись на услугу
@bot.message_handler(func=lambda message: message.text == 'Записаться на стрижку')
def book_service(message):
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for service in services:
        markup.add(types.KeyboardButton(service))
    markup.add(types.KeyboardButton('Назад'))
    bot.send_message(user_id, "Выберите услугу:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text in services)
def select_master(message):
    service = message.text
    user_id = message.chat.id

    # Инициализация записи пользователя, если ее еще нет
    if user_id not in user_appointments:
        user_appointments[user_id] = {}

    user_appointments[user_id]['service'] = service

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    masters = service_masters[service]
    for master in masters:
        markup.add(types.KeyboardButton(master))
    markup.add(types.KeyboardButton('Назад'))
    bot.send_message(user_id, "Выберите мастера:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text in service_masters.get(
    user_appointments.get(message.chat.id, {}).get('service', [])))
def select_date(message):
    master = message.text
    user_id = message.chat.id

    # Проверка на наличие услуги
    if user_id not in user_appointments or 'service' not in user_appointments[user_id]:
        bot.send_message(user_id, "Произошла ошибка. Пожалуйста, начните заново.")
        return

    user_appointments[user_id]['master'] = master

    # Получаем дату через 30 дней от текущей даты
    today = datetime.now()
    future_dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for date in future_dates:
        markup.add(types.KeyboardButton(date))
    markup.add(types.KeyboardButton('Назад'))
    bot.send_message(user_id, "Выберите дату:", reply_markup=markup)


@bot.message_handler(
    func=lambda message: message.text in [appointment[2] for appointment in get_user_appointments(message.chat.id)])
def select_time(message):
    date = message.text
    user_id = message.chat.id

    # Проверка на наличие услуги
    if user_id not in user_appointments or 'service' not in user_appointments[user_id]:
        bot.send_message(user_id, "Произошла ошибка. Пожалуйста, начните заново.")
        return

    user_appointments[user_id]['date'] = date

    # Получение доступного времени (здесь просто пример)
    available_times = ['10:00', '11:00', '12:00', '13:00', '14:00']

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for time in available_times:
        markup.add(types.KeyboardButton(time))
    markup.add(types.KeyboardButton('Назад'))
    bot.send_message(user_id, "Выберите время:", reply_markup=markup)


# Обработка нажатия кнопки "Назад" на этапе выбора даты
@bot.message_handler(
    func=lambda message: message.text == 'Назад' and 'master' in user_appointments.get(message.chat.id, {}))
def go_back_from_date_selection(message):
    user_id = message.chat.id
    # Удаляем дату из промежуточных данных
    user_appointments[user_id].pop('master', None)
    # Возвращаемся к выбору мастера
    select_master(message)


# Обработка нажатия кнопки "Назад" на этапе выбора времени
@bot.message_handler(
    func=lambda message: message.text == 'Назад' and 'date' in user_appointments.get(message.chat.id, {}))
def go_back_from_time_selection(message):
    user_id = message.chat.id
    # Удаляем время из промежуточных данных
    user_appointments[user_id].pop('date', None)
    # Возвращаемся к выбору даты
    select_date(message)


@bot.message_handler(func=lambda message: message.text in ['10:00', '11:00', '12:00', '13:00', '14:00'])
def confirm_appointment(message):
    selected_time = message.text
    user_id = message.chat.id

    # Проверка на наличие услуги
    if user_id not in user_appointments or 'service' not in user_appointments[user_id]:
        bot.send_message(user_id, "Произошла ошибка. Пожалуйста, начните заново.")
        return

    user_appointments[user_id]['time'] = selected_time

    user_data = user_appointments[user_id]

    # Проверяем, что все данные заполнены корректно
    service = user_data.get('service')
    master = user_data.get('master')
    date = user_data.get('date')

    if not all([service, master, date, selected_time]):  # Проверка на все данные, включая selected_time
        bot.send_message(user_id, "Произошла ошибка. Пожалуйста, попробуйте снова.")
        return

    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM appointments WHERE date = ? AND time = ? AND master = ?',
                   (date, selected_time, master))  # Используем selected_time для проверки
    existing_appointment = cursor.fetchone()

    if existing_appointment:
        bot.send_message(user_id,
                         "Ошибка: на это время у выбранного мастера уже есть запись. Пожалуйста, выберите другое время.")
        bot.register_next_step_handler(message, select_time)  # Повторный запрос времени
    else:
        success = add_appointment(
            user_id,
            service,
            master,
            date,
            selected_time  # Используем selected_time для добавления записи
        )

        if success:
            bot.send_message(user_id,
                             f"Ваша запись успешно создана на услугу '{service}' к мастеру {master} на {date} в {selected_time}.")
            # Получаем информацию о пользователе
            username = message.from_user.username
            full_name = user_data.get('full_name', 'Не указано')
            notify_admins(f"Новая запись: {service} к мастеру {master} на {date} в {selected_time}.", username,
                          full_name)
        else:
            bot.send_message(user_id, "Произошла ошибка при создании записи. Попробуйте снова.")

        bot.send_message(user_id, "Возвращаю вас в главное меню.", reply_markup=main_menu(is_admin(user_id)))
        user_appointments.pop(user_id, None)

    conn.close()


# Отмена записи
@bot.message_handler(func=lambda message: message.text == 'Отменить запись')
def cancel_appointment(message):
    user_id = message.chat.id
    appointments = get_user_appointments(user_id)

    if not appointments:
        bot.send_message(user_id, "У вас нет записей.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for appointment in appointments:
        date, time = appointment[2], appointment[3]
        markup.add(types.KeyboardButton(f"{date} {time}"))
    markup.add(types.KeyboardButton('Назад'))
    bot.send_message(user_id, "Выберите запись для отмены:", reply_markup=markup)


@bot.message_handler(func=lambda message: ' ' in message.text)
def delete_selected_appointment(message):
    user_id = message.chat.id
    selected_appointment = message.text.split(' ')
    date = selected_appointment[0]
    time = selected_appointment[1]

    delete_appointment(user_id, date, time)
    bot.send_message(user_id, "Запись отменена.", reply_markup=main_menu(is_admin(user_id)))


# Просмотр записей
@bot.message_handler(func=lambda message: message.text == 'Просмотреть записи')
def view_appointments(message):
    user_id = message.chat.id
    appointments = get_user_appointments(user_id)

    if not appointments:
        bot.send_message(user_id, "У вас нет записей.")
        return

    response = "Ваши записи:\n"
    for appointment in appointments:
        response += f"Услуга: {appointment[0]}, Мастер: {appointment[1]}, Дата: {appointment[2]}, Время: {appointment[3]}\n"

    bot.send_message(user_id, response)


# Запуск бота
if __name__ == '__main__':
    init_db()
    bot.polling(none_stop=True)
