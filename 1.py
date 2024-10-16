import telebot

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
API_TOKEN = '7488943616:AAEXvhqRNTgjWVX96IHfumF89o5tgF7huik'

bot = telebot.TeleBot(API_TOKEN)

# Обработчик всех текстовых сообщений
@bot.message_handler(func=lambda message: True)
def respond_to_all_messages(message):
    response_text = "этот бот лежит на локальном сервере с автозапуском"
    bot.reply_to(message, response_text)

# Запуск бота
bot.polling(none_stop=True)