import telebot
from telebot import types
from config import *
from databes import *
from gpt import *
import math
import os.path

bot = telebot.TeleBot(TOKEN)  # создаём объект бота 

create_table()

def is_stt_block_limit(message, duration):
    user_id = message.from_user.id
    
    # Переводим секунды в аудиоблоки
    audioblocks = math.ceil(duration / 15) # округляем в большую сторону
    # Проверяем, что аудио длится меньше 30 секунд
    if duration >= 30:
        msg = "SpeechKit STT работает с голосовыми сообщениями меньше 30 секунд"
        bot.send_message(user_id, msg)
        return None
    all_blocks = count_all_blocks(user_id) + audioblocks
    # Сравниваем all_blocks с количеством доступных пользователю аудиоблоков
    if all_blocks >= MAX_USER_STT_BLOCKS:
        msg = f"Превышен общий лимит SpeechKit STT {MAX_USER_STT_BLOCKS}. Использовано {all_blocks} блоков. Доступно: {MAX_USER_STT_BLOCKS - all_blocks}"
        bot.send_message(user_id, msg)
        return None
    
    conn = sqlite3.connect('speech.db')
    cur = conn.cursor()
    cur.execute("""UPDATE messsages SET audioblock=? WHERE user=?""", (all_blocks, user_id))
    conn.commit()
    cur.close()
    conn.close()

    return audioblocks 


@bot.message_handler(commands=['help'])
def handle_help(message):  
    markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
    btn1 = types.KeyboardButton('/start')
    btn2 = types.KeyboardButton('/stt')
    btn3 = types.KeyboardButton('/tts')
    btn4 = types.KeyboardButton('/gpt') 
    btn5 = types.KeyboardButton('/debug') 
    btn6 = types.KeyboardButton('/limit')
    markup.row(btn4)
    markup.add(btn1, btn5)  
    markup.add(btn2, btn3)
    markup.row(btn6)

    bot.send_message(message.chat.id, 'Здравствуйте.  /start - перезагружает бот. /stt - проверка распознавания речи. \n'
                     '/tts - проверка синтеза речи. /gpt - главная функция (бот собеседник). /debug - присылает файл слогами админу\n'
                     '/limit - позволяет увидеть расход токенов', reply_markup=markup)
 


@bot.message_handler(commands=['start'])
def start(message):
    create_table()
    user_name = message.from_user.first_name
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
    btn1 = types.KeyboardButton('/help')
    btn2 = types.KeyboardButton('/stt')
    btn3 = types.KeyboardButton('/tts')
    btn4 = types.KeyboardButton('/gpt') 
    btn5 = types.KeyboardButton('/debug') 
    markup.row(btn4)
    markup.add(btn1, btn5)  
    markup.add(btn2, btn3)
    insert_row(user_id)
    print(user_id)
    bot.send_message(message.chat.id, f'Привет, {user_name}! Я бот, с которым можно поболтать о чем угодно. Чтобы узнать подробности введи команду - /help', reply_markup=markup)


@bot.message_handler(commands=['stt'])
def stt(message):     
    bot.send_message(message.chat.id, f'Отправь голосовое сообщение!')
    bot.register_next_step_handler(message, message_userstt)

def message_userstt(message):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
    btn1 = types.KeyboardButton('/help')
    btn2 = types.KeyboardButton('/debug')
    markup.add(btn1, btn2) 
    # Проверка, что сообщение действительно голосовое
    if not message.voice:
        return
    
    stt_blocks = is_stt_block_limit(message, message.voice.duration)
    if not stt_blocks:
        return
    
    file_id = message.voice.file_id  # получаем id голосового сообщения
    file_info = bot.get_file(file_id)  # получаем информацию о голосовом сообщении
    file = bot.download_file(file_info.file_path)
    
    status, text = speech_to_text(file)
    
    
    if status:
        bot.send_message(user_id, text, reply_to_message_id=message.id, reply_markup=markup)
    else:
        bot.send_message(user_id, text, reply_markup=markup)
    



@bot.message_handler(commands=['tts'])
def tts(message):     
    bot.send_message(message.chat.id, f'Введите текст который бот должен озвучить.')
    bot.register_next_step_handler(message, handle_character)


def handle_character(message):
    user_id = message.from_user.id
    inp_text = message.text.lower()

    markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
    btn1 = types.KeyboardButton('/help')
    btn2 = types.KeyboardButton('/debug')
    markup.add(btn1, btn2)
    conn = sqlite3.connect('speech.db')
    cur = conn.cursor()
    cur.execute("""SELECT tokens FROM messsages WHERE user=?""", (user_id,))
    dat = cur.fetchone()
    datam = dat[0] + len(inp_text)
    if datam >= MAX_USER_TOKENS_BLOCKS:
        msg = f"Превышен общий лимит SpeechKit TTS {MAX_USER_STT_BLOCKS}. Использовано {datam} блоков. Доступно: {MAX_USER_STT_BLOCKS - datam}"
        bot.send_message(user_id, msg)
        
    else:
        if len(inp_text) < MAX_LEN:

            bot.send_message(message.chat.id, f'Ожидайте ответа.')
            success, response = text_to_speech(inp_text)
            cur.execute("""UPDATE messsages SET tokens=? WHERE user=?""", (datam, user_id))
            conn.commit()
            cur.close()
            conn.close()
            if success:
                bot.send_voice(user_id, response, reply_markup=markup)
            else:
                bot.send_message(user_id, response, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, f'Сообщение слишком длинное.', reply_markup=markup)




@bot.message_handler(commands=['gpt'])
def gpt(message):     
    bot.send_message(message.chat.id, f'Готов выдать вам биографию любого известного человека.\n' 
                     'Для этого прошу ввести его ФИО. Любым удобным для вас способом(текст, аудио).')
    bot.register_next_step_handler(message, message_user)
    

def gpt_question(text, user_id, ttos):

    markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
    btn1 = types.KeyboardButton('/help')
    btn2 = types.KeyboardButton('/debug')
    markup.add(btn1, btn2)
    gpt_text = ask_gpt(text, user_id)

    tok = count_tokens(gpt_text)

    conn = sqlite3.connect('speech.db')
    cur = conn.cursor()
    cur.execute("""SELECT histori FROM messsages WHERE user=?""", (user_id,))
    data = cur.fetchone()
    datam = data[0] + gpt_text
    cur.execute("""UPDATE messsages SET histori=? WHERE user=?""", (datam, user_id))
    conn.commit()
    cur.execute("""SELECT tokens FROM messsages WHERE user=?""", (user_id,))
    data = cur.fetchone()
    dat = data[0] + tok
    cur.execute("""UPDATE messsages SET tokens=? WHERE user=?""", (dat, user_id))
    conn.commit()
    cur.close()
    conn.close()

    if ttos == False:
        bot.send_message(user_id, gpt_text, reply_markup=markup)

    else:
        datat = dat + len(gpt_text)
        if datat >= MAX_USER_TOKENS_BLOCKS:
            msg = f"Превышен общий лимит SpeechKit TTS {MAX_USER_STT_BLOCKS}. Использовано {datat} блоков. Доступно: {MAX_USER_STT_BLOCKS - datat}"
            bot.send_message(user_id, msg)
        else:
            conn = sqlite3.connect('speech.db')
            cur = conn.cursor()
            cur.execute("""UPDATE messsages SET tokens=? WHERE user=?""", (datat, user_id))
            conn.commit()
            cur.close()
            conn.close()
            success, response = text_to_speech(gpt_text)
            if success:
                bot.send_voice(user_id, response, reply_markup=markup)
            else:
                bot.send_message(user_id, response, reply_markup=markup)


def message_user(message):
    user_id = message.from_user.id
    
    # Проверка, что сообщение действительно голосовое
    if message.voice:

        stt_blocks = is_stt_block_limit(message, message.voice.duration)
        if not stt_blocks:
            return
            
        file_id = message.voice.file_id  # получаем id голосового сообщения
        file_info = bot.get_file(file_id)  # получаем информацию о голосовом сообщении
        file = bot.download_file(file_info.file_path)

        status, text = speech_to_text(file)
        
        if status:
            user_answer = text
            ttos = True

        else:
            bot.send_message(user_id, text)
    
    elif message.text:
            user_answer = message.text
            ttos = False

    tok = count_tokens(user_answer)

    conn = sqlite3.connect('speech.db')
    cur = conn.cursor()
    cur.execute("""SELECT histori FROM messsages WHERE user=?""", (user_id,))
    data = cur.fetchone()
    print(data[0])
    datam = data[0] + user_answer
    cur.execute("""UPDATE messsages SET histori=? WHERE user=?""", (datam, user_id))
    conn.commit()

    cur.execute("""SELECT tokens FROM messsages WHERE user=?""", (user_id,))
    data = cur.fetchone()
    dat = data[0] + tok
    cur.execute("""UPDATE messsages SET histori=? WHERE user=?""", (dat, user_id))
    conn.commit()
    cur.close()
    conn.close()
    print(datam)
    if dat >= MAX_USER_TOKENS_BLOCKS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
        btn1 = types.KeyboardButton('/help')
        btn2 = types.KeyboardButton('/limit')
        markup.add(btn1, btn2)
        msg = f"Превышен общий лимит GPT {MAX_USER_STT_BLOCKS}. Использовано {dat} блоков. Доступно: {MAX_USER_TOKENS_BLOCKS - dat}"
        bot.send_message(user_id, msg,reply_markup=markup)

    else:
        gpt_question(user_answer, user_id, ttos)

    

@bot.message_handler(commands=['debug'])
def send_logs(message):
    # Если текущий пользователь имеет id = ADMIN_ID:
    # с помощью os.path.exists проверяем что файл с логами существует
    # если все ОК - отправляем пользователю файл с логами LOGS_PATH
    # если НЕ ОК - пишем пользователю сообщение что файл не найден
    markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
    btn1 = types.KeyboardButton('/help')
    btn2 = types.KeyboardButton('/start')
    markup.add(btn1, btn2)
    user_id = message.from_user.id
    if str(user_id) == ADMIN_ID:
        if os.path.exists('bot_logs.txt') == True:
            file = open('bot_logs.txt',"rb")
            bot.send_document(message.chat.id, file, reply_markup=markup)

        else:
            bot.send_message(message.chat.id, "!Фаил не найден!", reply_markup=markup)
    
    else:
        bot.send_message(message.chat.id, "К сожалению у Вас нет доступа к данной функции.", reply_markup=markup)

    
@bot.message_handler(commands=['limit'])
def limit(message):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
    markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
    btn1 = types.KeyboardButton('/help')
    btn2 = types.KeyboardButton('/start')
    markup.add(btn1, btn2)
    conn = sqlite3.connect('speech.db')
    cur = conn.cursor()
    cur.execute("""SELECT tokens FROM messsages WHERE user=?""", (user_id,))
    data = cur.fetchone()
    cur.execute("""SELECT audioblock FROM messsages WHERE user=?""", (user_id,))
    datam = cur.fetchone()
    msg = f"общий лимит GPT {MAX_USER_STT_BLOCKS}. Использовано {data[0]} блоков. Доступно: {MAX_USER_TOKENS_BLOCKS - data[0]}"
    bot.send_message(user_id, msg)
    msg = f"общий лимит SpeechKit STT {MAX_USER_STT_BLOCKS}. Использовано {datam[0]} блоков. Доступно: {MAX_USER_STT_BLOCKS - datam[0]}"
    bot.send_message(user_id, msg, reply_markup=markup)
    cur.close()
    conn.close()

bot.infinity_polling()