import logging
import sqlite3
import sys
from random import choice
from datetime import datetime
import csv

from PyQt5.QtGui import QPixmap, QImage, QIcon, QFontDatabase
from PyQt5.QtWidgets import *

from ui.widgets import *
from helps_files.helps_funcs import *


# Ловим ошибки, которые могут появиться при запуске
logging.captureWarnings(True)

# Ставим хорошее качество экрана
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


# Окно для регистрации или входа в профиль
class Registration_widget(QMainWindow, Ui_First_menu):
    def __init__(self):
        super().__init__()
        self.con = sqlite3.connect('databases/data')
        self.form = None
        self.setupUi(self)  # Подключаем всякие кнопки и тд
        self.btn_registration.clicked.connect(self.check_func)
        self.no_account_btn.toggled.connect(self.reformat)
        self.have_account_btn.toggled.connect(self.reformat)
        self.password_repeat_edit.setVisible(False)
        self.groupBox.setTitle('Войти')
        self.groupBox.resize(201, 171)
        self.btn_registration.setText('Войти')
        self.btn_registration.move(10, 120)

    def reformat(self):  # Функция для смены окна, при смене входа или регистрации
        self.statusbar.showMessage('')
        if self.sender() == self.have_account_btn:
            self.password_repeat_edit.setVisible(False)
            self.groupBox.setTitle('Войти')
            self.groupBox.resize(201, 171)
            self.btn_registration.setText('Войти')
            self.btn_registration.move(10, 120)
        else:
            self.password_repeat_edit.setVisible(True)
            self.groupBox.setTitle('Регистрация')
            self.groupBox.resize(201, 221)
            self.btn_registration.setText('Регистрация')
            self.btn_registration.move(10, 170)

    def check_func(self):  # Функция для проверки логина и пароля (и регистрация, и вход)
        self.statusbar.showMessage('')
        try:
            login, password, password_repeat = self.login_edit.text(), self.password_edit.text(), \
                self.password_repeat_edit.text()
            if self.have_account_btn.isChecked():
                if not len(self.con.cursor().execute("""SELECT * FROM users WHERE login = ? AND password = ?""",
                                                     (login, password)).fetchall()):
                    raise KeyboardInterrupt
            else:
                if not login.strip():
                    raise TypeError
                if not check_login(login):
                    raise SyntaxError
                if len(self.con.cursor().execute("""SELECT * FROM users WHERE login = ?""",
                                                 (login,)).fetchall()):  # Если есть такой логин, то говорим об этом
                    raise KeyError
                if password_repeat != password:
                    raise ValueError
                if check_password(password):
                    self.con.cursor().execute("""INSERT INTO users(login, password) VALUES(?, ?)""", (login, password))
                    self.con.commit()
            self.con.close()
            self.form = Collection_widget(self, login)
            self.form.show()
            self.close()
        except KeyboardInterrupt:
            self.statusbar.showMessage('Ошибка! Неверный логин или пароль!')
        except LetterError:
            self.statusbar.showMessage('Ошибка! В пароле все символы одного регистра или все числа!')
        except DigitError:
            self.statusbar.showMessage('Ошибка! Пароль не содержит чисел!')
        except LengthError:
            self.statusbar.showMessage('Ошибка! Пароль должен содержать не менее 6 символов!')
        except KeyError:
            self.statusbar.showMessage('Ошибка! Такой пользователь уже есть!')
        except ValueError:
            self.statusbar.showMessage('Ошибка! Пароли не совпадают!')
        except TypeError:
            self.statusbar.showMessage('Ошибка! У вас пустой логин!')
        except SyntaxError:
            self.statusbar.showMessage('Ошибка! В пароле не должно быть спец. символов кроме _ и пробела!')
        except sqlite3.ProgrammingError:
            print('Error db')


# Виджет с коллекциями и картами
class Collection_widget(QMainWindow, Ui_Collections_and_card_menu):
    def __init__(self, parent=None, login='', collection=''):
        super().__init__()
        self.widget = None
        self.cards_menu = None
        self.dialog = None
        self.parent = parent
        self.login = login
        self.collection = collection
        self.con = sqlite3.connect('databases/data')
        self.user_id = self.con.cursor().execute("""SELECT id FROM users WHERE login = ?""", (self.login,)).fetchone()[
            0]
        self.setupUi(self)
        self.update_box()
        self.update_coll(collection)
        if self.collection:
            self.collection_id = self.con.cursor().execute("""SELECT col_id FROM collections WHERE title = ?""",
                                                           (self.collection,)).fetchone()[0]
        else:
            self.collection_id = 0
        self.btn_add_collection.clicked.connect(self.add_collection)
        self.btn_del_collection.clicked.connect(self.del_collection)
        self.btn_add_card.clicked.connect(self.add_card)
        self.btn_edit_collection.clicked.connect(self.edit_collection)
        self.cards_in_collection.itemDoubleClicked.connect(self.edit_card)
        self.btn_statistics.clicked.connect(self.show_stat)
        self.btn_start_game.clicked.connect(self.start_game)
        self.btn_del_card.clicked.connect(self.del_card)
        self.action.triggered.connect(self.open_help)
        self.collection_box.textHighlighted.connect(self.update_list)
        self.profile_login_browse.setHtml(html_get_to_profile(self.login))
        self.statusbar.setStyleSheet('color: red;')
        self.setWindowModality(Qt.ApplicationModal)
        self.update_list(self.collection)

    def show_stat(self):  # Функция для открытия окна статистики
        self.dialog = Statistics_widget(self, self.user_id)
        self.dialog.exec_()

    def update_coll(self, collection=''):  # Функция для обновления self.collection
        if collection:  # Если коллекция передана, то выбираем её, иначе 1 элемент в списке
            self.collection = collection
        else:
            self.collection = self.collection_box.itemText(0)
        if self.collection:  # Если коллекция есть, то берём её айди
            self.collection_id = self.con.cursor().execute("""SELECT col_id FROM collections WHERE title = ?""",
                                                           (self.collection,)).fetchone()[0]
        else:
            self.collection_id = 0

    def update_box(self):  # Функция для обновления comboBox-а
        self.statusbar.showMessage('')
        self.collection_box.clear()
        collections_names = [str(line[0]) for line in
                             self.con.cursor().execute(
                                 """SELECT title FROM collections WHERE user_id = ? ORDER BY title""",
                                 (self.user_id,)).fetchall()]
        for collection in collections_names:
            self.collection_box.addItem(collection)
        index = self.collection_box.findText(self.collection)
        if index != -1:  # Изменяем индекс при добавлении новой коллекции
            self.collection_box.setCurrentIndex(index)

    def update_list(self, collection=''):  # Функция для обновления списка карт в коллекции
        self.update_coll(collection)
        index = self.collection_box.findText(self.collection)
        self.collection_box.setCurrentIndex(index)
        self.label_for_descript.setText('')
        self.cards_in_collection.clear()
        names_of_cards = [(str(line[0]), line[1]) for line in
                          self.con.cursor().execute(
                              """SELECT card_title, card_rating FROM cards WHERE col_id = ? AND user_id = ?""",
                              (self.collection_id, self.user_id))]
        for name, rating in names_of_cards:  # Устанавливаем иконки на карты
            if rating == -1:
                fname = 'ui/photo_data/card_idk.png'
            elif rating <= 3:
                fname = 'ui/photo_data/card_bad.png'
            elif rating <= 7:
                fname = 'ui/photo_data/card_norm.png'
            else:
                fname = 'ui/photo_data/card_best.png'
            self.cards_in_collection.addItem(QListWidgetItem(QIcon(fname), name))
        self.label_for_descript.setStyleSheet('color: black;')
        if not len(names_of_cards) and self.collection_id:  # Изменяем лейбл для информации
            self.label_for_descript.setText('Сейчас нет карточек, добавьте их нажав на плюсик')
        elif not self.collection_id:
            self.label_for_descript.setText('Сейчас нет коллекций, добавьте их нажав на плюсик под профилем')
        else:
            self.label_for_descript.setText(f'Количество карт сейчас: {len(names_of_cards)}')

    def add_collection(self):  # Функция для открытия виджета с добавлением коллекции
        self.statusbar.showMessage('')
        self.dialog = Add_collection_widget(self)
        self.dialog.exec_()

    def add_card(self):  # Функция для открытия виджета с добавлением карты
        if self.collection:
            self.dialog = Add_and_edit_card_widget(self, self.login, self.collection,
                                                   'add')  # Передаём add тк добавляем карту, а не изменяем
            self.dialog.exec_()
        else:
            self.label_for_descript.setStyleSheet('color: red;')
            self.label_for_descript.setText('Сначала добавьте коллекцию!')

    def del_collection(self):  # Функция для открытия виджета с удалением коллекции
        try:
            self.statusbar.showMessage('')
            collection = self.collection_box.currentText()
            if not len(collection):
                raise KeyboardInterrupt
            self.dialog = Delete_dialog_widget(self, collection)
            self.dialog.exec_()
        except KeyboardInterrupt:
            self.statusbar.showMessage('У вас нет коллекций для удаления!')

    def edit_collection(self):  # Функция для открытия виджета с изменением коллекции
        if self.collection:
            self.dialog = Rename_collection_widget(self)
            self.dialog.exec_()
        else:
            self.label_for_descript.setStyleSheet('color: red;')
            self.label_for_descript.setText('Сначала добавьте коллекцию!')

    def edit_card(self, item):  # Функция для открытия виджета с изменением карты
        card_name = item.text()
        self.dialog = Add_and_edit_card_widget(self, self.login, self.collection, 'edit',
                                               card_name)  # edit тк изменяем карту
        self.dialog.exec_()

    def del_card(self):  # Функция для открытия виджета с удалением карты
        try:
            card_text = self.cards_in_collection.selectedItems()[0].text()
            self.label_for_descript.setText('')
            self.dialog = Delete_dialog_widget(self, self.collection, card_text)
            self.dialog.exec_()
        except IndexError:
            self.label_for_descript.setStyleSheet('color: red;')
            self.label_for_descript.setText('Чтобы удалить карту выделите её синим цветом!')

    def start_game(self):  # Функция для начала игры
        nums_of_cards = len(
            self.con.cursor().execute("""SELECT card_title FROM cards WHERE col_id = ? AND user_id = ?""",
                                      (self.collection_id, self.user_id)).fetchall())
        # Делаем подсчёт карт, если карт нет, то пишем об этом, если есть 1, то начинаем игру сразу,
        # иначе открываем окно с выбором кол-ва карт
        if not nums_of_cards:
            self.label_for_descript.setStyleSheet('color: red;')
            self.label_for_descript.setText('Чтобы играть добавьте хотя бы 1 карту!')
        elif nums_of_cards == 1:
            self.widget = Card_game_widget(self, self.login, self.collection)
            self.con.close()
            self.widget.show()
            self.close()
        else:
            self.dialog = Card_count_widget(self)
            self.dialog.exec_()

    def open_help(self):  # Функция для открытия виджета с помощью
        self.dialog = Help_widget(self)
        self.dialog.exec_()


# Виджет (диалог) для добавления коллекции
class Add_collection_widget(QDialog, Ui_Collection_add):
    def __init__(self, parent=None):
        super().__init__()
        self.collection = None
        self.parent = parent
        self.setupUi(self)
        self.label_error.setText('')
        self.label_error.setStyleSheet('color: red;')
        self.btn_save_collection.clicked.connect(self.add_collection)
        self.btn_cancel.clicked.connect(self.exit)
        self.lineEdit_collection_name.textEdited.connect(self.clear_label)

    def clear_label(self):
        self.label_error.setText('')

    def add_collection(self):
        try:
            # Делаем всякие проверки на коллекции
            self.collection = self.lineEdit_collection_name.text()
            if not len(self.collection.strip()):
                raise KeyboardInterrupt
            if ',' in self.collection or '"' in self.collection:
                raise SyntaxError
            collections_names = [str(line[0]) for line in
                                 self.parent.con.cursor().execute("""SELECT title FROM collections WHERE user_id = ?""",
                                                                  (self.parent.user_id,))]
            if self.collection in collections_names:
                raise KeyError
            self.parent.con.cursor().execute("""INSERT INTO collections(title, user_id) VALUES(?, ?)""",
                                             (self.collection, self.parent.user_id))
            self.parent.con.commit()
            self.parent.update_list(self.collection)  # Обновляем всё в родительском виджете
            self.parent.update_box()
            self.close()
        except KeyError:
            self.label_error.setText('Ошибка! Коллекция с таким именем уже есть!')
        except KeyboardInterrupt:
            self.label_error.setText('Ошибка! Название коллекции не должно быть пустым!')
        except SyntaxError:
            self.label_error.setText('В названии коллекции не должно быть , и "')

    def exit(self):
        self.close()


# Виджет (диалог) для изменения имени коллекции
class Rename_collection_widget(QDialog, Ui_Rename_collection):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setupUi(self)
        self.lineEdit_old.setText(self.parent.collection)
        self.lineEdit_new.setText('')
        self.label_error.setText('')
        self.btn_rename_collection.clicked.connect(self.rename_coll)
        self.btn_cancel.clicked.connect(self.exit)

    def rename_coll(self):
        try:
            # Делаем всякие проверки на коллекцию
            new_name = str(self.lineEdit_new.text())
            if not len(new_name.strip()):
                raise KeyboardInterrupt
            if ',' in new_name or '"' in new_name:
                raise SyntaxError
            if self.parent.collection == new_name:
                raise ValueError
            collections_names = [str(line[0]) for line in
                                 self.parent.con.cursor().execute("""SELECT title FROM collections WHERE user_id = ?""",
                                                                  (self.parent.user_id,))]
            if new_name in collections_names:
                raise KeyError
            self.parent.con.cursor().execute("""UPDATE collections
            SET title = ? WHERE col_id = ? AND user_id = ?""",
                                             (new_name,
                                              self.parent.collection_id, self.parent.user_id))
            self.parent.con.commit()
            self.parent.update_list(new_name)  # Обновляем всё у родительского виджета
            self.parent.update_box()
            self.close()
        except KeyError:
            self.label_error.setText('Ошибка! Коллекция с таким именем уже есть!')
        except KeyboardInterrupt:
            self.label_error.setText('Ошибка! Название коллекции не должно быть пустым!')
        except ValueError:
            self.label_error.setText('Ошибка! Название коллекции не должно совпадать со старым!')
        except SyntaxError:
            self.label_error.setText('В названии коллекции не должно быть , и "')

    def exit(self):
        self.close()


# Виджет (диалог) для удаления карты / коллекции
class Delete_dialog_widget(QDialog, Ui_Delete_window):
    def __init__(self, parent=None, collection='', card=''):
        super().__init__()
        self.parent = parent
        self.collection = collection
        self.card = card
        self.setupUi(self)
        if not self.card:  # Если карта передана, то мы удаляем карту, иначе коллекцию
            self.textBrowser_delete.setHtml(html_get_to_delete_window(self.collection))
        else:
            self.setWindowTitle('Удалить карточку')
            self.textBrowser_delete.setHtml(html_get_to_delete_window(self.collection, self.card))
        self.btn_cancel.clicked.connect(self.exit)
        self.btn_delete.clicked.connect(self.delete_smt)

    def delete_smt(self):  # Функция для удаления чего-либо
        collection_id = self.parent.con.cursor().execute("""SELECT col_id FROM collections WHERE title = ?""",
                                                         (self.collection,)).fetchone()[0]
        if not self.card:  # Если карты есть, то удаляем карту, инчае коллекцию
            self.parent.con.cursor().execute("""DELETE FROM collections WHERE col_id = ?""",
                                             (collection_id,))
            photos = []
            # Делаем перебор по картам в коллекции, в которых есть фотки и удаляем их из папки БД с фотками
            for line in filter(lambda x: 'f' in x[0], self.parent.con.cursor().execute(
                    """SELECT card_type, front_data, back_data FROM cards WHERE col_id = ?""",
                    (collection_id,)).fetchall()):
                if line[0][0] == 'f':
                    photos.append(line[1])
                if line[0][1] == 'f':
                    photos.append(line[2])
            delete_photos(photos)

            self.parent.con.cursor().execute("""DELETE FROM cards WHERE col_id = ?""",
                                             (collection_id,))
        else:
            card = self.parent.con.cursor().execute(
                """SELECT card_type, front_data, back_data FROM cards WHERE col_id = ? AND card_title = ?""",
                (collection_id, self.card)).fetchone()
            # Удаляем фотки если они есть
            if card[0][0] == 'f':
                delete_photos([card[1]])
            if card[0][1] == 'f':
                delete_photos([card[2]])

            self.parent.con.cursor().execute("""DELETE FROM cards WHERE col_id = ? AND card_title = ?""",
                                             (collection_id, self.card))
        self.parent.con.commit()
        self.parent.update_box()
        self.parent.update_list()  # Не передаём ничего, тк удалили коллекции,
        self.close()

    def exit(self):
        self.close()


# Виджет (диалог) для добавления или изменения карты
class Add_and_edit_card_widget(QDialog, Ui_Add_and_change_card):
    def __init__(self, parent=None, login='', collection='', mode='', card_name=''):
        super().__init__()
        self.fdirectory_front_old = None
        self.fdirectory_back_old = None
        self.fdirectory_back = None
        self.fdirectory_front = None
        self.parent = parent
        self.login = login
        self.collection = collection
        self.mode = mode
        self.card_name = card_name
        self.setupUi(self)
        qs_pol = QSizePolicy()
        qs_pol.setRetainSizeWhenHidden(True)
        self.btn_add_photo_front.setSizePolicy(qs_pol)
        self.btn_add_photo_back.setSizePolicy(qs_pol)
        self.btn_change_card.setSizePolicy(qs_pol)
        if self.mode == 'add':  # Если тип add, то добавляем карту и прячем другие кнопки
            self.reformat_widget([False, False, False, False])
            self.btn_change_card.setVisible(False)
            self.btn_event_card.setText('Добавить карту')
            self.lineEdit_card_name.setReadOnly(False)
        else:  # Меняем главное окно и прячем некоторые кнопки
            icon = QIcon()
            icon.addPixmap(QPixmap("ui/photo_data/pencil.png"), QIcon.Normal, QIcon.Off)
            self.setWindowTitle('Посмотреть карту')
            self.setWindowIcon(icon)
            self.card_data = self.parent.con.cursor().execute(
                """SELECT * FROM cards WHERE user_id = ? AND col_id = ? AND card_title = ?""",
                (self.parent.user_id, self.parent.collection_id, self.card_name)).fetchone()
            self.lineEdit_card_name.setText(self.card_name)
            self.btn_add_photo_front.setVisible(False)
            self.btn_add_photo_back.setVisible(False)
            self.btn_event_card.setVisible(False)
            self.btn_event_card.setText('Подтвердить изменения')
            self.comboBox.setVisible(False)
            self.btn_change_card.clicked.connect(self.start_edit)
            self.show_card()
        self.btn_cancel.clicked.connect(self.exit)
        self.label_photo_front.setScaledContents(True)
        self.label_photo_back.setScaledContents(True)
        self.btn_event_card.clicked.connect(self.add_card)
        self.btn_add_photo_front.clicked.connect(self.photo_add)
        self.btn_add_photo_back.clicked.connect(self.photo_add)
        self.comboBox.textHighlighted.connect(self.card_type)
        self.label_error.setText('')

    def show_card(self):  # Показываем карту, если мод edit
        self.textEdit_back.setReadOnly(True)
        self.textEdit_front.setReadOnly(True)
        # В stackedWidget 0 индекс - текст, 1 индекс - картинка
        if self.card_data[2][0] == 't':
            self.stackedWidget_front.setCurrentIndex(0)
            self.textEdit_front.setHtml(html_get_to_card_game_text(self.card_data[3]))
        else:
            self.stackedWidget_front.setCurrentIndex(1)
            self.fdirectory_front = f'databases/users_photos/{self.card_data[3]}'
            self.fdirectory_front_old = self.fdirectory_front
            pix = QPixmap(self.fdirectory_front)
            w, h, = pix.width(), pix.height()
            self.label_photo_front.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio))
        if self.card_data[2][1] == 't':
            self.textEdit_back.setHtml(html_get_to_card_game_text(self.card_data[4]))
            self.stackedWidget_back.setCurrentIndex(0)
        else:
            self.stackedWidget_back.setCurrentIndex(1)
            self.fdirectory_back = f'databases/users_photos/{self.card_data[4]}'
            self.fdirectory_back_old = self.fdirectory_back
            pix = QPixmap(self.fdirectory_back)
            w, h, = pix.width(), pix.height()
            self.label_photo_back.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio))

    def start_edit(self):  # Начало редактирования карты, если нажата кнопка с редактированием
        self.setWindowTitle('Редактирование карты')
        self.btn_change_card.setEnabled(False)
        self.btn_event_card.setVisible(True)
        self.comboBox.setVisible(True)
        self.textEdit_back.setReadOnly(False)
        self.textEdit_front.setReadOnly(False)
        self.lineEdit_card_name.setReadOnly(False)
        index = (2 if self.card_data[2][0] == 'f' else 0) + (
            1 if self.card_data[2][1] == 'f' else 0)  # Выбор comboBox-а
        if index in (1, 3):
            self.btn_add_photo_front.setVisible(True)
        if index in (2, 3):
            self.btn_add_photo_back.setVisible(True)
        self.comboBox.setCurrentIndex(index)
        self.update_text_on_btns()

    def exit(self):
        self.close()

    def photo_add(self):  # Функция для добавления фотки при режимах с фотками
        self.label_error.setText('')
        sender = self.sender()
        fdirectory = QFileDialog.getOpenFileName(
            self, 'Выбрать картинку', '',
            'Картинка (*.jpg *.png *.jpeg)')[0]
        if not fdirectory:
            return
        pix = QPixmap(fdirectory)
        w, h, = pix.width(), pix.height()
        if sender == self.btn_add_photo_front:
            self.label_photo_front.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio))
            self.fdirectory_front = fdirectory
        else:
            self.label_photo_back.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio))
            self.fdirectory_back = fdirectory
        self.update_text_on_btns()

    def update_text_on_btns(self):  # Функция для изменения текста в кнопках, если есть фотка
        if self.fdirectory_front:
            self.btn_add_photo_front.setText('Изменить картинку')
        if self.fdirectory_back:
            self.btn_add_photo_back.setText('Изменить картинку')

    def card_type(self, text):  # Функция для изменения вида виджета
        self.label_error.setText('')
        if text == 'Текст -> Текст':
            self.reformat_widget([False, False, False, False])
        elif text == 'Текст -> Картинка':
            self.reformat_widget([False, True, False, True])
        elif text == 'Картинка -> Текст':
            self.reformat_widget([True, False, True, False])
        else:
            self.reformat_widget([True, True, True, True])
        index = self.comboBox.findText(text)
        self.comboBox.setCurrentIndex(index)

    def reformat_widget(self, pars):  # Функция для изменения вида
        self.btn_add_photo_front.setVisible(pars[0])
        self.btn_add_photo_back.setVisible(pars[1])
        self.stackedWidget_front.setCurrentIndex(1 if pars[2] else 0)
        self.stackedWidget_back.setCurrentIndex(1 if pars[3] else 0)

    def add_card(self):  # Функция для добавления карты
        try:
            self.label_error.setText('')
            type_of_card = self.comboBox.currentText()
            card_name = str(self.lineEdit_card_name.text())
            # Проверка названия карты
            if not card_name.strip():
                raise KeyboardInterrupt
            if ',' in card_name or '"' in card_name:
                raise SyntaxError
            cards = [str(line[0]) for line in
                     self.parent.con.cursor().execute(
                         """SELECT card_title FROM cards WHERE user_id = ? AND col_id = ?""",
                         (self.parent.user_id, self.parent.collection_id)).fetchall()]
            if card_name in cards and self.card_name != card_name:
                raise KeyError
            if type_of_card == 'Текст -> Текст':
                if self.mode == 'edit':  # Если мод edit, то удаляем фотки, если таковые были
                    if not (self.fdirectory_back_old is None):
                        delete_photos(
                            [self.fdirectory_back_old.split('/')[-1]])
                    if not (self.fdirectory_front_old is None):
                        delete_photos(
                            [self.fdirectory_front_old.split('/')[-1]])
                data_front, data_back = self.textEdit_front.toPlainText(), self.textEdit_back.toPlainText()
                if not data_back.strip() or not data_front.strip():
                    raise IndexError
                self.insert_to_db(
                    [self.parent.user_id, self.parent.collection_id, 'tt', data_front, data_back, card_name, '-1'])
            elif type_of_card == 'Текст -> Картинка':
                self.fdirectory_front = ''
                data_front = self.textEdit_front.toPlainText()
                if not data_front.strip():
                    raise IndexError
                if self.fdirectory_back is None:
                    raise TypeError
                if self.mode == 'edit':  # Проверка картинок
                    self.check_image()
                file_name_back = self.fdirectory_back.split('/')[-1]
                if self.fdirectory_back != self.fdirectory_back_old:
                    if check_path(file_name_back):
                        n = 1
                        new_file_name_back = file_name_back
                        while check_path(new_file_name_back):
                            new_file_name_back = f"{'.'.join(file_name_back.split('.')[:-1])}_{n}." \
                                                 f"{file_name_back.split('.')[-1]}"
                            n += 1
                        file_name_back = new_file_name_back
                self.insert_to_db(
                    [self.parent.user_id, self.parent.collection_id, 'tf', data_front, file_name_back, card_name, '-1'])
                image_back = QImage(self.fdirectory_back)
                image_back.save(f'databases/users_photos/{file_name_back}')  # Сохраняем фотки
            elif type_of_card == 'Картинка -> Текст':
                data_back = self.textEdit_back.toPlainText()
                self.fdirectory_back = ''
                if not data_back.strip():
                    raise IndexError
                if self.fdirectory_front is None:
                    raise TypeError
                if self.mode == 'edit':  # Проверка картинок
                    self.check_image()
                file_name_front = self.fdirectory_front.split('/')[-1]
                if self.fdirectory_front != self.fdirectory_front_old:
                    if check_path(file_name_front):
                        n = 1
                        new_file_name_front = file_name_front
                        while check_path(new_file_name_front):
                            new_file_name_front = f"{'.'.join(file_name_front.split('.')[:-1])}_{n}." \
                                                  f"{file_name_front.split('.')[-1]}"
                            n += 1
                        file_name_front = new_file_name_front
                    image_front = QImage(self.fdirectory_front)
                    image_front.save(f'databases/users_photos/{file_name_front}')  # Сохраняем фотки
                self.insert_to_db(
                    [self.parent.user_id, self.parent.collection_id, 'ft', file_name_front, data_back, card_name,
                     '-1'])
            else:
                if self.fdirectory_front is None or self.fdirectory_back is None:
                    raise TypeError
                if self.mode == 'edit':  # Проверка картинок
                    self.check_image()
                file_name_front = self.fdirectory_front.split('/')[-1]
                if self.fdirectory_front != self.fdirectory_front_old:
                    if check_path(file_name_front):
                        n = 1
                        new_file_name_front = file_name_front
                        while check_path(new_file_name_front):
                            new_file_name_front = f"{'.'.join(file_name_front.split('.')[:-1])}_{n}." \
                                                  f"{file_name_front.split('.')[-1]}"
                            n += 1
                        file_name_front = new_file_name_front
                    image_front = QImage(self.fdirectory_front)
                    image_front.save(f'databases/users_photos/{file_name_front}')  # Сохраняем фотки
                file_name_back = self.fdirectory_back.split('/')[-1]
                if self.fdirectory_back != self.fdirectory_back_old:
                    if check_path(file_name_back):
                        n = 1
                        new_file_name_back = file_name_back
                        while check_path(new_file_name_back):
                            new_file_name_back = f"{'.'.join(file_name_back.split('.')[:-1])}_{n}." \
                                                 f"{file_name_back.split('.')[-1]}"
                            n += 1
                        file_name_back = new_file_name_back
                    image_back = QImage(self.fdirectory_back)
                    image_back.save(f'databases/users_photos/{file_name_back}')  # Сохраняем фотки
                self.insert_to_db(
                    [self.parent.user_id, self.parent.collection_id, 'ff', file_name_front, file_name_back, card_name,
                     '-1'])
        except KeyboardInterrupt:
            self.label_error.setText('Название карты не должно быть пустым!')
        except KeyError:
            self.label_error.setText('Такое название карты уже есть!')
        except SyntaxError:
            self.label_error.setText('В названии карты не должно быть " и ,')
        except IndexError:
            self.label_error.setText('Текст в карточках не должен быть пустым!')
        except TypeError:
            self.label_error.setText('Ошибка! Вставьте картинку!')

    def check_image(self):  # Функция для удаления фоток (режимы только с картинками)
        if self.fdirectory_back != self.fdirectory_back_old and not (self.fdirectory_back_old is None):
            delete_photos([self.fdirectory_back_old.split('/')[-1]])
        if self.fdirectory_front != self.fdirectory_front_old and not (self.fdirectory_front_old is None):
            delete_photos([self.fdirectory_front_old.split('/')[-1]])

    def insert_to_db(self, spis):  # Функция для добавления / изменения карт
        if self.mode == 'add':
            self.parent.con.cursor().execute("""INSERT INTO 
            cards(user_id, col_id, card_type, front_data, back_data, card_title, card_rating) 
            VALUES(?, ?, ?, ?, ?, ?, ?)""", tuple(spis))
            self.parent.con.commit()
            self.parent.update_list(self.collection)
            self.close()
        else:
            spis = spis[2:]
            self.parent.con.cursor().execute("""UPDATE cards 
            SET card_type = ?, front_data = ?, back_data = ?, card_title = ?, card_rating = ?
            WHERE user_id = ? AND col_id = ? AND card_type = ? AND 
            front_data = ? AND back_data = ? AND card_title = ? AND card_rating = ?""",
                                             tuple(spis + list(self.card_data)))
            self.parent.con.commit()
            self.parent.update_list(self.collection)
            self.close()


# Виджет (диалог) для выбора количества карт
class Card_count_widget(QDialog, Ui_Card_amount):
    def __init__(self, parent=None):
        super().__init__()
        self.widget = None
        self.parent = parent
        self.setupUi(self)
        self.btn_continue.clicked.connect(self.play_game)
        self.btn_cancel.clicked.connect(self.exit)
        nums_of_cards = len(
            self.parent.con.cursor().execute("""SELECT card_title FROM cards WHERE col_id = ? AND user_id = ?""",
                                             (self.parent.collection_id, self.parent.user_id)).fetchall())
        # Ставим максимальное кол-во карт
        self.spinBox_cards.setMaximum(nums_of_cards)
        self.spinBox_cards.setValue(nums_of_cards)

    def exit(self):
        self.close()

    def play_game(self):  # Функция для начала игры
        self.widget = Card_game_widget(self, self.parent.login, self.parent.collection, self.spinBox_cards.value())
        self.parent.con.close()
        self.widget.show()
        self.close()
        self.parent.close()


# Виджет для игры
class Card_game_widget(QMainWindow, Ui_Card_game):
    def __init__(self, parent=None, login='', collection='', cards_num=1):
        super().__init__()
        self.parent = parent
        self.login = login
        self.collection = collection
        self.cards_num = cards_num
        self.now_card_index = 0
        self.corr_cards = 0
        self.widget = None
        self.now_card = None
        self.correct_cards, self.incorrect_cards = [], []
        self.con = sqlite3.connect('databases/data')
        self.user_id = self.con.cursor().execute("""SELECT id FROM users WHERE login = ?""", (self.login,)).fetchone()[
            0]
        self.collection_id = self.con.cursor().execute("""SELECT col_id FROM collections WHERE title = ?""",
                                                       (self.collection,)).fetchone()[0]
        # Создаём список с картами в игре, сортируем по рейтингу
        self.cards = self.con.cursor().execute(
            """SELECT * FROM cards WHERE user_id = ? AND col_id = ? ORDER BY card_rating""",
            (self.user_id, self.collection_id)).fetchall()[:self.cards_num]
        self.setupUi(self)
        self.label_back_photo.setScaledContents(True)
        self.label_front_photo.setScaledContents(True)
        pix = QPixmap('ui/photo_data/question.jpg')
        w, h, = pix.width(), pix.height()
        self.label_back_photo.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio))
        self.stackedWidget_back.setCurrentIndex(1)
        self.btn_back_to_menu.clicked.connect(self.exit)
        self.btn_open_card.clicked.connect(self.open_card)
        self.btn_remember.clicked.connect(self.next_card)
        self.btn_forgot.clicked.connect(self.next_card)
        self.btn_remember.setVisible(False)
        self.btn_forgot.setVisible(False)
        self.open_new_card()

    def next_card(self):  # Функция для переключения на следующую карту
        # В stackedWidget 0 индекс - текст, 1 индекс - картинка
        if self.cards_num - 1 != self.now_card_index:
            self.card_text_back.setText('')
            self.card_text_front.setText('')
            pix = QPixmap('ui/photo_data/question.jpg')
            w, h, = pix.width(), pix.height()
            self.label_back_photo.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio))
            self.stackedWidget_back.setCurrentIndex(1)
            self.btn_remember.setVisible(False)
            self.btn_forgot.setVisible(False)
            self.btn_open_card.setVisible(True)
            self.now_card_index += 1
            self.update_card_rating(self.sender())
            self.open_new_card()
        else:  # Если карт больше нет, то заканчиваем игру
            self.update_card_rating(self.sender())
            self.con.close()
            self.widget = End_game_widget(self, self.login, self.collection, self.cards_num, self.corr_cards)
            self.widget.show()
            self.close()

    def update_card_rating(self, from_who):  # Функция для обновления рейтинга карты
        rate = self.now_card[-1]
        # Максимальный рейтинг карты - 10, минимальный - 0
        if from_who == self.btn_remember:
            self.correct_cards.append(self.now_card[-2])
            if rate == -1:
                self.request_to_db((5, self.user_id, self.collection_id, self.now_card[-2]))
            else:
                self.request_to_db((min(10, rate + 1), self.user_id, self.collection_id, self.now_card[-2]))
            self.corr_cards += 1
        else:
            self.incorrect_cards.append(self.now_card[-2])
            if rate == -1:
                self.request_to_db((3, self.user_id, self.collection_id, self.now_card[-2]))
            else:
                self.request_to_db((max(0, rate - 1), self.user_id, self.collection_id, self.now_card[-2]))

    def request_to_db(self, tupl):  # Функция для обновления рейтинга в БД
        self.con.cursor().execute("""UPDATE cards 
        SET card_rating = ? WHERE user_id = ? AND col_id = ? AND card_title = ?""", tupl)
        self.con.commit()

    def show_card_rating(self, rate):  # Функция для отображения рейтинга карты в label
        if rate == -1:
            self.label_rate.setText('Вы ещё не видели эту карту.')
            self.label_rate.setStyleSheet('color: black;')
        elif rate <= 3:
            self.label_rate.setText('Вы плохо знаете эту карту...')
            self.label_rate.setStyleSheet('color: red;')
        elif rate <= 7:
            self.label_rate.setText('Вы хорошо знаете эту карту!')
            self.label_rate.setStyleSheet('color: blue;')
        else:
            self.label_rate.setText('Вы отлично знаете эту карту!')
            self.label_rate.setStyleSheet('color: green;')

    def open_new_card(self):  # Функция для изменения информации в виджетах
        self.card_text_back.setText('')
        self.card_text_front.setText('')
        self.now_card = self.cards[self.now_card_index]
        self.show_card_rating(self.now_card[-1])
        if self.now_card[2][0] == 't':
            self.stackedWidget_front.setCurrentIndex(0)
            self.card_text_front.setHtml(html_get_to_card_game_text(self.now_card[3]))
        else:
            self.stackedWidget_front.setCurrentIndex(1)
            pix = QPixmap(f'databases/users_photos/{self.now_card[3]}')
            w, h, = pix.width(), pix.height()
            self.label_front_photo.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio))
        self.label_card_number.setText(f'Номер карты: {self.now_card_index + 1}')

    def open_card(self):  # Функция для открытия карты
        if self.now_card[2][1] == 't':
            self.card_text_back.setHtml(html_get_to_card_game_text(self.now_card[4]))
            self.stackedWidget_back.setCurrentIndex(0)
        else:
            self.stackedWidget_back.setCurrentIndex(1)
            pix = QPixmap(f'databases/users_photos/{self.now_card[4]}')
            w, h, = pix.width(), pix.height()
            self.label_back_photo.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio))
        self.btn_open_card.setVisible(False)
        self.btn_remember.setVisible(True)
        self.btn_forgot.setVisible(True)

    def closeEvent(self, event, **kwargs):  # Функция для сохранения итогов игры при закрытии виджета
        true_cards = f"{', '.join(self.correct_cards)}"
        false_cards = f"{', '.join(self.incorrect_cards)}"
        current_date = datetime.now().strftime('Дата: %d.%m.%Y Время: %H:%M')
        if false_cards + true_cards:
            with open('databases/users_rating.csv', encoding="utf8", mode='a+') as f:
                f.write(f'\n{self.user_id};"{self.collection}";"{true_cards}";"{false_cards}";"{current_date}"')
        self.con.close()
        event.accept()

    def exit(self):
        self.con.close()
        self.widget = Collection_widget(self, self.login, self.collection)
        self.widget.show()
        self.close()


# Виджет для конца игры
class End_game_widget(QMainWindow, Ui_EndGame):
    def __init__(self, parent=None, login='', collection='', cards_num=1, corr_cards=0):
        super().__init__()
        self.parent = parent
        self.login = login
        self.collection = collection
        self.cards_num = cards_num
        self.corr_cards = corr_cards
        self.widget = None
        self.setupUi(self)
        self.set_texts()
        self.btn_back_to_menu.clicked.connect(self.exit)
        self.btn_restart_game.clicked.connect(self.game_again)

    def set_texts(self):  # Функция для изменения текста в textBrowsers
        self.textBrowser_card_kol.setHtml(html_get_to_num_of_card(self.cards_num, self.corr_cards))
        coeff = round(self.corr_cards / self.cards_num, 2)
        if coeff >= 0.7:
            self.textBrowser_rating.setHtml(html_get_to_user_fun(choice(GOOD_GAME), 'green'))
        elif coeff >= 0.4:
            self.textBrowser_rating.setHtml(html_get_to_user_fun(choice(MEDIUM_GAME), 'blue'))
        else:
            self.textBrowser_rating.setHtml(html_get_to_user_fun(choice(BAD_GAME), 'red'))

    def game_again(self):
        self.parent.con.close()
        self.widget = Card_game_widget(self, self.login, self.collection, self.cards_num)
        self.widget.show()
        self.close()

    def exit(self):
        self.parent.con.close()
        self.widget = Collection_widget(self, self.login, self.collection)
        self.widget.show()
        self.close()


# Виджет (дивлог) помощи
class Help_widget(QDialog, Ui_Help_menu):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setupUi(self)
        self.label_about_what.setText('Профиль')
        self.index = 0
        self.btn_left.clicked.connect(self.move_page)
        self.btn_right.clicked.connect(self.move_page)
        self.btn_exit.clicked.connect(self.exit)

    def move_page(self):  # Функция для перелистывания между страницами StackedWidgets
        if self.sender() == self.btn_left:
            self.index = max(0, self.index - 1)
        else:
            self.index = min(3, self.index + 1)
        self.update_all()

    def update_all(self):  # Функция для изменения дизайна виджета
        if self.index == 0:
            self.label_about_what.setText('Профиль')
        elif self.index == 1:
            self.label_about_what.setText('Коллекции')
        elif self.index == 2:
            self.label_about_what.setText('Карточки')
        else:
            self.label_about_what.setText('Просмотр и изменение карточек')
        self.stackedWidget_help.setCurrentIndex(self.index)

    def exit(self):
        self.close()


# Виджет (диалог) статистики
class Statistics_widget(QDialog, Ui_Dialog_statistics):
    def __init__(self, parent=None, user_id=''):
        super().__init__()
        self.parent = parent
        self.user_id = user_id
        self.setupUi(self)
        self.btn_exit.clicked.connect(self.exit)
        self.update_all()

    def update_all(self):  # Функция для выведения информации на экран
        # Берём всю информацию из нашего файла
        with open('databases/users_rating.csv', encoding="utf8") as csvfile:
            reader = csv.reader(csvfile, delimiter=';', quotechar='"')
            data = list(filter(lambda x: x[0] == str(self.user_id), reader))
        if not len(data):  # Если статистики нет, то говорим об этом
            n, t, f = 0, 0, 0
            self.textBrowser_rating.setText('Вы ещё не сыграли ни одной игры! Скорее пробуйте!')
        else:
            # n - кол-во карт, t - кол-во правильных карт, f - кол-во неправильных карт
            n, t, f = len(data), sum([1 if card else 0 for line in data for card in line[2].split(', ')]), sum(
                [1 if card else 0 for line in data for card in line[3].split(', ')])
            # Супер крутое списочное выражение, которое превращает информацию из карты в html текст, а
            # сортирует по дате и времени
            html_text = [html_get_to_statistics(*line[1:], n,
                                                round((get_num(line[2]) / (get_num(line[2]) + get_num(line[3]))) * 100))
                         for n, line in enumerate(sorted(data, key=lambda x: (
                            int(x[-1].split('.')[2].split()[0]), int(x[-1].split('.')[1]),
                            int(x[-1].split('.')[0].split()[1]), int(''.join(x[-1].split(':')[-2:])))), 1)]
            self.textBrowser_rating.setHtml(''.join(html_text[::-1]))
        self.label_count_games.setText(f'Количество игр всего: {n}')
        self.label_count_true_card.setText(f'Количество правильных карт: {t}')
        self.label_count_false_card.setText(f'Количество неправильных карт: {f}')

    def exit(self):
        self.close()


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Добавляем шрифты в БД
    path = os.getcwd().replace('\\', '/')
    QFontDatabase.addApplicationFont(fr'{path}/ui/fonts/Open_Sans.ttf')
    QFontDatabase.addApplicationFont(fr'{path}/ui/fonts/VAG_WORLD.ttf')
    # Выключаем ловление ошибок
    logging.captureWarnings(False)
    form = Registration_widget()
    form.show()
    sys.excepthook = except_hook
    sys.exit(app.exec_())
