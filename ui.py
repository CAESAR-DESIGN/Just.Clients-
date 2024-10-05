from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from settings_ui import SettingsWindow

class WorkerThread(QThread):
    finished = pyqtSignal()
    paused = pyqtSignal()
    resumed = pyqtSignal()

    def __init__(self, handler, search_query):
        super().__init__()
        self.handler = handler
        self.search_query = search_query
        self._is_paused = False  # Добавлен флаг паузы
        self._stop = False  # Флаг остановки

    def run(self):
        self.handler.stop_sending = False  # Сброс флага остановки
        self._stop = False
        self.handler.start_sending_messages(self.search_query)
        if not self._stop:
            self.finished.emit()

    def stop(self):
        self.handler.stop_sending = True
        self._stop = True
        self.finished.emit()

    def pause(self):
        self._is_paused = True
        self.handler.is_paused = True
        self.paused.emit()

    def resume(self):
        self._is_paused = False
        self.handler.is_paused = False
        self.resumed.emit()

    @property
    def is_paused(self):
        return self._is_paused

class VKMessengerApp(QWidget):
    def __init__(self, browser, message_handler):
        super().__init__()
        self.browser = browser
        self.message_handler = message_handler
        self.init_ui()
        self.worker_thread = None

    def init_ui(self):
        self.setStyleSheet("background-color: #0f0f0f;")
        self.setWindowTitle('Created by CAESAR DESIGN')
        self.setGeometry(100, 100, 800, 100)
        self.setWindowIcon(QIcon('icon.ico'))

        layout = QVBoxLayout()
        layout.setSpacing(20)

        header_label = QLabel('Автоматический рассыльщик для YouTube')
        header_label.setStyleSheet("font-size: 40px; color: #ffffff; font-weight: bold;")
        header_label.setAlignment(Qt.AlignTop)
        layout.addWidget(header_label)

        input_layout = QVBoxLayout()
        input_layout.setSpacing(10)

        link_layout = QHBoxLayout()
        self.link_label = QLabel('Введите тему:')
        self.link_label.setStyleSheet("color: #ffffff; font-size: 30px;")
        self.link_entry = QLineEdit()
        self.link_entry.setStyleSheet("color: #ffffff; font-size: 30px;")
        link_layout.addWidget(self.link_label)
        link_layout.addWidget(self.link_entry)

        input_layout.addLayout(link_layout)
        layout.addLayout(input_layout)

        buttons_layout = QHBoxLayout()
        self.send_button = QPushButton('Рассылка')
        self.send_button.setStyleSheet("background-color: #da3f21; color: #ffffff; font-size: 35px; border-radius: 25px; height: 50px;")
        self.send_button.clicked.connect(self.start_sending)
        buttons_layout.addWidget(self.send_button)

        self.stop_button = QPushButton('Стоп')
        self.stop_button.setStyleSheet("background-color: #da3f21; color: #ffffff; font-size: 35px; border-radius: 25px; height: 50px;")
        self.stop_button.clicked.connect(self.stop_sending)
        self.stop_button.setVisible(False)
        buttons_layout.addWidget(self.stop_button)

        self.pause_button = QPushButton('Пауза')
        self.pause_button.setStyleSheet("background-color: #da3f21; color: #ffffff; font-size: 35px; border-radius: 25px; height: 50px;")
        self.pause_button.clicked.connect(self.pause_sending)
        self.pause_button.setVisible(False)
        buttons_layout.addWidget(self.pause_button)

        self.settings_button = QPushButton('Настройки')
        self.settings_button.setStyleSheet("background-color: #da3f21; color: #ffffff; font-size: 35px; border-radius: 25px; height: 50px;")
        self.settings_button.clicked.connect(self.open_settings)
        buttons_layout.addWidget(self.settings_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def start_sending(self):
        search_query = self.link_entry.text().strip()
        if not search_query:
            QMessageBox.critical(self, 'Ошибка', 'Пожалуйста, введите поисковый запрос.')
            return

        # Сброс флагов перед запуском
        self.message_handler.stop_sending = False
        self.message_handler.is_paused = False

        self.worker_thread = WorkerThread(self.message_handler, search_query)
        self.worker_thread.finished.connect(self.sending_finished)
        self.worker_thread.start()

        self.send_button.setVisible(False)
        self.stop_button.setVisible(True)
        self.pause_button.setVisible(True)

    def stop_sending(self):
        if self.worker_thread:
            self.worker_thread.stop()
            self.worker_thread.wait()
        self.send_button.setVisible(True)
        self.stop_button.setVisible(False)
        self.pause_button.setVisible(False)

    def pause_sending(self):
        if self.worker_thread and self.worker_thread.is_paused:
            self.worker_thread.resume()
            self.pause_button.setText('Пауза')
        elif self.worker_thread:
            self.worker_thread.pause()
            self.pause_button.setText('Пуск')

    def sending_finished(self):
        QMessageBox.information(self, 'Информация', 'Рассылка завершена.')
        self.send_button.setVisible(True)
        self.stop_button.setVisible(False)
        self.pause_button.setVisible(False)

    def open_settings(self):
        self.settings_window = SettingsWindow()
        self.settings_window.show()
