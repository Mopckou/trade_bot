import errno
import os
import time
import datetime
import zipfile
from socket import timeout, gaierror
from ssl import SSLEOFError
from src.dbase import TRADE, REPORT
from src.burse import Exmo

LOG_DIRECTORY = os.path.join(os.getcwd(), 'LOGS')
NAME_LOG = 'log.txt'
SATOSHI = 0.00000001
MAX_SIZE_FILE = 40


class ErrorFoundPurchases(Exception):
    def __str__(self):
        return u'Error found purchases!'


class ErrorEnoughCash(Exception):
    def __str__(self):
        return u'Error enough cash!'


class ErrorCalcAmount(Exception):
    def __str__(self):
        return u'Error calc amount!'


class ErrorDownPrice(Exception):
    def __str__(self):
        return u'Error down price!'


class STAGE:
    BUY = 0
    WAIT_BUY = 1
    SELL = 2
    WAIT_SELL = 3
    REPORT = 4


class TRADER:
    flag = STAGE.BUY
    minimum_cash_in_currency = 0.  # колличество валюты в паре (например в BTC) при котором считаем что надо завержить сделку и переходим в блок stage.sell
    quantity_cash_of_buy = 0.  # колличество валюты которые мы хотим потратить на покупку например BTC. (обязательный параметр)
    substracted_value_of_price = 0.  # колличество валюты которые мы отнимает от цены в оредере (необзательный параметр)
    flag_check_partial_purchase = True  # флаг анализировать ли частичную покупку оредера (необязательный параметр)
    count_order_trades = 0  # колличество сделок по ордеру
    stop_timeout_of_waiting = 900  # время ожидания покупки ордера (необязательный параметр)
    percent_of_burse = 0.002  # комиссия биржы
    percent_of_additional_purchase = 1  # процент, при котором осуществляется дополнительная закупка
    maximum_amount_for_buy = 20  # максимльное количество денег на которое можно закупаться
    percent_of_profit = 1  # процент при котором продаем валюту
    increase_cash_of_buy = True  # флаг повышать ли цену покупки при каждом закупе
    coeff_increase_of_cash = 2.  # коэффициент увеличения цены при каждом закупе
    waiting_time_before_buying = 300  # время ожидания перед покупкой в секундах
    first_trader_id = 0.  # первый ордер покупки
    order_book_size = 3
    is_end_trade = False
    pair_is_complited = False
    smoll_fraction = 15
    __last_time_of_sale = None

    params = {
        'minimum_cash_in_currency': "Несгораемая сумма на счету.",
        'quantity_cash_of_buy': "Закупочная сумма.",
        'substracted_value_of_price': "Нет информации.",
        'flag_check_partial_purchase': "Проверка частичной покупки.",
        'stop_timeout_of_waiting': "Таймаут ожидания покупки/продажи ордера. (сек)",
        'percent_of_burse': "Комиссия биржы.",
        'percent_of_additional_purchase': "Процент допольнительной закупки. (усреднение)",
        'maximum_amount_for_buy': "Максимальное количество денег для закупки.",
        'percent_of_profit': "Процент продажи.",
        'increase_cash_of_buy': "Параметр повышения суммы закупки.",
        'coeff_increase_of_cash': "Коэффициент увеличения суммы закупки.",
        'is_end_trade': "Остановить пару после полной продажи.",
        'smoll_fraction': "Допустимое количество Сатоши сверху пересчитанной суммы.",
        'waiting_time_before_buying': "Время ожидания перед покупкой. Указывать время в секундах!",
        'first_trader_id': "Номер первого закупочного ордера.",
        'order_book_size': "Размер стакана в пределах котого допустима перебивка"
    }

    def __init__(self, db=None, pair=None, api=None, account=None):
        self.pair = pair
        self.api = api
        self.account = account
        self.db = db
        self.pair_info = None
        if pair is not None and api is not None and account is not None:
            self.create_log_file(pair, api, account)
        if pair is not None:
            self.in_currency = self.__get_in_currency()
            self.out_currency = self.__get_out_currency()

    def set_pair(self, pair):
        self.pair = pair
        self.in_currency = self.__get_in_currency()
        self.out_currency = self.__get_out_currency()

    def create_log_file(self, pair, api, account):
        name_api = '%s' % api
        name_log = 'log.txt'
        self.current_log_directory = os.path.join(LOG_DIRECTORY, name_api, account, pair)
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
        fl.write("%s: %s\n" % (time.ctime(), message))
        fl.close()

    def archive(self):
        size = os.path.getsize(self.log) / 1024 ** 2
        if size >= MAX_SIZE_FILE:

            log = os.path.join(self.current_log_directory, '%s.zip' % time.strftime('%d-%m-%y %H:%S'))
            try:
                with zipfile.ZipFile(log, 'w') as zf:
                    zf.write(self.log)
                os.remove(self.log)
            except Exception as ex:
                print('ОШИБКА АРХИВИРОВАНИЯ: %s' % ex)

    # @property
    # def first_order(self):
    #     return self.__first_order
    #
    # @first_order.setter
    # def first_order(self, order):
    #     self.__first_order = int(order)

    def run(self):
        self.pair_info = 'Время сбора информации:\n%s\n' % time.ctime()
        self.pair_info += 'Блок - %s\n' % self.flag
        try:
            if self.flag == STAGE.BUY:
                self.logging('\n' + '=' * 30 + ' STAGE BUY ' + '=' * 30 + '\n')
                self.block_of_buy()
            elif self.flag == STAGE.WAIT_BUY:
                self.logging('\n' + '=' * 30 + ' STAGE WAIT BUY ' + '=' * 30 + '\n')
                self.block_of_wait_buy()
            elif self.flag == STAGE.SELL:
                self.logging('\n' + '=' * 30 + ' STAGE WAIT PROFIT ' + '=' * 30 + '\n')
                self.block_of_sell()
            elif self.flag == STAGE.WAIT_SELL:
                self.logging('\n' + '=' * 30 + ' STAGE WAIT SELL ' + '=' * 30 + '\n')
                self.block_of_wait_sell()
            elif self.flag == STAGE.REPORT:
                self.logging('\n' + '=' * 30 + ' STAGE REPORT ' + '=' * 30 + '\n')
                print('\n' + time.ctime() + ' =' + ' STAGE REPORT ' + self.pair + ' =' + '\n')
                self.block_of_report()
        except ErrorEnoughCash as ex:
            self.logging(ex)
        except timeout as ex:
            self.logging(u'Вышел таймаут на подключение к серверу. Ошибка - %s' % ex, True)
        except gaierror as ex:
            self.logging(ex, True)
        except OSError as ex:
            self.logging(ex)
            if ex.errno not in [errno.ECONNABORTED, errno.ECONNRESET, errno.ETIMEDOUT]:
                raise
        except SSLEOFError as ex:
            self.logging(u'Ошиюка SSL - %s' % ex, True)
        except Exception as ex:
            self.logging(ex)
            if '40016' in ex.__str__():
                self.logging(u'На сервере ведутся технические работы.')
                time.sleep(420)
                return
            if '50173' in ex.__str__():
                self.logging(u'Не удалось найти ордер!')
                self.logging(self.api.get_open_orders())
                raise
            if 'Error while parsing response' in ex.__str__():
                self.logging(u'Ошибка парса сообщения от сервера биржы.')
                return
            raise
        finally:
            self.archive()
            self.report_about_pair()
            self.pair_info = None

    def report_about_pair(self):
        try:
            traders = self.db.query(TRADE).all()

            for trader in traders:
                if trader.pair == self.pair and trader.token_name == self.account:
                    trader.data = self.pair_info

            self.db.commit()
        except Exception as e:
            self.logging(e)
            print(e)

    def report_about_sell(self, amount_spent, amount_received, profit):
        amount_spent_str = 'Потрачено: %s(%s)' % (amount_spent, self.out_currency)
        amount_received_str = 'Получено: %s(%s)' % (amount_received, self.out_currency)
        profit_str = 'Выручка составила: %s(%s)' % (profit, self.out_currency)
        try:
            report = REPORT(
                0,
                'Пара %s (%s) сделала полную продажу!\n%s\n%s\n%s' % (
                    self.pair, self.account, amount_spent_str, amount_received_str, profit_str
                )
            )
            self.db.add(report)
            self.db.commit()
        except Exception as e:
            self.logging(e)
            print(e)

    def block_of_buy(self):
        open_orders = self.api.get_open_orders()

        if self.is_open_orders(open_orders):
            self.cancel_all_open_orders(open_orders[self.pair])

        if self.first_trader_id:  # self.is_more_currency_in_pair():
            self.logging('Первый trader id покупки: %s. Переходим в блок SELL.' % self.first_trader_id)
            self.flag = STAGE.SELL
            return

        if not self.is_ready_to_buy():
            return

        self.create_order_of_buy()
        self.flag = STAGE.WAIT_BUY
        self.reset_timeout_of_waiting()
        return

    def block_of_report(self):
        self.__last_time_of_sale = time.time()
        amount_spent, amount_received, profit = self.calc_profit()
        self.report_about_sell(
            amount_spent,
            amount_received,
            profit
        )

        self.first_trader_id = 0.
        if self.is_end_trade:
            self.pair_is_complited = True
            return

        self.flag = STAGE.BUY
        return

    def is_open_orders(self, open_orders):
        self.logging('open order - %s' % open_orders)
        return self.pair in open_orders

    def cancel_all_open_orders(self, orders):
        for order in orders:
            order_id = order['order_id']
            self.logging('order_id = %s' % order_id)
            answer = self.api.cancel_order(order_id)
            self.logging(answer)
            if not answer['result']:
                self.logging('order not cancel')
            self.logging('order is cancel')

    def is_ready_to_buy(self):
        if self.__last_time_of_sale is None:
            return True

        return (time.time() - self.__last_time_of_sale) > self.waiting_time_before_buying

    def is_currency(self, currency, cash):
        balances = self.__get_balances()
        if float(balances[currency]) == cash or float(balances[currency]) > cash:
            self.logging('money is enough. Currency - %s, cash - %s' % (currency, cash))
            return True
        self.logging('not money. Currency - %s, cash - %s' % (currency, cash))
        return False

    def is_more_currency_in_pair(self):
        return self.is_more_currency(self.in_currency, self.minimum_cash_in_currency)

    def is_more_currency(self, currency, cash):
        balances = self.__get_balances()
        balance = float(balances[currency])
        if balance > cash:
            self.logging(u'На счету (%s) больше валюты чем - %s (%s).' % (balance, cash, currency))
            return True
        self.logging(u'На счету (%s) меньше валюты чем - %s (%s)' % (balance, cash, currency))
        return False

    def __get_balances(self):
        user_info = self.api.user_info()
        self.logging('user_info : %s' % user_info)
        balances = user_info['balances']
        return balances

    def __get_out_currency(self):
        return self.pair.split('_')[1]

    def __get_in_currency(self):
        return self.pair.split('_')[0]

    def is_currency_for_buy(self, cash):
        return self.is_currency(self.out_currency, cash)

    def is_currency_for_sell(self, cash):
        return self.is_currency(self.in_currency, cash)

    def create_order_of_buy(self, important=True):
        first_order = self.get_first_order_of_buy()
        price = float(first_order[0]) + SATOSHI - self.substracted_value_of_price
        price = round(price, 9)
        if self.increase_cash_of_buy:
            quantity = self.__get_new_quantity_of_buy()
        else:
            quantity = self.quantity_cash_of_buy
        amount = price * quantity
        self.logging('Количество - %s, обойдется в - %s (%s)' % (quantity, amount, self.out_currency))
        if self.is_currency_for_buy(amount):
            self.last_order_id = self._create_order_of_buy(quantity, price)
        else:
            if important:
                raise ErrorEnoughCash('Недостаточно валюты для совершения покупки!')

    def __get_new_quantity_of_buy(self):
        quantities = []

        if not self.first_trader_id:
            self.logging(u'Покупаем стандартное количество - %s.' % self.quantity_cash_of_buy)
            return self.quantity_cash_of_buy

        last_orders = self.get_important_orders()
        for order in last_orders:
            if order['type'] == 'sell':
                continue
            quantities.append(float(order['quantity']))
        quantities.sort()
        quantities.reverse()
        quantity = quantities[0]
        self.logging(u'Количества валюты что мы купили (по убыванию) - %s' % quantities)
        if quantity < self.quantity_cash_of_buy:
            self.logging(u'Наибольшее количество которое было куплено (%s), меньше количества первой покупки (%s)' % (
            quantity, self.quantity_cash_of_buy))
            self.logging(u'Покупка стандартного количества - %s' % self.quantity_cash_of_buy)
            return self.quantity_cash_of_buy
        new_quantity = round(quantity * self.coeff_increase_of_cash, 8)
        self.logging(u'Предыдущее наибольшее купленное количество %s, новое количество - %s' % (quantity, new_quantity))
        return new_quantity

    def _create_order_of_buy(self, quantity, price):
        order_create_setup = {'pair': self.pair,
                              'quantity': quantity,
                              'price': price,
                              'type': 'buy'
                              }
        self.logging('order setup - %s' % order_create_setup)
        answer = self.api.order_create(order_create_setup)
        self.logging(answer)
        if not answer['result']:
            raise Exception('Error order create!')
        return answer['order_id']

    def create_order_of_sell(self, current_price_of_sell, quantity_for_sell, important=True):
        price = current_price_of_sell - SATOSHI - self.substracted_value_of_price
        if self.is_currency_for_sell(quantity_for_sell):
            self.last_order_id = self._create_order_of_sell(quantity_for_sell, price)
        else:
            if important:
                raise ErrorEnoughCash('Недостаточно валюты для совершения продажи!')

    def _create_order_of_sell(self, quantity_for_sell, price):
        order_create_setup = {'pair': self.pair,
                              'quantity': quantity_for_sell,
                              'price': price,
                              'type': 'sell'
                              }
        self.logging('order setup - %s' % order_create_setup)
        answer = self.api.order_create(order_create_setup)
        self.logging(answer)
        if not answer['result']:
            raise Exception('Ошибка создания ордера!')
        return answer['order_id']

    def get_first_order_of_buy(self):
        order_book = self.api.get_order_book(self.pair)
        self.logging('order book: %s' % order_book)
        order_book_by_pair = order_book[self.pair]
        bid_list = order_book_by_pair['bid']
        first_order = bid_list[0]
        self.logging('first price (bid): %s' % first_order[0])
        return first_order

    def get_first_order_of_sell(self):
        order_book = self.api.get_order_book(self.pair)
        self.logging('order book: %s' % order_book)
        order_book_by_pair = order_book[self.pair]
        ask_list = order_book_by_pair['ask']
        first_order = ask_list[0]
        self.logging('first price (bid): %s' % first_order[0])
        return first_order

    def block_of_wait_buy(self):
        open_orders = self.api.get_open_orders()

        if self.order_is_purchased(open_orders):
            self.flag = STAGE.SELL
            self.count_order_trades = 0

        elif not self.order_is_relevant(open_orders[self.pair], 'bid'):
            self.logging(u'Оредр перебит. Отмена ордера.')
            self.cancel_all_open_orders(open_orders[self.pair])
            self.flag = STAGE.BUY
            self.count_order_trades = 0

        elif self.is_timeout():
            if self.count_order_trades != 0:
                self.logging('Ордер частично куплен! Первый ордер = %s.' % self.last_order_id)
                self.flag = STAGE.SELL
            else:
                self.flag = STAGE.BUY
            self.cancel_all_open_orders(open_orders[self.pair])
            self.count_order_trades = 0  # колличество сделок по ордеру, обнуляем после выходы из блока ождания покупки.

        if self.flag == STAGE.SELL and not self.first_trader_id:
            self.logging('Первый ордер = %s' % self.last_order_id)
            first_trade_id = self.get_first_trade_id(self.last_order_id)
            self.logging('Первый trade id = %s' % first_trade_id)
            self.first_trader_id = first_trade_id

    def block_of_wait_sell(self):
        open_orders = self.api.get_open_orders()

        if self.order_is_purchased(open_orders):
            self.flag = STAGE.REPORT
            self.count_order_trades = 0

        elif not self.order_is_relevant(open_orders[self.pair], 'ask'):
            self.logging(u'Оредр перебит. Отмена ордера.')
            self.cancel_all_open_orders(open_orders[self.pair])
            self.flag = STAGE.SELL
            self.count_order_trades = 0

        elif self.is_timeout():
            self.logging(u'Вышло время ожидания покупки ордера! Переход в блок STAGE.SELL...')
            self.cancel_all_open_orders(open_orders[self.pair])
            self.flag = STAGE.SELL
            self.count_order_trades = 0  # колличество сделок по ордеру, обнуляем после выходы из блока ождания покупки.

    def order_is_relevant(self, open_orders, type):
        order = self.get_open_order_by_id(open_orders)
        price, quantity, amount = order["price"], order["quantity"], order["amount"]
        trades = self.get_trades(type, self.order_book_size)
        self.logging('Список ордеров из стакана. Тип %s, Количество %s, Ордера %s' % (type, self.order_book_size, trades))
        for trade in trades:
            if (price, quantity, amount) == (trade[0], trade[1], trade[2]):
                return True

        return False

    def get_trades(self, type, count):
        order_book = self.api.get_order_book(self.pair)
        order_book_by_pair = order_book[self.pair]
        return order_book_by_pair[type][:count]
        # price = first_order[0]
        # quantity = first_order[1]
        # amount = first_order[2]
        # return price, quantity, amount

    def get_first_trade_id(self, order_id):
        order = self.get_order_trades(order_id)
        self.logging('order trades: %s' % order)
        return order['trades'][-1]['trade_id']

    def order_is_purchased(self, open_orders):
        if self._order_is_purchased(open_orders):
            return True

        if self.flag_check_partial_purchase and self.is_partial_purchase():
            self.reset_timeout_of_waiting()
            return False

        return False

    def is_timeout(self):
        return time.time() - self.timeout_of_waiting > self.stop_timeout_of_waiting

    def get_open_order_by_id(self, open_orders):
        for order in open_orders:
            if self.last_order_id == int(order['order_id']):
                return order

    def _order_is_purchased(self, open_orders):
        self.logging(u'Проверка покупки ордера...')
        if not self.is_open_orders(open_orders):
            self.logging(u'Нет открытых ордеров!')
            return True

        self.logging(u'Есть открытые ордера!')
        for order in open_orders[self.pair]:
            if self.last_order_id == int(order['order_id']):
                self.logging(u'Нужный ордер найден!')
                return False
        self.logging(u'Нужный ордер не найден!')
        return True

    def is_partial_purchase(self):
        self.logging(u'Проверка частичной покупки ордера.')
        order_trades = self.get_order_trades(self.last_order_id)
        if not order_trades:
            return False
        self.logging(u'order trades: %s' % order_trades)
        count_order_trades_now = len(order_trades['trades'])
        if self.count_order_trades != count_order_trades_now:
            self.logging(u'Ордер частично куплен!')
            self.count_order_trades = count_order_trades_now
            return True

        self.logging(u'Орден частично не выкупался!')
        return False

    def get_order_trades(self, order_id) -> list:
        try:
            order_trades = self.api.order_trades(order_id)
        except Exception as ex:
            self.logging(u'Ошибка при запросе истории ордера. Ордер еще не выкупался.')
            self.logging(ex)
            return []

        return order_trades

    def reset_timeout_of_waiting(self):
        self.timeout_of_waiting = time.time()
        self.logging(u'Таймер сброшен!')

    def block_of_sell(self):
        try:
            quantity_in_currency = float(self.__get_balances()[self.in_currency])
            self.last_important_purchases = self.get_important_orders()
            sell, buy = self.get_count_sell_and_buy(self.last_important_purchases)
            self.pair_info += 'Всего ордеров сначала торгов - %s\nКоличество закупок - %s\nКоличество продаж - %s\n' % (
            len(self.last_important_purchases), buy, sell)
            amount = self.get_amount_for_sell(self.last_important_purchases)
            quantity = self.get_quantity_for_sell(quantity_in_currency, self.last_important_purchases)
            price_without_profit = self.__calc_price(amount, quantity, False)
            price_with_profit = self.__calc_price(amount, quantity, True)
            current_price_of_sell = float(self.get_first_order_of_sell()[0])
            current_percent = (current_price_of_sell / price_without_profit) * 100 - 100
            self.logging(
                u'Цена продажи - %s. Цена без профита (чтобы выйти в ноль) - %s. Цена с профитом - %s. Профит - %s.' % (
                current_price_of_sell, price_without_profit, price_with_profit, self.percent_of_profit))
            self.logging(
                u'Процент между ценой продажи из стакана и нашей средней цены продажи без профита - %s' % current_percent)
            self.pair_info += 'Потратили - %s (%s)\n' % (
            self.__get_spent_amount(self.last_important_purchases), self.out_currency)
            self.pair_info += u'Цена продажи - %s\nЦена без профита (чтобы выйти в ноль) - %s\nЦена с профитом - %s\nПрофит - %s\n' % (
            round(current_price_of_sell, 8), round(price_without_profit, 8), round(price_with_profit, 8),
            self.percent_of_profit)
            self.pair_info += 'Текущий процент - (%s)\n' % round(current_percent, 3)
            self.pair_info += 'Предполагаемый процент после закупа - (%s)' % round(
                self.get_future_percent(amount, quantity, current_price_of_sell), 9)
            if current_percent < - self.percent_of_additional_purchase:
                self.logging(u'Условие закупа соблюдается.')
                if amount < self.maximum_amount_for_buy:
                    print('ЗАКУП - %s!' % self.pair)
                    self.logging(u'Колличество валюты которое было куплено не превышает лимит!')
                    raise ErrorDownPrice
                self.logging(u'Колличество валюты которое было куплено превышает лимит!')
            elif price_with_profit <= current_price_of_sell:
                self.create_order_of_sell(current_price_of_sell, quantity)
                self.reset_timeout_of_waiting()
                self.flag = STAGE.WAIT_SELL
                return
            self.logging(u'Продолжаем ждать профит...')
        except ErrorCalcAmount:
            self.logging(u'Сумма окупилась, но некоторое количество валюты не распродано. Закупаем еще!')
            self.create_order_of_buy()
            self.reset_timeout_of_waiting()
            self.flag = STAGE.WAIT_BUY
            return
        except ErrorDownPrice:
            self.create_order_of_buy()
            self.reset_timeout_of_waiting()
            self.flag = STAGE.WAIT_BUY
            return
        except Exception as ex:
            if '50277' in ex.__str__():
                self.logging(u'Количество на продажу меньше допустимого минимума. Закупаем еще.')
                self.create_order_of_buy()
                self.reset_timeout_of_waiting()
                self.flag = STAGE.WAIT_BUY
                return
            self.logging(ex, True)
            raise

    def __correction_quantity(self, quantity_in_currency, quantity):
        quantity_without_minimum = quantity_in_currency - self.minimum_cash_in_currency
        round_quantity = round(quantity_without_minimum, 9)
        self.logging(
            u'Количество валюты на счету %s (%s), количество с вычетом несгораемой суммы %s. Округленное количество %s' % (
                quantity_in_currency, self.in_currency, quantity_without_minimum, round_quantity
            ))
        percent = (round_quantity * 100 / quantity) - 100
        self.logging(u'Процент между количеством без сгораемой величины и пересчитанным количеством - %s' % percent)
        if abs(percent) < 0.001:
            return round_quantity
        raise Exception(u'Ошибка коррекции количества.')

    def get_important_orders(self):
        self.logging('Первый ордер покупки %s' % self.first_trader_id)
        last_orders = self.api.user_trades(self.pair)[self.pair]
        self.logging(u'user trades - %s' % last_orders)
        cash_in_currency = float(self.__get_balances()[self.in_currency])
        self.logging(u'Количество валюты на счету %s (%s)' % (cash_in_currency, self.in_currency))

        number = None
        for num, order in enumerate(last_orders):
            if order['trade_id'] == self.first_trader_id:
                number = num

        if number is not None:
            self.logging('Ордера с начала торговли: %s' % last_orders[:number + 1])
            return last_orders[:number + 1]

        raise ErrorFoundPurchases

    def get_count_sell_and_buy(self, orders):
        sell = 0
        buy = 0
        for order in orders:
            if order['type'] == 'sell':
                sell += 1
            elif order['type'] == 'buy':
                buy += 1
        return sell, buy

    def __get_spent_amount(self, last_orders):
        amount = 0.
        for order in last_orders:
            if order['type'] == 'sell':
                continue
            amount += float(order['amount'])
        return round(amount, 8)

    def __equal(self, other):
        difference = other - self.minimum_cash_in_currency
        # self.logging(difference)
        return difference >= 0 and difference <= SATOSHI * self.smoll_fraction  # всегда остается остаток порядка
        # 5 сатоши, условие чтобы остаток не превышал 10 сатоши

    def get_amount_for_sell(self, last_important_purchases):
        amount = self.__get_amount_by_last_orders(last_important_purchases)
        self.logging(u'Количество amount (денег) которое было потрачено - %s' % amount)
        if amount < 0.:
            raise ErrorCalcAmount
        return amount

    def get_quantity_for_sell(self, quantity_in_currency, last_important_purchases):
        quantity_for_sell = self.__get_quantity_by_last_orders(last_important_purchases)
        #     self.__correction_quantity(
        #     quantity_in_currency,
        #     self.__get_quantity_by_last_orders(last_important_purchases)
        # )
        is_currency = self.is_currency(self.in_currency, quantity_for_sell)
        if not is_currency:
            raise ErrorEnoughCash(u'ВНИМАНИЕ! Недостаточно средств на счету. Этой ошибки не должно быть!')
        return quantity_for_sell

    def __calc_price(self, amount, quantity, is_profit):
        amount += amount * self.percent_of_burse  # прибавляем 0.2%, чтобы посчитать цену с учетом комиссии
        if is_profit:
            amount += amount * self.percent_of_profit / 100
        price = amount / quantity
        self.logging(u'Колличество - %s. Цена - %s. Комиссия биржы %s. Профит - %s' % (
            quantity, price, self.percent_of_burse, is_profit
        ))
        return price

    def calc_profit(self):
        self.logging('Номер ордера первой покупки: %s' % self.first_trader_id)
        last_orders = self.get_important_orders()
        self.logging('last orders: %s' % last_orders)
        amount_spent = round(self.get_amount_spent(last_orders), 9)
        amount_received = round(self.get_amount_received(last_orders), 9)
        profit = round(amount_received - amount_spent, 9)
        self.logging('Потрачено: %s, получено: %s, профит: %s' % (amount_spent, amount_received, profit))
        return amount_spent, amount_received, profit


    def get_amount_received(self, last_orders):
        amount_summ = 0.
        for order in last_orders:
            if order['type'] == 'buy':
                continue
            amount = float(order['amount'])
            amount_summ += amount - amount * self.percent_of_burse
        return amount_summ

    def get_amount_spent(self, last_orders):
        amount_summ = 0.
        for order in last_orders:
            if order['type'] == 'sell':
                continue
            amount_summ += float(order['amount'])
        return amount_summ

    def get_future_percent(self, amount, quantity, current_price_of_sell):
        new_quantity = self.__get_new_quantity_of_buy()
        new_quantity += new_quantity - new_quantity * self.percent_of_burse
        amount += new_quantity * current_price_of_sell
        quantity += new_quantity
        price = self.__calc_price(amount, quantity, False)
        return (current_price_of_sell / price) * 100 - 100

    def __get_amount_by_last_orders(self, orders):
        amount = 0.
        for order in orders:
            self.logging('$$$' + order['amount'])
            if order['type'] == 'sell':
                sell_amount = float(order['amount'])
                amount -= round(sell_amount, 8)
            elif order['type'] == 'buy':
                amount += float(order['amount'])
        self.logging(
            u'Сумма денег, которые были потрачены за последние ордера - %s (до первой главной покупки, с учетом неполных продаж)' % amount)
        return amount

    def __get_quantity_by_last_orders(self, orders):
        quantity = 0.
        for order in orders:
            if order['type'] == 'sell':
                quantity -= float(order['quantity'])
            elif order['type'] == 'buy':
                buy_quantity = float(order['quantity'])
                quantity += buy_quantity - (buy_quantity * self.percent_of_burse)  # с вычетом процента комиссии
        quantity = round(quantity, 8)
        self.logging(u'Количество валюты что мы купили за последние ордера (котрую нужно реализовать) - %s' % quantity)
        return quantity
