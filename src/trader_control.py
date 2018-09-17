import os
import time
import json
from src.dbase import TASK, REPORT, TRADE
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
        print(
            tasks != []
              )
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
                if result: self.put_task_comlited(task)

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
        new_trader = TRADER(pair, api, token_name)
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

        trader = TRADER(trade.pair, api, trade.token_name)
        self.update_params(trader, params)
        self.container.append(trader)
        print('Пара восстановлена после выключения бота. (%s)' % trader.pair)

    def report_new_trader(self, user_id, task):
        report = REPORT(user_id, 'Новая пара в работе! Задание номер - %s выполнено.' % task.id)
        self.db.add(report)
        self.db.commit()

    def report_edit_trader(self, user_id, task):
        report = REPORT(user_id, 'Настройки пары изменены! Задание номер - %s выполнено.' % (task.id))
        self.db.add(report)
        self.db.commit()

    def update_params(self, new_trader, params):
        for param in params:
            if new_trader.__getattribute__(param) != params[param]:
                new_trader.__setattr__(param, params[param])

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
                    time.sleep(1)
                except Exception as e:
                    print(e)
                    self.put_trade_in_archive()
            for trader in self.container:
                if trader.pair_is_complited:
                    print('Pair is delete')
                    self.container.remove(trader)

NAME = 'TRADE_DATA_BASE.db'
DATABASE = os.path.abspath(
    os.path.join(
        os.path.split(__file__)[0], 'db', NAME
    )
)

engine = create_engine('sqlite:///%s' % DATABASE, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

controller = TRADER_CONTROL(session)
controller.run()