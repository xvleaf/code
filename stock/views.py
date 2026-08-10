# -*- coding: utf-8 -*-
import json
import datetime
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from . import query


# ===================== 页面渲染视图 =====================
def test(request):
    # 假设从请求中获取参数，这里用固定值演示
    asset = 'E'
    tscode = '000333.SZ'
    start = '20260101'
    end = '20260810'
    freq = 'M'
    adj = None
    # df = query.get_industry_member(tscode)
    # df = query.get_last_price('125959.SZ', 2)
    # df = query.for_trend_data(tscode, 2)
    df = query.get_kline_data(asset, tscode, '20260101', '20260810', freq)

    # return HttpResponse(df['trend'].to_html(classes='table', border=0), content_type="text/html")
    return HttpResponse(df.to_html(classes='table table-striped', border=0), content_type="text/html")


def focus_list(request):
    stocks = []
    for i in range(1, 31):
        # 模拟涨跌幅，正负交替
        change_value = (i % 10 - 4) * 0.8
        change_class = 'positive' if change_value >= 0 else 'negative'
        stocks.append({
            'code': 100000 + i,
            'name': f'股票{i:02d}',          # 例如 股票01, 股票02 ...
            'price': 3000 + i * 15,
            'plan': 50 + (i % 20),
            'win_rate': f'{50 + (i * 3) % 40}%',   # 胜率 50%~89%
            'change': f'{change_value:+.2f}%',     # 带正负号
            'change_class': change_class,
        })
    return render(request, 'focus-list.html', {'stocks': stocks})


def focus_view(request):
    context = {
        "name": "工商银行",
        "code": "601398",
        "market": "SH",
        "cat": "stock",
        "site": "focus/view",

        "view": "kline",
        "screen": "norm",
        "interval": 3000,

        "trend_act": {
            "exit": "end",
            "edit": "edit",
            "deal": "deal"
        },

        "navi": True,
        "navi_index": 2,
        "navi_count": 8,
        "navi_prev": True,
        "navi_next": True,

        "show_pilot": True,
        "pilot_prev": True,
        "pilot_next": True,

        "show_tool_bar": True,
        "is_linkable": True,
    }
    return render(request, 'focus-view.html', context)


# ===================== 通用工具函数 =====================
def _date_to_timestamp(date_obj):
    """日期转13位毫秒时间戳"""
    if isinstance(date_obj, str):
        date_obj = pd.to_datetime(date_obj)
    return int(date_obj.timestamp() * 1000)


def _calc_simple_ma_aligned(df, col, window, deci=2):
    """
    简单移动平均线，对齐 fetch.py calc_ma 逻辑
    返回与df等长数组，索引一一对应，前window-1个值为None
    """
    ma_series = df[col].rolling(window=window).mean().round(deci)
    result = []
    for trade_date, value in zip(df['trade_date'], ma_series):
        ts = _date_to_timestamp(trade_date)
        result.append([ts, value if pd.notna(value) else None])
    return result


def _calc_ema_track_aligned(df, k, d, deci=2):
    """
    EWMA轨道线，完全对齐 fetch.py Kline.calc_ema 逻辑
    :param k: 轨道宽度百分比（整数，如10代表10%）
    :param d: EMA周期
    :return: tp, up, av, lw, fl 五个等长数组
    """
    close_series = df['close']
    # 指数加权移动平均（中轨 av）
    av_series = close_series.ewm(span=d, adjust=False).mean().round(deci)

    # 轨道系数
    k_tp = 1 + 2 * k / 100
    k_up = 1 + k / 100
    k_lw = 1 - k / 100
    k_fl = 1 - 2 * k / 100

    tp_series = (av_series * k_tp).round(deci)
    up_series = (av_series * k_up).round(deci)
    lw_series = (av_series * k_lw).round(deci)
    fl_series = (av_series * k_fl).round(deci)

    tp_list, up_list, av_list, lw_list, fl_list = [], [], [], [], []
    for trade_date, tp, up, av, lw, fl in zip(
        df['trade_date'], tp_series, up_series, av_series, lw_series, fl_series
    ):
        ts = _date_to_timestamp(trade_date)
        tp_list.append([ts, tp if pd.notna(tp) else None])
        up_list.append([ts, up if pd.notna(up) else None])
        av_list.append([ts, av if pd.notna(av) else None])
        lw_list.append([ts, lw if pd.notna(lw) else None])
        fl_list.append([ts, fl if pd.notna(fl) else None])

    return tp_list, up_list, av_list, lw_list, fl_list


# ===================== K线数据一次性组装 =====================
def _prepare_kline_full(df, period, right, k=10, d=20, deci=2):
    """一次性组装所有K线数据与指标，不再分阶段"""
    df = df.sort_values('trade_date').reset_index(drop=True)
    ohlc = []
    volume = []

    # 1. 基础K线与成交量
    for _, row in df.iterrows():
        ts = _date_to_timestamp(row['trade_date'])
        ohlc.append([
            ts,
            round(row['open'], deci),
            round(row['high'], deci),
            round(row['low'], deci),
            round(row['close'], deci),
            round(row['pct_chg'], 2) if pd.notna(row['pct_chg']) else 0
        ])
        volume.append([ts, int(row['vol'])])

    # 2. EMA五轨线：tp / up / av / lw / fl
    tp, up, av, lw, fl = _calc_ema_track_aligned(df, k, d, deci)

    # 3. 简单均线与均量线
    ma = _calc_simple_ma_aligned(df, 'close', window=20, deci=deci)
    mv = _calc_simple_ma_aligned(df, 'vol', window=5, deci=0)

    # 4. 区间切换按钮数量
    n = len(df)
    if n < 50:
        show_min, show_std, show_max = 5, 10, 20
    elif n < 120:
        show_min, show_std, show_max = 10, 30, 60
    else:
        show_min, show_std, show_max = 20, 60, 120

    deadline = _date_to_timestamp(df['trade_date'].iloc[-1]) if not df.empty else 0

    # 5. 交易信号预留
    deal = {'long': [], 'short': [], 'dual': [], 'divd': []}

    return {
        # 基础K线
        'ohlc': ohlc,
        'volume': volume,
        # 轨道指标
        'tp': tp,
        'up': up,
        'av': av,
        'lw': lw,
        'fl': fl,
        # 均线与均量
        'ma': ma,
        'mv': mv,
        # 交易信号
        'deal': deal,
        # 基础配置
        'show_min': show_min,
        'show_std': show_std,
        'show_max': show_max,
        'deadline': deadline,
        'deci': deci,
        'k': k,
        'd': d,
        'right': right,
        'period': period,
    }


# ===================== 业务处理函数 =====================
def handle_kline(params):
    # tscode = params.get('code')
    tscode = '000333.SZ'
    period = params.get('period', 'day')
    right = params.get('right', 'normal')
    # 轨道参数，默认值对齐常规ENE参数
    k = int(params.get('k', 10))
    d = int(params.get('d', 20))

    freq_map = {'day': 'D', 'week': 'W', 'month': 'M'}
    freq = freq_map.get(period, 'D')
    adj = 'qfq' if right == 'adj' else None

    # 取近两年日线数据
    end = datetime.datetime.now().strftime('%Y%m%d')
    start = (datetime.datetime.now() - datetime.timedelta(days=730)).strftime('%Y%m%d')

    df = query.get_kline_data(
        asset='E',
        tscode=tscode,
        start=start,
        end=end,
        freq='D',
        adj='qfq'
    )

    if df is None or df.empty:
        return JsonResponse({'error': 'No data'}, status=404)

    # 周/月线聚合
    if period != 'day':
        df = query.kline_periods_from_daily(df, freq)

    df = df.dropna(subset=['open', 'high', 'low', 'close', 'vol'])
    df = df.sort_values('trade_date').reset_index(drop=True)

    if df.empty:
        return JsonResponse({'error': 'No valid data'}, status=404)

    deci = 2
    # 一次性返回完整数据
    result = _prepare_kline_full(df, period, right, k, d, deci)
    return JsonResponse(result)


def handle_trend(params):
    tscode = params.get('code')
    deci = 2
    result = query.get_trend_data(tscode, deci)
    if not result:
        return JsonResponse({'error': 'No trend data'}, status=404)
    return JsonResponse(result)


# ===================== 统一接口入口 =====================
@csrf_exempt
@require_http_methods(["POST"])
def chart_data(request):
    try:
        params = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    func = params.get('func')
    if func == 'kline':
        return handle_kline(params)
    elif func == 'trend':
        return handle_trend(params)
    else:
        return JsonResponse({'error': 'unsupported func'}, status=400)