import ast
import hashlib
import math
import os
from bisect import bisect_right
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.db import transaction, DatabaseError, models
from django.db.models import F, Q, When, Value, Case, IntegerField, CharField, Max
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404

from models.models import StockCashFlow
from models.models import StockFilterList
from models.models import StockFocusIndex, StockFocusFlow
from models.models import StockFundList, StockSectorList
from models.models import StockTransIndex, StockTransFlow, StockTransDeal
from models.models import StockReviewFocus, StockReviewTrans
from stock import fetch
from website import base


def set_follow_up(session_key: str, site: str = None, code: str = None,
                  market: str = None, name: str = None, review=None) -> dict:
    cat = None
    if code:
        if '.' in code:
            code = code.split('.')[1]

        try_inst = None
        try_models = [StockFilterList, StockFundList, StockSectorList]
        cat_mapping = {StockFilterList: 'stock', StockFundList: 'fund', StockSectorList: 'sector'}
        for model in try_models:
            try_inst = model.objects.filter(code=code).first()
            if try_inst:
                cat, market, name = cat_mapping[model], try_inst.market, try_inst.name
                break

        if not try_inst:
            if code == '100000':
                cat, market, name = None, '1', '上证指数'
            elif code == '900000':
                cat, market, name = None, '0', '深证指数'
            else:
                raise Http404

    follow_up_cache_key = f'follow-up-{session_key}'
    follow_up = {
        'site': site,
        'cat': cat,
        'market': market,
        'code': code,
        'name': name
    }

    if review:
        follow_up.update({'review': review})

    cache.set(follow_up_cache_key, follow_up, base.configs('cache')['day'])
    return follow_up


# base-master 页面显示所需变量
def page_display(session_key: str, site: str, chart: bool = False, screen: str = None, viewport: str = None) -> dict:
    display_viewport_cache_key = f'display-viewport-{session_key}'
    display_screen_cache_key = f'display-screen-{session_key}'

    if not viewport:
        viewport = cache.get(display_viewport_cache_key) or base.configs('viewport')['fit']
    else:
        cache.set(display_viewport_cache_key, viewport, base.configs('cache')['long'])

    if not screen:
        screen = cache.get(display_screen_cache_key) or 'norm'
    else:
        cache.set(display_screen_cache_key, screen, base.configs('cache')['long'])

    display = {
        'site': site,
        'viewport': viewport,
        'screen': screen,
        'chart': chart
    }

    return display


# 被调用的 chart-view 页面显示所需变量
def chart_display(session_key: str, site: str, cat: str, code: str, name: str, market: str, view: str = None) -> dict:
    if not view:
        view = get_chart_view(session_key, site)

    display_screen_cache_key = f'display-screen-{session_key}'
    screen = cache.get(display_screen_cache_key) or 'norm'

    interval = base.configs('refresh')['interval']

    display = {
        'site': site,
        'cat': cat,
        'code': code,
        'name': name,
        'market': market,
        # chart 模式：kline/trend
        'view': view,
        # 用于显示最大化/最小化按钮
        'screen': screen,
        # 分时图/报价刷新周期
        'interval': interval
    }

    return display


def get_chart_view(session_key: str, site: str, view: str = None, delete: bool = None) -> str:
    view_mapping = {
        'focus/view': 'focus',
        'focus/plus': 'focus',
        'focus/edit': 'focus',
        'fund/view': 'fund',
        'sector/view': 'sector',
        'filter/view': 'filter',
        'filter/refer/view': 'filter',
        'trans/view': 'trans',
        'trans/deal': 'trans',
        'review/focus/view': 'review',
        'review/trans/view': 'review',
        'link/sector/view': 'query',
        'link/stock/view': 'query',
        'query': 'query'
    }

    if delete:
        for key in view_mapping.keys():
            chart_view_cache_key = f'{key}-view-{session_key}'
            cache.delete(chart_view_cache_key)

    chart_view_cache_key = f'{site}-view-{session_key}'
    if not view:
        view = cache.get(chart_view_cache_key) or base.configs('view').get(view_mapping.get(site), '')

    cache.set(chart_view_cache_key, view, base.configs('cache')['day'])
    return view


# 不包括 review/focus/view 及 review/trans/view
def get_chart_navi(session_key: str, site: str, code: str, navi_func: str = None, navi_way: str = None) -> dict:
    flow_list_mapping = {
        'focus/view': 'focus/list',
        'filter/view': 'filter/list',
        'filter/refer/view': 'filter/refer',
        'fund/view': 'fund/list',
        'sector/view': 'sector/list',
        'link/sector/view': 'link/sector/list',
        'link/stock/view': 'link/stock/list',
        'trans/view': 'trans/list'
    }
    flow_list_site = flow_list_mapping.get(site)
    if not flow_list_site:
        # 不在 flow_list_mapping 中，意味着不显示导航栏
        navi = get_navi_init(session_key, site, [], code)
    else:
        flow_list_cache_key = f'{flow_list_site}-flow-list-{session_key}'
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        follow_up_cache_key = f'follow-up-{session_key}'

        navi_list = cache.get(flow_list_cache_key)
        follow_up = cache.get(follow_up_cache_key)
        site_prev = follow_up['site'] if follow_up else None

        check_mapping = {
            'focus/view': ['focus/list', 'focus/view', 'focus/edit'],
            'filter/view': ['filter/list', 'filter/view'],
            'filter/refer/view': ['filter/refer', 'filter/refer/view'],
            'fund/view': ['fund/list', 'fund/view'],
            'sector/view': ['sector/list', 'sector/view'],
            'link/sector/view': ['link/sector/list', 'link/sector/view'],
            'link/stock/view': ['link/stock/list', 'link/stock/view'],
            'trans/view': ['trans/list', 'trans/view']
        }
        check_navi_index = True if site in check_mapping and site_prev in check_mapping[site] else False

        if '.' in code:
            code = code.split('.')[1]
        navi_index = base.find_satisfy_index(navi_list, 'code', code)

        if not check_navi_index or navi_index == -1:
            navi = get_navi_init(session_key, site, [], code)
        else:
            navi = cache.get(chart_navi_cache_key) or get_navi_init(session_key, site, navi_list, code)
            navi['navi_index'] = navi_index

        if navi_func == 'navi':
            # 仅适用于 fund/view 和 filter/view
            if navi_way == 'delete':
                navi_count = navi['navi_count']
                if site != 'filter/refer/view':
                    navi_list = navi_list.exclude(code=code)
                    cache.set(flow_list_cache_key, navi_list, base.configs('cache')['day'])
                    navi_count = navi_count - 1
                    if navi_index == navi_count:
                        navi_index = navi_index - 1
                else:
                    # 在 get_filter_refer_list 中使用了 union 方法后，exclude 就不能使用了
                    if navi_index < navi_count - 1:
                        navi_index = navi_index + 1

                navi_prev = True if navi_index > 0 else False
                navi_next = True if navi_index < navi_count - 1 else False
                navi.update({'navi_count': navi_count})
            elif navi_way == 'prev':
                # js 能够提交 navi_way == 'prev' 就说明 navi['navi_index'] != 0
                navi_index = navi['navi_index'] - 1
                navi_prev = True if navi_index > 0 else False
                navi_next = True
            # elif navi_way == 'next':
            else:
                navi_index = navi['navi_index'] + 1
                navi_count = navi['navi_count']
                navi_prev = True
                navi_next = True if navi_index < navi_count - 1 else False

            try:
                navi_market = navi_list[navi_index]['market']
                navi_code = navi_list[navi_index]['code']
                navi_name = navi_list[navi_index]['name']
            except TypeError:
                navi_market = navi_list[navi_index].market
                navi_code = navi_list[navi_index].code
                navi_name = navi_list[navi_index].name

            if site == 'link/sector/view' or site == 'link/stock/view':
                cat = 'sector' if site == 'link/sector/view' else 'stock'
                follow_up = {'site': site, 'cat': cat, 'market': navi_market, 'code': navi_code, 'name': navi_name}
                cache.set(follow_up_cache_key, follow_up, base.configs('cache')['day'])
            else:
                set_follow_up(session_key, site, navi_code, navi_market, navi_name)

            navi.update({
                'navi_index': navi_index,
                'navi_prev': navi_prev,
                'navi_next': navi_next
            })

            get_pilot = get_pilot_init(session_key, site, navi_code)
            navi.update(get_pilot)

        if navi_func == 'pilot':
            if navi_way == 'prev':
                pilot_index = navi['pilot_index'] + 1
                pilot_count = navi['pilot_count']
                pilot_prev = True if pilot_index < pilot_count - 1 else False
                pilot_next = True
            # elif navi_way == 'next':
            else:
                pilot_index = navi['pilot_index'] - 1
                pilot_next = True if pilot_index > 0 else False
                pilot_prev = True

            navi.update({
                'pilot_index': pilot_index,
                'pilot_prev': pilot_prev,
                'pilot_next': pilot_next
            })

            pilot_list = cache.get(pilot_list_cache_key)

            pilot_date = pilot_list[pilot_index]['date']
            deadline = base.date_to_timestamp(str(pilot_date))
            # 修改 deadline，用于 chart_data 视图
            get_kline_param(session_key, 'deadline', deadline)

        cache.set(chart_navi_cache_key, navi, base.configs('cache')['day'])

    return navi


def get_navi_init(session_key: str, site: str, navi_list: list, code: str) -> dict:
    chart_navi_cache_key = f'chart-navi-{session_key}'

    if '.' in code:
        code = code.split('.')[1]
    navi_index = base.find_satisfy_index(navi_list, 'code', code)

    if not navi_list or navi_index == -1:
        navi = {
            'navi': False,
            # 当前股票在列表中的顺序号，页面实际显示为 index + 1
            'navi_index': -1,
            'navi_count': 0,
            'navi_prev': False,
            'navi_next': False,
            # 是否显示 pilot（同一只股票同一 batch 之间的切换）
            'pilot': False,
            # 当前 batch 下的顺序号，页面实际显示为 index + 1
            'pilot_index': -1,
            'pilot_count': 0,
            # 是否激活状态显示向前/向后按钮，否为灰色显示
            'pilot_prev': False,
            'pilot_next': False
        }
        cache.delete(chart_navi_cache_key)
    else:
        navi_count = len(navi_list)
        navi_prev = True if navi_index > 0 else False
        navi_next = True if navi_index < navi_count - 1 else False

        navi = {
            'navi': True,
            # 当前股票在列表中的顺序号，实际为 index + 1
            'navi_index': navi_index,
            'navi_count': navi_count,
            # 是否显示 pilot（同一只股票同一 batch 之间的切换）
            'navi_prev': navi_prev,
            'navi_next': navi_next
        }

        get_pilot = get_pilot_init(session_key, site, code)
        navi.update(get_pilot)
        cache.set(chart_navi_cache_key, navi, base.configs('cache')['day'])

    return navi


# 不包括 review/focus/view 及 review/trans/view
def get_pilot_init(session_key: str, site: str, code: str):
    pilot_model_mapping = {
        'focus/view': 'StockFocusIndex',
        'trans/view': 'StockTransIndex'
    }

    pilot_display = True if site in pilot_model_mapping else False

    if not pilot_display:
        pilot_index = -1
        pilot_count = 0
        pilot_prev = False
        pilot_next = False
    else:
        pilot_model = pilot_model_mapping[site]

        if '.' in code:
            code = code.split('.')[1]

        if pilot_model == 'StockFocusIndex':
            flow_pilot_inst = StockFocusIndex.objects.get(code=code)
            pilot_list = list(flow_pilot_inst.Flows.values(
                'flow', 'code', 'name', 'market', 'date',
                # 增加 model 列
                model=Value('StockFocusFlow', output_field=CharField())
            ).order_by('-flow').exclude(event='E'))

        # elif pilot_model == 'StockTransIndex':
        else:
            flow_pilot_inst = StockTransIndex.objects.get(code=code)
            pilot_list = list(flow_pilot_inst.Flows.values(
                'flow', 'code', 'name', 'market', 'date',
                model=Value('StockTransFlow', output_field=CharField())
            ).order_by('-flow'))

        pilot_count = len(pilot_list)
        if pilot_count > 0:
            pilot_list_cache_key = f'pilot-list-{session_key}'
            cache.set(pilot_list_cache_key, pilot_list, base.configs('cache')['day'])

            pilot_index = 0
            pilot_prev = True if pilot_count > 1 else False
            pilot_next = False
        else:
            pilot_index = -1
            pilot_prev = False
            pilot_next = False

    pilot = {
        'pilot': pilot_display,
        'pilot_index': pilot_index,
        'pilot_count': pilot_count,
        'pilot_prev': pilot_prev,
        'pilot_next': pilot_next
    }

    return pilot


def review_chart_navi(session_key: str, site: str, navi_func: str = None, navi_way: str = None):
    follow_up_cache_key = f'follow-up-{session_key}'
    follow_up = cache.get(follow_up_cache_key)
    review = follow_up.get('review')

    navi_list = review['navi_list']
    pilot_list = review['pilot_list']
    navi_index = review['navi_index']
    pilot_index = review['pilot_index']
    current_model = review['current_model']
    current_flow = review['current_flow']
    current_code = review['current_code']
    current_market = review['current_market']
    current_name = review['current_name']

    navi_count = len(navi_list)
    pilot_count = len(pilot_list)
    navi_prev = True if navi_index > 0 else False
    navi_next = True if navi_index < navi_count - 1 else False
    pilot_prev = True if pilot_index < pilot_count - 1 else False
    pilot_next = True if pilot_index > 0 else False

    if navi_func == 'navi':
        if navi_way == 'prev':
            navi_index = navi_index - 1
            navi_prev = True if navi_index > 0 else False
            navi_next = True
        # elif navi_way == 'next':
        else:
            navi_index = navi_index + 1
            navi_next = True if navi_index < navi_count - 1 else False
            navi_prev = True

        current_model = 'StockReviewFocus' if site == 'review/focus/view' else 'StockReviewTrans'
        current_flow = navi_list[navi_index].flow
        current_code = navi_list[navi_index].code
        current_market = navi_list[navi_index].market
        current_name = navi_list[navi_index].name
        pilot_list = review_pilot_list(current_model, current_flow)
        pilot_index = 0
        pilot_count = len(pilot_list)
        pilot_prev = True
        pilot_next = False

    if navi_func == 'pilot':
        if navi_way == 'prev':
            pilot_index = pilot_index + 1
            pilot_prev = True if pilot_index < pilot_count - 1 else False
            pilot_next = True
        # elif navi_way == 'next':
        else:
            pilot_index = pilot_index - 1
            pilot_next = True if pilot_index > 0 else False
            pilot_prev = True

        pilot_list = review['pilot_list']
        # current_code/current_market/current_name 没有变化
        current_flow = pilot_list[pilot_index]['flow']
        current_model = pilot_list[pilot_index]['model']

        pilot_date = pilot_list[pilot_index]['date']
        deadline = base.date_to_timestamp(str(pilot_date))
        # 修改 deadline，用于 chart_data 视图
        get_kline_param(session_key, 'deadline', deadline)

    navi = {
        'navi': True,
        'navi_index': navi_index,
        'navi_count': navi_count,
        'navi_prev': navi_prev,
        'navi_next': navi_next,
        'pilot': True,
        'pilot_index': pilot_index,
        'pilot_count': pilot_count,
        'pilot_prev': pilot_prev,
        'pilot_next': pilot_next
    }
    chart_navi_cache_key = f'chart-navi-{session_key}'
    cache.set(chart_navi_cache_key, navi, base.configs('cache')['day'])

    review.update({
        'pilot_list': pilot_list,
        'navi_index': navi_index,
        'pilot_index': pilot_index,
        'current_model': current_model,
        'current_flow': current_flow,
        'current_code': current_code,
        'current_market': current_market,
        'current_name': current_name
    })
    set_follow_up(session_key, site, current_code, current_market, current_name, review)

    return navi


def review_pilot_list(model, flow: int):
    if model == 'StockReviewFocus':
        flow_pilot_review_inst = StockReviewFocus.objects.filter(flow=flow)
        pilot_list = list(flow_pilot_review_inst.values(
            'flow', 'code', 'name', 'market', 'date',
            model=Value('StockReviewFocus', output_field=CharField())
        ))

        flow_pilot_review_inst = flow_pilot_review_inst.first()
        flow_pilot_focus_list = list(
            flow_pilot_review_inst.Focus.values(
                'flow', 'code', 'name', 'market', 'date',
                model=Value('StockFocusFlow', output_field=CharField())
            ).order_by('-flow').exclude(event='E')
        )

        for each in flow_pilot_focus_list:
            pilot_list.append(each)

    # elif model == 'StockReviewTrans':
    else:
        flow_pilot_review_inst = StockReviewTrans.objects.filter(flow=flow)
        pilot_list = list(flow_pilot_review_inst.values(
            'flow', 'code', 'name', 'market', 'date',
            model=Value('StockReviewTrans', output_field=CharField())
        ))

        flow_pilot_review_inst = flow_pilot_review_inst.first()
        flow_pilot_trans_list = list(
            flow_pilot_review_inst.Trans.values(
                'flow', 'code', 'name', 'market', 'date',
                model=Value('StockTransFlow', output_field=CharField())
            ).order_by('-flow')
        )
        flow_pilot_focus_list = list(
            flow_pilot_review_inst.Focus.values(
                'flow', 'code', 'name', 'market', 'date',
                model=Value('StockFocusFlow', output_field=CharField())
            ).order_by('-flow').exclude(event='E')
        )

        for each in flow_pilot_trans_list:
            pilot_list.append(each)

        for each in flow_pilot_focus_list:
            pilot_list.append(each)

    return pilot_list


# 分时模式下操作按钮的显示状态
def get_trend_action(site: str) -> dict:
    trend_action = {
        'query': {'exit': 'hide', 'edit': 'plus', 'deal': 'hide'},
        'review/focus/view': {'exit': 'hide', 'edit': 'plus', 'deal': 'hide'},
        'review/trans/view': {'exit': 'hide', 'edit': 'plus', 'deal': 'hide'},
        'focus/view': {'exit': 'end', 'edit': 'edit', 'deal': 'deal'},
        'focus/plus': {'exit': 'exit', 'edit': 'hide', 'deal': 'hide'},
        'focus/edit': {'exit': 'hide', 'edit': 'off', 'deal': 'hide'},
        'trans/view': {'exit': 'hide', 'edit': 'divd', 'deal': 'deal'},
        'trans/deal': {'exit': 'hide', 'edit': 'hide', 'deal': 'hide'}
    }

    try:
        return trend_action[site]
    except KeyError:
        return {'exit': 'hide', 'edit': 'hide', 'deal': 'hide'}


# k 线模式下各个参数
def get_kline_param(session_key, param_name: str = None, param_value=None) -> dict:
    kline_config = base.configs('kline')

    kline_param_cache_key = f'kline-param-{session_key}'
    kline_param = cache.get(kline_param_cache_key)

    if not kline_param:
        kline_param = {
            'right': kline_config['right'],
            'period': kline_config['period'],
            'k': kline_config['ema'][kline_config['period']]['k'],
            'd': kline_config['ema'][kline_config['period']]['d'],
            'deadline': -1
        }

    if param_name:
        if param_name == 'right':
            kline_param['right'] = 'adj' if kline_param['right'] == 'div' else 'div'
        else:
            kline_param[param_name] = param_value

    cache.set(kline_param_cache_key, kline_param, base.configs('cache')['day'])
    return kline_param


def get_focus_flow_list():
    # 使用 values()，QuerySet 的每个对象是一个 dict 字典对象，python 中只能通过[]来访问，html 中可以通过点号访问
    # 不用 values()，QuerySet 的每个对象是模型的实例对象。模型实例对象具有与模型字段对应的属性，可以通过点号访问。
    # only() 不会返回字典，而是返回完整的模型对象，但只有特定的字段被实际加载，从而减少内存开销
    flow_list = StockFocusIndex.objects.select_related('Flows').annotate(
        # annotate 方法结合多个 F 表达式，为每个字段创建一个新的字段名
        flow=F('Flows__flow'),
        name=F('Flows__name'),
        date=F('Flows__date'),
        market=F('Flows__market'),
        type=F('Flows__type'),
        priority=F('Flows__priority'),
        price=F('Flows__price'),
        chance=F('Flows__chance'),
        batch=F('Flows__batch'),
        deci=Case(
            When(Flows__type='F', then=3),
            default=2,
            output_field=IntegerField(),
        )
    ).values(
        'flow',
        # code 是 StockFocusIndex 中的字段，不可以重命名，否则会报错冲突
        # 而 StockFocusIndex 中不存在 flow, priority 等字段，因此重命名不会出现错误
        'code',
        'name',
        'date',
        'market',
        'type',
        'priority',
        'price',
        'chance',
        'batch',
        'deci'
    ).filter(priority__gt=0).order_by('priority')

    return flow_list


def update_focus_priority(code: str, priority_new: int, priority_old: int = 999) -> int:
    focus_flow_list, update_lists, priority = handle_focus_priority(priority_new, priority_old)
    update_lists[code] = priority

    # 构建一个 Case 表达式，以便批量更新 priority 字段
    cases = [When(code=code, then=Value(priority)) for code, priority in update_lists.items()]

    # 使用 bulk_update 一次性更新所有对象的 priority 值
    focus_flow_list.update(
        priority=Case(*cases, default=F('priority'), output_field=IntegerField())
    )

    return priority


# 返回的update_lists不包括priority_new所对应的对象
def handle_focus_priority(priority_new: int, priority_old: int = 999):
    update_lists = {}
    breakpoints = 100, 200, 300, 400, 500, 600, 700, 800, 900
    ranges = (0, 100, 200, 300, 400, 500, 600, 700, 800, 900)

    focus_flow_list = StockFocusFlow.objects.filter(priority__gt=0).order_by('priority')

    start_old = ranges[bisect_right(breakpoints, priority_old)]
    end_old = start_old + 100

    if priority_new > 0:
        start_new = ranges[bisect_right(breakpoints, priority_new)]
        end_new = start_new + 100
    else:
        start_new = -100
        end_new = 0

    # 给定的顺序号与原顺序号不在同一个范围
    if start_new != start_old:
        # __range包括边界值
        # 需要先处理原所在范围顺序号
        focus_flow_old_after = focus_flow_list.filter(priority__range=(priority_old + 1, end_old))
        update_lists.update({each.code: each.priority - 1 for each in focus_flow_old_after})

        if priority_new > 0:
            # 再处理给定的顺序号所在范围
            focus_flow_new_after = focus_flow_list.filter(priority__range=(priority_new, end_new))
            if focus_flow_new_after.exists():
                update_lists.update({each.code: each.priority + 1 for each in focus_flow_new_after})
                priority = priority_new
            else:
                focus_flow_new_prev = focus_flow_list.filter(priority__range=(start_new, priority_new - 1))

                if focus_flow_new_prev.exists():
                    priority = focus_flow_new_prev.last().priority + 1
                else:
                    priority = start_new + 1
        else:
            priority = priority_new

    # 给定顺序号仍在原范围内
    else:
        # 前后顺序号没有相等的可能，在上一级调用程序中已经排除这种情况
        if priority_old < priority_new:
            focus_flow_btw_old_new = focus_flow_list.filter(priority__range=(priority_old + 1, priority_new))
            if focus_flow_btw_old_new.exists():
                update_lists.update({each.code: each.priority - 1 for each in focus_flow_btw_old_new})
                priority = focus_flow_btw_old_new.last().priority
            else:
                priority = start_new + 1
        else:
            focus_flow_btw_new_old = focus_flow_list.filter(priority__range=(priority_new, priority_old - 1))
            update_lists.update({each.code: each.priority + 1 for each in focus_flow_btw_new_old})
            priority = priority_new

    return focus_flow_list, update_lists, priority


# hold 代表从筛选出来的股票初始 batch 值为 0
def handle_focus_submit(session_key: str, code: str, name: str, market: str, values: dict, deci, hold: bool = False):
    try:
        priority_new = int(values['priority'])
        try:
            with transaction.atomic():

                if values['kind'] == 'edit':
                    focus_flow_inst = StockFocusIndex.objects.get(code=code).Flows.all().last()
                    priority_old = focus_flow_inst.priority
                    focus_index_inst = focus_flow_inst.index
                    priority = update_focus_priority(code, priority_new, priority_old)

                    if priority_old == 999:
                        run = 'update'
                        if priority_new == 999:
                            batch = focus_flow_inst.batch
                        else:
                            max_batch_focus = StockFocusFlow.objects.aggregate(max_batch=Max('batch'))['max_batch'] or 1
                            max_batch_trans = StockTransFlow.objects.aggregate(max_batch=Max('batch'))['max_batch'] or 1
                            batch = max(max_batch_focus + 1, max_batch_trans + 1)
                        event = 'F'
                    else:
                        run = 'create'
                        batch = focus_flow_inst.batch
                        focus_flow_inst.priority = -priority_old
                        focus_flow_inst.save()
                        event = 'U'
                # elif values['kind'] == 'plus':
                else:
                    run = 'create'
                    focus_index_inst = StockFocusIndex.objects.create(code=code)
                    fund_flow_inst = StockFundList.objects.filter(code=code).first()
                    if fund_flow_inst:
                        fund_flow_inst.mark = 1
                        fund_flow_inst.save()

                    else:
                        filter_flow_inst = StockFilterList.objects.filter(code=code).first()
                        # 上证指数/深证指数等不在 StockFilterList 中
                        if filter_flow_inst:
                            filter_flow_inst.mark = 1
                            filter_flow_inst.save()

                    if hold:
                        batch = 0
                    else:
                        trans_index_inst = StockTransIndex.objects.filter(code=code).all()
                        # 如何 trans 数据库中存在正在交易的相同股票，则 batch 按 trans 中的
                        if trans_index_inst:
                            trans_flow_inst = trans_index_inst.first().Flows.all().last()
                            batch = trans_flow_inst.batch

                            focus_flow_list = StockFocusFlow.objects.filter(batch=batch)
                            for each in focus_flow_list:
                                each.index = focus_index_inst
                                each.save()
                        else:
                            max_batch_focus = StockFocusFlow.objects.aggregate(max_batch=Max('batch'))['max_batch'] or 1
                            max_batch_trans = StockTransFlow.objects.aggregate(max_batch=Max('batch'))['max_batch'] or 1
                            batch = max(max_batch_focus + 1, max_batch_trans + 1)

                    priority = update_focus_priority(code, priority_new)

                    get_close_price = fetch.get_close_price(f'{market}.{code}', deci)
                    # 执行 set_follow_up 时，已经核查过存在 code 了，因此 get_close_price 一定可以返回值
                    if get_close_price:
                        # 不使用 set_follow_up 的 name 值，是希望 name 为最新名称
                        name = get_close_price['name']
                    else:
                        # 若 get_close_price 为空，说明外部服务器错误
                        raise Http404

                    event = 'F'

                intent = values.get('intent')
                qty = values.get('qty') if intent == 'L' else f'-{values.get("qty")}'

                fields_value = {
                    'batch': batch,
                    'index': focus_index_inst,
                    # 必须注明 None，否为为空，admin 页面会出错
                    'focus': None,
                    'trans': None,
                    'market': market,
                    'code': code,
                    'name': name,
                    'under': values.get('under'),
                    'type': values.get('type'),
                    'date': values.get('date'),
                    'event': event,
                    'settle': values.get('settle'),
                    'intent': intent,
                    'priority': priority,
                    'price': values.get('price'),
                    'qty': qty,
                    'target': values.get('target'),
                    'stop': values.get('stop'),
                    'chance': values.get('chance'),
                    'comments': values.get('comments')
                }

                if run == 'create':
                    StockFocusFlow.objects.create(**fields_value)

                    chart_navi_cache_key = f'chart-navi-{session_key}'
                    pilot_list_cache_key = f'pilot-list-{session_key}'
                    cache.delete(chart_navi_cache_key)
                    cache.delete(pilot_list_cache_key)
                # elif run == 'update':
                else:
                    focus_index_inst.Flows.update(**fields_value)

            msg = 'done'
        except DatabaseError as e:
            msg = str(e)
    except ValueError:
        msg = '数据填写错误 ！'

    return {'msg': msg}


def handle_focus_end(session_key: str, func: str, code: str, end_date: str):
    if '.' in code:
        code = code.split('.')[1]
    try:
        focus_index_inst = StockFocusIndex.objects.get(code=code)
        focus_flow_inst = focus_index_inst.Flows.all().last()
        price = focus_flow_inst.price
        target = focus_flow_inst.target

        with transaction.atomic():
            try:
                fund_list_inst = StockFundList.objects.get(code=code)
                fund_list_inst.focus = None
                fund_list_inst.save()
            except StockFundList.DoesNotExist:
                pass

            priority_old = focus_flow_inst.priority
            priority_new = -focus_flow_inst.priority
            update_focus_priority(code, priority_new, priority_old)

            StockFocusFlow.objects.create(
                batch=focus_flow_inst.batch,
                index=focus_index_inst,
                market=focus_flow_inst.market,
                code=code,
                name=focus_flow_inst.name,
                under=focus_flow_inst.under,
                type=focus_flow_inst.type,
                date=end_date,
                event='E'
            )

            focus_flow_list = StockFocusIndex.objects.get(code=code).Flows.all()
            if priority_old != 999:
                if func == 'end':
                    update_field = 'focus'
                    review_flow_inst = StockReviewFocus.objects.create(
                        batch=focus_flow_inst.batch,
                        date=end_date,
                        type=focus_flow_inst.type,
                        market=focus_flow_inst.market,
                        code=code,
                        name=focus_flow_inst.name,
                        price=price,
                        target=target,
                        star=0
                    )
                # elif func == 'deal':
                else:
                    update_field = 'trans'
                    review_flow_inst = StockReviewTrans.objects.filter(batch=focus_flow_inst.batch).first()
                    if not review_flow_inst:
                        review_flow_inst = StockReviewTrans.objects.create(
                            batch=focus_flow_inst.batch,
                            date=end_date,
                            type=focus_flow_inst.type,
                            market=focus_flow_inst.market,
                            code=code,
                            name=focus_flow_inst.name
                        )
                # 使用 update 批量更新 focus_flow_list 中的对象
                focus_flow_list.update(
                    **{update_field: review_flow_inst},
                    index=None
                )
            else:
                focus_flow_list.update(index=None)

            focus_index_inst.delete()

        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)

        data = {'msg': 'done'}
    except DatabaseError as e:
        data = {'msg': str(e)}

    return data


def get_shares_permit(intent: str, price: float, stop: float):
    try:
        cash_flow_list = StockCashFlow.objects.all().last()
        shares_cash = math.floor(float(cash_flow_list.cash) / price / 100) * 100

        gap = max(price - stop if intent == 'L' else stop - price, 0.1)
        shares_permit = math.floor(float(cash_flow_list.permit) / gap / 100) * 100
        permit = min(shares_cash, shares_permit)
    except (TypeError, ZeroDivisionError):
        permit = 0
    return permit


def get_filter_flow_list(filter_type, exclude_st=False):
    filter_list_base = StockFilterList.objects.all().exclude(hide='1')
    # 排除 ST 股
    if exclude_st:
        filter_list_base = filter_list_base.exclude(name__contains="ST")

    if not filter_list_base:
        filter_list_base = filter_init_data('stock')
    else:
        filter_list_base = filter_list_base.filter(base=1)

    if filter_type == 'mark-1st':
        lists = filter_list_base.filter(mark=1).order_by('code')
    elif filter_type == 'mark-2nd':
        lists = filter_list_base.filter(mark=2).order_by('code')
    elif filter_type == 'mark-all':
        lists = filter_list_base.filter(Q(mark=1) | Q(mark=2)).order_by('code')
    # elif filter_type == 'all':
    else:
        lists = filter_list_base.order_by('code')

    return lists


def get_filter_refer_list(filter_set):
    filter_setting = base.configs('filter')
    bases_cat = filter_setting['bases']['cat']
    bases_list_refer = filter_setting['bases'][bases_cat]['refer']
    bases_list_active = filter_setting['bases'][bases_cat]['active']

    if bases_cat == 'stock':
        model = StockFilterList
    elif bases_cat == 'fund':
        model = StockFundList
    else:
        model = StockSectorList

    filter_refer_bases = model.objects.filter(bases__regex=r'\b{}\b'.format(str(bases_list_refer)))
    filter_active_bases = model.objects.filter(bases__regex=r'\b{}\b'.format(str(bases_list_active)))

    # 获取 filter_refer_bases 和 filter_active_bases 的 code 字段集合
    refer_codes = set(filter_refer_bases.values_list('code', flat=True))
    active_codes = set(filter_active_bases.values_list('code', flat=True))

    if filter_set == 'all':
        # 在 filter_active_bases 中找出 code 不在 refer_codes 中的行，set 字段为 'gt'
        active_bases_with_gt = filter_active_bases.exclude(code__in=refer_codes).annotate(
            set=Value('gt', output_field=CharField())
        )

        # 在 filter_refer_bases 中找出 code 不在 active_codes 中的行，set字段为 'lt'
        refer_bases_with_lt = filter_refer_bases.exclude(code__in=active_codes).annotate(
            set=Value('lt', output_field=CharField())
        )

        # 在两个 QuerySet 的交集中，set 字段为空
        intersect_bases = filter_refer_bases.filter(code__in=active_codes).annotate(
            set=Value('', output_field=CharField())
        )

        # 合并三个 QuerySet，并清除重复项
        filter_refer_list = active_bases_with_gt.union(refer_bases_with_lt, intersect_bases).order_by('code')

    elif filter_set == 'gt':
        filter_refer_list = filter_active_bases.exclude(code__in=refer_codes).annotate(
            set=Value('gt', output_field=CharField())
        )

    elif filter_set == 'lt':
        filter_refer_list = filter_refer_bases.exclude(code__in=active_codes).annotate(
            set=Value('lt', output_field=CharField())
        )

    # elif filter_set == 'eq':
    else:
        filter_refer_list = filter_refer_bases.filter(code__in=active_codes).annotate(
            set=Value('', output_field=CharField())
        )

    return filter_refer_list


def filter_init_data(cat):
    if cat == 'stock':
        new_list_data = fetch.Stock.list()
        model = StockFilterList
    elif cat == 'fund':
        new_list_data = []

        new_data_etf = fetch.Fund.list('ETF')
        for each in new_data_etf:
            each.update({'type': 'ETF'})
        new_list_data.extend(new_data_etf)

        new_data_lof = fetch.Fund.list('LOF')
        for each in new_data_lof:
            each.update({'type': 'LOF'})
        new_list_data.extend(new_data_lof)

        new_data_cbf = fetch.Fund.list('CBF')
        for each in new_data_cbf:
            each.update({'type': 'CBF'})
        new_list_data.extend(new_data_cbf)

        model = StockFundList
    # elif cat == 'sector':
    else:
        new_list_data = fetch.Sector.list()
        model = StockSectorList

    with transaction.atomic():
        # 批量插入数据 #
        # 获取数据库中已存在的 code 值
        exist_codes = model.objects.values_list('code', flat=True)
        new_code_list = [item['f12'] for item in new_list_data]
        # 得出数据库中不存在的 code 值对应的数据
        insert_list = [item for item in new_list_data if item['f12'] not in exist_codes]

        data_to_insert = []
        for each in insert_list:
            code = each['f12']
            name = each['f14']
            market = each['f13']

            try:
                # StockFilterList，StockFundList，StockSectorList 中仅 StockFundList 存在 type 字段
                fund_type = each['type']
                if fund_type == 'CBF':
                    stock = each['f232']
                    data_to_insert.append({
                        'code': code, 'name': name, 'market': market,
                        'type': fund_type, 'stock': stock, 'bases': '0', 'base': 1
                    })
                # elif fund_type == 'ETF' or fund_type == 'LOF':
                else:
                    data_to_insert.append({
                        'code': code, 'name': name, 'market': market,
                        'type': fund_type, 'bases': '0', 'base': 1
                    })
            except KeyError:
                data_to_insert.append({'code': code, 'name': name, 'market': market, 'bases': '0', 'base': 1})

        # 批量插入数据
        model.objects.bulk_create([model(**item) for item in data_to_insert])

        # 批量更新数据 #
        # 获取已存在数据的字典形式
        # exist_data_dict = {obj.code: obj for obj in
        #                       StockFilterList.objects.filter(code__in=[item['code'] for item in insert_list])}
        # 构造要更新的对象列表
        # objects_to_update = [StockFilterList(code=item['code'], name=item['name'], market=item['market'],
        #                                      bases=item['bases'], base=item['base'])
        #                      for item in insert_list if item['code'] in exist_data_dict]
        # 批量更新已存在的数据，code 为主键，不能进行更新
        # StockFilterList.objects.bulk_update(objects_to_update, ['name', 'market', 'bases', 'base'])

        # 批量删除数据 #
        # 获取数据库中存在，但在 insert_list 中不存在的数据
        codes_to_delete = model.objects.exclude(
            code__in=new_code_list
        ).values_list('code', flat=True)
        # 删除不在 insert_list 中的数据
        model.objects.filter(code__in=codes_to_delete).delete()

    init_date = date.today().strftime("%Y-%m-%d")
    filter_setting = base.configs('filter')

    # 此条件代表股价大于 0，也就是所有股票
    init_criteria = [{
        "index": 0, "cat": "P", "right": "adj",
        "k1": "", "d1": "",
        "adjust": "1", "gap": "0",
        "exist": "1", "range": "1", "period": "day",
        "link": "S",
        "filter": "P",
        "set": "0",
        "k2": "", "d2": "", "curve": ""
    }]

    # 默认筛选参数
    init_default = {
        "cat": "E", "right": "adj",
        "k1": "10", "d1": "30",
        "adjust": "1", "gap": "0",
        "exist": "1", "range": "1", "period": "day",
        "link": "S",
        "filter": "U",
        "set": "10",
        "k2": "10", "d2": "30", "curve": "AV"
    }

    filter_base_list = model.objects.filter(base=1)
    init_qty = filter_base_list.count()

    if filter_setting:
        try:
            filter_setting['bases'][cat]['list'][0]['qty'] = init_qty
            filter_setting['bases'][cat]['list'][0]['range'] = filter_bases_ranges(cat)
        except KeyError:
            filter_setting['bases'].update({
                cat: {
                    'count': 1,
                    'active': 0,
                    'refer': 0,
                    'list': [{
                        'index': 0,
                        'date': init_date,
                        'qty': init_qty,
                        # 本次筛选时对应的股票号段
                        'range': filter_bases_ranges(cat),
                        # 本次筛选时的筛选条件
                        "criteria": init_criteria
                    }]
                }
            })

    else:
        init_base_start_day = (date.today() - relativedelta(months=12)).strftime("%Y%m%d")
        init_base_start_week = (date.today() - relativedelta(months=24)).strftime("%Y%m%d")
        init_base_start_month = (date.today() - relativedelta(months=36)).strftime("%Y%m%d")

        filter_setting = {
            # 0 - 当前未进行筛选操作； 1 - 正在筛选；2 - 强制筛选
            'running': 0,
            # 在设定中的显示数量，筛选条件与选股集合均使用同一个设置
            'display': 5,
            # kline 筛选起始日期
            'start': {'day': init_base_start_day, 'week': init_base_start_week, 'month': init_base_start_month},
            # 筛选条件
            'filters': {
                # 筛选条件总数量
                'count': 1,
                # 当前 list 中对应的筛选条件
                'active': 0,
                # 默认筛选条件参数
                'default': init_default,
                # 所有使用过的筛选条件
                'list': [{
                    'index': 0,
                    'date': init_date,
                    "criteria": init_criteria
                }]
            },
            # 选股集合
            'bases': {
                'cat': cat,
                cat: {
                    # 总筛选次数
                    'count': 1,
                    # 当前 list 中对应的选股集合
                    'active': 0,
                    # 当前 list 中对应的对比参照集合
                    'refer': 0,
                    # 所有已筛选过的股票集合
                    'list': [{
                        'index': 0,
                        'date': init_date,
                        'qty': init_qty,
                        # 本次筛选时对应的股票号段
                        'range': filter_bases_ranges(cat),
                        # 本次筛选时的筛选条件
                        "criteria": init_criteria
                    }]
                }
            }
        }

    base.save_setting('filter', filter_setting)

    return filter_base_list


def filter_bases_ranges(cat):
    ranges = []
    if cat == 'stock':
        model = StockFilterList
    elif cat == 'fund':
        model = StockFundList
    # elif cat == 'sector':
    else:
        model = StockSectorList

    filter_setting = base.configs('filter')
    try:
        bases_list_active = filter_setting['bases'][cat]['active']
    except (KeyError, TypeError):
        bases_list_active = 0

    # 提取数据库中被选中的 code 列表，并去重
    prefix_list_selected = list(model.objects.filter(base=1).annotate(
        # 1, 2分别代表 code 字段从第1字符到第2字符的字符串
        prefix=models.functions.Substr('code', 1, 2)).values_list('prefix', flat=True).distinct())

    # 提取数据库中 code 字段前两位字符，并去重
    prefix_list_all = list(model.objects.filter(bases__regex=r'\b{}\b'.format(str(bases_list_active))).annotate(
        # 1, 2分别代表 code 字段从第1字符到第2字符的字符串
        prefix=models.functions.Substr('code', 1, 2)).values_list('prefix', flat=True).distinct())
    for index, each in enumerate(prefix_list_all):
        # 1 代表该前缀将包括在选股集合中， 0 代表不包括
        selected = 1 if each in prefix_list_selected else 0
        ranges.append({'index': index, 'value': each, 'select': selected})

    # 按照 value 键对列表进行排序
    ranges = sorted(ranges, key=lambda x: x['value'])
    # 按排序顺序更新 index 键的值
    for i, item in enumerate(ranges):
        item['index'] = i

    return ranges


def filter_criteria_display(lists):
    # cat: 收盘价[P]/成交量[V]/EMA[E]/MA[M]
    # right: 复权[adj]/除权[div]
    # k1/d1: EMA的 k/d 值（仅当 cat == E 或 M 时存在）
    # adjust/gap: 偏差 ＋[1]/－[-1]，及偏差百分比值（仅当 cat == P 或 V 时存在）
    # exist/range: 连续/存在周期范围，例： 5/10 代表 10 个周期内存在 5 个周期符合条件；10/10 代表连续 10 填符合条件
    # period: 周期 day/week/month
    # link: >[S]/<[L](当 cat == E/M 时，S 代表加速(Speedup)，L 代表趋势(Line))；
    # 加速[S]/趋势[L]/波动[B](当 cat == P/V 时，S 代表大于(Surpass)，L 代表小于(Less)，B 代表波动(Box))
    # filter: 当 cat == P/V 时：收盘价[P]/振幅[A]/EMA[E]/MA[M](针对收盘价)；振幅[A]/MA[M](针对成交量)
    # 当 cat == E/M 时：向上[U]/向下[D]
    # set: 针对收盘价：设定价格；针对振幅：设定振幅百分比值（当 cat == P 或 V 时，或者 cat == B 时）
    # k/d: 针对EMA/MA的 k/d 值（仅当 cat == P 或 V 时存在）
    # curve: 针对EMA：TP/UP/AV/LW/FL（仅当 cat == P 或 V 时存在）

    contents = []

    for each in lists:
        if each['cat'] == 'P':
            content = '收盘价'
        elif each['cat'] == 'V':
            content = '成交量'
        elif each['cat'] == 'E':
            content = 'EMA'
        # elif each['cat'] == 'M':
        else:
            content = 'MA'

        if each['right'] == 'adj':
            content += '[复权,'
        else:
            content += '[除权,'

        if each['cat'] == 'P' or each['cat'] == 'V':
            if each['adjust'] == '1':
                content += f'+{each["gap"]}%]'
            else:
                content += f'−{each["gap"]}%]'

            content += f'在{each["exist"]}/{each["range"]}'

            if each['period'] == 'day':
                content += '日'
            elif each['period'] == 'week':
                content += '周'
            else:
                content += '月'

            if each['link'] == 'S':
                content += '<span class="color-orange">></span>'
            # elif each['link'] == 'L':
            else:
                content += '<span class="color-orange"><</span>'

            if each['filter'] == 'E':
                content += f'EMA[k{each["k2"]},d{each["d2"]},{each["curve"]}]'
            elif each['filter'] == 'M':
                content += f'MA[d{each["d2"]}]'
            elif each['filter'] == 'P':
                content += f'价格{each["set"]}'
            else:
                content += f'振幅{each["set"]}%'

        # elif each['cat'] == 'E' or each['cat'] == 'M':
        else:
            if each['cat'] == 'E':
                content += f'k{each["k1"]},'

            content += f'd{each["d1"]}]'
            content += f'在{each["exist"]}/{each["range"]}'

            if each['period'] == 'day':
                content += '日'
            elif each['period'] == 'week':
                content += '周'
            else:
                content += '月'

            if each['link'] == 'S' or each['link'] == 'L':
                content += '<span class="color-orange">' + '加速' if each['link'] == 'S' else '趋势'
                content += '向上' if each['filter'] == 'U' else '向下' + '</span>'
            # elif each['link'] == 'B'
            else:
                content += '<span class="color-orange">波动'
                content += f'{each["set"]}%</span>'

        contents.append(content)

    return contents


def filter_config_active(kind, index):
    filter_dict = {'base': 'bases', 'mark': 'marks'}
    field_name = filter_dict[kind]

    filter_setting = base.configs('filter')
    bases_cat = filter_setting['bases']['cat']
    base_list_range = filter_setting['bases'][bases_cat]['list'][index]['range']

    if bases_cat == 'stock':
        model = StockFilterList
    elif bases_cat == 'fund':
        model = StockFundList
    else:
        model = StockSectorList

    if kind == 'base':
        model.objects.update(
            **{kind: Case(
                When(Q(**{f'{field_name}__regex': r'\b{}\b'.format(str(index))}), then=Value(1)),
                default=Value(None),
                output_field=IntegerField(),
            )}
        )
    else:
        model.objects.update(
            **{kind: Case(
                When(Q(**{f'{field_name}__regex': r'\b{}\b'.format(f'{str(index)}.1')}), then=Value(1)),
                When(Q(**{f'{field_name}__regex': r'\b{}\b'.format(f'{str(index)}.2')}), then=Value(2)),
                default=Value(None),
                output_field=IntegerField(),
            )}
        )

    for each in base_list_range:
        if each['select'] == 0:
            # 构建查询参数字典，将 base 设置为新值
            filter_params = {'code__startswith': each['value']}
            update_params = {kind: None}
            model.objects.filter(**filter_params).update(**update_params)


def filter_bases_delete(filter_setting, bases_cat, list_active):
    count = filter_setting['bases'][bases_cat]['count']
    lists = filter_setting['bases'][bases_cat]['list']

    for i in range(list_active + 1, count):
        # i 不会为 0，在模板中以及上面条件中已经进行排除了
        lists[i]['index'] = i - 1

    del lists[list_active]
    count -= 1

    filter_setting['bases'][bases_cat]['count'] = count
    filter_setting['bases'][bases_cat]['active'] = count - 1

    if filter_setting['bases'][bases_cat]['refer'] == count:
        filter_setting['bases'][bases_cat]['refer'] = 0

    if bases_cat == 'stock':
        model = StockFilterList
    elif bases_cat == 'fund':
        model = StockFundList
    # elif bases_cat == 'sector':
    else:
        model = StockSectorList

    filter_list_obj = model.objects.filter(
        bases__regex=r'\b{}\b'.format(str(list_active))
    )

    def process_bases_list(handle_list):
        # 查找包含 list_active 的位置
        remove_index = next((index for index, num in enumerate(handle_list) if num == list_active), -1)
        # 移除 list_active，并将 list_active 后面的数字减 1
        if remove_index != -1:
            handle_list = [x - 1 if index > remove_index else x
                           for index, x in enumerate(handle_list) if x != list_active]
        setattr(each, 'bases', ','.join(map(str, handle_list)) if handle_list else None)

    def process_marks_list(handle_list):
        remove_index = next((index for index, num in enumerate(handle_list)
                             if num == f'{list_active}.1' or num == f'{list_active}.2'), -1)
        if remove_index != -1:
            new_list = []
            for index, x in enumerate(handle_list):
                index_part, mark_part = x.split('.')
                index_part = int(index_part)
                if index_part != list_active:
                    new_marks = f'{index_part - 1}.{mark_part}' if index > remove_index else x
                    new_list.append(new_marks)
            handle_list = new_list
        setattr(each, 'marks', ','.join(map(str, handle_list)) if handle_list else None)

    for each in filter_list_obj:
        bases_list = [int(x) for x in each.bases.split(',')] if each.bases else []
        process_bases_list(bases_list)
        marks_list = [x for x in each.marks.split(',')] if each.marks else []
        process_marks_list(marks_list)

    model.objects.bulk_update(filter_list_obj, ['bases', 'marks', 'base', 'mark'])

    filter_config_active('base', count - 1)
    filter_config_active('mark', count - 1)

    filter_setting['running'] = 0
    base.save_setting('filter', filter_setting)


def async_filter_run(session_key):
    filter_criteria_cache_key = f'filter-criteria-{session_key}'
    criteria = cache.get(filter_criteria_cache_key)

    grouped_criteria = {}
    for each in criteria:
        period = each['period']
        right = each['right']
        key = f'{period}-{right}'
        if key not in grouped_criteria:
            grouped_criteria[key] = [each]
        else:
            grouped_criteria[key].append(each)

    filter_setting = base.configs('filter')
    bases_cat = filter_setting['bases']['cat']

    if bases_cat == 'stock':
        model = StockFilterList
        deci = 2
    elif bases_cat == 'fund':
        model = StockFundList
        deci = 3
    else:
        model = StockSectorList
        deci = 2

    bases_list_obj = model.objects.filter(base=1)
    bases_code_list = [[item.market, item.code] for item in bases_list_obj]
    bases_code_count = len(bases_code_list)
    # 将新的筛选作为当前选股集合
    bases_list_obj.update(base=None, mark=None)

    kline_date_start = filter_setting['start']
    filter_setting['bases'][bases_cat]['count'] += 1
    filter_bases_active = filter_setting['bases'][bases_cat]['count'] - 1
    filter_setting['bases'][bases_cat]['active'] = filter_bases_active

    filter_setting['bases'][bases_cat]['list'].append({
        'index': filter_bases_active,
        'date': date.today().strftime("%Y-%m-%d"),
        # qty, range 需要筛选完成时更新
        'qty': 0,
        'range': [],
        "criteria": criteria
    })
    base.save_setting('filter', filter_setting)

    run_break = False
    code_eligible = []

    for index, market_and_code in enumerate(bases_code_list):
        # 说明已经强制终止筛选了
        if run_break:
            break

        percent = f'{round(index / bases_code_count * 100)}%'
        filter_percent_cache_key = f'filter-percent-{session_key}'
        cache.set(filter_percent_cache_key, percent, base.configs('cache')['day'])

        to_add = True

        for key, group in grouped_criteria.items():
            if run_break:
                break

            filter_period, filter_right = key.split('-')
            kline_fetch = fetch.Kline.get_kline(
                '.'.join(market_and_code), filter_right, filter_period, kline_date_start[filter_period]
            )

            if kline_fetch:
                kline_fetch = kline_fetch['klines']
            else:
                to_add = False
                break

            for each in group:
                if base.configs('filter')['running'] == 0:
                    run_break = True
                    break
                filter_cat = each.get('cat')
                filter_k1 = each.get('k1')
                filter_d1 = each.get('d1')
                filter_adjust = int(each['adjust']) if each.get('adjust') else ''
                filter_gap = float(each['gap']) if each.get('gap') else ''
                filter_exist = int(each['exist'])
                filter_range = int(each['range'])
                filter_link = each['link']
                filter_type = each.get('filter')
                filter_set = each.get('set')
                filter_k2 = each.get('k2')
                filter_d2 = each.get('d2')
                filter_curve = each.get('curve')

                kline = kline_fetch[max(0, len(kline_fetch) - filter_range):]

                if filter_cat == 'E' or filter_cat == 'M':
                    ohlc, volume = fetch.Kline.sort_kline(kline_fetch)
                    if not ohlc:
                        to_add = False
                        break

                    if filter_link == 'B':
                        data = filter_em_list(
                            'P', filter_cat, ohlc, volume, filter_k1, filter_d1,
                            filter_range, 'AV', deci
                        )

                        if len(data) <= 1:
                            to_add = False
                        else:
                            max_value = max(data)
                            min_value = min(data)
                            diff_value = round(max_value - min_value, deci)
                            amplitude_eligible = round(diff_value / min_value * 100, 2)
                            if amplitude_eligible > float(filter_set):
                                to_add = False

                    # filter_link == 'L' or filter_link == 'S':
                    else:
                        if filter_link == 'L':
                            data = filter_em_list(
                                'P', filter_cat, ohlc, volume, filter_k1, filter_d1,
                                filter_range + 1, 'AV', deci
                            )
                        # elif filter_link == 'S':
                        else:
                            data = filter_em_list(
                                'P', filter_cat, ohlc, volume, filter_k1, filter_d1,
                                filter_range + 2, 'AV', deci
                            )
                            data = [round(data[i + 1] - data[i], deci) for i in range(len(data) - 1)]

                        if data:
                            data_left = data.copy()
                            data_right = data.copy()
                            data_left.pop()
                            data_right.pop(0)
                            # 使用 zip 将两个列表的对应元素配对
                            paired_elements = zip(data_left, data_right)
                            # 计算第一个列表元素大于第二个列表元素的数量
                            if filter_type == 'U':
                                count_eligible = sum(1 for x, y in paired_elements if y > x)
                            # elif filter_type == 'D':
                            else:
                                count_eligible = sum(1 for x, y in paired_elements if y < x)

                            if count_eligible < filter_exist:
                                to_add = False
                        else:
                            to_add = False

                    if not to_add:
                        break
                else:
                    if filter_cat == 'P':
                        if filter_type == 'A':
                            data_left = []
                            for element in kline:
                                price_list = element.split(',')
                                data_left.extend([float(price_list[3]), float(price_list[4])])
                        else:
                            data_left = [float(element.split(',')[2]) for element in kline]
                    else:
                        data_left = [int(element.split(',')[5]) for element in kline]

                    if filter_type != 'A':
                        # 条件为振幅时，不需要 * gap
                        gap = 1 + filter_adjust * filter_gap / 100
                        data_left = [element * gap for element in data_left]

                    if filter_type == 'P':
                        if filter_link == 'S':
                            # 得到列表中符合比较关系的元素数量
                            count_eligible = sum(1 for element in data_left if element > float(filter_set))
                        else:
                            count_eligible = sum(1 for element in data_left if element < float(filter_set))

                        if count_eligible < filter_exist:
                            to_add = False
                            break

                    elif filter_type == 'A':
                        # 条件为振幅时，忽略 gap，exist，range的数据
                        max_value = max(data_left)
                        min_value = min(data_left)
                        diff_value = max_value - min_value
                        if filter_link == 'S':
                            amplitude_eligible = diff_value / min_value * 100
                            if amplitude_eligible < float(filter_set):
                                to_add = False
                                break
                        else:
                            amplitude_eligible = diff_value / max_value * 100
                            if amplitude_eligible > float(filter_set):
                                to_add = False
                                break

                    else:
                        ohlc, volume = fetch.Kline.sort_kline(kline_fetch)
                        if not ohlc:
                            to_add = False
                            break

                        data_right = filter_em_list(
                            filter_cat, filter_type, ohlc, volume, filter_k2, filter_d2,
                            filter_range, filter_curve, deci
                        )

                        if len(data_left) == len(data_right):
                            # 使用 zip 将两个列表的对应元素配对
                            paired_elements = zip(data_left, data_right)
                            # 计算第一个列表元素大于第二个列表元素的数量
                            if filter_link == 'S':
                                count_eligible = sum(1 for x, y in paired_elements if x > y)
                            else:
                                count_eligible = sum(1 for x, y in paired_elements if x < y)

                            if count_eligible < filter_exist:
                                to_add = False
                                break
                        else:
                            to_add = False

            if not to_add:
                break

        if to_add:
            code_eligible.append(market_and_code[1])
            if len(code_eligible) > 10:
                filter_bases_new_add(bases_cat, code_eligible, filter_bases_active)
                code_eligible = []

    if run_break:
        filter_bases_delete(filter_setting, bases_cat, filter_bases_active)
    else:
        if code_eligible:
            filter_bases_new_add(bases_cat, code_eligible, filter_bases_active)

        bases_list_obj = model.objects.filter(base=1)
        filter_setting['bases'][bases_cat]['list'][filter_bases_active]['qty'] = bases_list_obj.count()

        filter_setting['bases'][bases_cat]['list'][filter_bases_active]['range'] = filter_bases_ranges(bases_cat)
        filter_setting['running'] = 0
        base.save_setting('filter', filter_setting)


def filter_em_list(em_cat, em_type, ohlc, volume, k, d, ranges, curve, deci):
    if em_type == 'E':
        data = fetch.Kline.calc_ema(
            ohlc,
            int(k),
            int(d),
            deci
        )[curve.lower()]
    # elif em_type == 'M':
    else:
        if em_cat == 'P':
            data = fetch.Kline.calc_ma('price', ohlc, int(d), deci)
        # elif em_cat == 'V':
        else:
            data = fetch.Kline.calc_ma('volume', volume, int(d), 0)
    data = data[max(0, len(data) - ranges):]
    data = [element[1] for element in data if element[1]]
    return data


def filter_bases_new_add(cat: str, lists: list, batch: str):
    if cat == 'stock':
        model = StockFilterList
    elif cat == 'fund':
        model = StockFundList
    # elif cat == 'sector':
    else:
        model = StockSectorList

    filter_list_obj = model.objects.filter(code__in=lists)

    for record in filter_list_obj:
        record.bases += f',{batch}' if record.bases else batch
        record.base = 1

    model.objects.bulk_update(filter_list_obj, fields=['bases', 'base'])


def get_fund_flow_list(fund_type: str, order_type: str):
    fund_flow_list = StockFundList.objects.filter(type=fund_type, base=1).exclude(hide='1')
    filter_running = base.configs('filter')['running']
    # 将查询结果存入缓存,缓存有效期单位为秒
    if not fund_flow_list and filter_running != 1:
        refresh_fund_flow_list(fund_type)
        fund_flow_list = StockFundList.objects.filter(type=fund_type, base=1).exclude(hide='1')

    if order_type == 'mark':
        for each in fund_flow_list:
            each.order = each.mark if each.mark else 3
        # Python 列表层面进行排序需要采用下面方法，直接使用 order_by 方法是无效的
        lists = sorted(fund_flow_list, key=lambda obj: obj.order)

    elif order_type == 'code-asc':
        lists = fund_flow_list.order_by('code')

    elif order_type == 'code-desc':
        lists = fund_flow_list.order_by('-code')

    else:
        new_funds = refresh_fund_flow_list(fund_type)
        if order_type == 'change-asc':
            new_funds_list = {each['f12']: each['f3'] for each in new_funds}
            for index, each in enumerate(fund_flow_list):
                each.order = float(new_funds_list[each.code])
            lists = sorted(fund_flow_list, key=lambda obj: obj.order)

        elif order_type == 'change-desc':
            new_funds_list = {each['f12']: each['f3'] for each in new_funds}
            for index, each in enumerate(fund_flow_list):
                each.order = float(new_funds_list[each.code])
            lists = sorted(fund_flow_list, key=lambda obj: obj.order, reverse=True)

        # 股票市值排序，仅适用于 ETF 和 LOF
        elif order_type == 'cap-asc':
            new_funds_list = {each['f12']: each['f20'] for each in new_funds}
            for index, each in enumerate(fund_flow_list):
                each.order = float(new_funds_list[each.code])
            lists = sorted(fund_flow_list, key=lambda obj: obj.order)

        # elif order_type == 'cap-desc':
        else:
            new_funds_list = {each['f12']: each['f20'] for each in new_funds}
            for index, each in enumerate(fund_flow_list):
                each.order = float(new_funds_list[each.code])
            lists = sorted(fund_flow_list, key=lambda obj: obj.order, reverse=True)

    return lists


def refresh_fund_flow_list(fund_type: str):
    new_list_all = fetch.Fund.list(fund_type)

    with transaction.atomic():
        # 批量插入数据 #
        # 获取数据库中已存在的 code 值
        exist_codes = StockFundList.objects.filter(type=fund_type).values_list('code', flat=True)
        # 过滤出数据库中不存在的 code 值对应的数据
        insert_list = [item for item in new_list_all if item['f12'] not in exist_codes]
        data_to_insert = []
        for each in insert_list:
            code = each['f12']
            name = each['f14']
            market = each['f13']

            if fund_type == 'CBF':
                data_to_insert.append({
                    'code': code, 'name': name, 'market': market, 'type': fund_type,
                    'stock': each['f232'], 'bases': '0', 'base': 1
                })
            else:
                data_to_insert.append({
                    'code': code, 'name': name, 'market': market, 'type': fund_type, 'bases': '0', 'base': 1
                })

        StockFundList.objects.bulk_create([StockFundList(**item) for item in data_to_insert])

        # 批量删除数据 #
        # 获取数据库中存在，但在 insert_list 中不存在的数据
        codes_to_delete = StockFundList.objects.filter(type=fund_type).exclude(
            code__in=[item['f12'] for item in new_list_all]
        ).values_list('code', flat=True)
        # 删除不在 insert_list 中的数据
        StockFundList.objects.filter(code__in=codes_to_delete).delete()

        return new_list_all


def get_sector_flow_list(order_type):
    sector_flow_list = StockSectorList.objects.all().filter(base=1)
    # 将查询结果存入缓存,缓存有效期单位为秒
    if not sector_flow_list:
        refresh_sector_flow_list()
        sector_flow_list = StockSectorList.objects.all().filter(base=1)

    if order_type == 'code-asc':
        lists = sector_flow_list.order_by('code')
    elif order_type == 'code-desc':
        lists = sector_flow_list.order_by('-code')
    elif order_type == 'mark':
        for each in sector_flow_list:
            each.order = each.mark if each.mark else 3
        # Python 列表层面进行排序需要采用下面方法，直接使用 order_by 方法是无效的
        lists = sorted(sector_flow_list, key=lambda obj: obj.order)
    else:
        new_sectors = refresh_sector_flow_list()
        if order_type == 'change-asc':
            new_sectors_list = {each['f12']: each['f3'] for each in new_sectors}
            for index, each in enumerate(sector_flow_list):
                each.order = float(new_sectors_list[each.code])
            lists = sorted(sector_flow_list, key=lambda obj: obj.order)
        elif order_type == 'change-desc':
            new_sectors_list = {each['f12']: each['f3'] for each in new_sectors}
            for index, each in enumerate(sector_flow_list):
                each.order = float(new_sectors_list[each.code])
            lists = sorted(sector_flow_list, key=lambda obj: obj.order, reverse=True)
        elif order_type == 'rise':
            new_sectors_list = {each['f12']: [each['f104'], each['f105']] for each in new_sectors}
            for index, each in enumerate(sector_flow_list):
                rise_qty = float(new_sectors_list[each.code][0])
                fall_qty = float(new_sectors_list[each.code][1])
                each.order = rise_qty / (fall_qty if fall_qty > 0 else 0.01)
            lists = sorted(sector_flow_list, key=lambda obj: obj.order, reverse=True)
        # elif order_type == 'fall':
        else:
            new_sectors_list = {each['f12']: [each['f104'], each['f105']] for each in new_sectors}
            for index, each in enumerate(sector_flow_list):
                fall_qty = float(new_sectors_list[each.code][1])
                rise_qty = float(new_sectors_list[each.code][0])
                each.order = fall_qty / (rise_qty if rise_qty > 0 else 0.01)
            lists = sorted(sector_flow_list, key=lambda obj: obj.order, reverse=True)

    return lists


def refresh_sector_flow_list():
    new_list_all = fetch.Sector.list()

    with transaction.atomic():
        # 批量插入数据 #
        # 获取数据库中已存在的 code 值
        exist_codes = StockSectorList.objects.values_list('code', flat=True)
        # 过滤出数据库中不存在的 code 值对应的数据
        insert_list = [item for item in new_list_all if item['f12'] not in exist_codes]
        data_to_insert = []
        for each in insert_list:
            code = each['f12']
            name = each['f14']
            market = each['f13']
            data_to_insert.append({'code': code, 'name': name, 'market': market, 'bases': '0', 'base': 1})

        StockSectorList.objects.bulk_create([StockSectorList(**item) for item in data_to_insert])

        # 批量删除数据 #
        # 获取数据库中存在，但在 insert_list 中不存在的数据
        codes_to_delete = StockSectorList.objects.exclude(
            code__in=[item['f12'] for item in new_list_all]
        ).values_list('code', flat=True)
        # 删除不在 insert_list 中的数据
        StockSectorList.objects.filter(code__in=codes_to_delete).delete()

        return new_list_all


# filter, fund, sector 公共函数
def set_mark_focus(session_key: str, site: str, code: str, grade: int):
    try:
        StockFocusIndex.objects.get(code=code)
        focus_old = 1
    except StockFocusIndex.DoesNotExist:
        focus_old = -1

    model_mapping = {
        'filter/view': [StockFilterList, 'stock'],
        'filter/refer/view': [StockFilterList, 'stock'],
        'fund/view': [StockFundList, 'fund'],
        'sector/view': [StockSectorList, 'sector']
    }

    flow_inst = model_mapping[site][0].objects.get(code=code)

    if grade == -1:
        flow_inst.hide = '1'
        flow_inst.bases = None
        flow_inst.base = None
        flow_inst.marks = None
        flow_inst.mark = None
        flow_inst.save()

        get_chart_navi(session_key, site, code, 'navi', 'delete')
        follow_up_cache_key = f'follow-up-{session_key}'
        follow_up = cache.get(follow_up_cache_key)
        data = {'delete': True, 'market': follow_up["market"], 'code': follow_up["code"]}
    else:
        mark_old = flow_inst.mark or -1

        if site == 'sector/view':
            focus = -1
            mark = -1 if mark_old == grade else grade
            hide = 0
        elif grade == 0:
            hide = 0
            if focus_old == -1:
                try:
                    try_inst = StockFilterList.objects.get(code=code)
                    stock_under = 'SH' if try_inst.market == '1' else 'SZ'
                    stock_type = 'S'
                    deci = 2
                except StockFilterList.DoesNotExist:
                    try_inst = get_object_or_404(StockFundList, code=code)
                    stock_under = 'SH' if try_inst.market == '1' else 'SZ'
                    stock_type = 'B' if try_inst.type == 'CBF' else 'F'
                    deci = 3

                market = try_inst.market
                name = try_inst.name

                values = {
                    'kind': 'plus',
                    'date': date.today(),
                    'under': stock_under,
                    'type': stock_type,
                    'settle': '1',
                    'intent': 'L',
                    'priority': 999,
                    'price': 0,
                    'qty': 0,
                    'target': 0,
                    'stop': 0,
                    'chance': 0
                }
                handle_focus_submit(session_key, code, name, market, values, deci, True)
                focus = 1
                mark = 1
            else:
                end_date = date.today().strftime("%Y-%m-%d")
                handle_focus_end(session_key, 'end', code, end_date)
                focus = -1
                mark = mark_old
        # elif grade == 1 or grade == 2:
        else:
            hide = 0
            focus = focus_old
            if focus == -1:
                mark = -1 if mark_old == grade else grade
            else:
                mark = 1

        filter_setting = base.configs('filter')
        list_active = filter_setting['bases'][model_mapping[site][1]]['active']
        orig_marks = flow_inst.marks.split(',') if flow_inst.marks else []
        new_marks = []
        found = False

        for x in orig_marks:
            index_part, mark_part = x.split('.')
            index_part = int(index_part)
            if index_part == list_active:
                found = True
                if mark != -1:
                    new_marks.append(f'{list_active}.{mark}')
            else:
                new_marks.append(x)

        if not found:
            new_marks.append(f'{list_active}.{mark}')

            bases_split = flow_inst.bases.split(',')
            if str(list_active) not in bases_split:
                flow_inst.bases = (flow_inst.bases + ',' + str(list_active)) if flow_inst.bases else str(list_active)
            flow_inst.base = 1

        flow_inst.marks = ','.join(map(str, new_marks)) if new_marks else None
        flow_inst.mark = mark if mark != -1 else None
        flow_inst.hide = None
        flow_inst.save()

        data = {'msg': 'done', 'grades': [focus, mark, hide]}

    return data


def get_trans_flow_list():
    flow_list = StockTransIndex.objects.annotate(
        latest_flow_id=Max('Flows__flow')
    ).filter(Flows__flow=F('latest_flow_id')).select_related('Flows').annotate(
        flow=F('Flows__flow'),
        name=F('Flows__name'),
        date=F('Flows__date'),
        market=F('Flows__market'),
        type=F('Flows__type'),
        intent=F('Flows__intent'),
        target=F('Flows__target'),
        stop=F('Flows__stop'),
        batch=F('Flows__batch'),
        deci=Case(
            When(Flows__type='F', then=3),
            default=2,
            output_field=IntegerField(),
        )
    ).values(
        'flow',
        'code',
        'name',
        'date',
        'market',
        'type',
        'intent',
        'target',
        'stop',
        'batch',
        'deci'
    ).order_by('flow')

    return flow_list


def get_deal_chance(price: float, target: float, stop: float):
    if target - stop != 0:
        chance = round((target - price) / (target - stop) * 100)
        # 将 chance 限制在 0 到 99 之间
        chance = max(0, min(99, chance))
    else:
        chance = 99
    return chance


def get_deal_fee(stock_under: str, stock_type: str, intent: str, price: float, qty: float):
    fee_setting = base.configs('fee')[stock_under][stock_type][intent]
    total = abs(price * qty)
    # stamp - 印花税
    stamp = round(total * fee_setting['stamp'] / 100, 2)
    # trans - 过户费
    trans = round(total * fee_setting['trans'] / 100, 2)
    commi_min = fee_setting['commi']['min']
    commi_rate = round(total * fee_setting['commi']['rate'] / 1000, 2)
    # commi - 券商佣金
    commi = max(commi_min, commi_rate)
    fee = round(stamp + trans + commi, 2)
    return fee


def get_deal_risk(price: float, qty: float, stop: float):
    risk = max(math.ceil((price - stop) * qty), 0) if stop != -1 else ''
    return risk


def get_deal_cost(code: str, this_price: float, this_qty: float, this_fee: float):
    amount = this_price * this_qty
    fee = this_fee

    trans_index_inst = StockTransIndex.objects.filter(code=code).first()
    if trans_index_inst:
        trans_flow_list = StockTransIndex.objects.get(code=code).Flows.all()
        position_exist = float(trans_flow_list.last().position) if trans_flow_list else 0
        position = this_qty + position_exist
        for each in trans_flow_list:
            amount = amount + float(each.amount) if each.amount else 0
            fee = fee + float(each.fee) if each.fee else 0
    else:
        position = this_qty

    gross = round(amount / position, 6)
    cost = round((amount + fee) / position, 6)

    return cost, gross


def get_deal_profit(code: str, this_amount: float, this_fee: float):
    trans_flow_list = StockTransIndex.objects.get(code=code).Flows.all()
    profit = this_amount + this_fee
    for each in trans_flow_list:
        profit = profit + (float(each.amount) if each.amount else 0)
        profit = profit + (float(each.fee) if each.fee else 0)

    profit = -1 * round(profit, 2)
    return profit


def get_dynamic_profit(code, close):
    trans_flow_inst = StockTransIndex.objects.get(code=code).Flows.all().last()
    profit = float(trans_flow_inst.profit)
    cost = float(trans_flow_inst.cost)
    position = float(trans_flow_inst.position)
    profit = profit + (close - cost) * position
    return profit


# view: kind = 0, intent/calc: kind = 1, submit: kind = 2
def handle_trans_deal(session_key: str, code: str, kind: int = 0, intent: str = None, values: dict = None):
    focus_index_inst = StockFocusIndex.objects.filter(code=code).first()
    trans_index_inst = StockTransIndex.objects.filter(code=code).first()
    intent_reverse = {'L': 'S', 'S': 'L'}

    if not focus_index_inst and not trans_index_inst:
        raise Http404

    if focus_index_inst:
        flow_inst = focus_index_inst.Flows.all().last()
        intent = values.get('intent') if values else (intent if intent else flow_inst.intent)
        intent_keep = flow_inst.intent == intent
        deal_cat = 'plus' if not trans_index_inst else 'deal'
    else:
        flow_inst = trans_index_inst.Flows.filter(Q(event='T') | Q(event='D')).last()
        intent = values.get('intent') if values else (intent if intent else (
            intent_reverse[flow_inst.intent] if kind == 0 else flow_inst.intent))
        intent_keep = flow_inst.intent == intent
        deal_cat = 'deal'

    stock_under = flow_inst.under
    stock_type = flow_inst.type
    settle = flow_inst.settle
    code = flow_inst.code
    name = flow_inst.name
    market = flow_inst.market
    cost_exist = float(getattr(flow_inst, 'cost', 0))
    gross_exist = float(getattr(flow_inst, 'gross', 0))
    position_exist = float(getattr(flow_inst, 'position', 0))
    deci = 2 if stock_type == 'S' else 3

    # risk 需要的是整个 batch 的最后一行数据
    if trans_index_inst:
        flow_inst_for_risk = trans_index_inst.Flows.last()
        risk_exist = float(getattr(flow_inst_for_risk, 'risk', 0))
    else:
        risk_exist = 0

    next_batch = None
    next_event = None
    next_qty = None
    next_position = None
    next_amount = None
    next_cost = None
    next_gross = None
    next_target = None
    next_stop = None
    next_chance = None
    next_risk = None
    next_fee = None
    next_profit = None

    if values:
        deal_date = values.get('date', date.today())
        price = float(values.get('price'))
        qty = float(values.get('qty')) if intent == 'L' else -float(values.get('qty'))
        fee = values.get('fee') if values.get('type') != 'price' and values.get('type') != 'qty' else None
        fee = float(fee) if fee else get_deal_fee(stock_under, stock_type, intent, price, qty)
        target = values.get('target')
        target = float(target) if target else (float(flow_inst.target) if intent_keep else '')
        stop = values.get('stop')
        stop = float(stop) if stop else (float(flow_inst.target) if intent_keep else '')
    else:
        deal_date = date.today()
        price = float(flow_inst.price)
        qty = float(getattr(flow_inst, 'position', flow_inst.qty)) * (1 if intent_keep else -1)
        fee = get_deal_fee(stock_under, stock_type, intent, price, qty)
        target = float(flow_inst.target) if intent_keep else ''
        stop = float(flow_inst.stop) if intent_keep else ''

    position = qty + position_exist
    if position == 0:
        status = 0
        loops = ['this']
        this_batch = flow_inst.batch
        this_event = 'E'
        this_qty = qty
        this_position = 0
        this_amount = round(price * qty, 2)
        this_cost = cost_exist
        this_gross = gross_exist
        this_target = ''
        this_stop = ''
        this_chance = ''
        this_risk = 0
        this_fee = fee
        this_profit = get_deal_profit(code, this_amount, this_fee)
        guide = {
            'cost': this_cost,
            'gross': this_gross,
            'profit': this_profit,
            'target': this_target,
            'stop': this_stop,
            'chance': this_chance,
            'risk': this_risk
        }
    elif position * position_exist >= 0:
        status = 1
        loops = ['this']
        this_batch = flow_inst.batch
        this_event = 'T'
        this_qty = qty
        this_position = position
        this_amount = round(price * qty, 2)
        this_cost, this_gross = get_deal_cost(code, price, qty, fee)
        this_target = target
        this_stop = stop
        this_chance = get_deal_chance(this_gross, this_target, this_stop) if this_target and this_stop else ''
        this_risk = get_deal_risk(this_gross, this_position, this_stop) if this_stop else ''
        this_fee = fee
        this_profit = 0
        guide = {
            'cost': this_cost,
            'gross': this_gross,
            'profit': this_profit,
            'target': this_target,
            'stop': this_stop,
            'chance': this_chance,
            'risk': this_risk
        }
    else:
        status = -1
        loops = ['this', 'next']
        this_batch = flow_inst.batch
        this_event = 'E'
        this_qty = -position_exist
        this_position = 0
        this_amount = round(price * this_qty, 2)
        this_cost = cost_exist
        this_gross = gross_exist
        this_target = None
        this_stop = None
        this_chance = None
        this_risk = 0
        this_fee = fee
        this_profit = get_deal_profit(code, this_amount, this_fee)

        max_batch_focus = StockFocusFlow.objects.aggregate(max_batch=Max('batch'))['max_batch'] or 1
        max_batch_trans = StockTransFlow.objects.aggregate(max_batch=Max('batch'))['max_batch'] or 1
        next_batch = max(max_batch_focus + 1, max_batch_trans + 1)
        next_event = 'T'
        next_qty = position
        next_position = position
        next_amount = round(price * next_qty, 2)
        next_cost = price
        next_gross = price
        next_target = target
        next_stop = stop
        next_chance = get_deal_chance(next_gross, next_target, next_stop) if target and stop else ''
        next_risk = get_deal_risk(next_gross, next_position, next_stop) if stop else ''
        next_fee = 0
        next_profit = 0
        guide = {
            'cost': next_cost,
            'gross': next_gross,
            'profit': this_profit,
            'target': next_target,
            'stop': next_stop,
            'chance': next_chance,
            'risk': next_risk
        }

    if kind == 0 or kind == 1:
        data = {
            'status': status,
            'cat': deal_cat,
            'code': code,
            'name': name,
            'market': market,
            'under': stock_under,
            'type': stock_type,
            'date': deal_date,
            'settle': flow_inst.settle,
            'intent': intent,
            'price': price,
            'qty': abs(qty),
            'amount': round(abs(price * qty), 2),
            'position': position,
            'fee': this_fee,
            'deci': deci
        }
        data.update(guide)
    # elif kind == 2:
    else:
        ohlc_data = fetch.Kline.value(f'{market}.{code}', 'div', 'day')
        ohlc_date = fetch.get_timestamp(str(deal_date), '%Y-%m-%d')
        index_ohlc = base.first_satisfy_index(ohlc_data, 0, ohlc_date, 'left')

        if index_ohlc != -1:
            msg = None
            adjusted = {'price': price, 'qty': float(values.get('qty')), 'open': ohlc_data[index_ohlc][1]}

            for each in loops:
                try:
                    with transaction.atomic():
                        trans_index_inst = StockTransIndex.objects.filter(code=code).first() or \
                                           StockTransIndex.objects.create(code=code)

                        trans_flow_inst = StockTransFlow.objects.create(
                            batch=this_batch if each == 'this' else next_batch,
                            index=trans_index_inst,
                            deal=None,
                            trans=None,
                            cash=None,
                            market=market,
                            code=code,
                            name=name,
                            under=stock_under,
                            type=stock_type,
                            date=deal_date,
                            event=this_event if each == 'this' else next_event,
                            settle=settle,
                            intent=intent,
                            price=price,
                            qty=this_qty if each == 'this' else next_qty,
                            amount=this_amount if each == 'this' else next_amount,
                            target=this_target if each == 'this' else next_target,
                            stop=this_stop if each == 'this' else next_stop,
                            chance=this_chance if each == 'this' else next_chance,
                            fee=fee if each == 'this' else next_fee,
                            cost=this_cost if each == 'this' else next_cost,
                            gross=this_gross if each == 'this' else next_gross,
                            position=this_position if each == 'this' else next_position,
                            profit=this_profit if each == 'this' else next_profit,
                            risk=this_risk if each == 'this' else next_risk,
                            adjusted=adjusted if each == 'this' else None,
                            comments=values.get('comments') if each == 'this' else None,
                        )

                        if each == 'this':
                            focus_index_inst = StockFocusIndex.objects.filter(code=code).first()
                            if focus_index_inst and focus_index_inst.Flows.all().last().intent == intent:
                                handle_focus_end(session_key, 'deal', code, deal_date)

                            fetch.Deal.save_deal(code)
                            trans_deal_inst = StockTransDeal.objects.filter(code=code).first()
                            # 在 handle_focus_end 时就已经保存 StockReviewTrans
                            trans_review_inst = StockReviewTrans.objects.get(batch=this_batch)
                            trans_flow_inst.deal = trans_deal_inst
                            trans_flow_inst.trans = trans_review_inst

                            if status == 0 or status == -1:
                                # status == -1 时，费用算在前面，也就是后面的成本就等于 price
                                trans_cost = round((this_qty * price + fee) / this_qty, 6)
                                # 注意 intent 为当前交易方向
                                price_gap = trans_cost - cost_exist if intent == 'S' else cost_exist - trans_cost
                                percent = round(price_gap / cost_exist * 100, 2)
                                trans_review_inst.date = deal_date
                                trans_review_inst.cost = cost_exist
                                trans_review_inst.price = trans_cost
                                trans_review_inst.percent = percent
                                trans_review_inst.profit = this_profit
                                trans_review_inst.star = 0
                                trans_review_inst.save()

                        else:
                            trans_review_inst = StockReviewTrans.objects.create(
                                batch=next_batch,
                                date=deal_date,
                                type=stock_type,
                                market=market,
                                code=code,
                                name=name
                            )
                            trans_flow_inst.trans = trans_review_inst

                        cash_flow_inst_last = StockCashFlow.objects.all().last()
                        if each == 'this':
                            each_event = this_event
                            each_profit = this_profit
                            each_qty = this_qty
                            each_fee = this_fee
                            stock_gap = round(this_gross * this_position - gross_exist * position_exist, 2)
                            risk_gap = this_risk - risk_exist
                        else:
                            each_event = next_event
                            each_profit = next_profit
                            each_qty = next_qty
                            each_fee = next_fee
                            stock_gap = round(next_gross * next_position, 2)
                            risk_gap = next_risk

                        total_profit = round(float(cash_flow_inst_last.profit) + each_profit, 2)
                        total_cash = round(float(cash_flow_inst_last.cash) - price * each_qty - each_fee, 2)

                        total_stock = round(float(cash_flow_inst_last.stock) + stock_gap, 2)
                        total = round(total_cash + total_stock, 2)

                        total_permit = float(cash_flow_inst_last.permit)
                        total_risk = float(cash_flow_inst_last.risk) + risk_gap
                        total_remain = total_permit - total_risk

                        cash_flow_inst_new = StockCashFlow.objects.create(
                            date=deal_date,
                            event=each_event,
                            intent=intent,
                            total=total,
                            cash=total_cash,
                            stock=total_stock,
                            profit=total_profit,
                            risk=total_risk,
                            permit=total_permit,
                            remain=total_remain
                        )

                        trans_flow_inst.cash = cash_flow_inst_new
                        trans_flow_inst.save()

                        if status == 0:
                            trans_flow_all = trans_index_inst.Flows.all()
                            for flow in trans_flow_all:
                                flow.index = None
                                flow.save()
                            trans_index_inst.delete()

                except DatabaseError as e:
                    msg = str(e)
                    break
            data = {'msg': msg} if msg else {'msg': 'done', 'status': status}
        else:
            data = {'msg': '日期填写有误 ！'}
    return data


def adj_deal_data(trans_flow_list, market_with_code, deci):
    ohlc = fetch.Kline.value(market_with_code, 'adj', 'day')

    for each in trans_flow_list:
        if each.adjusted:
            stamp_date = fetch.get_timestamp(str(each.date), '%Y-%m-%d')
            index_ohlc = base.first_satisfy_index(ohlc, 0, stamp_date, 'left')
            open_now = float(ohlc[index_ohlc][1])
            adjusted = ast.literal_eval(str(each.adjusted))
            open_prev = float(adjusted['open'])
            price_prev = float(adjusted['price'])

            open_adjusted = open_now
            price_adjusted = round(price_prev + (open_now - open_prev), deci)
            qty_adjusted = round(abs(float(each.amount)) / price_adjusted, 2)
            adjusted = {'price': price_adjusted, 'qty': qty_adjusted, 'open': open_adjusted}
            StockTransFlow.objects.filter(flow=each.flow).update(adjusted=adjusted)


def get_review_flow_list(review_type: str, order_type: str, review_range: int):
    model = StockReviewFocus if review_type == 'focus' else StockReviewTrans
    start_date = date.today() - timedelta(days=review_range)
    # 以免将结束关注但未结束交易的数据筛选过来
    review_flow_list = model.objects.filter(date__gte=start_date).exclude(star=None)

    if order_type == 'date':
        lists = review_flow_list.order_by('-date')
    elif order_type == 'star-asc':
        lists = review_flow_list.order_by('star')
    # elif order_type == 'star-desc':
    else:
        lists = review_flow_list.order_by('-star')
    return lists


def hash_path_index(session_key, path, use):
    if os.path.exists(path):
        # 使用SHA-256哈希函数计算路径的哈希值，取前 7 位
        index = hashlib.sha256(path.encode()).hexdigest()[:7]
        # use == path or use == download
        file_path_index_cache_key = f'file-{use}-{index}-{session_key}'
        cache.set(file_path_index_cache_key, path, base.configs('cache')['day'])
    else:
        index = -1
    return index
