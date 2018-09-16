import time
from src.trader import TRADER
from src.burse import Exmo

api = Exmo('K-361b9b48d086a6e0fdd023b52e511fb240a47086', 'S-0fec47713fe877c7894671a75e0465e774009f8c')
trader = TRADER('ETH_USD', api, 'bot')
trader.quantity_cash_of_buy = 8.
trader.substracted_value_of_price = 0.
#trader.minimum_cash_in_currency = 0.00000142
trader2 = TRADER('BCH_USD', api, 'bot')
trader2.quantity_cash_of_buy = 4.
trader2.substracted_value_of_price = 0.
trader2.maximum_amount_for_buy = 100.
trader3 = TRADER('DXT_USD', api, 'bot')
trader3.minimum_cash_in_currency = 0.0000001
trader3.quantity_cash_of_buy = 10.
trader3.substracted_value_of_price = 0.
trader4 = TRADER('BTC_USD', api, 'bot')
trader4.quantity_cash_of_buy = 10.
trader4.maximum_amount_for_buy = 90
trader4.substracted_value_of_price = 0.
trader4.is_end_trade = True
#trader.minimum_cash_in_currency = 0.00000142
#trader5 = TRADER('DOGE_BTC', api_vtoroi, 'drr')
#trader5.quantity_cash_of_buy = 0.000051
#trader5.minimum_cash_in_currency = 0.0061486
trader6 = TRADER('BTG_USD', api, 'bot')
trader6.quantity_cash_of_buy = 10.
trader6.maximum_amount_for_buy = 40
trader7 = TRADER('HBZ_USD', api, 'bot')
trader7.quantity_cash_of_buy = 5.
trader7.minimum_cash_in_currency = 998.00000001
trader7.maximum_amount_for_buy = 50
trader7.is_end_trade = True
#trader8 = TRADER('HBZ_USD', api_vtoroi, 'drr')
#trader8.quantity_cash_of_buy = 5.
#trader8.maximum_amount_for_buy = 40
trader9 = TRADER('XRP_USD', api, 'bot')
trader9.quantity_cash_of_buy = 6.
trader9.percent_of_additional_purchase = 0.4
trader9.percent_of_profit = 0.4
trader9.maximum_amount_for_buy = 40
trader9.is_end_trade = True
trader10 = TRADER('USDT_USD', api, 'bot')
trader10.quantity_cash_of_buy = 3.5
trader10.percent_of_profit = 0.1
trader10.maximum_amount_for_buy = 30
trader10.percent_of_additional_purchase = 0.2
trader10.timeout_of_waiting = 120
trader11 = TRADER('ADA_USD', api, 'bot')
trader11.quantity_cash_of_buy = 6.
trader11.minimum_cash_in_currency = 0
trader11.maximum_amount_for_buy = 50
trader11.smoll_fraction = 10
#trader7.minimum_cash_in_currency = 998.00000001
#trader7.maximum_amount_for_buy = 50
#trader7.is_end_trade = True
container = []
container.append(trader)
container.append(trader2)
container.append(trader3)
#container.append(trader4)
#container.append(trader5)
container.append(trader6)
container.append(trader7)
#container.append(trader8)
#container.append(trader9)
#container.append(trader10)
container.append(trader11)
while 1:
    for tr in container:
        tr.run()
        print("%s   " % tr.pair, end="\r", flush=True)
        time.sleep(1)
    for tr in container:
        if tr.pair_is_complited:
            print('Pair is delete')
            container.remove(tr)