import pandas as pd
import trade_client as tr
import settings
import logging
import processing
import time
import datetime
from joblib import load
import csv
import warnings

warnings.simplefilter(action='ignore',
                      category=pd.core.common.SettingWithCopyWarning)


def write_csv(time_str, predict_results, side, price):
    with open(settings.history_csv_path, 'a') as f:
        writer = csv.writer(f)
        writer.writerow([time_str, predict_results, side, price])


def get_last_trade_time():
    df = pd.read_csv(settings.history_csv_path)
    order_time = df.tail(1)['order_time'].values[0]
    return datetime.datetime.fromisoformat(order_time)


def ml_predict(row):
    path_list = [
        '/app/models/forest_profit_4.bin',
        '/app/models/forest_profit_5.bin',
        '/app/models/forest_profit_6.bin']
    results = []

    scaler = load('/app/models/std_scaler.bin')
    for path in path_list:
        forest = load(path)
        X_test_scaled = scaler.transform(row)
        results.append(forest.predict(X_test_scaled)[0])

    return results


def check_exec_time(diff_seconds, start_time):
    '''
    時間経過しているかチェック
    dff_secod : しきい値(seconds)
    start_time : チェックする時間
    now_time :　比較する時間
    '''
    now_time = datetime.datetime.today()
    exec_time = now_time - start_time
    if exec_time.total_seconds() > diff_seconds:
        logging.info('時間が%s秒を超えました', diff_seconds)
        return 1
    return 0


def stop_func(bybit):
    '''終了処理'''
    bybit.cancel_all_orders(bybit.symbol)
    pos, size = bybit.get_position()
    logging.info('end, position=%s, size=%s', pos, size)


def main():
    trade_logic = {1: 'Buy', -1: 'Sell', 0: ''}
    close_logic = {tr.trade_client.posLong: 'Sell',
                   tr.trade_client.posShort: 'Buy',
                   'Buy': 'Sell',
                   'Sell': 'Buy'}
    logging.basicConfig(filename='/app/logs/log.txt',
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
        profit = bybit.get_profit()
        side = close_logic[pos]

        # 損切りロジック
        order_result = ""
        if profit < 0:

            last_trade_time = get_last_trade_time()
            if check_exec_time(60*26, last_trade_time) == 1:
                while order_result != 'Filled':
                    order_result = bybit.send_order(side, size, pos)
                    if order_result == 'Cancelled':
                        pass
                    elif order_result in ['New', 'PartiallyFilled']:
                        time.sleep(20)
                        pos, size = bybit.get_position()
                        if pos != bybit.posNone:
                            bybit.cancel_all_orders(bybit.symbol)
                            bybit.market_order(side, size)
                        else:
                            order_result = 'Filled'

                logging.info('損切りしました。')
            stop_func(bybit)
            return 0

        # 利確ロジック
        order_result = ""
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

            order_result = bybit.send_order(side, size, pos)
            if order_result == 'Cancelled':
                tmp_p = 0
                pass
            elif order_result == 'New' or order_result == 'PartiallyFilled':
                time.sleep(60)
                pos, size = bybit.get_position()
                if pos != bybit.posNone:
                    bybit.cancel_all_orders(bybit.symbol)
                    if check_exec_time(180, start_time=now) == 1:
                        stop_func(bybit)
                        return 0
                    tmp_p = 0
                    continue
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
                tmp_p = 0
                continue
            elif order_result in ['New', 'PartiallyFilled']:
                time.sleep(60)
                pos, size = bybit.get_position()
                logging.info('order_result=%s, position=%s, size=%s',
                             order_result, pos, size)

                if pos == bybit.posNone:
                    bybit.cancel_all_orders(bybit.symbol)
                    if check_exec_time(180, start_time=now) == 1:
                        stop_func(bybit)
                        return 0
                    tmp_p = 0
                    continue
                else:
                    order_result = 'Filled'
            elif order_result != 'Filled':
                break

        stop_func(bybit)
        write_csv(now, predict_results, side, tmp_p)


if __name__ == '__main__':
    main()
