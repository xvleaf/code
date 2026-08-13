# -*- coding: utf-8 -*-

import os
import datetime
import pytz
import pandas as pd

from . import ashare

AM_START = int(os.environ.get('STOCK_TRADE_AM_START', 34200))   # 09:30
AM_END   = int(os.environ.get('STOCK_TRADE_AM_END', 41400))     # 11:30
PM_START = int(os.environ.get('STOCK_TRADE_PM_START', 46800))   # 13:00
PM_END   = int(os.environ.get('STOCK_TRADE_PM_END', 54000))     # 15:00


def get_trend_data(tscode, init, session):
    """
    核心函数：获取分时图数据
    :param code: 股票代码（如 'sh000001' 或 '000001.XSHG'）
    :param init: 字符串 '1' 表示初始化，'0' 表示增量更新
    :param session: Flask session 对象（需支持字典式存取）
    :return: 字典，格式与 trend.js 的预期一致
    """
    tscode = tscode.upper()
    if tscode.endswith('.SZ'):
        code = 'sz' + tscode.replace('.SZ', '')
    else:
        code = 'sh' + tscode.replace('.SH', '')

    # 获取当天分钟数据
    df = _get_today_minute_data(code)
    if df is None:
        # 无数据时返回空结构
        return {
            'ohlc': [],
            'volume': [],
            'index': 0,
            'pc': 0.0,
            'deci': 2,
            'tick_itv': 0,
            'tick_max': 0,
            'tick_min': 0
        }

    # 获取前收盘价
    pre_close = _get_pre_close_price(code)
    if pre_close is None:
        # 若无法获取，用当日第一笔价格代替（极端情况）
        pre_close = df.iloc[0]['close']

    # 构建 ohlc / volume 数据列表
    ohlc = []
    volume = []
    for idx, row in df.iterrows():
        ts = int(idx.timestamp() * 1000)          # 毫秒时间戳
        close = row['close']
        delta = close - pre_close
        percent = (delta / pre_close * 100) if pre_close != 0 else 0.0
        ohlc.append([ts, close, percent, delta])
        volume.append([ts, row['volume']])

    # 4. 计算 Y 轴参数
    tick_min, tick_max, tick_itv = _calc_tick_params(df, pre_close)
    deci = _calc_price_decimal(df)

    # 5. 增量逻辑
    last_ts = session.get('last_timestamp', None)

    if init == '1' or last_ts is None:
        # 首次或强制初始化：返回全部数据，保存最后时间戳
        if ohlc:
            session['last_timestamp'] = ohlc[-1][0]
        return {
            'ohlc': ohlc,
            'volume': volume,
            'index': len(ohlc),
            'pc': pre_close,
            'deci': deci,
            'tick_itv': tick_itv,
            'tick_max': tick_max,
            'tick_min': tick_min
        }

    # 增量更新：只返回时间戳大于 last_ts 的新数据
    new_ohlc = []
    new_volume = []
    for o_item, v_item in zip(ohlc, volume):
        if o_item[0] > last_ts:
            new_ohlc.append(o_item)
            new_volume.append(v_item)

    if new_ohlc:
        session['last_timestamp'] = new_ohlc[-1][0]

    return {
        'ohlc': new_ohlc,
        'volume': new_volume,
        'index': len(new_ohlc),
        'pc': pre_close,
        'deci': deci,
        'tick_itv': tick_itv,
        'tick_max': tick_max,
        'tick_min': tick_min
    }


def _seconds_from_midnight(dt):
    """返回 datetime 对象距离当天零点的秒数"""
    return dt.hour * 3600 + dt.minute * 60 + dt.second


def _is_trading_time(dt):
    """判断给定时间是否在交易时段内"""
    sec = _seconds_from_midnight(dt)
    return (AM_START <= sec <= AM_END) or (PM_START <= sec <= PM_END)


def _get_pre_close_price(code):
    """
    获取前一交易日的收盘价（用于计算涨跌额/涨跌幅）
    若无法获取，返回 None
    """
    try:
        df = ashare.get_price(code, frequency='1d', count=2)
        if df.empty:
            return None
        df = df.sort_index()
        if len(df) >= 2:
            return df.iloc[-2]['close']
        elif len(df) == 1:
            # 只有今日数据（如新股），用今日开盘价替代
            return df.iloc[0]['open']
        return None
    except Exception:
        return None


def _get_today_minute_data(code):
    """
    获取当天的全部 1 分钟 K 线，并过滤出交易时间段内的数据
    返回按时间升序的 DataFrame，包含列：open, close, high, low, volume
    若获取失败或无数据，返回 None
    """
    today = datetime.date.today()
    try:
        # count 取 1000 保证覆盖全天（A股一天最多 240 条）
        df = ashare.get_price(code, frequency='1m', count=300)
        if df.empty:
            return None
        # 仅保留今日数据
        df = df[df.index.date == today]
        if df.empty:
            return None

        # 强制指定为北京时间（无时区 -> 带时区）
        tz = pytz.timezone('Asia/Shanghai')
        if df.index.tz is None:
            df.index = df.index.tz_localize(tz, ambiguous='infer')

        # 过滤交易时间
        df = df[df.index.map(_is_trading_time)]
        if df.empty:
            return None

        df = df.sort_index()
        return df
    except Exception:
        return None


def _calc_price_decimal(df):
    """
    根据价格数据自动判断小数位数（最多 3 位）
    """
    max_dec = 0
    for val in df['close']:
        if isinstance(val, float):
            dec = len(str(val).split('.')[-1])
            max_dec = max(max_dec, dec)
    return min(max_dec, 3)


def _calc_tick_params(df, pre_close):
    """
    计算 Y 轴范围 (tick_min, tick_max) 和刻度间隔 (tick_itv)
    以前收盘价为中心，上下各扩展实际波动的 10%，保证至少 ±1%
    """
    if df.empty:
        return 0, 0, 0

    min_c = df['close'].min()
    max_c = df['close'].max()
    # 实际波动范围
    range_c = max_c - min_c
    if range_c == 0:
        range_c = abs(pre_close) * 0.01 if pre_close != 0 else 0.01

    # 扩展 10%
    lower = min(min_c, pre_close) - range_c * 0.1
    upper = max(max_c, pre_close) + range_c * 0.1
    # 保证最小范围（至少 ±1%）
    if upper - lower < abs(pre_close) * 0.01:
        upper = pre_close * 1.01
        lower = pre_close * 0.99

    tick_itv = (upper - lower) / 5
    # 四舍五入到价格小数位数
    dec = _calc_price_decimal(df)
    tick_itv = round(tick_itv, dec)
    if tick_itv <= 0:
        tick_itv = 0.01

    return lower, upper, tick_itv
