from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QSpinBox, QHBoxLayout, QMessageBox, QApplication
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
import sys
import os
from config_manager import load_config, save_config, reset_config
import traceback

class SettingsWindow(QWidget):
    config_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Настройки")
        self.setGeometry(100, 100, 1600, 800)  # Увеличиваем размер окна
        self.setFixedSize(1600, 800)  # Фиксируем размер окна
        self.setWindowIcon(QIcon('icon.ico'))

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Настройка стиля окна с увеличенным размером шрифта и элементов
        self.setStyleSheet("""
            background-color: #0f0f0f;
            color: #ffffff;
            font-size: 30px;
        """)

        # Поля ввода для сообщений
        self.message_inputs = []

        self.load_config_ui()

        # Кнопка для добавления нового сообщения
        self.add_message_button = QPushButton("Добавить сообщение")
        self.add_message_button.setStyleSheet("""
            background-color: #da3f21;
            color: #ffffff;
            font-size: 25px;
            padding: 10px;
            border-radius: 10px;
        """)
        self.add_message_button.clicked.connect(lambda: self.add_message_field(""))
        self.main_layout.addWidget(self.add_message_button)

        # Кнопка для выбора фото
        self.photo_button = QPushButton("Выбрать фото")
        self.photo_button.setStyleSheet("""
            background-color: #da3f21;
            color: #ffffff;
            font-size: 25px;
            padding: 10px;
            border-radius: 10px;
        """)
        self.photo_button.clicked.connect(self.select_photo)
        self.main_layout.addWidget(self.photo_button)

        # Метка для выбранного фото
        self.photo_path_label = QLabel(f"Выбрано фото: {self.config.get('photo_path', '')}")
        self.photo_path_label.setStyleSheet("color: #ffffff; font-size: 20px;")
        self.main_layout.addWidget(self.photo_path_label)

        # Лимиты для каждой социальной сети
        self.vk_limit_spinbox = QSpinBox()
        self.vk_limit_spinbox.setStyleSheet("background-color: #000000; color: #ffffff; font-size: 30px;")
        self.vk_limit_spinbox.setValue(self.config["vk_limit"])
        self.main_layout.addWidget(QLabel("Лимит для ВКонтакте"))
        self.main_layout.addWidget(self.vk_limit_spinbox)

        self.telegram_limit_spinbox = QSpinBox()
        self.telegram_limit_spinbox.setStyleSheet("background-color: #000000; color: #ffffff; font-size: 30px;")
        self.telegram_limit_spinbox.setValue(self.config["telegram_limit"])
        self.main_layout.addWidget(QLabel("Лимит для Телеграма"))
        self.main_layout.addWidget(self.telegram_limit_spinbox)

        self.instagram_limit_spinbox = QSpinBox()
        self.instagram_limit_spinbox.setStyleSheet("background-color: #000000; color: #ffffff; font-size: 30px;")
        self.instagram_limit_spinbox.setValue(self.config["instagram_limit"])
        self.main_layout.addWidget(QLabel("Лимит для Инстаграма"))
        self.main_layout.addWidget(self.instagram_limit_spinbox)

        # Кнопки для управления настройками
        buttons_layout = QHBoxLayout()

        self.apply_button = QPushButton("Применить")
        self.apply_button.setStyleSheet("background-color: #da3f21; color: #ffffff; padding: 10px; font-size: 25px; border-radius: 10px;")
        self.apply_button.clicked.connect(self.apply_settings)
        buttons_layout.addWidget(self.apply_button)

        self.reset_button = QPushButton("Сбросить")
        self.reset_button.setStyleSheet("background-color: #da3f21; color: #ffffff; padding: 10px; font-size: 25px; border-radius: 10px;")
        self.reset_button.clicked.connect(self.reset_to_default)
        buttons_layout.addWidget(self.reset_button)

        self.main_layout.addLayout(buttons_layout)

    def load_config_ui(self):
        for i, message in enumerate(self.config["messages"]):
            self.add_message_field(message)

    def add_message_field(self, message=""):
        message_label = QLabel(f"Сообщение {len(self.message_inputs) + 1}")
        message_input = QLineEdit()
        message_input.setText(message)  # Если сообщение передано, оно будет установлено в качестве текста
        message_input.setStyleSheet("background-color: #000000; color: #ffffff; font-size: 30px; border-radius: 5px;")
        delete_button = QPushButton("Удалить")
        delete_button.setStyleSheet("background-color: #da3f21; color: #ffffff; font-size: 20px; padding: 5px; border-radius: 5px;")

        message_layout = QHBoxLayout()
        message_layout.addWidget(message_label)
        message_layout.addWidget(message_input)
        message_layout.addWidget(delete_button)

        self.main_layout.insertLayout(len(self.message_inputs), message_layout)
        self.message_inputs.append(message_input)

        # Добавляем логику удаления
        delete_button.clicked.connect(lambda: self.delete_message_field(message_layout, message_input))

    def delete_message_field(self, message_layout, message_input):
        # Удаляем из интерфейса
        for i in reversed(range(message_layout.count())):
            widget = message_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
                message_layout.removeWidget(widget)

        # Удаляем из списка сообщений
        self.message_inputs.remove(message_input)

    def select_photo(self):
        photo_path, _ = QFileDialog.getOpenFileName(self, "Выберите фото", "", "Images (*.png *.jpg *.jpeg)")
        if photo_path:
            self.config["photo_path"] = photo_path
            self.photo_path_label.setText(f"Выбрано фото: {photo_path}")

    def apply_settings(self):
        reply = QMessageBox.question(
            self,
            "Применение настроек",
            "Для применения изменений требуется перезапуск.",
            QMessageBox.Ok | QMessageBox.Cancel
        )

        if reply == QMessageBox.Ok:
            self.config["messages"] = [input.text() for input in self.message_inputs]
            self.config["vk_limit"] = self.vk_limit_spinbox.value()
            self.config["telegram_limit"] = self.telegram_limit_spinbox.value()
            self.config["instagram_limit"] = self.instagram_limit_spinbox.value()
            save_config(self.config)
            self.close()
            python = sys.executable
            os.execl(python, python, *sys.argv)
        else:
            self.close()

    def reset_to_default(self):
        confirmation = QMessageBox.question(self, "Сброс настроек", "Для сброса изменений требуется перезапуск.",
                                            QMessageBox.Ok | QMessageBox.Cancel)
        if confirmation == QMessageBox.Cancel:
            return
        try:
            reset_config()
            QMessageBox.information(self, "Настройки", "Настройки сброшены до значений по умолчанию.")
            self.close()
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            print(traceback.format_exc())
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при сбросе настроек: {str(e)}")
