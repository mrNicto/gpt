import sqlite3

 
def create_table(db_name="speech.db"):
    try:
        # Создаём подключение к базе данных
        with sqlite3.connect(db_name) as conn:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS messsages (
                user integer,
                histori text,
                audioblock integer,
                tokens integer
                    )''')
            # Сохраняем изменения
            conn.commit()
    except Exception as e:(
        print(f"Error: {e}")) 


def insert_row(user_id, db_name="speech.db"):
    try:
        # Создаем подключение к базе данных
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''INSERT INTO messsages (user, histori, audioblock, tokens) VALUES (?,?,?,?)''', (user_id, ' ', 0, 0))
            # Сохраняем изменения
            conn.commit()
    except Exception as e:
        print(f"Error: {e}")
       
def count_all_blocks(user_id, db_name="speech.db"):
    try:
        # Подключаемся к базе
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            # Считаем, сколько аудиоблоков использовал пользователь
            cursor.execute('''SELECT audioblock FROM messsages WHERE user=?''', (user_id,))
            data = cursor.fetchone()
            # Проверяем data на наличие хоть какого-то полученного результата запроса
            # И на то, что в результате запроса мы получили какое-то число в data[0]
            if data and data[0]:
                # Если результат есть и data[0] == какому-то числу, то
                return data[0]  # возвращаем это число - сумму всех потраченных аудиоблоков
            else:
                # Результата нет, так как у нас ещё нет записей о потраченных аудиоблоках
                return 0  # возвращаем 0
    except Exception as e:
        print(f"Error: {e}") 
