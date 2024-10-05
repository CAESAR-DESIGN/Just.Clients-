import sqlite3
from openai import OpenAI

def extract_topic_from_title(video_title):
    api_key = "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"
    client = OpenAI(api_key=api_key)

    video_title_quotes = f"'{video_title}'"

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Ты знаешь все правила русского языка и умеешь ставить пробелы, но умеешь писать только в винительном падеже, маленькими буквами и без точек, все твои ответы начинаются со слова 'про' и заканчиваются '!'."},
            {"role": "user", "content": f"Напиши тему для ютуб видео {video_title_quotes} в двух словах."}
        ] 
    )

    topic = completion.choices[0].message.content
    return topic

def init_db():
    conn = sqlite3.connect('sent_links.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS SentLinks (
        id INTEGER PRIMARY KEY,
        link TEXT UNIQUE
    )
    ''')
    conn.commit()
    conn.close()

def connect_db():
    conn = sqlite3.connect('sent_links.db')
    cursor = conn.cursor()
    return conn, cursor

def add_link_to_db(cursor, link):
    try:
        cursor.execute('INSERT INTO SentLinks (link) VALUES (?)', (link,))
    except sqlite3.IntegrityError:
        pass

def link_exists_in_db(cursor, link):
    cursor.execute('SELECT 1 FROM SentLinks WHERE link = ?', (link,))
    return cursor.fetchone() is not None

def close_db(conn):
    conn.close()

def extract_user_screen_name(link):
    if "vk.com/" in link:
        user_screen_name = link.split("vk.com/")[-1]
        if "/" in user_screen_name:
            user_screen_name = user_screen_name.split("/")[0]
        if user_screen_name.isdigit():
            return user_screen_name
        else:
            return user_screen_name
    elif ".ru/" in link:
        user_screen_name = link.split(".ru/")[-1]
        if "/" in user_screen_name:
            user_screen_name = user_screen_name.split("/")[0]
        return user_screen_name
    elif ".com/" in link:
        user_screen_name = link.split(".com/")[-1]
        if "/" in user_screen_name:
            user_screen_name = user_screen_name.split("/")[0]
        return user_screen_name
    else:
        return None

def read_sent_links():
    conn = sqlite3.connect('sent_links.db')
    cursor = conn.cursor()
    cursor.execute("SELECT link FROM SentLinks")
    links = {row[0] for row in cursor.fetchall()}
    conn.close()
    return links

def write_links_to_db(vk_links, telegram_links, instagram_links, channel_url):
    conn, cursor = connect_db()
    for link in vk_links + telegram_links + instagram_links + [channel_url]:
        add_link_to_db(cursor, link)
    conn.commit()
    close_db(conn)

# Initialize the database on script run
init_db()
