import os
import errno
import json
import time
from src.trader import LOG_DIRECTORY
from src.trader import TRADER
from src.dbase import TOKEN, TASK, REPORT, TRADE
from src.burse import Exmo
from urllib.parse import quote_plus
from selenium.common.exceptions import NoSuchElementException


TGBot = 'TBot'

class SESSION:
    __session_is_done = False
    timeout = 60

    def __init__(self, chat_id, send_message):
        self.chat_id = chat_id
        self.send = send_message


    def put_next_step(self, func):
        self.next_func = func

    def create_log_file(self, chat_it):
        name_folder = 'chat id - %s' % chat_it
        method_name = "%s" % self.__class__.__name__
        name_log = 'log.txt'
        self.current_log_directory = os.path.join(LOG_DIRECTORY, TGBot, name_folder, method_name)
        self.log = os.path.join(self.current_log_directory, name_log)
        if not os.path.exists(self.current_log_directory):
            self.make_sure_path_exists(self.current_log_directory)

    def make_sure_path_exists(self, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    def logging(self, message, printed=False):
        try:
            fl = open(self.log, 'a')
            if printed:
                print(message)
        except:
            fl = open(self.log, 'w')
        fl.write("%s:\n %s\n" % (time.ctime(), message))
        fl.close()

    def get_next_step(self):
        return self.next_func

    def run(self, txt):
        self.reset_timeout()
        func = self.get_next_step()
        self.logging('                                %s' % txt)
        return func(txt)

    def reset_timeout(self):
        self.time = time.time()

    def session_is_done(self):
        return self.__session_is_done

    def put_session_complited(self):
        self.__session_is_done = True

    def is_timeouted(self):
        return time.time() - self.time > self.timeout

    def send_msg(self, txt):
        self.logging(txt)
        return self.send(self.chat_id, txt)


class NEW(SESSION):
    burse_list = {'EXMO': Exmo}

    def __init__(self, chat_id, send_msg, db):
        super().__init__(chat_id, send_msg)
        self.reset_timeout()
        self.trader = TRADER()
        self.user_burse = None
        self.user_pair = None
        self.user_token = None
        self.put_next_step(self.begin_chat)
        self.db = db
        self.__pair_confirmed = False
        self.__burse_confirmed = False
        self.DEBUG_COUNTER = 0

        self.tokens = None
        self.create_log_file(self.chat_id)


    def show_menu(self):
        if self.burse_is_confirmed():
            burse = self.__get_user_burse()
        else:
            burse = '...'
        if self.pair_is_confirmed():
            pair = self.__get_user_pair()
        else:
            pair = '...'

        menu = 'Создание новой пары.\n' \
               '\n' \
               'Выберите номер:\n' \
               '1. Биржа - (%s)\n' \
               '2. Пара - (%s)\n' \
               '3. Настройки пары\n' \
               '4. Подтверждение создания пары\n' \
               '\n' \
               '0. Выход.' \
               '' % (burse, pair)
        return menu

    def show_menu_burse(self):
        burse = self.__get_user_burse()
        token = self.__get_user_token_name()
        menu = 'Меню настройки биржы.\n' \
               '\n' \
               'Выберите номер:\n' \
               '1. Выбор биржы - (%s)\n' \
               '2. Настройки токена биржы - (%s)\n' \
               '3. Подтвердить ввод настроек\n' \
               '\n' \
               '0. Назад' \
               '' % (burse, token)
        return menu

    def show_menu_token(self):
        user_token = self.__get_user_token_name()
        menu = 'Меню ввода токена.\n' \
               '\n' \
               'Выберите номер:\n' \
               '1. Выбор токена - (%s)\n' \
               '2. Ввод нового токена\n' \
               '3. Удаление токена\n' \
               '\n' \
               '0. Назад' \
               '' % (user_token)
        return menu

    def show_menu_params(self):
        params = self.trader.params
        menu = 'Выберите нужный параметр:'
        for num, param in enumerate(params, 1):
            menu += '\n%s. %s (%s)' % (num, param, self.trader.__getattribute__(param))
        menu += '\n' \
                '\n' \
                '0. Назад'
        return menu

    def show_menu_change_param(self):
        info_param = self.trader.params[self.change_param]
        value = self.trader.__getattribute__(self.change_param)
        menu = 'Описание параметра: \n' \
               '%s\n' \
               '\n' \
               'Выберите номер:\n' \
               '1. Ввод параметра (%s)\n' \
               '\n' \
               '0. Назад.' \
               '' % (info_param, value)
        return menu

    def show_menu_accept(self):
        menu = 'Вы уверены, что хотите создать новую пару? \n' \
               '\n' \
               'Выберите номер:\n' \
               '1. Да\n'\
               '0. Нет\n' \

        return menu

    def put_item_menu(self, txt):
        if txt not in ['0', '1', '2', '3', '4']:
            self.send_msg('Не корректный номер. Повторите ввод.')
            return
        if txt == '0':
            self.put_session_complited()
            self.send_msg('Выход из сессии.')
            return
        elif txt == '1':
            self.put_next_step(self.put_item_menu_burse)
            self.send_msg(self.show_menu_burse())
            return
        elif txt == '2':
            if not self.burse_is_confirmed():
                self.send_msg('Введите сначала биржу!')
                return
            self.put_next_step(self.put_pair)
            self.send_msg('Введите пару!')
            return
        elif txt == '3':
            if not self.burse_is_confirmed() or not self.pair_is_confirmed():
               self.send_msg('Введите сначада пару!')
               return
            self.put_next_step(self.put_item_menu_param)
            self.send_msg(self.show_menu_params())
            return
        elif txt == '4':
            if not self.burse_is_confirmed() or not self.pair_is_confirmed():
                self.send_msg('Введите сначала биржу и пару!')
                return
            self.put_next_step(self.put_item_menu_accept)
            self.send_msg(self.show_menu_accept())
            return

    def put_param(self, txt):
        print(self.trader.__getattribute__(self.change_param))
        format = self.get_format_param(self.trader.__getattribute__(self.change_param))
        print(format)
        if not self.is_format_param(txt, format):
            self.send_msg('Неверный формат параметра! Повторите ввод.')
        else:
            value = format(txt)
            self.trader.__setattr__(self.change_param, value)
            self.put_next_step(self.put_item_menu_param)
            self.send_msg('Параметр введен!')
            self.send_msg(self.show_menu_params())
            self.change_param = None

    def get_format_param(self, txt):
        try:
            self.to_bool(txt)
        except:
            return float
        else:
            return self.to_bool

    def is_format_param(self, param, format):
        try:
            format(param)
        except:
            return False
        else:
            return True

    def to_bool(self, txt):
        if type(txt) is not bool:
            txt = txt.upper()
        if txt in [True, 'TRUE', '1']:
            return True
        elif txt in [False, 'FALSE', '0']:
            return False
        else:
            print('not bool')
            raise Exception('Not bool')

    def put_item_menu_burse(self, txt):
        if txt not in ['0', '1', '2', '3']:
            self.send_msg('Не корректный номер. Повторите ввод.')
            return
        if txt == '0':
            self.put_next_step(self.put_item_menu)
            self.send_msg(self.show_menu())
            return
        elif txt == '1':
            self.put_next_step(self.put_burse)
            self.__burse_confirmed = False
            self.__pair_confirmed = False
            self.send_msg('Выберите биржу из списка: \n%s' % self.show_burse())
            return
        elif txt == '2':
            self.put_next_step(self.put_item_menu_token)
            self.__burse_confirmed = False
            self.__pair_confirmed = False
            self.send_msg(self.show_menu_token())
            return
        elif txt == '3':
            result = self.accept_setup_burse()
            if not result:
                self.send_msg('Настройки введены неверно! Повторите ввод.')
                return
            self.DEBUG_COUNTER = 0
            self.send_msg('Биржа успешно введена!')
            self.put_next_step(self.put_item_menu)
            self.__burse_confirmed = True
            self.send_msg(self.show_menu())
            return

    def put_item_menu_token(self, txt):
        if txt not in ['0', '1', '2', '3']:
            self.send_msg('Не корректный номер. Повторите ввод.')
            return
        if txt == '0':
            self.put_next_step(self.put_item_menu_burse)
            self.send_msg(self.show_menu_burse())
            return
        elif txt == '1':
            self.put_next_step(self.put_token)
            self.__burse_confirmed = False
            self.send_msg('Выберите токен из списка: \n%s' % self.show_tokens_by_name())
            return
        elif txt == '2':
            self.put_next_step(self.put_new_token)
            self.__burse_confirmed = False
            self.send_msg('Введите имя токена (по нему осуществлется выбор токена)!')
            return
        elif txt == '3':
            self.put_next_step(self.del_token)
            self.__burse_confirmed = False
            self.send_msg('Выберите токен из списка: \n%s' % self.show_tokens_by_name())
            return

    def put_item_menu_accept(self, txt):
        if txt not in ['0', '1']:
            self.send_msg('Не корректный номер. Повторите ввод.')
            return
        if txt == '0':
            self.put_next_step(self.put_item_menu)
            self.send_msg(self.show_menu())
            return
        elif txt == '1':
            result, task_id = self.create_task()
            if not result:
                self.send_msg('Ошибка. Новая пара не зарегистрирована!')
                self.put_next_step(self.put_item_menu)
                self.send_msg(self.show_menu())
                return
            self.send_msg('Новая пара зарегистрирована. \nОжидайте сообщение о начале работы новой пары. \n\nЗадание номер - %s.' % task_id)
            self.put_session_complited()
            return


    def del_token(self, txt):
        token_by_num = self.__get_tokens_by_name()
        if txt == '0':
            self.put_next_step(self.put_item_menu_token)
            self.send_msg(self.show_menu_token())
            return
        if txt not in token_by_num:
            self.send_msg('Некорректное значние! Повторите ввод!')
            return
        result = self.__del_token(token_by_num[txt])
        if not result:
            self.send_msg('Ошибка. Токен не удален!')
        else:
            self.send_msg('Токен удален!')
        self.put_next_step(self.put_item_menu_token)
        self.send_msg(self.show_menu_token())

    def __del_token(self, token_name):
        tokens = self.__get_tokens()
        try:
            for token in tokens:
                if token.name_token == token_name:
                    self.db.delete(token)
                    self.db.commit()
        except Exception as ex:
            self.logging(ex)
            return False
        else:
            return True

    def put_menu_change_param(self, txt):
        if txt not in ['0', '1']:
            self.send_msg('Не корректный номер. Повторите ввод.')
            return
        if txt == '0':
            self.put_next_step(self.put_item_menu_param)
            self.send_msg(self.show_menu_params())
            return
        elif txt == '1':
            self.put_next_step(self.put_param)
            self.send_msg('Введите значение параметра.')
            return

    def put_new_token(self, txt):
        if txt not in self.token_list:
            self.send_msg('Имя введено!')
            self.new_token_name = txt
            self.new_token_data = []
            self.put_next_step(self.put_api_key)
            self.send_msg('Введите api key!')
        else:
            self.send_msg('Такое имя токена уже есть! Повторите ввод.')

    def put_item_menu_param(self, txt):
        params = self.trader.params
        if txt == '0':
            self.put_next_step(self.put_item_menu)
            self.send_msg(self.show_menu())
            return
        try:
            int(txt)
        except:
            self.send_msg('Введите число!')
            return
        for num, param in enumerate(params, 1):
            if int(txt) == num:
                self.send_msg('Параметр выбран!')
                self.put_next_step(self.put_menu_change_param)
                self.change_param = param
                self.send_msg(self.show_menu_change_param())
                return
        self.send_msg('Неверный номер параметра!')

    def put_api_key(self, txt):
        self.api_key = txt
        self.send_msg('Api key введен!')
        self.new_token_data.append(txt)
        self.put_next_step(self.put_api_secret)
        self.send_msg('Введите api secret!')

    def put_api_secret(self, txt):
        self.api_secret = txt
        self.new_token_data.append(txt)
        self.send_msg('Api secret введен!')
        result = self.set_new_token(self.new_token_name, self.new_token_data)
        if not result:
            self.put_next_step(self.put_item_menu_token)
            self.send_msg('Ошибка создания токена!')
            self.send_msg(self.show_menu_token())
            return
        self.send_msg('Токен успешно создан!')
        self.put_next_step(self.put_item_menu_token)
        self.send_msg('Выберите новый токен!')
        self.send_msg(self.show_menu_token())

    def set_new_token(self, name, data):
        data = json.dumps(data)
        token = TOKEN(None, name, data)
        try:
            self.db.add(token)
            self.db.commit()
        except:
            return False
        else:
            return True

    def show_tokens_by_name(self):
        str = ''
        tokens = self.__get_tokens_by_name()
        for token in tokens:
            str += "%s - %s\n" % (token, tokens[token])
        str += '\n 0. Назад'
        return str

    @property
    def token_list(self):
        tokens = {}
        query = self.__get_tokens()
        for num, token in enumerate(query, 1):
            data = json.loads(token.data)
            print(data)
            tokens.update(
                {token.name_token: data}
            )
        return tokens

    def __get_tokens_by_name(self):
        tokens_by_name = {}
        token_list = self.token_list
        for num, token in enumerate(token_list, 1):
            print(num, token)
            tokens_by_name.update(
                {'%s' % num: token}
            )
        return tokens_by_name

    def __get_burse_by_num(self):
        burse = {}
        for num, element in enumerate(self.burse_list, 1):
            burse.update(
                {str(num): element}
            )
        return burse

    def __get_tokens(self):
        return self.db.query(TOKEN).all()

    def begin_chat(self, txt):
        if txt == '/new':
            self.put_next_step(self.put_item_menu)
            #self.send_msg("'K-361b9b48d086a6e0fdd023b52e511fb240a47086', 'S-0fec47713fe877c7894671a75e0465e774009f8c'")
            self.send_msg(self.show_menu())

    def show_burse(self):
        burse = ''
        for num, element in enumerate(self.burse_list, 1):
            burse += '%s - %s\n' % (num, element)
        return burse

    def __get_user_burse(self):
        if self.user_burse is None:
            return '...'
        else:
            return self.user_burse

    def __get_user_pair(self):
        if self.user_pair is None:
            return '...'
        else:
            return self.user_pair

    def __get_user_token_name(self):
        if self.user_token is None:
            return '...'
        else:
            return self.user_token

    def put_burse(self, txt):
        burse = self.__get_burse_by_num()
        if txt not in burse:
            self.send_msg('Неверная биржа! Повторите ввод!')
            return
        self.user_burse = burse.get(txt)
        self.send_msg('Биржа введена!')

        self.put_next_step(self.put_item_menu_burse)
        self.send_msg(self.show_menu_burse())

    def put_token(self, txt):
        token_by_num = self.__get_tokens_by_name()
        if txt == '0':
            self.put_next_step(self.put_item_menu_token)
            self.send_msg(self.show_menu_token())
            return
        if txt not in token_by_num:
            self.send_msg('Некорректное значние! Повторите ввод!')
            return
        self.user_token = token_by_num[txt]#{token_by_num[txt]: self.token_list[token_by_num[txt]]}
        self.send_msg('Токен выбран!')
        self.put_next_step(self.put_item_menu_burse)
        self.send_msg(self.show_menu_burse())

    def burse_is_confirmed(self):
        return self.__burse_confirmed

    def pair_is_confirmed(self):
        return self.__pair_confirmed

    def put_pair(self, txt):
        txt = txt.upper()
        result = self.check_pair(txt)
        if not result:
            self.send_msg('Неверная пара! Введите еще раз!')
            return
        self.__pair_confirmed = True
        self.user_pair = txt
        self.send_msg('Пара введена!')
        self.put_next_step(self.put_item_menu)
        self.send_msg(self.show_menu())

    def accept_setup_burse(self):
        if self.user_burse is None or self.user_token is None:
            return False
        api = self.burse_list[self.user_burse]
        token = self.token_list[self.user_token]
        self.trader.api = api(token[0], token[1])
        self.send_msg('Проверка токена. \nЗапрос количества USD на счету...')
        try:
            user_info = self.trader.api.user_info()
            self.logging(user_info)
            balance = user_info['balances']['USD']
        except Exception as ex:
            print(ex)
            return False
        else:
            self.send_msg('На счету - %s USD.' % balance)
            return True

    def create_task(self):
        task = self.__create_task()
        task_id = None
        try:
            self.db.add(task)
            self.db.commit()
        except Exception as ex:
            self.logging(ex)
            return False, task_id

        try:
            query = self.db.query(TASK).all()
        except Exception as ex:
            self.logging(ex)
            return False, task_id

        self.logging(query)
        for task in query:
            if task.create_time == task.create_time:
                task_id = task.id
        return True, task_id

    def __create_task(self):
        data = {}
        data.update(
            {
                'burse': self.user_burse,
                'token_name': self.user_token,
                'token': self.token_list[self.user_token],
                'pair': self.user_pair,
                'trader_data': self.__get_trader_data()
            }
        )
        str_data = json.dumps(data)
        task = TASK(self.chat_id, __class__.__name__, str_data)
        self.logging(task)
        return task

    def __get_trader_data(self):
        trader_data = {}
        for param in self.trader.params:
            trader_data.update(
                {param: self.trader.__getattribute__(param)}
            )
        return trader_data

    def check_pair(self, txt):
        try:
            traders = self.db.query(TRADE).filter_by(token_name=self.user_token).all()
        except Exception as ex:
            print(ex)
            return False

        if '_' not in txt:
            return False
        two_currency = txt.split('_')
        in_currency = two_currency[0]
        out_currency = two_currency[1]

        for trader in traders:
            if trader.pair == txt:
                return False

        for trader in traders:
            currency = trader.pair.split('_')
            tr_in_currency = currency[0]
            tr_out_currency = currency[1]
            if out_currency == tr_in_currency or in_currency == tr_in_currency or in_currency == tr_out_currency:
                return False
        return True


class EDIT(SESSION):

    def __init__(self, chat_id, send_message, db):
        super().__init__(chat_id, send_message)
        self.reset_timeout()
        self.db = db
        self.user_pair = None
        self.__pair_confirmed = False
        self.put_next_step(self.begin_chat)
        self.create_log_file(chat_id)

    def begin_chat(self, txt):
        if txt == '/edit':
            self.put_next_step(self.put_item_menu)
            #self.send_msg("'K-361b9b48d086a6e0fdd023b52e511fb240a47086', 'S-0fec47713fe877c7894671a75e0465e774009f8c'")
            self.send_msg(self.show_menu())

    def pair_is_confirmed(self):
        return self.__pair_confirmed

    def show_menu(self):
        pair = self.__get_user_pair()
        menu = 'Редактирование настроек пары.\n' \
               '\n' \
               'Выберите номер:\n' \
               '1. Выбор пары - (%s)\n' \
               '2. Настройки пары\n' \
               '3. Подтверждение создания пары\n' \
               '\n' \
               '0. Выход.' \
               '' % (pair)
        return menu

    def show_menu_pair(self):
        menu = 'Выберите пару:\n'

        traders = self.__get_traders
        for num, trader in enumerate(traders, 1):
            menu += '%s. Пара - (%s), Токен - (%s), Биржка - (%s).\n' % (num, trader.pair, trader.token_name, trader.burse)

        menu += '\n\n' \
                '0. Назад'
        return menu

    def show_menu_params(self):
        params = self.trader.params
        menu = 'Выберите нужный параметр:'
        for num, param in enumerate(params, 1):
            menu += '\n%s. %s (%s)' % (num, param, self.trader.__getattribute__(param))
        menu += '\n' \
                '\n' \
                '0. Назад'
        return menu

    def show_menu_change_param(self):
        info_param = self.trader.params[self.change_param]
        value = self.trader.__getattribute__(self.change_param)
        menu = 'Описание параметра: \n' \
               '%s\n' \
               '\n' \
               'Выберите номер:\n' \
               '1. Ввод параметра (%s)\n' \
               '\n' \
               '0. Назад.' \
               '' % (info_param, value)
        return menu

    def show_menu_accept(self):
        menu = 'Вы уверены, что хотите изменить пару? \n' \
               '\n' \
               'Выберите номер:\n' \
               '1. Да\n'\
               '0. Нет\n' \

        return menu

    @property
    def __get_traders(self):
        try:
            traders = self.db.query(TRADE).all()
        except Exception as e:
            self.logging(e)
            return []
        return traders

    def __get_trader_data(self):
        trader_data = {}
        for param in self.trader.params:
            trader_data.update(
                {param: self.trader.__getattribute__(param)}
            )
        return trader_data

    def put_item_menu(self, txt):
        if txt not in ['0', '1', '2', '3', '4']:
            self.send_msg('Не корректный номер. Повторите ввод.')
            return
        if txt == '0':
            self.put_session_complited()
            self.send_msg('Выход из сессии.')
            return
        elif txt == '1':
            self.put_next_step(self.put_item_menu_pair)
            self.send_msg(self.show_menu_pair())
            return
        elif txt == '2':
            if not self.pair_is_confirmed():
               self.send_msg('Выберите сначада пару!')
               return
            self.put_next_step(self.put_item_menu_param)
            self.send_msg(self.show_menu_params())
            return
        elif txt == '3':
            if not self.pair_is_confirmed():
                self.send_msg('Выберите сначала пару!')
                return
            self.put_next_step(self.put_item_menu_accept)
            self.send_msg(self.show_menu_accept())
            return

    def __get_user_pair(self):
        if self.user_pair is None:
            return '...'
        else:
            return self.user_pair

    def put_item_menu_pair(self, txt):
        trade_by_num = self.__get_trade_by_num()
        if txt == '0':
            self.put_next_step(self.put_item_menu)
            self.send_msg(self.show_menu())
            return
        if txt not in trade_by_num:
            self.send_msg('Некорректное значние! Повторите ввод!')
            return
        self.__pair_confirmed = True
        self.trader = TRADER()
        self.trade_from_db = trade_by_num[txt]
        self.user_pair = self.trade_from_db.pair
        params = json.loads(self.trade_from_db.params)
        self.update_params(self.trader, params)
        self.send_msg('Пара выбрана!')
        self.put_next_step(self.put_item_menu)
        self.send_msg(self.show_menu())

    def put_item_menu_param(self, txt):
        params = self.trader.params
        if txt == '0':
            self.put_next_step(self.put_item_menu)
            self.send_msg(self.show_menu())
            return
        try:
            int(txt)
        except:
            self.send_msg('Введите число!')
            return
        for num, param in enumerate(params, 1):
            if int(txt) == num:
                self.send_msg('Параметр выбран!')
                self.put_next_step(self.put_menu_change_param)
                self.change_param = param
                self.send_msg(self.show_menu_change_param())
                return
        self.send_msg('Неверный номер параметра!')

    def put_menu_change_param(self, txt):
        if txt not in ['0', '1']:
            self.send_msg('Не корректный номер. Повторите ввод.')
            return
        if txt == '0':
            self.put_next_step(self.put_item_menu_param)
            self.send_msg(self.show_menu_params())
            return
        elif txt == '1':
            self.put_next_step(self.put_param)
            self.send_msg('Введите значение параметра.')
            return

    def put_item_menu_accept(self, txt):
        if txt not in ['0', '1']:
            self.send_msg('Не корректный номер. Повторите ввод.')
            return
        if txt == '0':
            self.put_next_step(self.put_item_menu)
            self.send_msg(self.show_menu())
            return
        elif txt == '1':
            result, task_id = self.create_task()
            if not result:
                self.send_msg('Ошибка. Изменение пары не зарегистрировано!')
                self.put_next_step(self.put_item_menu)
                self.send_msg(self.show_menu())
                return
            self.send_msg('Изменение пары зарегистрировано. \nОжидайте сообщение о вступлении в силу изменений. \n\nЗадание номер - %s.' % task_id)
            self.put_session_complited()
            return

    def put_param(self, txt):
        print(self.trader.__getattribute__(self.change_param))
        format = self.get_format_param(self.trader.__getattribute__(self.change_param))
        print(format)
        if not self.is_format_param(txt, format):
            self.send_msg('Неверный формат параметра! Повторите ввод.')
        else:
            value = format(txt)
            self.trader.__setattr__(self.change_param, value)
            self.put_next_step(self.put_item_menu_param)
            self.send_msg('Параметр введен!')
            self.send_msg(self.show_menu_params())
            self.change_param = None

    def get_format_param(self, txt):
        try:
            self.to_bool(txt)
        except:
            return float
        else:
            return self.to_bool

    def is_format_param(self, param, format):
        try:
            format(param)
        except:
            return False
        else:
            return True

    def to_bool(self, txt):
        if type(txt) is not bool:
            txt = txt.upper()
        if txt in [True, 'TRUE', '1']:
            return True
        elif txt in [False, 'FALSE', '0']:
            return False
        else:
            print('not bool')
            raise Exception('Not bool')

    def create_task(self):
        task = self.__create_task()
        task_id = None
        try:
            self.db.add(task)
            self.db.commit()
        except Exception as ex:
            self.logging(ex)
            return False, task_id

        try:
            query = self.db.query(TASK).all()
        except Exception as ex:
            self.logging(ex)
            return False, task_id

        self.logging(query)
        for task in query:
            if task.create_time == task.create_time:
                task_id = task.id
        return True, task_id

    def __create_task(self):
        data = {}
        token = json.loads(self.trade_from_db.tokens)
        data.update(
            {
                'burse': self.trade_from_db.burse,
                'token_name': self.trade_from_db.token_name,
                'token': token,
                'pair': self.trade_from_db.pair,
                'trader_data': self.__get_trader_data()
            }
        )
        str_data = json.dumps(data)
        task = TASK(self.chat_id, __class__.__name__, str_data)
        self.logging(task)
        return task

    def update_params(self, new_trader, params):
        for param in params:
            if new_trader.__getattribute__(param) != params[param]:
                new_trader.__setattr__(param, params[param])

    def __get_trade_by_num(self):
        traders_list = {}
        traders = self.__get_traders
        for num, trader in enumerate(traders, 1):
            traders_list.update(
                {str(num): trader}
            )
        return traders_list


class DELETE():
    pass

class ARCHIVE():
    pass




class TBot:
    HTTP_ADDR = r'https://api.telegram.org'
    offset = 0
    active_of_session = {}
    special_commands = {'/new': NEW,
                        '/edit': EDIT}

    def __init__(self, opera_driver, token, db):
        self.browser = opera_driver
        self.token = token
        self.db = db

    def get_updates(self, offset):
        self.browser.get('https://api.telegram.org/bot%s/getUpdates?offset=%s&timeout=120' % (self.token, offset))
        js = self.__get_json_obj()
        if not js['ok']:
            print(js['error_code'], js['description'])
            raise Exception('Error - %s' % js['error_code'])
        return js

    def send_msg(self, chat_id, txt):
        txt = quote_plus(txt)
        self.browser.get('https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s' % (self.token, chat_id, txt))
        js = self.__get_json_obj()
        if not js['ok']:
            print(js['error_code'], js['description'])
            raise Exception('Error - %s' % js['error_code'])
        return js

    def __get_json_obj(self):
        txt = self.browser.find_element_by_tag_name('pre').text
        return json.loads(txt)

    def clear_session_of_done(self):
        while 1:
            for chat_id in self.active_of_session:
                if self.active_of_session[chat_id].is_timeouted():
                    self.active_of_session.pop(chat_id)
                    self.send_msg(chat_id, 'Сессия завершена.')
                    break
                if self.active_of_session[chat_id].session_is_done():
                    self.active_of_session.pop(chat_id)
                    break
            else:
                return

    def send_message_to_all(self):
        try:
            reports = self.db.query(REPORT).all()
            for report in reports:
                self.send_msg(report.user_id, report.data)
                self.db.delete(report)
            self.db.commit()
        except Exception as e:
            print(e)


    def run(self):
        try:
            while 1:
                upd = self.get_updates(self.offset)
                print(len(upd['result']))
                for update in upd['result']:
                    self.offset = int(update['update_id']) + 1
                    if 'message' not in update or 'text' not in update['message']:
                        continue

                    txt = update['message']['text']
                    chat_id = update['message']['chat']['id']
                    if txt in self.special_commands:
                        if chat_id in self.active_of_session:
                            self.active_of_session.pop(chat_id)
                            self.send_msg(chat_id, 'Предыдущая сессия завершена.')
                        new_session = self.special_commands[txt]
                        self.active_of_session.update(
                            {chat_id: new_session(chat_id, self.send_msg, self.db)}
                        )
                    if chat_id in self.active_of_session:
                        session = self.active_of_session[chat_id]
                        session.run(txt)
                    else:
                        self.send_msg(chat_id, txt)#'Gde%0A20+20%D0%A2%D1%8B')
                self.clear_session_of_done()
                self.send_message_to_all()
                time.sleep(1)
        except NoSuchElementException:
            print('Ошибка получения элемента страницы.')
        except Exception as ex:
            print(ex)
            raise