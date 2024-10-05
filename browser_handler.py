import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def create_browser():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "localhost:9222")
    return webdriver.Chrome(options=chrome_options)

def scroll_for_limited_time(browser, duration=10):
    end_time = time.time() + duration
    last_height = browser.execute_script("return document.documentElement.scrollHeight")
    while time.time() < end_time:
        browser.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(3)
        new_height = browser.execute_script("return document.documentElement.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
