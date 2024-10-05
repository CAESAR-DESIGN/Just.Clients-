import json
import os

CONFIG_FILE_PATH = "config.json"

DEFAULT_CONFIG = {
    "messages": [
        "Приветствую, {user_name}",
        "Мне очень понравилось Ваше последнее видео {topic}",
        "Кстати, могу Вам помочь с превью на Вашем канале. Так мы поднимем просмотры и CTR, а также улучшим визуальную часть канала",
        "Что думаете?"
    ],
    "vk_limit": 40,
    "telegram_limit": 40,
    "instagram_limit": 40,
    "theme": "dark",
    "photo_path": ""
}

def load_config():
    if not os.path.exists(CONFIG_FILE_PATH):
        return DEFAULT_CONFIG.copy()
    
    with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)

def save_config(config):
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=4)

def reset_config():
    save_config(DEFAULT_CONFIG.copy())
