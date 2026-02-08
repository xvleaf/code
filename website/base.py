import json
from datetime import datetime
import simplejson
import numpy as np
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

from django.http import HttpResponseServerError
from django.template import loader
from django.core.cache import cache
from django.db import DatabaseError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from models.models import WebConfigs
from stock import func


# 自定义注销程序
def quit(request):
    # 执行注销逻辑（手动清除用户会话）
    if request.user.is_authenticated:
        logout(request)
    # 注销后返回根目录
    return redirect('/')


# views 直接调用 settings，而不是使用常量的形式，好处是无论 gunicorn 的哪一个进程调用，调取的都是数据库的数据，保证多个进程的数据一致
def configs(item):
    config_list = WebConfigs.objects.all()
    config = config_list.get(item__iexact=item).config
    config = simplejson.loads(config) if config else None
    return config


@login_required
def setting(request):
    session_key = request.session.session_key

    if request.method != 'POST':
        site = 'setting'
        func.set_follow_up(session_key, site)
        context = func.page_display(session_key, site, False)
        data = get_setting()
        context.update({'data': data})

        return render(request, 'config-view.html', context)
    else:
        if request.POST.get('func') == 'get':
            # icp 在 get_icp_info 中
            if request.POST.get('query') == 'size':
                data = {
                    'frame': configs('frame'),
                    'chart': configs('chart'),
                    'quote': configs('quote')
                }
            # elif not request.POST.get('query'):
            else:
                # 设置中的下拉菜单改变，从而区域获取选项下的设定值
                item = request.POST.get('item')
                key = request.POST.get('key')
                values = json.loads(request.POST.get('values'))
                data = get_setting(item, key, values)

        # elif request.POST.get('func') == 'set':
        else:
            item = request.POST.get('item')
            path = json.loads(request.POST.get('path'))
            value = request.POST.get('value')
            if value:
                if ':int' in value:
                    value = int(value.split(':')[0])
                elif ':float' in value:
                    value = float(value.split(':')[0])

                config = configs(item)
                update_config_value(config, path, value)
                data = save_setting(item, config)

                if item == 'kline':
                    kline_param_cache_key = f'kline-param-{session_key}'
                    cache.delete(kline_param_cache_key)
                elif item == 'view':
                    follow_up_cache_key = f'follow-up-{session_key}'
                    follow_up = cache.get(follow_up_cache_key)
                    func.get_chart_view(session_key, follow_up['site'], None, True)
            else:
                data = {'msg': '参数不能为空 ！'}

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


# 由于登录界面没有权限，因此获取 icp 函数不能添加 @login_required
def get_icp_info(request):
    if request.POST.get('query') == 'icp':
        icp_filing = configs('icp')
        data = {
            'name': icp_filing['name'],
            'url': icp_filing['url']
        }
    else:
        data = {}

    return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


def save_setting(item, value):
    try:
        configs_inst = WebConfigs.objects.get(item=item)
        # 使用json.dumps目的是使单引号替换为双引号，否则重新调用时会出现simplejson.errors.JSONDecodeError错误
        configs_inst.config = json.dumps(value)
        configs_inst.save()
        data = {'msg': 'done'}
    except DatabaseError as e:
        data = {'msg': str(e)}
    return data


def get_setting(item: str = None, key: str = None, values: dict = None):
    get_configs = WebConfigs.objects.all().exclude(item='filter')
    data = {}
    select_key = {
        'frame': {'screen': 'norm', 'device': 'mb'},
        'chart': {'screen': 'norm', 'device': 'mb'},
        'quote': {'device': 'mb'},
        'kline': {'ema-period': 'day', 'ma-period': 'day'},
        'fee': {'market': 'SH', 'type': 'S', 'intent': 'L'},
    }

    if item in select_key:
        if item == 'kline':
            select_key[item][key] = values[key]
        else:
            select_key[item] = values

    for each in get_configs:
        config = json.loads(each.config)
        if each.item in select_key and each.item != 'kline':
            path = select_key[each.item].copy()
            nested_keys = list(path.keys())  # 获取嵌套键列表
            nested_values = config  # 初始值为配置文件

            for key in nested_keys:
                nested_values = nested_values.get(path[key], {})  # 逐层获取嵌套值
                path[key] = nested_values  # 更新嵌套字典

            data[each.item] = nested_values
            data[each.item].update(select_key[each.item])
        else:
            if each.item == 'kline':
                ema = config.pop('ema')
                ma = config.pop('ma')
                period_ema = select_key['kline']['ema-period']
                period_ma = select_key['kline']['ma-period']
                config['ema'] = {'k': ema[period_ema]['k'], 'd': ema[period_ema]['d']}
                config['ma'] = {'a': ma[period_ma]['a'], 'v': ma[period_ma]['v']}

            data[each.item] = config

    return data


# 使用递归法更新设定值
def update_config_value(config, path, value):
    if len(path) == 1:
        config[path[0]] = value
    else:
        update_config_value(config[path[0]], path[1:], value)


def find_satisfy_index(lists, field, target):
    if lists:
        # 构建一个映射，以每个元素的 field 值为键，索引为值
        try:
            mapping = {each[field]: i for i, each in enumerate(lists)}
        except TypeError:
            # 当 lists 中的元素为模型时，需要使用如 each.code 的形式
            mapping = {getattr(each, field): i for i, each in enumerate(lists)}
        # 在需要查找索引的时候，使用映射来快速找到，若没有找到，返回设定的默认值
        index = mapping.get(target, -1)
    else:
        index = -1
    return index


def first_satisfy_index(lists: list, field_index: int, target: float, compare: str) -> int:
    # 转换为NumPy数组
    arr = np.array(lists)
    # field_index: 基于零的数组列索引, compare=left: 大于等于，compare=right: 小于等于
    # 返回的是如果 target 插入到数组中，应该被插入的位置
    index = np.searchsorted(arr[:, field_index], target, side=compare)
    count = len(lists)
    # 判断 target 的值是否等于 index 前后的值，返回的应是 target 的位置，而不是插入点的位置
    i = (index - 1) if compare == 'left' else (index + 1)
    if 0 <= i < count and lists[i] == target:
        index = i
    elif index == count:
        # 如果 index 等于数组的长度，代表没有找到 target
        index = -1
    return int(index)


def date_to_timestamp(date: str) -> int:
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    timestamp = int(date_obj.timestamp()) * 1000
    return timestamp


def format_decimal(num: float, deci: int = -1) -> str:
    """
    deci=-1，代表自动，调用时，可不赋值：若 num 小数位数小于2位自动添加0，否则不变，但最多3位小数
    deci>=0，代表 num 保留 deci 位小数
    """
    if isinstance(num, float) or isinstance(num, int):
        if deci == -1:
            gap = abs(num) - round(abs(num), 2)
            num = f"{num:.3f}" if gap > 0 else f"{num:.2f}"
        else:
            num = f"{num:.{deci}f}"
    else:
        num = str(num)
    return num


def page_lost(request, exception):
    return render(request, 'error_page.html', {'msg': '404'}, status=404 if exception else 404)


def page_error(request):
    template = loader.get_template('error_page.html')
    return HttpResponseServerError(template.render({'msg': '500'}, request))
