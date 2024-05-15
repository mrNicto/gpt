import requests
from config import *
import logging 
from iinfo import SYSTEM_PROMPT
import sqlite3

#stt
def speech_to_text(data):
    headers = {'Authorization': f"Bearer {IAM_TOKEN}"}
    params = "&".join([
        "topic=general",  # используем основную версию модели
        f"folderId={FOLDER_ID}",
        "lang=ru-RU"  # распознаём голосовое сообщение на русском языке
    ])

    url = f"https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?{params}"

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return True, response.json()["result"]
    else:
        return False, "При запросе в SpeechKit возникла ошибка"
    
#tts
def text_to_speech(text):
    headers = {'Authorization': f"Bearer {IAM_TOKEN}"}
    data = {'text': text,  # текст, который нужно преобразовать в голосовое сообщение
            'lang': 'ru-RU',  # язык текста - русский
            'voice': VOICE,  # мужской голос Филиппа
            'folderId': FOLDER_ID}
    url = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        return True, response.content
    
    else:
        return False, "При запросе в SpeechKit возникла ошибка" 
    

#gpt
logging.basicConfig(filename=LOGS_PATH, 
                    level=logging.DEBUG, 
                    format="%(asctime)s %(message)s", 
                    filemode="w")


def count_tokens(text): 
    """Подсчитывает количество токенов в сообщении.""" 
    headers = { 
        'Authorization': f'Bearer {IAM_TOKEN}', 
        'Content-Type': 'application/json' 
    } 
    data = { 
       "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest", 
       "text": text, 
    } 
    return len( 
        requests.post( 
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize", 
            json=data, 
            headers=headers 
        ).json()["tokens"] 
    ) 


def ask_gpt(text, user_id): 
    """Запрос к Yandex GPT""" 
    conn = sqlite3.connect('speech.db')
    cur = conn.cursor()
    cur.execute("""SELECT histori FROM messsages WHERE user=?""", (user_id,))
    data = cur.fetchone()
    cur.close()
    conn.close()
    history = data[0]
    promt = SYSTEM_PROMPT + history + text
    url = f"https://llm.api.cloud.yandex.net/foundationModels/v1/completion" 
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",  # модель для генерации текста
        "completionOptions": {
            "stream": False,  # потоковая передача частично сгенерированного текста выключена
            "temperature": 0.6,  # чем выше значение этого параметра, тем более креативными будут ответы модели (0-1)
            "maxTokens": 50  # максимальное число сгенерированных токенов, очень важный параметр для экономии токенов
        },
        "messages": [
            {
                "role": "user",  # пользователь спрашивает у модели
                "text": promt  # передаём текст, на который модель будет отвечать
            }
        ]
    }

    try: 
        print('DATA to GPT:', data) 
        response = requests.post(url, headers=headers, json=data) 
        if response.status_code != 200: 
            logging.debug(f"Response {response.json()} Status code:{response.status_code} Message {response.text}") 
            result = f"Status code {response.status_code}. Подробности см. в журнале." 
            return result 
        result = response.json()['result']['alternatives'][0]['message']['text'] 
        print('RESPONSE from GPT:', response.json()) 
    except Exception as e: 
        logging.error(f"An unexpected error occurred: {e}") 
        result = "Произошла непредвиденная ошибка. Подробности см. в журнале." 
    return result 