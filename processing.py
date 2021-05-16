import pandas_ta as ta
import settings


def AddStrategy(df):
    '''settings.py上の指標を追加'''
    MyStrategy = ta.Strategy(
        name='eth',
        ta=settings.talist
    )

    # 指定指標をを追加
    df.ta.strategy(MyStrategy)
    return df


def drop_column(df):
    drop_column_list = settings.drop_column_list
    df = df.drop(drop_column_list, axis=1, errors='ignore')

    # df = df.fillna(method='ffill')
    # df = df.dropna()
    return df
