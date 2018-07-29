from exmo_api_lib import ExmoAPI

class MotherOfBurse:

    def get_open_orders(self, *args, **kwargs):
        pass

    def cancel_orders(self, *args, **kwargs):
        pass

    def order_create(self, *args, **kwargs):
        pass

    def get_order_book(self, **kwargs):
        pass

    def user_info(self):
        pass

    def order_trades(self, *args):
        pass

    def user_trades(self, *args):
        pass


class Exmo(ExmoAPI, MotherOfBurse):

    def get_open_orders(self):
        return self.api_query('user_open_orders')

    def cancel_order(self, id):
        inquiry = {'order_id': id}
        return self.api_query('order_cancel', inquiry)

    def get_order_book(self, pair):
        inquiry = {'pair': pair}
        return self.api_query('order_book', inquiry)

    def order_create(self, order_setup):
        return self.api_query('order_create', order_setup)

    def user_info(self):
        return self.api_query('user_info')

    def order_trades(self, order_id):
        inquiry = {
            'order_id': order_id
        }
        return self.api_query('order_trades', inquiry)

    def user_trades(self, pair):
        inquiry = {
            'pair': pair
        }
        return self.api_query('user_trades', inquiry)

    def __str__(self):
        return 'EXMO'




#if __name__ == '__main__':
    #btc = 0.001518956
    #price = 6570

    #price_with_percent = price + (price * 0.02)
    #end_usd1 = price_with_percent * btc

    #end_usd_with_kommission = end_usd1 - (end_usd1 * 0.002)

    #price_with_percent_and_kommission = price + (price * 0.018)
    #end_usd2 = price_with_percent_and_kommission * btc

    #print('usd 1 - %s' % end_usd_with_kommission)
    #print('usd 2 - %s' % end_usd2)

    #usd_before = btc * price
    #percent_of_usd_after_and_before = (end_usd1 - usd_before) * 100 / usd_before

#api = Exmo('K-361b9b48d086a6e0fdd023b52e511fb240a47086', 'S-0fec47713fe877c7894671a75e0465e774009f8c')
#trades = api.order_trades("1040878357")
    # e = Exmo('K-361b9b48d086a6e0fdd023b52e511fb240a47086', 'S-0fec47713fe877c7894671a75e0465e774009f8c')
    # #print(e.get_open_orders())
    # #print(e.api_query('user_trades', {'pair':'BTC_USD', 'limit': '100', 'offset': '0'}))
    # user_trades = e.api_query('user_trades', {"pair":"BTC_USD,LTC_USD", "limit":"10", "offset":"0"})
    # for trades in user_trades:
    #     print('pair - %s' % trades)
    #     for trade in user_trades[trades]:
    #         print(trade)