import time
import errno
import os
from exmo_api_lib import ExmoAPI
from burse import Exmo
LOG_DIRECTORY = os.path.join(os.getcwd(), 'LOGS')
NAME_LOG = 'log.txt'
SATOSHI = 0.0000001

class ErrorFoundPurchases(Exception):
    pass

class ErrorEnoughCash(Exception):
    pass

class STAGE:
    BUY = 0
    WAIT_BUY = 1
    SELL = 2
    WAIT_SELL = 3
    REPORT = 4

class TRADER():
    flag = STAGE.BUY
    minimum_cash_in_currency = SATOSHI # колличество валюты в паре (например в BTC) при котором считаем что надо завержить сделку и переходим в блок stage.sell
    quantity_cash_of_buy = 0. # колличество валюты которые мы хотим потратить на покупку например BTC. (обязательный параметр)
    substracted_value_of_price = 0. # колличество валюты которые мы отнимает от цены в оредере (необзательный параметр)
    flag_check_partial_purchase = True # флаг анализировать ли частичную покупку оредера (необязательный параметр)
    count_order_trades = 0 # колличество сделок по ордеру
    stop_timeout_of_waiting = 420 # время ожидания покупки ордера (необязательный параметр)
    percent_of_burse = 0.002 # комиссия биржы
    percent_of_additional_purchase = 2 #процент, при котором осуществляется дополнительная закупка
    maximum_amount_for_buy = 20 #максимльное количество денег на которое можно закупаться
    percent_of_profit = 2 #процент при котором продаем валюту
    increase_cash_of_buy = True # флаг повышать ли цену покупки при каждом закупе
    coeff_increase_of_cash = 2. # коэффициент увеличения цены при каждом закупе

    def __init__(self, pair, api):
        self.pair = pair
        self.api = api
        self.create_log_file(pair, api)

    def create_log_file(self, pair, api):
        name_folder = '%s' % api
        name_log = '%s.txt' % pair
        self.current_log_directory = os.path.join(LOG_DIRECTORY, name_folder)
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

    def run(self):
        try:
            if self.flag == STAGE.BUY:
                self.logging('\n' + '=' * 30 + ' STAGE BUY ' + '=' * 30 + '\n')
                return self.block_of_buy()
            elif self.flag == STAGE.WAIT_BUY:
                self.logging('\n' + '=' * 30 + ' STAGE WAIT BUY ' + '=' * 30 + '\n')
                return self.block_of_wait_buy()
            elif self.flag == STAGE.SELL:
                self.logging('\n' + '=' * 30 + ' STAGE WAIT PROFIT ' + '=' * 30 + '\n')
                return self.block_of_sell()
            elif self.flag == STAGE.WAIT_SELL:
                self.logging('\n' + '=' * 30 + ' STAGE WAIT SELL ' + '=' * 30 + '\n')
                return self.block_of_wait_sell()
            elif self.flag == STAGE.REPORT:
                self.logging('\n' + '=' * 30 + ' STAGE REPORT ' + '=' * 30 + '\n')
                print('\n' + '=' * 30 + ' STAGE REPORT ' + '=' * 30 + '\n')
                #self.block_of_report()
                self.flag = STAGE.BUY
                return
        except ErrorEnoughCash as ex:
            self.logging(ex)
        except OSError as ex:
            self.logging(ex)
            if ex.errno not in [errno.ECONNABORTED, errno.ECONNRESET, errno.ETIMEDOUT]:
                raise
        except Exception as ex:
            self.logging(ex)
            raise

    def block_of_buy(self):
        open_orders = self.api.get_open_orders()
        if self.is_open_orders(open_orders):
            self.cancel_all_open_orders(open_orders[self.pair])
        if self.is_currency_in_pair():
            self.flag = STAGE.SELL
            return
        else:
            self.create_order_of_buy()
            self.flag = STAGE.WAIT_BUY
            self.reset_timeout_of_waiting()
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

    def is_currency(self, currency, cash):
        self.logging('is_currency_in_pair')
        balances = self.__get_balances()
        if float(balances[currency]) == cash or float(balances[currency]) > cash:
            self.logging('money is enough. Currency - %s, cash - %s' % (currency, cash))
            return True
        self.logging('not money. Currency - %s, cash - %s' % (currency, cash))
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

    def is_currency_in_pair(self):
        in_currency = self.__get_in_currency()
        return self.is_currency(in_currency, self.minimum_cash_in_currency)

    def is_currency_for_buy(self, cash):
        out_pair = self.__get_out_currency()
        return self.is_currency(out_pair, cash)

    def is_currency_for_sell(self, cash):
        in_pair = self.pair.split('_')[0]
        return self.is_currency(in_pair, cash)

    def create_order_of_buy(self, important=True):
        first_order = self.get_first_order_of_buy()
        price = float(first_order[0]) + SATOSHI - self.substracted_value_of_price
        if self.increase_cash_of_buy:
            amount = self.__get_new_amount_for_buy()
        else:
            amount = self.quantity_cash_of_buy
        if self.is_currency_for_buy(amount):
            self.last_order_id = self._create_order_of_buy(amount, price)
        else:
            if important:
                raise ErrorEnoughCash('Недостаточно валюты для совершения покупки!')

    def __get_new_amount_for_buy(self):
        last_orders = self.get_important_orders_for_re_calc()
        if last_orders == []:
            self.logging(u'Первая покупка по стандартной цене - %s.' % self.quantity_cash_of_buy)
            return self.quantity_cash_of_buy
        for order in last_orders:
            if order['type'] == 'buy':
                continue
            amount = float(order['amount'])
            new_amount = amount * self.coeff_increase_of_cash
            self.logging(u'Цена последней покупки %s, новая цена - %s' % (amount, new_amount))
            return new_amount

    def _create_order_of_buy(self, amount, price):
        order_create_setup = {'pair': self.pair,
                              'quantity': amount/price,
                              'price': price,
                              'type': 'buy'
                              }
        self.logging('order setup - %s' % order_create_setup)
        answer = self.api.order_create(order_create_setup)
        self.logging(answer)
        if not answer['result']:
            raise Exception('Error order create!')
        return answer['order_id']

    def create_order_of_sell(self, quantity_for_sell, important=True):
        first_order = self.get_first_order_of_sell()
        price = float(first_order[0]) - SATOSHI - self.substracted_value_of_price
        if self.is_currency_for_sell(quantity_for_sell):
            self.last_order_id = self._create_order_of_sell(quantity_for_sell, price)
            print(self.last_order_id)
            print(self.last_order_id + 1)
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
        if self.order_is_purchased():
            self.flag = STAGE.SELL
            #self.last_order_id_of_buy = None
            self.count_order_trades = 0
            return
        if self.is_timeout():
            self.logging(u'wait buy is timeout! Flag = stage.buy')
            self.flag = STAGE.BUY
            self.count_order_trades = 0 # колличество сделок по ордеру, обнуляем после выходы из блока ождания покупки.
            return

    def block_of_wait_sell(self):
        if self.order_is_purchased():
            self.flag = STAGE.REPORT
            self.count_order_trades = 0
            return
        if self.is_timeout():
            self.logging(u'Вышло время ожидания покупки ордера! Переход в блок STAGE.SELL...')
            open_orders = self.api.get_open_orders()
            self.cancel_all_open_orders(open_orders[self.pair])
            self.flag = STAGE.BUY
            self.count_order_trades = 0 # колличество сделок по ордеру, обнуляем после выходы из блока ождания покупки.
            return

    def order_is_purchased(self):
        if self._order_is_purchased():
            return True
        if self.flag_check_partial_purchase and self.is_partial_purchase():
            self.reset_timeout_of_waiting()
            return False
        return False

    def is_timeout(self):
        return time.time() - self.timeout_of_waiting > self.stop_timeout_of_waiting

    def _order_is_purchased(self):
        open_orders = self.api.get_open_orders()
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
        try:
            order_trades = self.api.order_trades(self.last_order_id)
        except Exception as ex:
            self.logging(u'Ошибка при запросе истории ордера. Ордер еще не выкупался.')
            self.logging(ex)
            return False
        self.logging(u'order trades: %s' % order_trades)
        count_order_trades_now = len(order_trades['trades'])
        if self.count_order_trades != count_order_trades_now:
            self.logging(u'Ордер частично куплен!')
            self.count_order_trades = count_order_trades_now
            return True
        self.logging(u'Орден частично не выкупался!')
        return False

    def reset_timeout_of_waiting(self):
        self.timeout_of_waiting = time.time()
        self.logging(u'Таймер сброшен!')

    def block_of_sell(self):
        last_important_purchases = self.get_important_orders_for_re_calc()
        price_with_profit = self.calc_price_by_last_purchases(last_important_purchases, is_profit=True)
        price_without_profit = self.calc_price_by_last_purchases(last_important_purchases, is_profit=False)
        current_price_of_sell = float(self.get_first_order_of_sell()[0])
        price_difference = (current_price_of_sell/price_without_profit) * 100 - 100
        price_difference_with_profit = (current_price_of_sell/price_with_profit) * 100 - 100
        self.logging(u'Цена продажи - %s. Цена без профита (чтобы выйти в ноль) - %s. Цена с профитом - %s. Профи - %s.' % (current_price_of_sell, price_without_profit, price_with_profit, self.percent_of_profit))
        self.logging(u'Процент между ценой продажи из стакана и нашей средней цены продажи без профита - %s' % price_difference)
        if price_difference < - self.percent_of_additional_purchase:
            self.logging(u'Условие закупа соблюдается.')
            amount = self.__get_amount_by_last_orders(last_important_purchases)
            self.logging(u'Количество валюты которое было потрачено - %s' % amount)
            print('ЗАКУП!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            if amount < self.maximum_amount_for_buy:
                self.logging(u'Колличество валюты которое было продано не превышает лимит!')
                self.create_order_of_buy()
                self.reset_timeout_of_waiting()
                self.flag = STAGE.WAIT_BUY
                return
            self.logging(u'Колличество валюты которые было продано превышает лимит!')
        elif price_with_profit <= current_price_of_sell:
            quantity_for_sell = self.__get_quantity_by_last_orders(last_important_purchases)
            self.create_order_of_sell(quantity_for_sell)
            self.reset_timeout_of_waiting()
            self.flag = STAGE.WAIT_SELL
            return
        self.logging(u'Продолжаем ждать профит...')

    def get_important_orders_for_re_calc(self):
        last_orders = self.api.user_trades(self.pair)[self.pair]
        self.logging(u'user trades - %s' % last_orders)
        in_currency = self.__get_in_currency()
        cash_in_currency = float(self.__get_balances()[in_currency])
        self.logging(u'Количество валюты на счету %s (%s)' % (cash_in_currency, in_currency))
        important_orders = []
        if self.__eq__(cash_in_currency):
            self.logging(u'Покупки еще не совершались.')
            return []
        for order in last_orders:
            important_orders.append(order)
            if order['type'] == 'sell':
                cash_in_currency += float(order['quantity'])
            elif order['type'] == 'buy':
                buy_quantity = float(order['quantity'])
                cash_in_currency -= buy_quantity - (buy_quantity * self.percent_of_burse)
            if self.__eq__(cash_in_currency):
                sell, buy = self.get_count_sell_and_buy(important_orders)
                self.logging(u'Пследние ордера покупок (количество закупок - %s, количество продаж - %s) - %s' % (buy, sell, len(important_orders)))
                return important_orders
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

    def __eq__(self, other):
        return other >= 0 and other <= self.minimum_cash_in_currency


    def calc_price_by_last_purchases(self, last_purchases, is_profit=None):
        quantity = self.__get_quantity_by_last_orders(last_purchases)
        in_currency = self.__get_in_currency()
        is_currency = self.is_currency(in_currency, quantity)
        if not is_currency:
            raise Exception(u'ВНИМАНИЕ! Недостаточно средств на счету. Этой ошибки не должно быть!')
        amount = self.__get_amount_by_last_orders(last_purchases)
        amount += amount * self.percent_of_burse # прибавляем 0.2%, чтобы посчитать цену с учетом комиссии
        if is_profit:
            amount += amount * self.percent_of_profit / 100
        price = amount / quantity
        self.logging(u'Колличество - %s. Цена - %s. Комиссия биржы %s. Профит - %s' % (
            quantity, price, self.percent_of_burse, is_profit
        ))
        return price

    def __get_amount_by_last_orders(self, orders):
        amount = 0.
        for order in orders:
            if order['type'] == 'sell':
                amount -= float(order['amount'])
            elif order['type'] == 'buy':
                amount += float(order['amount'])
        self.logging(u'Сумма денег, которые были потрачены за последние ордера - %s (до первой главной покупки, с учетом неполных продаж)' % amount)
        return amount

    def __get_quantity_by_last_orders(self, orders):
        quantity = 0.
        for order in orders:
            if order['type'] == 'sell':
                quantity -= float(order['quantity'])
            elif order['type'] == 'buy':
                buy_quantity = float(order['quantity'])
                quantity += buy_quantity - (buy_quantity * self.percent_of_burse) # с вычетом процента комиссии
        self.logging(u'Сумма валюты что мы купили за последние ордера (котрую нужно реализовать) - %s' % quantity)
        return quantity

    # def get_last_purchases(self):
    #     user_trades = self.api.user_trades(self.pair)[self.pair]
    #     self.logging(u'user trades - %s' % user_trades)
    #     last_purchases = []
    #     for user_trade in user_trades:
    #         if user_trade['type'] == 'sell': # цикл до первой продажи, для выделения массива последних покупок
    #             self.logging(u'Пследние ордера покупок (количество - %s) - %s' % (len(last_purchases), last_purchases))
    #             return last_purchases
    #         last_purchases.append(user_trade)
    #     self.logging(u'Пследние ордера покупок (количество - %s) - %s' % (len(last_purchases), last_purchases))
    #     return last_purchases


if __name__ == '__main__':
    api = Exmo('K-361b9b48d086a6e0fdd023b52e511fb240a47086', 'S-0fec47713fe877c7894671a75e0465e774009f8c')
    trader = TRADER('ETH_USD', api)
    trader.quantity_cash_of_buy = 8.
    trader.substracted_value_of_price = 0.
    #trader.minimum_cash_in_currency = 0.00000142
    trader2 = TRADER('BCH_USD', api)
    trader2.quantity_cash_of_buy = 4.
    trader2.substracted_value_of_price = 0.
    trader3 = TRADER('DXT_USD', api)
    trader3.quantity_cash_of_buy = 4.
    trader3.substracted_value_of_price = 0.
    trader4 = TRADER('BTC_USD', api)
    trader4.quantity_cash_of_buy = 10.
    trader4.substracted_value_of_price = 0.
    #trader.minimum_cash_in_currency = 0.00000142
    container = []
    container.append(trader)
    container.append(trader2)
    container.append(trader3)
    container.append(trader4)
    while 1:
        for tr in container:
            tr.run()
            print(tr.pair)
            time.sleep(10)