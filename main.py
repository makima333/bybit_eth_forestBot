import pandas as pd
import trade_client as tr
import settings
import logging
import processing
import time
import datetime
from joblib import load
import csv


def write_csv(time_str, predict_results, side, price):
    with open(settings.history_csv_path, 'a') as f:
        writer = csv.writer(f)
        writer.writerow([time_str, predict_results, side, price])


def ml_predict(row):
    path_list = [
        './models/forest_profit_4.bin',
        './models/forest_profit_5.bin',
        './models/forest_profit_6.bin']

    results = []

    scaler = load('./models/std_scaler.bin')
    for path in path_list:
        forest = load(path)
        X_test_scaled = scaler.transform(row)
        results.append(forest.predict(X_test_scaled)[0])

    return results


def stop_func(bybit):
    bybit.cancel_all_orders(bybit.symbol)
    pos, size = bybit.get_position()
    logging.info('end, position=%s, size=%s', pos, size)


def main():
    trade_logic = {1: 'Buy', -1: 'Sell', 0: ''}
    close_logic = {tr.trade_client.posLong: 'Sell',
                   tr.trade_client.posShort: 'Buy',
                   'Buy': 'Sell',
                   'Sell': 'Buy'}
    logging.basicConfig(filename='log.txt',
                        level=logging.INFO,
                        format='%(asctime)s:%(levelname)s:%(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    bybit = tr.trade_client({
        'apiKey': settings.apiKey,
        'secret': settings.secret
    })
    now = datetime.datetime.today()
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
                if pos != bybit.posNone:
                    bybit.cancel_all_orders(bybit.symbol)
                    bybit.market_order(side, size)
                    return 0
                else:
                    order_result = 'Filled'
            else:
                return 0
    else:
        # データ取得
        time_from = now - datetime.timedelta(hours=32)
        history = bybit.get_histricaldata(time.mktime(time_from.timetuple()))

        # データ加工
        ohlc = pd.DataFrame.from_dict(history).astype(bybit.data_type)
        ohlc = processing.AddStrategy(ohlc)
        ohlc = processing.drop_column(ohlc)

        # 予測
        results_list = ml_predict([ohlc.iloc[len(ohlc)-1]])
        predict_result = results_list[-1]
        predict_results = ",".join(map(str, results_list))
        logging.info('機械学習の結果=%s, %s', predict_result, predict_results)

        if predict_result == 0:
            # 終了時の関数
            bybit.cancel_all_orders(bybit.symbol)

            stop_func(bybit)
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
                    stop_func(bybit)
                    return 0
            order_result = bybit.send_order(side, settings.amount, pos, tmp_p)

            print(order_result, tmp_p)
            if order_result == 'Cancelled':
                pass
            elif order_result == 'New':
                time.sleep(60)
                pos, size = bybit.get_position()
                if pos == bybit.posNone:
                    stop_func(bybit)
                    return 0
                else:
                    order_result == 'Filled'
            elif order_result != 'Filled':
                return 0
        write_csv(now, predict_results, side, tmp_p)


if __name__ == '__main__':
    main()
