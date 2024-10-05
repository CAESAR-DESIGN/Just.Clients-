import sys
from PyQt5.QtWidgets import QApplication
from ui import VKMessengerApp
from browser_handler import create_browser
from vk_api_handler import get_vk_token, save_token
from messaging import MessageHandler

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMessageBox QLabel { color: white; }
        QMessageBox QPushButton { color: white; }
    """)
    
    browser = create_browser()

    token = get_vk_token(browser)
    save_token(token)

    message_handler = MessageHandler(browser)  # Создаем объект MessageHandler
    messenger_app = VKMessengerApp(browser, message_handler)  # Передаем browser и message_handler в VKMessengerApp
    messenger_app.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()