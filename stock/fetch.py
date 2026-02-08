import ast
import datetime
import json
import time
import random
from typing import Dict, List

import requests

import pandas as pd
import numpy as np
import simplejson
from django.db.models import Q

from django.core.cache import cache

from models.models import StockTransFlow, StockTransDeal
from stock import func
from website import base


def check_market_code(market_with_code):
    if market_with_code == '1.100000':
        market_with_code = '1.000001'
    elif market_with_code == '0.900000':
        market_with_code = '0.399001'
    return market_with_code


def convert_market_code(market, code):
    market_with_code = f'{market}.{code}'
    if market_with_code == '1.000001':
        market = '1'
        code = '100000'
    elif market_with_code == '0.399001':
        market = '0'
        code = '900000'
    return market, code


class Link:
    # 根据板块得到板块内股票列表
    @staticmethod
    def stocks(code):
        # https://push2.eastmoney.com/api/qt/clist/get?fid=f12&pz=500&pn=1&np=1&fltt=2&fs=b:BK0437&fields=f2,f3,f12,f14
        url = 'https://push2.eastmoney.com/api/qt/clist/get'

        params = {
            'ut': random.randint(1000000, 9999999),
            'fid': 'f12',
            'pz': '1000',
            'pn': '1',
            'np': '1',
            'fltt': '2',
            'fs': f'b:{code}',
            'fields': 'f12,f13,f14'
        }

        res = requests.get(url, params=params).json()
        try:
            lists = []
            data = res['data']['diff']
            for each in data:
                lists.append({
                    'code': each['f12'],
                    'market': each['f13'],
                    'name': each['f14']
                })
        except TypeError:
            lists = []
        return lists

    # 根据股票得到所有板块列表
    @staticmethod
    def sectors(market_with_code):
        # https://push2.eastmoney.com/api/qt/slist/get?fltt=2&invt=2&fields=f12,f13,f14&secid=1.600395&pi=0&po=1&np=1&pz=5&spt=3
        url = 'https://push2.eastmoney.com/api/qt/slist/get'
        params = {
            'ut': random.randint(1000000, 9999999),
            'pi': '0',
            'po': '1',
            'pz': '100',
            'spt': '3',
            'np': '1',
            'fltt': '2',
            'invt': '2',
            'secid': market_with_code,
            'fields': 'f2,f3,f12,f13,f14'
        }

        res = requests.get(url, params=params).json()
        try:
            lists = []
            data = res['data']['diff']

            for each in data:
                lists.append({
                    'code': each['f12'],
                    'market': each['f13'],
                    'name': each['f14']
                })
        except TypeError:
            lists = []
        return lists


class Stock:
    """
    f2 - 当前价
    f3 - 涨幅
    f12 - 股票代码
    f13 - 股票市场代码
    f14 - 股票名称
    f20 - 股票市值
    """
    @staticmethod
    def list():
        url = 'https://push2.eastmoney.com/api/qt/clist/get'
        params = {
            'ut': random.randint(1000000, 9999999),
            'fid': 'f12',
            'pz': '20000',
            'pn': '1',
            'np': '1',
            'fltt': '2',
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048',
            'fields': 'f12,f13,f14'
        }
        res = requests.get(url, params=params).json()['data']['diff']
        # 排除掉以 4 开头的代码
        data = [item for item in res if not item["f12"].startswith("4")]
        return data

    @staticmethod
    def data(lists):
        data = []
        secids = ''

        for each in lists:
            try:
                market_with_code = f'{each["market"]}.{each["code"]}'
            except TypeError:
                market_with_code = f'{each.market}.{each.code}'

            market_with_code = check_market_code(market_with_code)
            secids = f'{secids},{market_with_code}' if secids else market_with_code

        if lists:
            url = 'https://push2.eastmoney.com/api/qt/ulist.np/get'

            params = {
                'ut': random.randint(1000000, 9999999),
                'fields': 'f2,f3,f12,f13,f14',
                'secids': secids
            }

            res = requests.get(url, params=params).json()['data']['diff']
            for each in res:
                market, code = convert_market_code(each['f13'], each['f12'])
                data.append({
                    'code': code,
                    'name': each['f14'],
                    'market': market,
                    'close': round(float(each['f2']) / 100, 2),
                    'change': base.format_decimal(float(each['f3']) / 100, 2)
                })

        return data


class Fund:
    @staticmethod
    def list(fund_type):
        """
        f2 - 当前价
        f3 - 涨幅
        f12 - 板块(股票)代码
        f13 - 板块(股票)市场代码
        f14 - 板块(股票)名称
        f20 - 板块(股票)市值
        f104 - 板块上涨家数
        f105 - 板块下跌家数
        f232 - 可转债正股代码
        f234 - 可转债正股名称
        """
        # 可转债 (CBF)
        # https://push2.eastmoney.com/api/qt/clist/get?fid=f12&pz=1000&pn=1&np=1&fltt=2&fs=b:MK0354
        # 上市基金 (ETF)
        # https://push2.eastmoney.com/api/qt/clist/get?fid=f12&pz=1000&pn=1&np=1&fltt=2&fs=b:MK0021,b:MK0022,b:MK0023,b:MK0024
        # 指数基金 (LOF)
        # https://push2.eastmoney.com/api/qt/clist/get?fid=f12&pz=1000&pn=1&np=1&fltt=2&fs=b:MK0404,b:MK0405,b:MK0406,b:MK0407

        if fund_type == 'CBF':
            fs = 'b:MK0354'
            fields = 'f3,f12,f13,f14,f232'
        elif fund_type == 'ETF':
            fs = 'b:MK0021,b:MK0022,b:MK0023,b:MK0024'
            fields = 'f3,f12,f13,f14,f20'
        # elif fund_type == 'LOF':
        else:
            fs = 'b:MK0404,b:MK0405,b:MK0406,b:MK0407'
            fields = 'f3,f12,f13,f14,f20'

        url = 'https://push2.eastmoney.com/api/qt/clist/get'
        params = {
            'ut': random.randint(1000000, 9999999),
            'fid': 'f12',
            'pz': '10000',
            'pn': '1',
            'np': '1',
            'fltt': '2',
            'fs': fs,
            'fields': fields
        }
        res = requests.get(url, params=params).json()
        data = res['data']['diff']
        return data

    @staticmethod
    def data(fund_type, lists):
        data = []
        if lists:
            url = 'https://push2.eastmoney.com/api/qt/ulist.np/get'

            fields = 'f2,f3,f12' if fund_type == 'CBF' else 'f2,f3,f12,f20'
            params = {
                'ut': random.randint(1000000, 9999999),
                'fields': fields,
                'secids': ','.join(f'{each.market}.{each.code}' for each in lists)
            }
            res = requests.get(url, params=params).json()['data']['diff']

            if fund_type == 'CBF':
                for each in res:
                    data.append({
                        'code': each['f12'],
                        'price': round(float(each['f2']) / 1000, 3),
                        'change': base.format_decimal(float(each['f3']) / 100, 2)
                    })
            else:
                for each in res:
                    data.append({
                        'code': each['f12'],
                        'price': round(float(each['f2']) / 1000, 3),
                        'change': base.format_decimal(float(each['f3']) / 100, 2),
                        'cap': base.format_decimal(float(each['f20']) / 100000000, 1)
                    })
        return data


class Sector:
    """
    f2 - 当前价
    f3 - 涨幅 (需/100)
    f12 - 板块(股票)代码
    f13 - 板块(股票)市场代码
    f14 - 板块(股票)名称
    f20 - 板块(股票)市值
    f104 - 板块上涨家数
    f105 - 板块下跌家数
    f232 - 可转债正股代码
    f234 - 可转债正股名称
    """

    @staticmethod
    def list():
        # https://push2.eastmoney.com/api/qt/clist/get?fid=f12&pz=200&pn=1&np=1&fltt=2&fs=m:90+t:2+f:!50&fields=f12,f14
        url = 'https://push2.eastmoney.com/api/qt/clist/get'
        params = {
            'ut': random.randint(1000000, 9999999),
            'fid': 'f12',
            'pz': '1000',
            'pn': '1',
            'np': '1',
            'fltt': '2',
            'fs': 'm:90+t:2+f:!50',
            'fields': 'f3,f12,f13,f14,f104,f105'
        }
        res = requests.get(url, params=params).json()
        data = res['data']['diff']
        return data

    @staticmethod
    def data(lists):
        url = 'https://76.push2.eastmoney.com/api/qt/ulist.np/get'

        combine_code = []
        for each in lists:
            try:
                combine_code.append(f'{each.market}.{each.code}')
            except AttributeError:
                combine_code.append(f'{each["market"]}.{each["code"]}')

        params = {
            'ut': random.randint(1000000, 9999999),
            'fields': 'f3,f12,f104,f105',
            'secids': ','.join(each for each in combine_code)
        }
        res = requests.get(url, params=params).json()['data']['diff']
        data = [
            {
                'code': each['f12'],
                'change': base.format_decimal(float(each['f3']) / 100, 2),
                'rise': each['f104'],
                'fall': each["f105"]
            }
            for i, each in enumerate(res)
        ] if lists else []

        return data


def quote(market_with_code: str, cat: str, deci):
    """
    https://push2.eastmoney.com/api/qt/stock/get?ut=202305061124&fltt=2&invt=2&volt=2
    &fields=f43,f44,f45,f46,f47,f48,f58,f60,f86,f162&secid=1.601398
    eastmoney报价数据：
    f58：”大秦铁路”，股票名字；
    f46：”27.55″，今日开盘价；
    f60：”27.25″，昨日收盘价；
    f43：”26.91″，当前价格；
    f44：”27.55″，今日最高价；
    f45：”26.20″，今日最低价；
    f19：”26.91″，竞买价，即“买一”报价；
    f39：”26.92″，竞卖价，即“卖一”报价；
    f47：”22114263″，成交的股票数，由于股票交易以一百股为基本单位，所以在使用时，通常把该值除以一百；
    f48：”589824680″，成交金额，单位为“元”，为了一目了然，通常以“万元”为成交金额的单位，所以通常把该值除以一万；
    f20：”46.95″，“买一”47手；
    f19：”26.91″，“买一”报价；
    f18：”575.90″，“买二”
    f17：”26.90″，“买二”
    f16：”147.00″，“买三”
    f15：”26.89″，“买三”
    f14：”143.00″，“买四”
    f13：”26.88″，“买四”
    f12：”151.00″，“买五”
    f11：”26.87″，“买五”
    f40：”31.00″，“卖一”31手；
    f39：”26.92″，“卖一”报价
    (f38, f37), (f36, f35), (f34,f33), (f32, f31)分别为“卖二”至“卖五”
    f86：”1683273578″，时间戳，需*1000转换；
    f162：市盈率；
    """
    if cat == 'M':
        market = market_with_code.split('.')[0]
        if market == '0':
            code = '399001'
        elif market == '1':
            code = '000001'
        else:
            market = '1'
            code = '000001'
        market_with_code = f'{market}.{code}'
    # elif cat == 'S':
    else:
        market_with_code = check_market_code(market_with_code)

    fields = 'f43,f44,f45,f46,f58,f60,f86,f162,f530'
    # 获取简洁数据
    # fields = 'f43,f58,f60'

    url = 'https://push2.eastmoney.com/api/qt/stock/get'
    params = {
        'ut': random.randint(1000000, 9999999),
        'fltt': '2',  # 报价单位为分，而不是元
        'invt': '2',  # 无数据时，为 1 时以 '0' 表示；为 2 时以 '-' 表示；为 3 时以 null 表示；为 4 时以 NaN 表示
        'volt': '3',  # 为 2 时，f47 单位为手，带小数部分；为 1 时为股；为 3 时单位为手，不带小数部分
        'fields': fields,  # f530 为报价数据
        'secid': market_with_code
    }
    res = requests.get(url, params=params)
    res = res.json()
    data = res['data']

    if data:
        try:
            change = round((data['f43'] - data['f60']) / data['f60'] * 100, 2)
        except (TypeError, ZeroDivisionError):
            change = '-'

        return {
            # 'd': data['f86'],     # 时间戳
            'n': data['f58'],       # 股票名称
            'deci': deci,             # 小数点位数
            'o': data['f46'],       # 今日开盘价
            'pc': data['f60'],      # 昨日收盘价
            'c': data['f43'],       # 当前价格
            'h': data['f44'],       # 今日最高价
            'l': data['f45'],       # 今日最低价
            'p': change,            # 涨幅
            'pe': data['f162'],     # 市盈率
            **{f'sq{5 - i}': data[f'f{31 + 2 * i}'] for i in range(0, 5)},  # 卖五到卖一报价
            **{f'ss{5 - i}': data[f'f{32 + 2 * i}'] for i in range(0, 5)},  # 卖五到卖一股数(手)
            **{f'bq{5 - i}': data[f'f{11 + 2 * i}'] for i in range(0, 5)},  # 买五到买一报价
            **{f'bs{5 - i}': data[f'f{12 + 2 * i}'] for i in range(0, 5)}   # 买五到买一股数(手)
        }
    else:
        return {}


def trend(request, market_with_code, init, deci):
    """
    https://push2.eastmoney.com/api/qt/stock/trends2/get?
    fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13
    &fields2=f51,f52,f53,f54,f55,f56,f57,f58
    &ut=fa5fd1943c7b386f172d689310b
    &ndays=1
    &iscr=0
    &secid=1.601398

    fields1:
        //f1=code
        //-f2=market
        //-f3=type
        //-f4=status
        //f5=name
        //-f6=deci
        //-f7=preSettlement
        //f8=preClose
        //-f9=beticks
        //-f10=trendsTotal
        //-f11=time
        //-f12=kind
        //-f13=prePrice

    fields2:
        //f51 = time
        //-f52 = open
        //f53 = close
        //-f54 = high
        //-f55 = low
        //f56 = volume
        //-f57 = amount
        //-f58 = Amplitude
    """
    market_with_code = check_market_code(market_with_code)
    cache_key = f"trend-{request.session.session_key}"

    # 确定曲线上显示的小数点位数
    ohlc = []
    volume = []

    cache_data = cache.get(cache_key)
    if not cache_data or init or cache_data['code'] != market_with_code:
        cache_data = {
            'code': market_with_code,
            'index': 0,
            'high': float('-inf'),
            'low': float('inf')
        }

    index = cache_data['index']
    high = cache_data['high']
    low = cache_data['low']

    url = 'https://push2.eastmoney.com/api/qt/stock/trends2/get'
    params = {
        'ut': random.randint(1000000, 9999999),
        'ndays': '1',
        'iscr': '0',
        'fields1': 'f1,f5,f8',
        'fields2': 'f51,f53,f56',
        'secid': market_with_code
    }

    res = requests.get(url, params=params).json()
    data = res['data']

    close_prev = float(data['preClose'])
    trends = data['trends']
    count_trends = len(trends)

    for item in trends[index:]:
        each = item.split(',')
        timestamp = get_timestamp(each[0], '%Y-%m-%d %H:%M')
        close = float(each[1])
        high = max(high, close)
        low = min(low, close)

        delta = close - close_prev
        percent = delta / close_prev * 100

        ohlc.append([
            int(timestamp),
            float(close),
            round(float(percent), 2),
            round(float(delta), deci)
        ])
        volume.append([
            int(timestamp),
            int(float(each[2]))
        ])

    index = count_trends - 1

    if index == -1:
        high = close_prev
        low = close_prev
    else:
        cache_data = {
            'code': market_with_code,
            'index': index,
            'high': high,
            'low': low
        }
        cache.set(cache_key, cache_data, base.configs('cache')['day'])

    tick_gap = max(abs(close_prev - high), abs(close_prev - low))
    tick_gap = 1.2 * tick_gap if tick_gap > 0 else close_prev * 0.1
    unit = 10 ** (-deci)
    tick_itv = max(round(tick_gap / 2, deci), unit)
    tick_max = round(close_prev + 2 * tick_itv, deci)
    tick_min = round(close_prev - 2 * tick_itv, deci)

    if init:
        count_volume = len(volume)
        open_time = base.configs('time')

        if count_volume > 0:
            time_start = volume[count_volume - 1][0]
        else:
            time_start = datetime.date.today().strftime('%Y-%m-%d') + ' ' + open_time['open']
            time_start = get_timestamp(time_start, '%Y-%m-%d %H:%M')

        date = time.strftime('%Y-%m-%d', time.localtime(time_start / 1000))

        time_points = {
            'break': open_time['break'],
            'resume': open_time['resume'],
            'end': open_time['close']
        }

        for point_name, point_value in time_points.items():
            point_time = get_timestamp(f'{date} {point_value}', '%Y-%m-%d %H:%M')
            time_points[point_name] = point_time

        time_increment = 60000
        time_start += time_increment
        placeholder = []

        while time_start < time_points['end']:
            if time_start < time_points['break']:
                placeholder.append([time_start, None, None, None])
            elif time_start < time_points['resume']:
                time_start = time_points['resume']
                placeholder.append([time_start, None, None, None])
            else:
                placeholder.append([time_start, None, None, None])
            time_start += time_increment

        ohlc.extend(placeholder)
        volume.extend([[item[0], None] for item in placeholder])

    return {
        'pc': close_prev,
        'high': high,
        'low': low,
        'deci': deci,
        'index': index,
        'tick_itv': tick_itv,
        'tick_max': tick_max,
        'tick_min': tick_min,
        'ohlc': ohlc,
        'volume': volume
    }


class Kline:
    """
    https://push2his.eastmoney.com/api/qt/stock/kline/get?
    fields1=f1,f2,f3,f4,f5,f6,f7,f8&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61
    &beg=0&end=20500101&ut=fa5fd1943c7b386f172d689310b&rtntype=6&secid=1.000001&klt=101&fqt=1

    fields1：
    f1 = code
    -f2 = market
    f3 = name
    -f4 = deci
    -f5 = dktotal
    -f6 = preKPrice //后复权f6!=f7
    -f7 = prePrice
    -f8 = qtMiscType

    fields2：
    f51 = date, yyyy-MM-dd
    f52 = open
    f53 = close
    f54 = high
    f55 = low
    f56 = volume,手
    -f57 = amount
    -f58 = Amplitude
    f59 = change percent
    -f60 = change price
    f61 = turnover rate

    beg: begin date (0-股票上市日期)
    end: end date
    ut: random number

    rtntype: return type

    secid:
    0. - 上证
    1. - 深证

    klt: kline time
    101 - day
    102 - week
    103 - month
    104 - quarter
    105 - half year
    106 - year

    fqt:
    0 - 不复权
    1 - 前复权
    -2 - 后复权
    """

    # right=adj 复权, right=div 除权
    @staticmethod
    def view(market_with_code: str, right: str, period: str, k: int, d: int, width: int, deci, deadline: int = -1):
        market_with_code = check_market_code(market_with_code)
        data = Kline.get_kline(market_with_code, right, period)
        klines = data['klines']
        ohlc, volume = Kline.sort_kline(klines)
        return Kline.show_kline(ohlc, volume, market_with_code, deci, right, period, k, d, width, deadline)

    @staticmethod
    def value(market_with_code: str, right: str, period: str):
        market_with_code = check_market_code(market_with_code)
        data = Kline.get_kline(market_with_code, right, period)
        klines = data['klines']
        ohlc = []
        for kline in klines:
            each = kline.split(',')
            timestamp = get_timestamp(each[0], '%Y-%m-%d')
            open_price, close, high, low = map(float, each[1:5])
            # 日期，开盘，最高，最低，收盘
            ohlc.append([timestamp, open_price, high, low, close])
        return ohlc

    @staticmethod
    def last(market_with_code):
        market_with_code = check_market_code(market_with_code)
        # 30 天内必定会有 k 线数据
        delta = datetime.timedelta(days=30)
        start = datetime.date.today() - delta
        start = start.strftime('%Y%m%d')

        kline = Kline.get_kline(market_with_code, 'adj', 'day', start)
        name = kline['name']
        klines = kline['klines']
        get_last = klines[len(klines) - 1].split(',')
        close = float(get_last[2])
        change = float(get_last[7])

        return name, close, change

    @staticmethod
    def get_kline(market_with_code: str, right: str, period: str, start: str = None):
        market_with_code = check_market_code(market_with_code)
        kline_param = base.configs('kline')

        klt = 101 if period == 'day' else 102 if period == 'week' else 103 if period == 'month' else 106
        if not start:
            start = kline_param['start'][period]
        end = kline_param['end'][period]

        url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
        params = {
            'ut': random.randint(1000000, 9999999),
            'beg': start,
            'end': end,
            'klt': klt,
            'fqt': 0 if right == 'div' else 1,
            'rtntype': 6,
            # 若不带fields1参数，返回的是空数据
            'fields1': 'f1,f3',
            # f51/52等顺序不会改变返回来的数据顺序
            'fields2': 'f51,f52,f53,f54,f55,f56,f58,f59,f61',
            'secid': market_with_code
        }
        res = requests.get(url, params=params).json()
        data = res['data']
        return data

    @staticmethod
    def sort_kline(klines: list):
        ohlc = []
        volume = []

        for kline in klines:
            each = kline.split(',')
            timestamp = get_timestamp(each[0], '%Y-%m-%d')
            open_price, close_price, high_price, low_price = map(float, each[1:5])

            # 若 each[5] 为带小数点字符串，int 直接转换会出现错误，因此先转为浮点数，再转整数
            volume_value = int(float(each[5]))
            volume.append([timestamp, volume_value])
            amplitude, change, turnover = map(float, each[6:9])

            # 日期，开盘，最高，最低，收盘，涨幅，振幅，换手率
            ohlc.append([timestamp, open_price, high_price, low_price, close_price, change, amplitude, turnover])

        return ohlc, volume

    @staticmethod
    def show_kline(ohlc: list, volume: list, market_with_code: str, deci: int,
                   right: str, period: str, k: int, d: int, width: int, deadline: int):
        # 由于数据库中存储的 code 为 100000 或 900000，因此不执行 check_market_code
        # market_with_code = check_market_code(market_with_code)
        ema = Kline.calc_ema(ohlc, k, d, deci)

        kline_param = base.configs('kline')
        period_ma_d = int(kline_param['ma'][period]['a'])
        period_mv_d = int(kline_param['ma'][period]['v'])
        ma_p = Kline.calc_ma('price', ohlc, period_ma_d, deci)
        ma_v = Kline.calc_ma('volume', volume, period_mv_d, 0)
        ma = {'ma': ma_p, 'mv': ma_v}

        deal = Deal.get_deal(ohlc, market_with_code, right, period)
        show = Kline.calc_show(ohlc, volume, period, width, deadline)
        data = {**show, **ema, **ma, **deal}
        data.update({
            'right': right,
            'period': period,
            'k': k,
            'd': d,
            'deci': deci
        })

        return data

    @staticmethod
    def calc_show(ohlc: list, volume: list, period: str, width: int, deadline: int = -1):
        kline_param = base.configs('kline')
        density = kline_param['density']

        count = len(volume)
        increment = 86400000 * (7 if period == 'week' else 30 if period == 'month' else 1)

        # k线显示蜡烛数量
        count_std = round(width * float(density['std']) / 100)
        count_max = round(width * float(density['max']) / 100)
        count_min = round(width * float(density['min']) / 100)

        if count < count_std:
            missing = count_std - count
            ohlc, volume = Kline.append_gaps(ohlc, volume, increment, count, missing)
            count = len(volume)
            # deadline 索引
            index_ddl = count - 1
        else:
            if deadline == -1:
                index_ddl = count - 1
            else:
                index_ddl = base.first_satisfy_index(volume, 0, deadline, 'left')

        index_std = min(max(index_ddl, count_std - 1), count - 1)
        index_max = min(max(index_ddl, count_max - 1), count - 1)
        index_min = min(max(index_ddl, count_min - 1), count - 1)

        show_std = int((volume[index_std][0] - volume[max(index_std - count_std + 1, 0)][0]) / 86400000)
        show_max = int((volume[index_max][0] - volume[max(index_max - count_max + 1, 0)][0]) / 86400000)
        show_min = int((volume[index_min][0] - volume[max(index_min - count_min + 1, 0)][0]) / 86400000)

        deadline = volume[index_std][0]

        return {'show_std': show_std, 'show_max': show_max, 'show_min': show_min,
                'deadline': deadline, 'ohlc': ohlc, 'volume': volume}

    @staticmethod
    def append_gaps(ohlc: list, volume: list, increment: int, count: int, missing: int):
        last = volume[count - 1][0]

        last_dates = np.array([last + (i + 1) * increment for i in range(missing)])

        ohlc_missing = np.column_stack((last_dates, np.zeros((missing, 4)))).tolist()
        ohlc.extend(ohlc_missing)

        volume_missing = np.column_stack((last_dates, np.zeros((missing, 1)))).tolist()
        volume.extend(volume_missing)

        return ohlc, volume

    @staticmethod
    def calc_ma(cat: str, lists, d: int, deci: int):
        value_position = 4 if cat == 'price' else 1

        extract = Kline.extract_list(lists, value_position)

        series_ma = pd.Series(extract)
        ma = series_ma.rolling(window=d).mean().round(deci)

        date = Kline.extract_list(lists, 0)
        ma = Kline.combine_list(date, ma)
        for each in ma[:d - 1]:
            each[1] = None

        return ma

    @staticmethod
    def calc_ema(ohlc, k: int, d: int, deci: int):
        cls = Kline.extract_list(ohlc, 4)
        series = pd.Series(cls)
        k_tp = 1 + 2 * k / 100
        k_up = 1 + k / 100
        k_lw = 1 - k / 100
        k_fl = 1 - 2 * k / 100

        av = series.ewm(span=d, adjust=False).mean().round(deci)
        tp = (av * k_tp).round(deci)
        up = (av * k_up).round(deci)
        lw = (av * k_lw).round(deci)
        fl = (av * k_fl).round(deci)

        date = Kline.extract_list(ohlc, 0)
        tp = Kline.combine_list(date, tp)
        up = Kline.combine_list(date, up)
        av = Kline.combine_list(date, av)
        lw = Kline.combine_list(date, lw)
        fl = Kline.combine_list(date, fl)

        return {'tp': tp, 'up': up, 'av': av, 'lw': lw, 'fl': fl}

    @staticmethod
    def extract_list(lists: list, col: int) -> np.ndarray:
        try:
            dim = len(lists[0])
        except TypeError:
            dim = 1
        array = np.array(lists) if dim == 1 else np.array(lists)[:, col]
        return array

    @staticmethod
    def combine_list(list_a, list_b, col_a: int = 0, col_b: int = 0):
        if not isinstance(list_a, np.ndarray):
            list_a = Kline.extract_list(list_a, col_a)

        if not isinstance(list_b, np.ndarray):
            list_b = Kline.extract_list(list_b, col_b)

        # 组合两个 list 中的指定列
        lists = np.hstack((list_a[:, np.newaxis], list_b[:, np.newaxis])).tolist()
        return lists


class Deal:
    @staticmethod
    def process_deal(trans_flow_list: List[Dict], right: str, period: str, market_with_code: str) -> dict:
        long_factor = 0.99
        short_factor = 1.01
        dual_factor = 0.99

        # info 用于K线指示, 格式为[{'stamp':ohlc[0]日期戳，'deal':[买入日期(mm/dd)，交易方向:'L'-买入/'S'-卖出，价格，数量]}]
        info = []
        # 买入集合，数组格式为[时间戳，开盘价 * 0.99]
        long = []
        # 卖出集合，数组格式为[时间戳，收盘价 * 1.01]
        short = []
        # 既有买入也有卖出集合，数组格式为[时间戳，开盘价 * 0.99]
        dual = []

        # check 的原因是交易当天的周/月 k 线不是周/月的最后一个交易日
        # check 用于后面 js 调用 deal 数据库时，核查是否 long/short/dual 最后一个数据是否与 trans_flow_list 最后交易日期进行过核查
        # 格式为{'done':0-未核查完/1-核查完，可直接调用，'date':最后交易日期时间戳，用于后面 check 时比较用}
        done = 1 if period == 'day' else 0
        last_deal_date = trans_flow_list[len(trans_flow_list) - 1]['date']
        check = {'done': done, 'date': get_timestamp(str(last_deal_date), '%Y-%m-%d')}

        ohlc_data = Kline.value(market_with_code, right, period)
        index = []
        index_prev = None

        for i, trans in enumerate(trans_flow_list):
            stamp_date = get_timestamp(str(trans['date']), '%Y-%m-%d')
            index_ohlc = base.first_satisfy_index(ohlc_data, 0, stamp_date, 'left')

            if index_ohlc == index_prev:
                last_group = index.pop()
                last_group.append(i)
                index.append(last_group)
            else:
                index.append([index_ohlc, i])
                index_prev = index_ohlc if index_ohlc != -1 else None

        for each in index:
            if each[0] >= 0:

                info_each = {'stamp': ohlc_data[each[0]][0]}
                deal_each = []
                group_trade = ''

                for i in each[1:]:
                    flows = trans_flow_list[i]
                    adjusted = ast.literal_eval(flows['adjusted'])
                    deal_each.append([
                        flows['date'].strftime('%m/%d'),
                        flows['intent'],
                        flows['price'] if right == 'div' else adjusted['price'],
                        flows['qty'].replace('-', '') if right == 'div' else adjusted['qty']
                    ])

                    group_trade += flows['intent']

                info_each.update({'deal': deal_each})
                info.append(info_each)

                ohlc_each = ohlc_data[each[0]]
                if 'L' in group_trade and 'S' in group_trade:
                    dual.append([ohlc_each[0], round(dual_factor * ohlc_each[3], 3)])
                elif 'L' in group_trade:
                    long.append([ohlc_each[0], round(long_factor * ohlc_each[3], 3)])
                else:
                    short.append([ohlc_each[0], round(short_factor * ohlc_each[2], 3)])

        data = {right: {'check': check, 'info': info, 'long': long, 'short': short, 'dual': dual}}
        return data

    @staticmethod
    def save_deal(code: str) -> None:
        trans_flow_list = StockTransFlow.objects.filter(code=code).values(
            'market', 'name', 'date', 'intent', 'price', 'qty', 'adjusted'
        ).filter(Q(event='T') | Q(event='E')).order_by('flow')

        period_mapping = ['day', 'week', 'month']
        right_mapping = ['adj', 'div']
        name = trans_flow_list[0]['name']
        market = trans_flow_list[0]['market']

        data = {}

        trans_deal_inst = StockTransDeal.objects.filter(code=code).first()
        if trans_deal_inst is not None:
            trans_deal_inst.day = None
            trans_deal_inst.week = None
            trans_deal_inst.month = None
        else:
            trans_deal_inst = StockTransDeal(
                code=code,
                name=name,
                market=market
            )

        for period in period_mapping:
            data[period] = {}
            for right in right_mapping:
                data[period].update(Deal.process_deal(trans_flow_list, right, period, f'{market}.{code}'))

        # 更新 trans_deal_inst 对象的属性
        for period, period_data in data.items():
            setattr(trans_deal_inst, period, json.dumps(period_data))
        trans_deal_inst.save()

    @staticmethod
    def get_deal(ohlc: list, market_with_code: str, right: str, period: str):
        try:
            code = market_with_code.split('.')[1]

            confirm_adj_deal_data_cache_key = f'confirm_adj_deal_data'
            confirm_adj_deal_data = cache.get(confirm_adj_deal_data_cache_key)

            if right == 'adj':
                # 设置为在 4 秒内 k 线图中，点击 div 再点击 adj，代表更新交易的复权数据
                if confirm_adj_deal_data and confirm_adj_deal_data == [code, 'div', period]:
                    trans_flow_list = StockTransFlow.objects.filter(code=code)
                    trans_flow_inst = trans_flow_list.last()
                    deci = 3 if trans_flow_inst.type == 'F' else 2
                    func.adj_deal_data(trans_flow_list, market_with_code, deci)
                    Deal.save_deal(code)
                    cache.delete(confirm_adj_deal_data_cache_key)
                else:
                    cache.set(confirm_adj_deal_data_cache_key, [code, 'adj', period], 4)
            else:
                if confirm_adj_deal_data and confirm_adj_deal_data == [code, 'adj', period]:
                    cache.set(confirm_adj_deal_data_cache_key, [code, 'div', period], 2)
                else:
                    cache.delete(confirm_adj_deal_data_cache_key)

            trans_deal_inst = StockTransDeal.objects.get(code=code)
            deal_dict = simplejson.loads(getattr(trans_deal_inst, period))

            deal_check = deal_dict[right]['check']
            if deal_check['done'] == 0:
                index_ohlc = base.first_satisfy_index(ohlc, 0, deal_check['date'], 'left')
                stamp = ohlc[index_ohlc][0]
                done = 1 if index_ohlc < len(ohlc) - 1 else 0

                deal_last_index = len(deal_dict[right]['info']) - 1
                info_stamp_last = deal_dict[right]['info'][deal_last_index]['stamp']

                for r in ['adj', 'div']:
                    deal_dict[r]['check']['done'] = done
                    deal_dict[r]['info'][deal_last_index]['stamp'] = stamp

                    for kind in ['long', 'short', 'dual']:
                        deal_cat_index = len(deal_dict[r][kind]) - 1
                        if deal_cat_index >= 0 and deal_dict[r][kind][deal_cat_index][0] == info_stamp_last:
                            deal_dict[r][kind][deal_cat_index][0] = stamp

                setattr(trans_deal_inst, period, json.dumps(deal_dict))
                trans_deal_inst.save()

            deal = deal_dict[right]
        except StockTransDeal.DoesNotExist:
            deal = []
        return {'deal': deal}


def get_close_price(market_with_code: str, deci: int) -> dict:
    market_with_code = check_market_code(market_with_code)
    stock_data = quote(market_with_code, 'S', deci)

    if stock_data:
        # 早盘前得不到 close 数据
        try:
            name = stock_data['n']
            # float 作用仅是触发值错误
            close = float(stock_data['c'])
            # 转换为字符型，并自动设定小数点后保留位数
            close = base.format_decimal(close)
            change = base.format_decimal(stock_data['p'], 2)
        except (ValueError, IndexError):
            try:
                name, close, change = Kline.last(market_with_code)
                close = base.format_decimal(close)
                change = base.format_decimal(change, 2)
            except IndexError:
                return {}
        return {'name': name, 'close': close, 'change': change}
    else:
        return {}


"""
def count_decimals(lists, loops: int = 10) -> int:
    count = len(lists)
    decimals = [
        len(each_str.split('.')[1].rstrip('0'))
        for each_str in map(str, lists[:loops if count >= loops else count])
        if '.' in each_str
    ]
    return max(decimals, default=0)
"""


def get_timestamp(date: str, form: str) -> int:
    # strptime()， 将时间字符串转换成结构化时间，后面格式须与前面时间格式一致
    # mktime()，将结构化时间转换为时间戳，单位为秒，因此需要 *1000，将时间单位转换为毫秒
    return int(time.mktime(time.strptime(date, form)) * 1000)
