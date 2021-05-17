import pandas as pd
import trade_client as tr
import settings
import logging
import processing
import time
import datetime
from joblib import load


def ml_predict(row):
    scaler = load('./models/std_scaler.bin')
    forest = load('./models/forest_profit_1.bin')

    X_test_scaled = scaler.transform(row)
    forest_result = forest.predict(X_test_scaled)[0]

    return forest_result


def stop_func(bybit):
    bybit.cancel_all_orders(bybit.symbol)
    pos, size = bybit.get_position()
    logging.info('end, position=%s, size=%s', pos, size)


def main():
    trade_logic = {2: 'Buy', 0: 'Sell'}
    close_logic = {tr.trade_client.posLong: 'Sell',
                   tr.trade_client.posShort: 'Buy'}
    logging.basicConfig(filename='log.txt',
                        level=logging.INFO,
                        format='%(asctime)s:%(levelname)s:%(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    bybit = tr.trade_client({
        'apiKey': settings.apiKey,
        'secret': settings.secret
    })

    pos, size = bybit.get_position()
    logging.info('start, position=%s, size=%s', pos, size)
    # クローズロジック
    if pos != bybit.posNone:
        side = close_logic[pos]
        order_result = ""
        while order_result != 'Filled':
            order_result = bybit.send_order(side, size, pos)
            if order_result == 'Cancelled':
                pass
            elif order_result == 'New':
                time.sleep(30)
                pos, size = bybit.get_position()
                if pos == bybit.posNone:
                    bybit.cancel_all_orders(bybit.symbol)
                    bybit.market_order(side, size)
            else:
                return 0
    else:
        # データ取得
        now = datetime.datetime.today()
        time_from = now - datetime.timedelta(hours=32)
        history = bybit.get_histricaldata(time.mktime(time_from.timetuple()))

        # データ加工
        ohlc = pd.DataFrame.from_dict(history).astype(bybit.data_type)
        ohlc = processing.AddStrategy(ohlc)
        ohlc = processing.drop_column(ohlc)

        # 予測
        predict_result = ml_predict([ohlc.iloc[len(ohlc)-1]])
        logging.info('機械学習の結果=%s', predict_result)
        if predict_result == 1:
            # 終了時の関数
            bybit.cancel_all_orders(bybit.symbol)

            stop_func()
            return 0

        # エントリロジック
        order_result = ""
        side = trade_logic[predict_result]
        first_p = bybit.get_price(side)
        tmp_p = first_p
        while order_result != 'Filled':
            if tmp_p != first_p:
                tmp_p = bybit.get_price(side)

                # 初期エントリー時との乖離を取得
                diff_p = bybit.diff_price(side, first_p, tmp_p)
                if diff_p < -3:
                    # 終了時の関数
                    logging.info('価格が乖離したため、終了します, first_p=%s, tmp_p=%s',
                                 first_p, tmp_p)
                    stop_func()
                    return 0

            order_result = bybit.send_order(side, settings.amount, pos, tmp_p)
            print(order_result, tmp_p)
            if order_result == 'Cancelled':
                pass
            elif order_result == 'New':
                time.sleep(60)
                pos, size = bybit.get_position()
                if pos == bybit.posNone:
                    # 終了時の関数
                    stop_func()
                    return 0
                else:
                    order_result == 'Filled'
            else:
                return 0


if __name__ == '__main__':
    main()
