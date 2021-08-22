import ccxt
# import datetime
import settings
import time
import logging


class trade_client(ccxt.bybit):
    '''トレード用のクラス'''
    # ポジション用文字列
    posLong = "Long"
    posShort = "Short"
    posNone = "NoPosiotion"
    symbol = "ETH/USD"
    symbol_param = "ETHUSD"
    amount = settings.amount
    order_type = "limit"
    data_type = {
        'symbol':        'object',
        'interval':       'int64',
        'open_time':      'int64',
        'open':         'float64',
        'high':         'float64',
        'low':          'float64',
        'close':        'float64',
        'volume':         'int64',
        'turnover':     'float64'
    }

    def market_order(self, side, amount):
        self.create_order(self.symbol, "market", side, amount)

    def send_order(self, side, amount, pos, price=None):
        result = []
        if price is None:
            price = self.get_price(side)
        if side == 'Buy':
            buffer = -0.1
        else:
            buffer = 0.1

        order = self.create_order(self.symbol, self.order_type,
                                  side, amount, price + buffer,
                                  params={'time_in_force': 'PostOnly'})
        for i in range(10):
            time.sleep(10)
            olist = self.fetch_orders(self.symbol)
            result = [dic for dic in olist if dic.get('id') == order['id']]
            if len(result) > 0:
                break
            if i == 9:
                logging.info("Order Error")
                return 'New'
        logging.info("Created Order, price=%s, side=%s, order_result=%s",
                     price, side,
                     result[0]['info']['order_status'])

        return result[0]['info']['order_status']

    def get_price(self, side):
        if side == 'Buy':
            return self.fetch_ticker(symbol=self.symbol)['ask']
        elif side == 'Sell':
            return self.fetch_ticker(symbol=self.symbol)['bid']

    def cal_profit(self, pos, side, entry_p):
        entry_p = float(entry_p)
        now_price = float(self.get_price(side))
        if pos == self.posLong:
            return now_price - entry_p

        elif pos == self.posShort:
            return entry_p - now_price
        return 0

    def diff_price(self, side, first_p, tmp_p):
        '''
        返り値が小さいほど、t+1の価格が負の方に動いている
        '''
        if side == 'Buy':
            return tmp_p - first_p
        elif side == 'Sell':
            return first_p - tmp_p

    def get_position(self):
        pos_dict = self.v2_private_get_position_list({'symbol':
                                                      self.symbol_param})
        if pos_dict['ret_msg'] == 'OK':
            if pos_dict['result']['side'] == 'Buy':
                return self.posLong, pos_dict['result']['size']

            elif pos_dict['result']['side'] == 'Sell':
                return self.posShort, pos_dict['result']['size']

            else:
                return self.posNone, 0
        else:
            return None, 0

    def get_profit(self):
        pos_dict = self.v2_private_get_position_list({'symbol':
                                                      self.symbol_param})
        if pos_dict['ret_msg'] == 'OK':
            pnl = pos_dict['result']['unrealised_pnl']
            return float(pnl)
        return 0

    def get_histricaldata(self, unixtime):
        histrical_list = []
        time_index_key = 'open_time'

        while True:
            tmp_list = []
            tmp_list = self.v2_public_get_kline_list(
                params={'symbol': self.symbol_param,
                        'interval': '5',
                        'from': int(unixtime)})['result']

            if len(histrical_list) != 0:
                latest_tmp = tmp_list[len(tmp_list)-1][time_index_key]
                latest_hist = histrical_list[len(
                    histrical_list)-1][time_index_key]
                if latest_tmp == latest_hist:
                    break

            unixtime = tmp_list[len(tmp_list)-1][time_index_key]
            histrical_list += tmp_list

        histrical_list = self.remove_duplicate(histrical_list, time_index_key)
        return histrical_list

    def remove_duplicate(self, list, key):
        res = []
        for i in list:
            tmp_list = []
            tmp_list = [dict[key] for dict in res]
            if i[key] in tmp_list:
                res.append(i)

        return list
