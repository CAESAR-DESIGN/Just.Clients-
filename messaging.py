import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import vk_api
from vk_api.exceptions import ApiError
from PyQt5.QtWidgets import QMessageBox
from browser_handler import scroll_for_limited_time
from vk_api_handler import load_token, get_user_id
from youtube_data import get_youtube_data
from utils import read_sent_links, write_links_to_db, extract_user_screen_name, extract_topic_from_title, remove_emojis
import sqlite3
import traceback
import json

class MessageHandler:
    def __init__(self, browser, db_path="sent_links.db"):
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
        self.browser = browser
        self.vk_message_count = 0
        self.telegram_message_count = 0
        self.instagram_message_count = 0
        self.message_count = 0
        self.db_path = db_path
        self.vk_count_limit = config.get('vk_limit')
        self.telegram_count_limit = config.get('telegram_limit')
        self.instagram_count_limit = config.get('instagram_limit')
        self.stop_sending = False
        self.is_paused = False

    def link_exists_in_db(self, url):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM SentLinks WHERE link = ?", (url,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def start_sending_messages(self, search_query):
        search_query = search_query.replace(" ", "+")
        search_url = f"https://www.youtube.com/results?search_query={search_query}+%2B&sp=EggIAxABGAMgAQ%253D%253D"
        self.browser.get(search_url)

        processed_links = set()
        try:
            while not self.stop_sending:
                if self.is_paused:
                    time.sleep(1)
                    continue

                # Проверяем, что первая вкладка для скроллинга активна
                if len(self.browser.window_handles) > 0:
                    self.browser.switch_to.window(self.browser.window_handles[0])

                # Находим все ссылки на каналы
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.yt-simple-endpoint.style-scope.yt-formatted-string"))
                )
                current_links = set()
                elements = self.browser.find_elements(By.CSS_SELECTOR, "a.yt-simple-endpoint.style-scope.yt-formatted-string")
                for element in elements:
                    href = element.get_attribute('href')
                    if href and href.startswith('https://www.youtube.com/@'):
                        current_links.add(href)

                filtered_links = {url for url in current_links if not self.link_exists_in_db(url)}
                for link in filtered_links: 
                    self.add_link_to_db(link)

                new_links = filtered_links - processed_links
                if not new_links:
                    # Если нет новых ссылок, переключаемся на первую вкладку и скроллим
                    self.browser.switch_to.window(self.browser.window_handles[0])
                    scroll_for_limited_time(self.browser, 10)
                    continue

                for url in new_links:
                    if self.stop_sending:
                        break
                    try:
                        self.process_link(url)  # Переходим к обработке канала
                    except Exception as e:
                        # Если произошла ошибка на канале, просто идём к следующему
                        print(f'Ошибка при обработке ссылки {url}: {str(e)}')
                        continue  # Переходим к следующему каналу

                    processed_links.add(url)

        except Exception as e:
            print(traceback.format_exc())
            QMessageBox.critical(None, 'Ошибка', f'Ошибка при обработке результатов поиска: {str(e)}')

    def process_link(self, url):
        if len(self.browser.window_handles) > 1:
            # Переключаемся на открытую вкладку с каналом
            self.browser.switch_to.window(self.browser.window_handles[1])
            # Загружаем новый адрес канала в этой же вкладке
            self.browser.get(f'{url}/about')
        else:
            # Если второй вкладки нет (например, она закрыта), открываем новую
            self.browser.execute_script(f"window.open('{url}/about', '_blank');")
            self.browser.switch_to.window(self.browser.window_handles[-1])
        
        try:
            # Обработка данных канала
            self.handle_channel(url + '/about', read_sent_links())
        except Exception as e:
            print(f'Ошибка при обработке канала {url}/about: {str(e)}')
            import traceback
            print(traceback.format_exc())
            # Если произошла ошибка при обработке канала, просто переходим к следующему каналу
        finally:
            # Если вкладка с каналом открыта, остаёмся на ней, не переключаемся
            pass


    def handle_channel(self, channel_url, sent_links):
        try:
            vk_session = vk_api.VkApi(token=load_token())
            vk = vk_session.get_api()

            # Извлекаем все данные с канала один раз
            data = get_youtube_data(self.browser, channel_url)

            if data is None:
                return

            # Сохраняем данные
            social_links_decoded, vk_links, telegram_links, instagram_links, video_title, video_thumbnail = data

            # Если есть ссылки на соц.сети
            if social_links_decoded:
                topic = extract_topic_from_title(video_title)

                # Сообщения, которые мы будем отправлять
                second_message = f'Мне очень понравилось Ваше последнее видео {topic}'
                third_message = 'Кстати, могу Вам помочь с превью на Вашем канале. Так мы поднимем просмотры и CTR, а также улучшим визуальную часть канала'
                fourth_message = 'Что думаете?'
                thumbnail_message = video_thumbnail

                all_links = vk_links + telegram_links + instagram_links

                vk_counter = 0
                telegram_counter = 0
                instagram_counter = 0

                messages_sent = False

                # Проходим по всем социальным ссылкам
                for link in all_links:
                    if self.stop_sending:
                        break
                    if self.is_paused:
                        while self.is_paused and not self.stop_sending:
                            time.sleep(1)

                    if link in sent_links:
                        print(f'Не отправлено (дубликат): {link}')
                        continue

                    # Отправляем сообщения в VK
                    if vk_counter <= self.vk_count_limit:
                        self.send_vk_messages(vk, [link], second_message, video_thumbnail, third_message, fourth_message)
                        vk_counter += 1
                        messages_sent = True

                    # Отправляем сообщения в Telegram
                    if telegram_counter <= self.telegram_count_limit:
                        self.send_telegram_messages([link], second_message, third_message, fourth_message, thumbnail_message)
                        telegram_counter += 1
                        messages_sent = True

                    # Отправляем сообщения в Instagram
                    if instagram_counter <= self.instagram_count_limit:
                        self.send_instagram_messages([link], second_message, third_message, fourth_message)
                        instagram_counter += 1
                        messages_sent = True

                    # Проверяем, нужно ли остановить выполнение
                    if vk_counter >= self.vk_count_limit and telegram_counter >= self.telegram_count_limit and instagram_counter >= self.instagram_count_limit:
                        break

                    # Добавляем ссылку в базу данных
                    self.add_link_to_db(link)
                    sent_links.update([link])

                if not messages_sent:
                    print(f'Не найдено социальных ссылок на канале: {channel_url}')
                else:
                    print(f'Завершена рассылка на канал: {channel_url}.')
            else:
                print(f'Не найдено социальных ссылок на канале: {channel_url}')
        except Exception as e:
            print(f'Ошибка при обработке канала {channel_url}: {str(e)}')
            print(traceback.format_exc())

    def add_link_to_db(self, link):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO SentLinks (link) VALUES (?)", (link,))
        conn.commit()
        conn.close()

    def send_vk_messages(self, vk, vk_links, second_message, video_thumbnail, third_message, fourth_message):
        for i, vk_link in enumerate(vk_links):
            user_screen_name = extract_user_screen_name(vk_link)
            user_id = get_user_id(vk, user_screen_name)

            if not user_id:
                print(f'Не отправлено: {vk_link}')
                continue

            user_info = vk.users.get(user_ids=user_id, fields="first_name")
            user_name = user_info[0].get("first_name", "") if user_info else ""
            user_name = user_name.lower().capitalize()

            upload = vk_api.VkUpload(vk)
            with open('config.json', 'r') as config_file:
                config = json.load(config_file)
            photo_path = config.get('photo_path')
            photo = upload.photo_messages(photo_path)[0]

            welcome_message_vk = f'Приветствую, {user_name}' if user_name else 'Приветствую'

            try:
                if user_id > 0:
                    vk.friends.add(user_id=user_id)
                else:
                    vk.groups.join(group_id=abs(user_id))

                vk.messages.send(user_id=user_id, message=welcome_message_vk, random_id=0)
                vk.messages.send(user_id=user_id, message=second_message, random_id=0)
                if video_thumbnail:
                    vk.messages.send(user_id=user_id, attachment=video_thumbnail, random_id=0)
                vk.messages.send(user_id=user_id, message=third_message, random_id=0)
                vk.messages.send(user_id=user_id, attachment=f'photo{photo["owner_id"]}_{photo["id"]}', random_id=0)
                vk.messages.send(user_id=user_id, message=fourth_message, random_id=0)
                self.vk_message_count += 1
                self.message_count += 1
                print(f'Отправлено: {vk_link} ({self.vk_message_count})')
            except ApiError as e:
                if "group_id not domain" in str(e):
                    print(f'Не отправлено (такой группы не существует): {vk_link}')
                elif "user_id not domain" in str(e):
                    print(f'Не отправлено (такого пользователя не существует): {vk_link}')
                elif "are not allowed to send messages" in str(e):
                    print(f'Не отправлено (закрыт директ): {vk_link}')
                elif "privacy settings" in str(e):
                    print(f'Не отправлено (закрыт директ): {vk_link}')
            except Exception as e:
                print(traceback.format_exc())
                continue

    def send_telegram_messages(self, telegram_links, second_message, third_message, fourth_message, thumbnail_message):
        for i, telegram_link in enumerate(telegram_links):
            try:
                # Работаем на второй вкладке
                if len(self.browser.window_handles) > 1:
                    self.browser.switch_to.window(self.browser.window_handles[1])
                    self.browser.get(telegram_link)
                else:
                    self.browser.execute_script(f"window.open('{telegram_link}', '_blank');")
                    self.browser.switch_to.window(self.browser.window_handles[-1])

                time.sleep(1)
                if "bot" in telegram_link.lower():
                    print(f'Не отправлено (бот): {telegram_link}')
                else:
                    wait = WebDriverWait(self.browser, 10)
                    user_name_telegram_element = wait.until(
                        EC.presence_of_element_located((By.XPATH, '//span[@dir="auto"]')))
                    user_name_telegram = remove_emojis(user_name_telegram_element.text)
                    user_name_telegram = user_name_telegram.lower().capitalize()

                    tgme_page_extra = self.browser.find_elements(By.CSS_SELECTOR, 'div.tgme_page_extra')
                    if tgme_page_extra and "subscribers" in tgme_page_extra[0].text:
                        print(f'Не отправлено (канал): {telegram_link}')
                    elif tgme_page_extra and "members" in tgme_page_extra[0].text:
                        print(f'Не отправлено (группа): {telegram_link}')
                    else:
                        open_in_web_button = wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, 'a.tgme_action_button_new.tgme_action_web_button')))
                        open_in_web_button.click()
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'input-message-container')))
                        time.sleep(2)
                        self.browser.switch_to.active_element.send_keys('Приветствую, ' + user_name_telegram)
                        self.browser.switch_to.active_element.send_keys(Keys.ENTER)
                        telegram_url = self.browser.current_url
                        time.sleep(0.5)
                        self.browser.switch_to.active_element.send_keys(second_message)
                        self.browser.switch_to.active_element.send_keys(Keys.ENTER)
                        time.sleep(0.5)

                        if thumbnail_message:
                            self.browser.get(thumbnail_message)
                            actions = ActionChains(self.browser)
                            actions.key_down(Keys.CONTROL).send_keys("c").key_up(Keys.CONTROL).perform()

                            self.browser.get(telegram_url)
                            wait.until(EC.presence_of_element_located((By.XPATH,
                                                                    "//div[@class='input-message-input is-empty scrollable scrollable-y no-scrollbar input-field-input-fake']")))
                            actions.key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
                            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".popup-photo .popup-item-media")))
                            self.browser.switch_to.active_element.send_keys(Keys.ENTER)
                            time.sleep(0.5)

                        self.browser.switch_to.active_element.send_keys(third_message)
                        self.browser.switch_to.active_element.send_keys(Keys.ENTER)
                        time.sleep(0.5)

                        self.browser.get("C:\\Users\\dyach\\OneDrive\\Рабочий стол\\Just.Clients\\Just.Clients\\Почему_CAESAR_DESIGN.jpg")
                        actions = ActionChains(self.browser)
                        actions.key_down(Keys.CONTROL).send_keys("c").key_up(Keys.CONTROL).perform()

                        self.browser.get(telegram_url)
                        wait.until(EC.presence_of_element_located((By.XPATH,
                                                                "//div[@class='input-message-input is-empty scrollable scrollable-y no-scrollbar input-field-input-fake']")))
                        actions.key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".popup-photo .popup-item-media")))
                        self.browser.switch_to.active_element.send_keys(fourth_message)
                        self.browser.switch_to.active_element.send_keys(Keys.ENTER)
                        time.sleep(2)

                        self.telegram_message_count += 1
                        self.message_count += 1
                        print(f'Отправлено: {telegram_link} ({self.telegram_message_count})')
            except Exception as e:
                print(f'Не отправлено: {telegram_link}. Ошибка: {str(e)}')
                print(traceback.format_exc())
            finally:
                self.browser.close()
                self.browser.switch_to.window(self.browser.window_handles[0])

    def send_instagram_messages(self, instagram_links, second_message, third_message, fourth_message):
        for i, instagram_link in enumerate(instagram_links):
            try:
                # Работаем на второй вкладке
                if len(self.browser.window_handles) > 1:
                    self.browser.switch_to.window(self.browser.window_handles[1])
                    self.browser.get(instagram_link)
                else:
                    self.browser.execute_script(f"window.open('{instagram_link}', '_blank');")
                    self.browser.switch_to.window(self.browser.window_handles[-1])

                time.sleep(0.5)
                subscribe_button = WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button._acan._acap._acas._aj1-._ap30')))
                if subscribe_button:
                    subscribe_button.click()

                send_message_button = WebDriverWait(self.browser, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.x1i10hfl.xjqpnuy.xa49m3k.xqeqjp1.x2hbi6w.x972fbf.xcfux6l.x1qhh985.xm0m39n.xdl72j9.x2lah0s.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.x2lwn1j.xeuugli.xexx8yu.x18d9i69.x1hl2dhg.xggy1nq.x1ja2u2z.x1t137rt.x1q0g3np.x1lku1pv.x1a2a7pz.x6s0dn4.xjyslct.x1lq5wgf.xgqcy7u.x30kzoy.x9jhf4c.x1ejq31n.xd10rxx.x1sy0etr.x17r0tee.x9f619.x1ypdohk.x78zum5.x1f6kntn.xwhw2v2.x10w6t97.xl56j7k.x17ydfre.x1swvt13.x1pi30zi.x1n2onr6.x2b8uid.xlyipyv.x87ps6o.x14atkfc.xcdnw81.x1i0vuye.x1gjpkn9.x5n08af.xsz8vos[role="button"][tabindex="0"]')))
                if send_message_button:
                    send_message_button.click()

                    WebDriverWait(self.browser, 10).until(EC.url_contains("/direct/"))
                    WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.x9f619 > div.x9f619 > span.x1lliihq')))
                    time.sleep(1)
                    self.browser.switch_to.active_element.send_keys('Приветствую.' + ' ' + second_message + ' ' + third_message + '.' + ' ' + fourth_message)
                    self.browser.switch_to.active_element.send_keys(Keys.ENTER)
                    time.sleep(2)
                    self.instagram_message_count += 1
                    self.message_count += 1
                    print(f'Отправлено: {instagram_link} ({self.instagram_message_count})')
                else:
                    print(f'Не отправлено (закрытый аккаунт): {instagram_link}')
            except Exception as e:
                print(traceback.format_exc())
                print(f'Не отправлено: {instagram_link}. Ошибка: {str(e)}')
            finally:
                self.browser.close()
                self.browser.switch_to.window(self.browser.window_handles[0])

    def stop(self):
        self.stop_sending = True

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False
