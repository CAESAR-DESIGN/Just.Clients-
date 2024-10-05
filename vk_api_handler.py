import vk_api
import configparser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_vk_token(browser):
    browser.get('https://oauth.vk.com/authorize?client_id=6287487&scope=1073737727&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&revoke=1')
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button.flat_button.fl_r.button_indent')))
    allow_button = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.flat_button.fl_r.button_indent')))
    allow_button.click()
    token = browser.current_url.split("access_token=")[1].split("&expires")[0]
    return token

def save_token(token):
    config = configparser.ConfigParser()
    config['VK'] = {'token': token}
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def load_token():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config.get('VK', 'token', fallback='')

def get_user_id(api, screen_name):
    try:
        response = api.users.get(user_id=screen_name)
        if response:
            return response[0]['id']
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при получении user_id: {e}")

    try:
        response = api.groups.getById(group_id=screen_name)
        if response:
            return -response[0]['id']
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при получении user_id для сообщества: {e}")

    return None
