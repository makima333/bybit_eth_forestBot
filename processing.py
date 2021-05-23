import pandas_ta as ta
import pandas as pd
import settings


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
