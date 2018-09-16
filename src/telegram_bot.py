from telebot import apihelper
import telebot
from src.config import token
bot = telebot.TeleBot(token)
is_running = False
apihelper.proxy = {'https': 'socks5://user:80.241.222.169@host:1080'
}
@bot.message_handler(commands=['new', 'edit'])
def start_handler(message):
    #global is_running
    print('start')
    chat_id = message.chat.id
    text = message.text
    msg = bot.send_message(chat_id, 'Сколько вам лет?')
    print(msg)
    if text == 'new':
        bot.register_next_step_handler(msg, askAge)
    elif text == 'edit':
        msg = bot.send_message(chat_id, 'Команда не готова!')
    print('end')
    is_running = True

def askAge(message):
    #global is_running
    chat_id = message.chat.id
    text = message.text.lower()
    if text == 'end':
        return
    if not text.isdigit():
        msg = bot.send_message(chat_id, 'Возраст должен быть числом, введите ещё раз.')
        bot.register_next_step_handler(msg, askAge) #askSource
        return
    msg = bot.send_message(chat_id, 'Спасибо, я запомнил что вам ' + text + ' лет.')
    #is_running = False

bot.polling(none_stop=True)