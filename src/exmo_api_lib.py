import sys
import http.client
import urllib.error
import json
import hashlib
import hmac
import time

class ExmoAPI:
    def __init__(self, API_KEY, API_SECRET, API_URL = 'api.exmo.com', API_VERSION = 'v1'):
        self.API_URL = API_URL
        self.API_VERSION = API_VERSION
        self.API_KEY = API_KEY
        self.API_SECRET = bytes(API_SECRET, encoding='utf-8')

    def sha512(self, data):
        H = hmac.new(key=self.API_SECRET, digestmod=hashlib.sha512)
        H.update(data.encode('utf-8'))
        return H.hexdigest()

    def api_query(self, api_method, params={}):
        params['nonce'] = int(round(time.time() * 1000))
        params = urllib.parse.urlencode(params)

        sign = self.sha512(params)
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "Key": self.API_KEY,
            "Sign": sign
        }
        conn = http.client.HTTPSConnection(self.API_URL, timeout=5*60)
        conn.request("POST", "/" + self.API_VERSION + "/" + api_method, params, headers)
        response = conn.getresponse().read()

        conn.close()

        try:
            obj = json.loads(response.decode('utf-8'))
            if 'error' in obj and obj['error']:
                #print(obj['error'])
                #raise sys.exit()
                raise Exception(obj['error'])
            return obj
        except json.decoder.JSONDecodeError:
            #print('Error while parsing response:', response)
            #raise sys.exit()
            raise Exception('Error while parsing response:', response)

# Example
# ExmoAPI_instance = ExmoAPI('K-361b9b48d086a6e0fdd023b52e511fb240a47086', 'S-0fec47713fe877c7894671a75e0465e774009f8c')
# # print(ExmoAPI_instance.api_query('required_amount', {'pair':'BTC_USD', 'quantity':'0.001'}))
# pair = {
#     'pair': 'EOS_USD'
# }
# order_book = ExmoAPI_instance.api_query('order_book', pair)
# print(order_book)
# order_book_by_pair = order_book[pair['pair']]
# ask_list = order_book_by_pair['bid']
# print(ask_list)
# first_order = ask_list[0]
# print(first_order[0])
# price = float(first_order[0]) + 0.0000001
# print(price)
#
# order_create_setup = {'pair': pair['pair'],
#                       'quantity': 10/price,
#                       'price': price,
#                       'type': 'buy'
#                       }
# print(order_create_setup)
# print(ExmoAPI_instance.api_query('order_create', order_create_setup))
# order_id = 886444679
# profit = 2
#
# def get_quantity_by_order(exmo, id):
#     order_id = {
#         'order_id': id
#     }
#     quantity = exmo.api_query('order_trades', order_id)['trades'][0]['quantity']
#     return quantity
#
#
# def get_price_by_order(exmo, id):
#     order_id = {
#         'order_id': id
#     }
#     price = exmo.api_query('order_trades', order_id)['trades'][0]['price']
#     return price
#
# def get_current_price(exmo, pair, view):
#     order_book = exmo.api_query('order_book', pair)
#     order_book_by_pair = order_book[pair['pair']]
#     ask_list = order_book_by_pair[view]
#     first_order = ask_list[0]
#     return first_order[0]
#
#
# def get_percent_of_trade(price_buy, price_sell):
#     return (float(price_sell) * 100) / float(price_buy)
#
# quantity = float(get_quantity_by_order(ExmoAPI_instance, order_id))
# current_price = get_current_price(ExmoAPI_instance, pair, 'ask')
# price_buy = get_price_by_order(ExmoAPI_instance, order_id)
# print('current price - %s' % current_price)
# print('quantity by order %s' % quantity)
# print('price buy - %s' % price_buy)
# percent = get_percent_of_trade(price_buy, current_price)
# print('begin percent - %s' % percent)
# before = time.time()
# while percent < 100 + profit:
#     try:
#         current_price = get_current_price(ExmoAPI_instance, pair, 'ask')
#         percent = get_percent_of_trade(price_buy, current_price)
#         print(percent)
#         time.sleep(1)
#     except:
#         print('error')
#         percent = 100
# after = time.time()
# timer = after - before
# print('%s min, %s sec' % (timer/60, timer%60))
# price_sell = float(current_price) - 0.0000001
# quantity_with_commission = quantity - (quantity * 0.002)
# dollars = price_sell * quantity
# print('price sell - %s' % price_sell)
# print('quntity dollars - %s' % dollars)
# print('quanity with commission - %s' % quantity_with_commission)
# order_create = {
#     'pair': pair['pair'],
#     'quantity': quantity_with_commission,
#     'price': price_sell,
#     'type': 'sell'
# }
# print(order_create)
# print(ExmoAPI_instance.api_query('order_create', order_create))