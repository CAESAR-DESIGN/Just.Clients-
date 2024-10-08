from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from urllib.parse import unquote
import traceback

def get_youtube_data(browser, channel_url):
    browser.get(channel_url)
    wait = WebDriverWait(browser, 20)
    try:
        link_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#link-list-container')))
        links = link_container.find_elements(By.TAG_NAME, 'a')
        social_links_encoded = [link.get_attribute('href') for link in links]
        social_links_decoded = [unquote(link.split("q=")[1]) if "q=" in link else None for link in social_links_encoded]
        social_links_decoded = [link for link in social_links_decoded if link]

        if social_links_decoded:
            vk_links = [link for link in social_links_decoded if ('vk.com' in link or 'vk.ru' in link) and '/video/' not in link]
            telegram_links = [link for link in social_links_decoded if ('t.me' in link or 'telegram.me' in link) and 'bot' not in link.lower()]
            instagram_links = [link for link in social_links_decoded if 'instagram.com' in link]

            video_thumbnail_link = channel_url.replace('/about', '/videos')
            browser.get(video_thumbnail_link)
            video_thumbnails = WebDriverWait(browser, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'img.yt-core-image.yt-core-image--fill-parent-height[src*="hqdefault"]'))
            )

            if video_thumbnails:
                video_thumbnail = video_thumbnails[0].get_attribute('src')
            else:
                video_thumbnail = None

            video_title_element = browser.find_element(By.CSS_SELECTOR, 'yt-formatted-string#video-title')
            title = video_title_element.text if video_title_element else ""
            video_title = title.split()

            return social_links_decoded, vk_links, telegram_links, instagram_links, video_title, video_thumbnail
        else:
            return None
    except Exception as e:
        print(traceback.format_exc())
        print(f"Ошибка при извлечении данных YouTube: {e}")
        return None
