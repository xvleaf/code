# -*- coding: utf-8 -*-
import os
import json
import datetime
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from . import tushare, kline, trend

TREND_REQUEST_INTERVAL = int(os.environ.get('TREND_REQUEST_INTERVAL', 60000))


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
    df = tushare.get_kline_data(asset, tscode, '20240101', '20260810', freq)

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
        "code": "601398.SH",
        "market": "SH",
        "cat": "stock",
        "site": "focus/view",

        "view": "trend",
        "screen": "norm",
        "interval": TREND_REQUEST_INTERVAL,

        "trend_act": {
            "exit": "end",
            "edit": "edit",
            "deal": "deal"
        },

        "navi": False,
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


# ===================== 统一接口入口 =====================
@require_http_methods(["POST"])
def chart_data(request):
    try:
        params = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    func = params.get('func')
    if func == 'kline':
        data = kline.kline_data_for_chart('E', '000333.SZ')
        return data
    elif func == 'trend':
        code = params.get('code')
        init = params.get('init')
        data = trend.get_trend_data('000333.SZ', init, request.session)
        return JsonResponse(data)
    else:
        return JsonResponse({'error': 'unsupported func'}, status=400)