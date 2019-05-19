import os
import time
import json
from src.dbase import TASK, REPORT, TRADE, ARCHIVE
from src.trader import TRADER
from src.burse import Exmo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from logging import log


class TRADER_CONTROL:

    def __init__(self, db):
        self.container = []
        self.db = db
        self.commands = {
            'NEW': self.append_new_trader,
            'EDIT': self.edit_trader,
            'DELETE': None
        }
        self.burse = {
            'EXMO': Exmo
        }

    def is_new_task(self):
        try:
            tasks = self.db.query(TASK).filter_by(is_done=False).all()
        except Exception as ex:
            print(ex)
            return False
        return tasks != []

    def update_container(self):
        tasks = []
        try:
            tasks = self.db.query(TASK).filter_by(is_done=False).all()
        except Exception as ex:
            print(ex)

        for task in tasks:
            if task.task_name in self.commands:
                result = self.handler(task)
                if result:
                    self.put_task_comlited(task)

    def put_task_comlited(self, task):
        task.is_done = True
        try:
            self.db.commit()
        except Exception as ex:
            print(ex)

    def handler(self, task):
        method = self.commands.get(task.task_name)
        return method(task)

    def append_new_trader(self, task):
        data = json.loads(task.data)
        burse = data['burse']
        token = data['token']
        pair = data['pair']
        params = data['trader_data']
        token_name = data['token_name']

        api = self.burse[burse](token[0], token[1])
        new_trader = TRADER(self.db, pair, api, token_name)
        self.update_params(new_trader, params)

        result = self.add_new_trader_in_db(burse, pair, token, params, token_name)
        if result:
            self.container.append(new_trader)
            self.report_new_trader(task.user_id, task)
            print('Новая пара введена!')
            return True
        print('Пара не введена!')
        return False

    def edit_trader(self, task):
        data = json.loads(task.data)
        pair = data['pair']
        params = data['trader_data']
        token_name = data['token_name']

        result = self.__edit_trader_in_db(pair, token_name, params)
        if result:
            trader = self.__get_trader_in_container(pair, token_name)
            self.update_params(trader, params)
            self.report_edit_trader(task.user_id, task)
            print('Изменены настройки пары!')
            return True
        print('Настройки пары не изменены!')
        return False

    def __edit_trader_in_db(self, pair, token_name, params):
        traders = self.__get_traders_from_db()

        for trader in traders:
            if trader.pair == pair and trader.token_name == token_name:
                trader.params = json.dumps(params)
        try:
            self.db.commit()
        except Exception as e:
            print(e)
            return False

        traders = self.__get_traders_from_db()
        for trader in traders:
            if trader.pair == pair and trader.token_name == token_name and trader.params == json.dumps(params):
                return True
        return False

    def __get_traders_from_db(self):
        traders = []
        try:
            traders = self.db.query(TRADE).all()
            print()
        except Exception as e:
            print(e)
        return traders

    def __get_trader_in_container(self, pair, token_name):
        for trader in self.container:
            if trader.pair == pair and trader.account == token_name:
                return trader

    def add_new_trader_in_db(self, burse, pair, token, params, token_name):
        trade = TRADE(burse, pair, token_name, json.dumps(token), json.dumps(params))
        try:
            self.db.add(trade)
            self.db.commit()
        except Exception as e:
            print(e)
            return False
        return True

    def first_update_container(self):
        trades = self.__get_traders_from_db()

        for trade in trades:
            self.back_trader_in_work(trade)

    def back_trader_in_work(self, trade):
        params = json.loads(trade.params)
        token = json.loads(trade.tokens)
        api = self.burse[trade.burse](token[0], token[1])

        trader = TRADER(self.db, trade.pair, api, trade.token_name)
        self.update_params(trader, params)
        self.container.append(trader)
        print('Пара восстановлена после выключения бота. (%s)' % trader.pair)

    def report_new_trader(self, user_id, task):
        report = REPORT(user_id, 'Пара в работе! Задание номер - %s выполнено.' % task.id)
        try:
            self.db.add(report)
            self.db.commit()
        except Exception as e:
            print(e)

    def report_edit_trader(self, user_id, task):
        report = REPORT(user_id, 'Настройки пары изменены! Задание номер - %s выполнено.' % (task.id))
        try:
            self.db.add(report)
            self.db.commit()
        except Exception as e:
            print(e)

    def report_archive_trader(self, pair, err):
        if err is None:
            ans = 'На паре - %s торговля завершена. Ошибок нет. \n\nВведите команду /return для возообновления работы пары.' % (pair)
        else:
            ans = 'Ошибка! Пара - %s выключена и помещена в архив!\nОшибка - %s.\n\nВведите команду /return для возообновления работы пары.' % (pair, err)
        report = REPORT(0, ans)
        try:
            self.db.add(report)
            self.db.commit()
        except Exception as e:
            print(e)

    @staticmethod
    def update_params(new_trader, params):
        for param in params:
            if new_trader.__getattribute__(param) != params[param]:
                new_trader.__setattr__(param, params[param])

    def put_trader_in_archive(self, trader, err=None):
        traders = self.__get_traders_from_db()
        for tr in traders:
            if tr.pair == trader.pair and tr.token_name == trader.account:
                result = self.__create_archive_trader(tr, err)
                if result:
                    res = self.__delete_trader_in_db(tr)
                    print('Результат удаления пары - %s' % res)
                    self.report_archive_trader(trader.pair, err)
                    self.container.remove(trader)
                    return True
        return False

    def __delete_trader_in_db(self, trader):
        pair = trader.pair
        token_name = trader.token_name
        try:
            self.db.delete(trader)
            self.db.commit()
        except Exception as e:
            print(e)
            return False

        traders = self.__get_traders_from_db()
        for trader in traders:
            if trader.pair == pair and trader.token_name == token_name:
                return False
        return True

    def __create_archive_trader(self, tr, err):
        archive = ARCHIVE(tr.burse, tr.pair, tr.token_name, tr.tokens, tr.params, '%s' % err)
        try:
            self.db.add(archive)
            self.db.commit()
        except Exception as e:
            print(e)
            return False
        return True

    def run(self):
        self.first_update_container()
        while 1:
            if self.is_new_task():
                self.update_container()
            time.sleep(1)
            for trader in self.container:
                try:
                    trader.run()
                    print("%s   " % trader.pair, end="\r", flush=True)
                    time.sleep(10)
                except Exception as e:
                    print(e)
                    self.put_trader_in_archive(trader, e)
            for trader in self.container:
                if trader.pair_is_complited:
                    self.put_trader_in_archive(trader)


NAME = 'TRADE_DATA_BASE.db'
DATABASE = os.path.abspath(
    os.path.join(
        os.path.split(__file__)[0], 'src', 'db', NAME
    )
)

engine = create_engine('sqlite:///%s' % DATABASE, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

controller = TRADER_CONTROL(session)
controller.run()
