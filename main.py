import telebot
from telebot import types

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
API_TOKEN = '7488943616:AAEXvhqRNTgjWVX96IHfumF89o5tgF7huik'

bot = telebot.TeleBot(API_TOKEN)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Приветственное сообщение
    welcome_text = (
        "Привет! Добро пожаловать в наш салон красоты. "
        "Выберите одну из опций ниже, чтобы продолжить:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())

# Главное меню с кнопками
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    booking_btn = types.KeyboardButton("Записаться")
    cancel_btn = types.KeyboardButton("Отменить запись")
    view_btn = types.KeyboardButton("Просмотреть записи")
    contact_btn = types.KeyboardButton("Контакты")
    help_btn = types.KeyboardButton("Помощь")

    markup.add(booking_btn, cancel_btn, view_btn, contact_btn, help_btn)
    return markup

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def menu_response(message):
    if message.text == "Записаться":
        bot.send_message(message.chat.id, "Функция записи еще не реализована.")
    elif message.text == "Отменить запись":
        bot.send_message(message.chat.id, "Функция отмены записи еще не реализована.")
    elif message.text == "Просмотреть записи":
        bot.send_message(message.chat.id, "Функция просмотра записей еще не реализована.")
    elif message.text == "Контакты":
        bot.send_message(message.chat.id, "Наш адрес: ул. Примерная, 123\nТелефон: +123456789")
    elif message.text == "Помощь":
        bot.send_message(message.chat.id, "Если у вас есть вопросы, свяжитесь с нами по телефону или посетите наш сайт.")
    else:
        bot.send_message(message.chat.id, "Выберите одну из опций меню.", reply_markup=main_menu())

# Запуск бота
bot.polling(none_stop=True)