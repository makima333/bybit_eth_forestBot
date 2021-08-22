import pandas_ta as ta
import pandas as pd
import settings
from datetime import datetime as dt


def AddStrategy(df):
    df = df.drop_duplicates(subset=['open_time'])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='s')
    df.set_index(pd.DatetimeIndex(df["open_time"]), inplace=True)
    # '''settings.py上の指標を追加'''
    # MyStrategy = ta.Strategy(
    #     name='eth',
    #     ta=settings.talist
    # )

    # 指定指標をを追加
    df.ta.strategy(ta.AllStrategy)
    df = df.reset_index(drop=True)
    return df


def drop_column(df):
    drop_column_list = settings.drop_column_list
    df = df.drop(drop_column_list, axis=1, errors='ignore')

    df = df.fillna(method='ffill')
    # df = df.dropna()
    return df


def get_profitrate_log(fpath):
    """ログから利益率取得
    """
    result_dict = {}
    with open(fpath, 'r', encoding='utf_8') as f:
        lines = f.readlines()
    for line in lines:
        parse_line = line.split(':INFO:')
        key = parse_line[0]
        value = parse_line[1].replace('利益率＝', '').replace('\n', '')
        if parse_line[1].find("利益率") >= 0:
            result_dict[key] = value

    return result_dict


def fillter_datetime_dict(ddict, start_dtime, end_dtime):
    """時間がキーとなっている辞書型をフィルタ
    """
    result_dict = dict(filter(lambda item: float(item[1]) < 0, ddict.items()))
    result_dict = dict(filter(
        lambda item: dt.strptime(item[0], '%Y-%m-%d %H:%M:%S') > start_dtime,
        result_dict.items()))
    result_dict = dict(filter(
        lambda item: dt.strptime(item[0], '%Y-%m-%d %H:%M:%S') < end_dtime,
        result_dict.items()))
    return result_dict
