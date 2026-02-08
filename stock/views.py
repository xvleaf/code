import json
import math
import threading
import os
import shutil
import zipfile
# 检测给定文本的字符编码类型
import chardet
from datetime import date, timedelta, datetime
from itertools import chain

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.core.paginator import Paginator, EmptyPage
from django.db import transaction, DatabaseError

from django.http import JsonResponse, Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.core.cache import cache

from models.models import StockCashFlow
from models.models import StockFilterList
from models.models import StockFocusIndex, StockFocusFlow
from models.models import StockFundList, StockSectorList
from models.models import StockTransIndex, StockTransFlow
from models.models import StockReviewFocus, StockReviewTrans

from stock import fetch
from stock import func
from website import base
from website.settings import BASE_DIR


@login_required
def files_view(request):
    session_key = request.session.session_key
    home_path = os.path.abspath('..').replace('\\', '/')

    if request.method != 'POST':
        if request.GET.get('id'):
            file_path_index_cache_key = f'file-download-{request.GET.get("id")}-{session_key}'
            download_path = cache.get(file_path_index_cache_key).replace('\\', '/')

            if os.path.exists(download_path):
                try:
                    with open(download_path, 'rb') as file:
                        name = download_path.split('/').pop()
                        response = HttpResponse(file.read(), content_type='application/octet-stream')
                        response['Content-Disposition'] = f'attachment; filename="{name}"'
                        return response
                except OSError:
                    raise Http404
            else:
                raise Http404
        else:
            folder_path_cache_key = f'folder-path-{session_key}'
            folder_path = cache.get(folder_path_cache_key, home_path)

            try:
                # 使用os.access检查读权限
                if not os.access(folder_path, os.R_OK):
                    folder_path = home_path
            except OSError:
                folder_path = home_path

            files = os.listdir(folder_path)
            file_info = []
            for file in files:
                full_path = os.path.join(folder_path, file)
                modified_time = datetime.fromtimestamp(os.path.getmtime(full_path))
                file_size = f'{math.ceil(os.path.getsize(full_path) / 1024)} KB'
                file_type = '文件夹' if os.path.isdir(full_path) else '文件'
                file_info.append({'name': file, 'date': modified_time, 'type': file_type, 'size': file_size})
                file_info = sorted(file_info, key=lambda x: (x['type'] == '文件', x['name']))
            context = {'folder': folder_path, 'files': file_info}
            return render(request, 'files-view.html', context)
    else:
        file_folder = request.POST.get('folder')

        if request.POST.get('func') == 'new-file':
            folder_path = request.POST.get('folder')
            folder_name = request.POST.get('name')
            new_file_path = os.path.join(folder_path, folder_name)

            if not os.path.exists(new_file_path):
                try:
                    # 使用 open() 创建空文件
                    with open(new_file_path, 'w') as _:
                        pass  # 空语句，不做任何操作
                    msg = 'done'
                except OSError as e:
                    msg = str(e)
                data = {'msg': msg}
            else:
                data = {'msg': '文件名已存在 ！'}

        elif request.POST.get('func') == 'new-folder':
            folder_path = request.POST.get('folder')
            folder_name = request.POST.get('name')
            new_folder_path = os.path.join(folder_path, folder_name)

            if not os.path.exists(new_folder_path):
                try:
                    # 使用 os.makedirs() 创建文件夹
                    os.makedirs(new_folder_path, exist_ok=False)
                    msg = 'done'
                except (OSError, FileExistsError) as e:
                    msg = f'{str(e)}'
                data = {'msg': msg}
            else:
                data = {'msg': '文件夹已存在 ！'}

        elif request.POST.get('func') == 'rename':
            file_name = request.POST.get('name')
            new_name = request.POST.get('new')
            folder_path = request.POST.get('folder')
            old_file_path = os.path.join(folder_path, file_name)
            new_file_path = os.path.join(folder_path, new_name)

            if old_file_path != new_file_path and os.path.exists(new_file_path):
                msg = f'"{new_name}"文件名已存在 ！'
            elif os.path.exists(old_file_path):
                os.rename(old_file_path, new_file_path)
                msg = 'done'
            else:
                msg = f'"{file_name}"文件不存在 ！'
            data = {'msg': msg}

        elif request.POST.get('func') == 'copy' or request.POST.get('func') == 'cut':
            msg = []
            wrong = False
            target_folder = request.POST.get('target')
            source_folder = request.POST.get('source')
            files_name = json.loads(request.POST.get('files'))

            for name in files_name:
                source_file_path = os.path.join(source_folder, name)
                try:
                    # 使用 shutil.copy() 复制文件，或者 shutil.copytree() 复制文件夹
                    if not os.path.exists(os.path.join(target_folder, name)):
                        if os.path.isfile(source_file_path):
                            shutil.copy(source_file_path, target_folder)
                            if request.POST.get('func') == 'cut':
                                os.remove(source_file_path)
                        elif os.path.isdir(source_file_path):
                            shutil.copytree(source_file_path, os.path.join(target_folder, name))
                            if request.POST.get('func') == 'cut':
                                shutil.rmtree(source_file_path)
                        else:
                            msg.append(name)
                    else:
                        msg.append(name)
                except Exception as e:
                    wrong = True
                    msg.append(str(e))
            if msg:
                msg = msg if wrong else ','.join(msg) + '文件未操作成功 ！'
                data = {'msg': msg}
            else:
                data = {'msg': 'done'}

        elif request.POST.get('func') == 'delete':
            msg = []
            file_names = json.loads(request.POST.get('files'))
            for name in file_names:
                full_path = os.path.join(file_folder, name)
                if os.path.exists(full_path):
                    if os.path.isdir(full_path):
                        # 递归删除文件夹
                        shutil.rmtree(full_path)
                    else:
                        os.remove(full_path)
                else:
                    msg.append(file_names)
            if msg:
                data = {'msg': ','.join(msg) + ' 文件不存在 ！'}
            else:
                data = {'msg': 'done'}

        elif request.POST.get('func') == 'download':
            files_or_dirs_name = json.loads(request.POST.get('files'))

            if len(files_or_dirs_name) == 1 and not os.path.isdir(os.path.join(file_folder, files_or_dirs_name[0])):
                download_file_path = os.path.join(file_folder, files_or_dirs_name[0])
            else:
                download_path = os.path.join(BASE_DIR, 'temp')
                os.makedirs(download_path, exist_ok=True)
                download_file_path = os.path.join(download_path, 'download.zip')

                with zipfile.ZipFile(download_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for name in files_or_dirs_name:
                        full_path = os.path.join(file_folder, name)

                        if os.path.isdir(full_path):
                            for root, dirs, files in os.walk(full_path):
                                for file in files:
                                    file_path = str(os.path.join(root, file))
                                    rel_path = os.path.relpath(file_path, file_folder)
                                    zip_info = zipfile.ZipInfo(rel_path)
                                    zip_info.create_system = 3
                                    zip_info.external_attr = 0o777 << 16  # Set permissions for Unix systems
                                    with open(file_path, 'rb') as file_obj:
                                        zip_file.writestr(zip_info, file_obj.read())
                                for dir_name in dirs:
                                    dir_path = os.path.join(root, dir_name)
                                    rel_path = str(os.path.relpath(dir_path, file_folder))
                                    zip_info = zipfile.ZipInfo(rel_path + '/')
                                    zip_info.external_attr = 0o777 << 16  # Set permissions for Unix systems
                                    zip_file.writestr(zip_info, b'')
                        else:
                            rel_path = os.path.relpath(full_path, file_folder)
                            zip_file.write(full_path, rel_path)

            download_id = func.hash_path_index(session_key, download_file_path, 'download')
            data = {'id': download_id}

        elif request.FILES:
            uploaded_file = request.FILES.get('filepond')
            if uploaded_file:
                file_path = os.path.join(file_folder, uploaded_file.name)
                if not os.path.exists(file_path):
                    chunk_size = 500 * 1024  # 500KB的分块大小
                    with default_storage.open(file_path, 'wb+') as destination:
                        for chunk in uploaded_file.chunks(chunk_size=chunk_size):
                            destination.write(chunk)

                    data = {'msg': 'done', 'path': file_path}
                else:
                    data = {'msg': '文件名已存在', 'name': uploaded_file.name}
            else:
                data = {'msg': '文件不存在'}

        # elif request.POST.get('func') == 'path':
        else:
            action = request.POST.get('action')

            if action == 'home':
                full_path = home_path
            elif action == 'up':
                full_path = os.path.dirname(file_folder)
            elif action == 'refresh':
                full_path = file_folder
            elif action == 'click':
                file_name = request.POST.get('name')
                full_path = os.path.join(file_folder, file_name).replace('\\', '/')
            # elif action == 'set':
            else:
                full_path = os.path.abspath(file_folder).replace('\\', '/')

            if os.path.isdir(full_path):
                folder_path_cache_key = f'folder-path-{session_key}'
                cache.set(folder_path_cache_key, full_path, base.configs('cache')['day'])
                data = {'msg': 'done'}
            elif os.path.isfile(full_path):
                path_index = func.hash_path_index(session_key, full_path, 'path')
                if path_index != -1:
                    data = {'msg': 'isfile', 'index': path_index}
                else:
                    data = {'msg': '文件不存在 ！'}
            else:
                data = {'msg': '文件无法打开 ！'}

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def files_load(request):
    session_key = request.session.session_key

    if request.method != 'POST':
        path_index = request.GET.get('index')
        if path_index:
            file_path_index_cache_key = f'file-path-{path_index}-{session_key}'
            file_path = cache.get(file_path_index_cache_key)

            if os.path.exists(file_path):
                cache.set(file_path_index_cache_key, file_path, base.configs('cache')['day'])
                context = {'index': path_index, 'path': file_path}
                return render(request, 'files-load.html', context)
            else:
                raise Http404
        else:
            raise Http404

    else:
        request_func = request.POST.get('func')
        file_path = request.POST.get('path')

        # files-view 跳转到 files-load 前询问
        if request_func == 'open':
            path_index = func.hash_path_index(session_key, file_path, 'path')
            data = {'index': path_index}
        elif request_func == 'save':
            try:
                content = request.POST.get('content')
                # 检测文件编码
                with open(file_path, 'rb') as file:
                    raw_data = file.read()
                    encoding_info = chardet.detect(raw_data)
                    encoding = encoding_info['encoding']
                with open(file_path, 'w', encoding=encoding) as file:
                    file.write(content)
                data = {'msg': '备份完成 ！'}
            except Exception as e:
                data = {'msg': str(e)}
        # elif request_func == 'load':
        else:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    raw_data = file.read()
                    encoding_info = chardet.detect(raw_data)
                    encoding = encoding_info['encoding']

                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        data = file.read()
                except UnicodeDecodeError:
                    # 处理解码错误，尝试备选编码
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            data = file.read()
                    except UnicodeDecodeError:
                        data = '文件无法解码 !'
            else:
                data = '未找到此文件 ！'

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def overall_view(request):
    site = 'overall/view'
    session_key = request.session.session_key
    func.set_follow_up(session_key, site)

    if request.method != 'POST':
        stats_config = base.configs('stats')
        start_date = date.today() - timedelta(days=stats_config['range'])
        cash_flow_list = StockCashFlow.objects.filter(date__gte=start_date)

        field_names = ['total', 'stock', 'cash', 'profit']
        all_values = list(chain.from_iterable(data for data in cash_flow_list.values_list(*field_names)))
        all_values = [float(value) for value in all_values if value]

        max_value = max(all_values)
        min_value = min(all_values)
        gap = round((max_value - min_value) * 0.1, 0)
        max_value += gap
        min_value -= gap

        ohlc_date = []
        ohlc_total = []
        ohlc_cash = []
        ohlc_stock = []
        ohlc_profit = []
        ohlc_risk = []
        ohlc_tips = []

        for each in cash_flow_list:
            ohlc_date.append(each.date.strftime('%y/%m/%d'))
            ohlc_total.append(float(each.total))
            ohlc_cash.append(float(each.cash))
            ohlc_stock.append(float(each.stock))
            ohlc_profit.append(float(each.profit))
            ohlc_risk.append(float(each.risk))

            final = {
                'date': each.date.strftime('%Y-%m-%d'),
                'total': each.total,
                'cash': each.cash,
                'stock': each.stock,
                'profit': each.profit,
                'permit': each.permit,
                'risk': each.risk
            }

            try:
                trans_data = each.Trans

                code = trans_data.code
                name = trans_data.name
                event = trans_data.get_event_display()
                # 如果 amount 为空，则仅显示 risk
                # 如果 amount 不为空，则显示 intent/amount/profit/fee/risk
                intent = trans_data.get_intent_display()
                amount = abs(float(trans_data.amount)) if trans_data.amount else ''
                fee = trans_data.fee if trans_data.fee else ''
                profit = trans_data.profit if trans_data.profit else ''
                risk = trans_data.risk
                deal = {
                    'code': code,
                    'name': name,
                    'event': event,
                    'intent': intent,
                    'amount': amount,
                    'profit': profit,
                    'fee': fee,
                    'risk': risk
                }

            except ObjectDoesNotExist:
                deal = ''

            tips = {
                'final': final,
                'deal': deal
            }

            ohlc_tips.append(tips)

        # x 轴最多显示 6/5/4 个日期，哪个显示的最对称就选哪个，若都不对称，选最后一个
        shows = [6, 5, 4]
        indexes = []
        length = len(ohlc_date)

        for i, show in enumerate(shows):
            interval = math.ceil(length / show)
            indexes = list(range(0, length, interval))[:show]

            left = (length - indexes[len(indexes) - 1] - 1) // 2
            indexes = [item + left for item in indexes]

            if (length - indexes[len(indexes) - 1] - 1) % 2 == 0:
                break

        ohlc_labels = [ohlc_date[pos] if pos in indexes else '' for pos in range(length)]

        ohlc = {
            'label': ohlc_labels,
            'total': ohlc_total,
            'cash': ohlc_cash,
            'stock': ohlc_stock,
            'profit': ohlc_profit,
            'tips': ohlc_tips,
            'max': max_value,
            'min': min_value
        }

        context = func.page_display(session_key, site, True)
        context.update({'chart': True})
        context.update({'ohlc': json.dumps(ohlc)})
        context.update({'data': cash_flow_list.last()})

        return render(request, 'overall-view.html', context)
    else:
        try:
            request_func = request.POST.get('func')
            value = float(request.POST.get('value'))

            cash_flow_inst_last = StockCashFlow.objects.all().last()

            if request_func == 'cash':
                cash_gap = value - float(cash_flow_inst_last.cash)
                total = round(float(cash_flow_inst_last.total) + cash_gap, 2)
                cash = round(value, 2)
                permit = cash_flow_inst_last.permit
                remain = cash_flow_inst_last.remain

            else:
                permit_gap = value - float(cash_flow_inst_last.permit)
                permit = round(value, 2)
                remain = round(float(cash_flow_inst_last.remain) + permit_gap, 2)
                total = cash_flow_inst_last.total
                cash = cash_flow_inst_last.cash

            StockCashFlow.objects.create(
                date=date.today(),
                event='C',
                intent=None,
                total=total,
                cash=cash,
                stock=cash_flow_inst_last.stock,
                profit=cash_flow_inst_last.profit,
                risk=cash_flow_inst_last.risk,
                permit=permit,
                remain=remain
            )

            data = {'msg': 'done'}
        except ValueError:
            data = {'msg': '数据填写有误 ！'}

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def query_view(request, code):
    site = 'query'
    session_key = request.session.session_key
    follow_up = func.set_follow_up(session_key, site, code)
    if follow_up['code'] == code:
        return HttpResponseRedirect(f'/view/{follow_up["market"]}.{follow_up["code"]}')

    context = func.page_display(session_key, site, True)
    context.update(
        func.chart_display(
            session_key, site, follow_up['cat'],
            follow_up['code'], follow_up['name'], follow_up['market']
        )
    )
    return render(request, 'query-view.html', context)


@login_required
def focus_list(request):
    site = 'focus/list'
    session_key = request.session.session_key
    func.set_follow_up(session_key, site)
    interval = base.configs('refresh')['interval']

    focus_flow_list = func.get_focus_flow_list()
    flow_list_cache_key = f'{site}-flow-list-{session_key}'
    cache.set(flow_list_cache_key, focus_flow_list, base.configs('cache')['day'])

    if request.method != 'POST':
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)

        focus_market_list = focus_flow_list.filter(priority__gt=0, priority__lte=99)
        focus_ready_list = focus_flow_list.filter(priority__gte=100, priority__lte=199)
        focus_expensive_list = focus_flow_list.filter(priority__gte=200, priority__lte=299)
        focus_cheap_list = focus_flow_list.filter(priority__gte=300, priority__lte=399)
        focus_hold_list = focus_flow_list.filter(priority__gte=400, priority__lte=999)

        context = {
            'markets': focus_market_list,
            'ready': focus_ready_list,
            'expensive': focus_expensive_list,
            'cheap': focus_cheap_list,
            'hold': focus_hold_list,
            'interval': interval
        }

        page_display = func.page_display(session_key, site, False, 'norm')
        context.update(page_display)

        return render(request, 'focus-list.html', context)

    else:
        data = fetch.Stock.data(focus_flow_list)
        # 若 data 不是字典，需要设置 safe=False
        # ensure_ascii': False 表示不会将中文转换为 ascii 形式
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def focus_view(request, code):
    site = 'focus/view'
    session_key = request.session.session_key

    if request.method != 'POST':
        follow_up_cache_key = f'follow-up-{session_key}'
        follow_up = cache.get(follow_up_cache_key)
        site_prev = follow_up['site'] if follow_up else None
        site_prev_mapping = ['focus/list', 'focus/view', 'focus/edit', 'focus/plus']
        if site_prev not in site_prev_mapping:
            chart_navi_cache_key = f'chart-navi-{session_key}'
            pilot_list_cache_key = f'pilot-list-{session_key}'
            cache.delete(chart_navi_cache_key)
            cache.delete(pilot_list_cache_key)

        follow_up = func.set_follow_up(session_key, site, code)
        page_display = func.page_display(session_key, site, True)
        chart_display = func.chart_display(
            session_key, site, follow_up['cat'],
            follow_up['code'], follow_up['name'], follow_up['market']
        )
        navi = func.get_chart_navi(session_key, site, code)
        # 执行 get_chart_navi 时只要 code 在数据库中存在，必然会生成 pilot_list
        pilot_list_cache_key = f'pilot-list-{session_key}'
        pilot_list = cache.get(pilot_list_cache_key)
        pilot_index = navi['pilot_index']

        if not pilot_list or pilot_index == -1:
            try:
                focus_flow_inst = StockFocusIndex.objects.get(code=follow_up['code']).Flows.all().last()
            except StockFocusIndex.DoesNotExist:
                raise Http404
        else:
            flow = pilot_list[pilot_index]['flow']
            focus_flow_inst = StockFocusFlow.objects.get(flow=flow)

        priority = focus_flow_inst.priority
        focus_flow_inst.priority = -priority if priority < 0 else priority
        focus_flow_inst.qty = abs(float(focus_flow_inst.qty))
        try:
            shares_permit = func.get_shares_permit(
                focus_flow_inst.intent,
                float(focus_flow_inst.price),
                float(focus_flow_inst.stop)
            )
        except TypeError:
            shares_permit = 0

        context = page_display
        context.update(chart_display)
        context.update(navi)
        context.update({
            'data': focus_flow_inst,
            'permit': shares_permit,
            'deci': 3 if focus_flow_inst.type == 'F' else 2
        })
        return render(request, 'focus-view.html', context)

    else:
        request_func = request.POST.get('func')

        if request_func == 'priority':
            try:
                code = code.split('.')[1]
                # js 中给的 code 为 market_with_code
                priority_old = StockFocusIndex.objects.get(code=code).Flows.all().last().priority
                try:
                    priority_new = int(request.POST.get('value'))
                    priority = func.update_focus_priority(code, priority_new, priority_old)
                    msg = f'关注顺序更新为{priority} ！' if priority_new != priority else '已更新 ！'
                except ValueError:
                    priority = priority_old
                    msg = '数据填写错误 ！'
            except (StockFocusIndex.DoesNotExist, StockFocusFlow.DoesNotExist):
                priority = ''
                msg = '数据库不存在 ！'

            data = {'msg': msg, 'priority': priority}
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})

        # elif request_func == 'comments':
        else:
            try:
                flow = request.POST.get('flow')
                focus_flow_inst = StockFocusFlow.objects.get(flow=flow)
                focus_flow_inst.comments = request.POST.get('value')
                focus_flow_inst.save()
                data = {'msg': '备忘保存完成 ！'}
            except StockFocusFlow.DoesNotExist:
                data = {'msg': '数据库不存在 ！'}
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def focus_edit(request, code):
    site = 'focus/edit'
    session_key = request.session.session_key
    follow_up = func.set_follow_up(session_key, site, code)

    if request.method != 'POST':
        page_display = func.page_display(session_key, site, True)
        chart_display = func.chart_display(
            session_key, site, follow_up['cat'],
            follow_up['code'], follow_up['name'], follow_up['market']
        )

        focus_flow_inst = get_object_or_404(StockFocusIndex, code=follow_up['code']).Flows.all().last()
        focus_flow_inst.date = date.today()
        focus_flow_inst.qty = abs(float(focus_flow_inst.qty))

        try:
            shares_permit = func.get_shares_permit(
                focus_flow_inst.intent,
                float(focus_flow_inst.price),
                float(focus_flow_inst.stop)
            )
        except TypeError:
            shares_permit = 0

        context = page_display
        context.update(chart_display)

        # 不显示导航栏
        # navi = func.get_chart_navi(session_key, site, code)
        # context.update(navi)

        context.update({
            'data': focus_flow_inst,
            'permit': shares_permit,
            'deci': 3 if focus_flow_inst.type == 'F' else 2
        })

        return render(request, 'focus-edit.html', context)

    else:
        request_func = request.POST.get('func')

        if request_func == 'submit':
            values = request.POST
            deci = 3 if follow_up['cat'] == 'fund' else 2
            data = func.handle_focus_submit(
                session_key,
                follow_up['code'],
                follow_up['name'],
                follow_up['market'],
                values,
                deci
            )
            data.update({'code': follow_up['code'], 'market': follow_up['market']})
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})

        elif request_func == 'end':
            end_date = date.today().strftime("%Y-%m-%d")
            data = func.handle_focus_end(session_key, request_func, code, end_date)
            if data['msg'] == 'done':
                chart_navi_cache_key = f'chart-navi-{session_key}'
                pilot_list_cache_key = f'pilot-list-{session_key}'
                cache.delete(chart_navi_cache_key)
                cache.delete(pilot_list_cache_key)
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})

        # elif request_func == 'calc':
        else:
            intent = request.POST.get('intent')
            try:
                price = float(request.POST.get('price'))
                target = float(request.POST.get('target'))
                stop = float(request.POST.get('stop'))
                permit = func.get_shares_permit(intent, float(price), float(stop))
                chance = func.get_deal_chance(float(price), float(target), float(stop))
            except ValueError:
                permit = ''
                chance = ''
            msg = 'done' if permit == 0 or permit else '数据填写有误 ！'
            data = {'msg': msg, 'permit': permit, 'chance': chance}
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def focus_plus(request):
    site = 'focus/plus'
    session_key = request.session.session_key
    code = request.POST.get('code') or request.GET.get('code')
    if code and '.' in code:
        code = code.split('.')[1]
    follow_up = func.set_follow_up(session_key, site, code)

    if request.method != 'POST':
        context = {}
        if code:
            try:
                focus_index_inst = StockFocusIndex.objects.get(code=code)
                return HttpResponseRedirect(f'/focus/view/{focus_index_inst.Flows.all().last().market}.{code}')
            except StockFocusIndex.DoesNotExist:
                page_display = func.page_display(session_key, site, True)
                chart_display = func.chart_display(
                    session_key, site, follow_up['cat'],
                    follow_up['code'], follow_up['name'], follow_up['market']
                )
                context.update(page_display)
                context.update(chart_display)
        else:
            page_display = func.page_display(session_key, site, False)
            context.update(page_display)

        return render(request, 'focus-plus.html', context)

    else:
        # if request.POST.get('func') == 'plus':
        try:
            StockFocusIndex.objects.get(code=code)
            data = {'msg': '数据库中已存在 ！'}
        except StockFocusIndex.DoesNotExist:
            data = {
                'code': follow_up['code'],
                'market': follow_up['market']
            }
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def fund_list(request):
    site = 'fund/list'
    session_key = request.session.session_key
    func.set_follow_up(session_key, site)
    interval = base.configs('refresh')['interval']

    flow_list_cache_key = f'fund/list-flow-list-{session_key}'
    fund_page_list_cache_key = f'fund-page-list-{session_key}'
    fund_type_cache_key = f'fund-type-{session_key}'
    fund_type = cache.get(fund_type_cache_key) or 'ETF'

    if request.method != 'POST':
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)

        page_number = int(request.GET.get('page', 1))

        fund_order_cache_key = f'fund-order-{session_key}'
        order_type = request.GET.get('order') or cache.get(fund_order_cache_key) or 'code-asc'
        cache.set(fund_order_cache_key, order_type, base.configs('cache')['day'])

        paginator_list = func.get_fund_flow_list(fund_type, order_type)
        cache.set(flow_list_cache_key, paginator_list, base.configs('cache')['day'])

        per_page = base.configs('page')['fund']
        paginator = Paginator(paginator_list, per_page)

        try:
            page_list = paginator.page(page_number)
        except EmptyPage:
            # 处理页码超出范围的情况，重定向到最后一页
            page_list = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        cache.set(fund_page_list_cache_key, page_list, base.configs('cache')['day'])
        cache.set(fund_type_cache_key, fund_type, base.configs('cache')['day'])

        context = {
            'lists': page_list,
            'type': fund_type,
            'interval': interval,
            'page_number': page_number,
            'page_total': paginator.num_pages,
            'order_type': order_type
        }

        page_display = func.page_display(session_key, site, False, 'norm')
        context.update(page_display)
        return render(request, 'fund-list.html', context)

    else:
        request_func = request.POST.get('func')
        if request_func == 'update':
            page_list = list(cache.get(fund_page_list_cache_key))
            data = fetch.Fund.data(fund_type, page_list)
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
        elif request_func == 'refresh':
            cache.delete(flow_list_cache_key)
            cache.delete(fund_page_list_cache_key)
            fund_type_name = request.POST.get('type')
            func.refresh_fund_flow_list(fund_type_name)
            return JsonResponse({}, safe=False, json_dumps_params={'ensure_ascii': False})
        # if request_func == 'type':
        else:
            cache.delete(flow_list_cache_key)
            cache.delete(fund_page_list_cache_key)
            cache.set(fund_type_cache_key, request.POST.get('type'), base.configs('cache')['day'])
            return JsonResponse({}, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def fund_view(request, code):
    site = 'fund/view'
    session_key = request.session.session_key

    if request.method != 'POST':
        follow_up_cache_key = f'follow-up-{session_key}'
        follow_up = cache.get(follow_up_cache_key)
        site_prev = follow_up['site'] if follow_up else None
        site_prev_mapping = ['fund/list', 'fund/view']
        if site_prev not in site_prev_mapping:
            chart_navi_cache_key = f'chart-navi-{session_key}'
            pilot_list_cache_key = f'pilot-list-{session_key}'
            cache.delete(chart_navi_cache_key)
            cache.delete(pilot_list_cache_key)

        follow_up = func.set_follow_up(session_key, site, code)
        page_display = func.page_display(session_key, site, True)
        chart_display = func.chart_display(
            session_key, site, follow_up['cat'],
            follow_up['code'], follow_up['name'], follow_up['market']
        )
        navi = func.get_chart_navi(session_key, site, code)

        context = page_display
        context.update(chart_display)
        context.update(navi)

        fund_flow_inst = StockFundList.objects.get(code=follow_up['code'])
        try:
            StockFocusIndex.objects.get(code=follow_up['code'])
            focus = 1
        except StockFocusIndex.DoesNotExist:
            focus = 0

        context.update({
            'data': fund_flow_inst,
            'focus': focus
        })

        return render(request, 'multi-view.html', context)

    else:
        request_func = request.POST.get('func')

        if '.' in code:
            code = code.split('.')[1]

        if request_func == 'comments':
            try:
                fund_flow_inst = StockFundList.objects.get(code=code)
                fund_flow_inst.comments = request.POST.get('value')
                fund_flow_inst.save()
                data = {'msg': '备忘保存完成 ！'}
            except StockFundList.DoesNotExist:
                data = {'msg': '数据库不存在 ！'}

        elif request_func == 'mark':
            grade = int(request.POST.get('grade'))
            data = func.set_mark_focus(session_key, site, code, grade)

        # elif request_func == 'back':
        else:
            flow_list_cache_key = f'fund/list-flow-list-{session_key}'
            paginator_list = cache.get(flow_list_cache_key)

            if paginator_list:
                navi_index = base.find_satisfy_index(paginator_list, 'code', code)
                per_page = base.configs('page')['fund']
                page = math.floor(navi_index / per_page) + 1
                url = 'fund/list' if page == 1 else f'fund/list?page={page}'
                data = {'url': url}
            else:
                data = {'url': 'fund/list'}

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def sector_list(request):
    site = 'sector/list'
    session_key = request.session.session_key
    func.set_follow_up(session_key, site)
    interval = base.configs('refresh')['interval']

    flow_list_cache_key = f'sector/list-flow-list-{session_key}'
    sector_page_list_cache_key = f'sector-page-list-{session_key}'

    if request.method != 'POST':
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)

        page_number = int(request.GET.get('page', 1))

        sector_order_cache_key = f'sector-order-{session_key}'
        order_type = request.GET.get('order') or cache.get(sector_order_cache_key) or 'code-asc'
        cache.set(sector_order_cache_key, order_type, base.configs('cache')['day'])

        paginator_lists = func.get_sector_flow_list(order_type)
        cache.set(flow_list_cache_key, paginator_lists, base.configs('cache')['day'])

        per_page = base.configs('page')['sector']
        paginator = Paginator(paginator_lists, per_page)

        try:
            page_list = paginator.page(page_number)
        except EmptyPage:
            # 处理页码超出范围的情况，重定向到最后一页
            page_list = paginator.page(paginator.num_pages)

        cache.set(sector_page_list_cache_key, page_list, base.configs('cache')['day'])

        context = {
            'lists': page_list,
            'page_number': page_number,
            'page_total': paginator.num_pages,
            'order_type': order_type,
            'interval': interval
        }

        page_display = func.page_display(session_key, site, False, 'norm')
        context.update(page_display)

        return render(request, 'sector-list.html', context)

    else:
        request_func = request.POST.get('func')
        if request_func == 'update':
            page_list = list(cache.get(sector_page_list_cache_key))
            data = fetch.Sector.data(page_list)
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
        # elif request_func == 'refresh':
        else:
            cache.delete(flow_list_cache_key)
            cache.delete(sector_page_list_cache_key)
            func.refresh_sector_flow_list()
            return JsonResponse({}, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def sector_view(request, code):
    site = 'sector/view'
    session_key = request.session.session_key

    if request.method != 'POST':
        follow_up_cache_key = f'follow-up-{session_key}'
        follow_up = cache.get(follow_up_cache_key)
        site_prev = follow_up['site'] if follow_up else None
        site_prev_mapping = ['sector/list', 'sector/view']
        if site_prev not in site_prev_mapping:
            chart_navi_cache_key = f'chart-navi-{session_key}'
            pilot_list_cache_key = f'pilot-list-{session_key}'
            cache.delete(chart_navi_cache_key)
            cache.delete(pilot_list_cache_key)

        follow_up = func.set_follow_up(session_key, site, code)
        page_display = func.page_display(session_key, site, True)
        chart_display = func.chart_display(
            session_key, site, follow_up['cat'],
            follow_up['code'], follow_up['name'], follow_up['market']
        )
        navi = func.get_chart_navi(session_key, site, code)

        context = page_display
        context.update(chart_display)
        context.update(navi)

        sector_flow_inst = StockSectorList.objects.get(code=follow_up['code'])
        context.update({'data': sector_flow_inst})

        return render(request, 'multi-view.html', context)

    else:
        request_func = request.POST.get('func')

        if '.' in code:
            code = code.split('.')[1]

        if request_func == 'comments':
            try:
                sector_flow_inst = StockSectorList.objects.get(code=code)
                sector_flow_inst.comments = request.POST.get('value')
                sector_flow_inst.save()
                data = {'msg': '备忘保存完成 ！'}
            except StockSectorList.DoesNotExist:
                data = {'msg': '数据库不存在 ！'}

        elif request_func == 'mark':
            grade = int(request.POST.get('grade'))
            data = func.set_mark_focus(session_key, site, code, grade)

        # elif request_func == 'back':
        else:
            flow_list_cache_key = f'sector/list-flow-list-{session_key}'
            paginator_list = cache.get(flow_list_cache_key)

            if paginator_list:
                navi_index = base.find_satisfy_index(paginator_list, 'code', code)
                per_page = base.configs('page')['sector']
                page = math.floor(navi_index / per_page) + 1
                url = 'sector/list' if page == 1 else f'sector/list?page={page}'
                data = {'url': url}
            else:
                data = {'url': 'sector/list'}

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def filter_list(request):
    site = 'filter/list'
    session_key = request.session.session_key
    func.set_follow_up(session_key, site)
    interval = base.configs('refresh')['interval']

    flow_list_cache_key = f'filter/list-flow-list-{session_key}'
    filter_page_list_cache_key = f'filter/list-page-list-{session_key}'
    filter_type_cache_key = f'filter-type-{session_key}'

    if request.method != 'POST':
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)

        filter_type = cache.get(filter_type_cache_key) or 'all'
        page_number = int(request.GET.get('page', 1))

        paginator_list = func.get_filter_flow_list(filter_type)
        cache.set(flow_list_cache_key, paginator_list, base.configs('cache')['day'])

        per_page = base.configs('page')['filter']
        paginator = Paginator(paginator_list, per_page)

        try:
            page_list = paginator.page(page_number)
        except EmptyPage:
            # 处理页码超出范围的情况，重定向到最后一页
            page_list = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        cache.set(filter_page_list_cache_key, page_list, base.configs('cache')['day'])

        context = {
            'lists': page_list,
            'type': filter_type,
            'interval': interval,
            'page_number': page_number,
            'page_total': paginator.num_pages
        }

        page_display = func.page_display(session_key, site, False, 'norm')
        context.update(page_display)
        return render(request, 'filter-list.html', context)

    else:
        request_func = request.POST.get('func')
        if request_func == 'update':
            page_list = list(cache.get(filter_page_list_cache_key))
            data = fetch.Stock.data(page_list)
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
        elif request_func == 'pick':
            pick_type = request.POST.get('type')
            pick_flow_list = func.get_filter_flow_list(pick_type, True)

            pick_list = list(pick_flow_list.values_list('code', flat=True))
            filter_setting = base.configs('filter')
            stock_filter_count = filter_setting['bases']['stock']['count']
            stock_filter_active = filter_setting['bases']['stock']['active']
            stock_filter_criteria = filter_setting['bases']['stock']['list'][stock_filter_active]['criteria']
            stock_pick_index = stock_filter_count
            stock_pick_count = stock_filter_count + 1

            stock_filter_list = StockFilterList.objects.all()
            stock_filter_list.update(base=None, mark=None)
            func.filter_bases_new_add('stock', pick_list, stock_pick_index)

            filter_setting['bases']['stock']['active'] = stock_pick_index
            filter_setting['bases']['stock']['count'] = stock_pick_count
            base.save_setting('filter', filter_setting)

            pick_range = func.filter_bases_ranges('stock')
            filter_setting['bases']['stock']['list'].append({
                'index': stock_pick_index,
                'date': date.today().strftime("%Y-%m-%d"),
                'qty': len(pick_list),
                'range': pick_range,
                "criteria": stock_filter_criteria
            })
            base.save_setting('filter', filter_setting)

            cache.delete(flow_list_cache_key)
            cache.delete(filter_type_cache_key)
            cache.delete(filter_page_list_cache_key)
            return JsonResponse({'msg': 'done'}, safe=False, json_dumps_params={'ensure_ascii': False})
        # elif request_func == 'type':
        else:
            cache.set(filter_type_cache_key, request.POST.get('type'), base.configs('cache')['day'])
            cache.delete(flow_list_cache_key)
            cache.delete(filter_page_list_cache_key)
            return JsonResponse({}, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def filter_refer(request):
    site = 'filter/refer'
    session_key = request.session.session_key
    func.set_follow_up(session_key, site)
    interval = base.configs('refresh')['interval']

    flow_list_cache_key = f'filter/refer-flow-list-{session_key}'
    filter_page_list_cache_key = f'filter/refer-page-list-{session_key}'
    filter_set_cache_key = f'filter-set-{session_key}'

    if request.method != 'POST':
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)

        filter_set = cache.get(filter_set_cache_key) or 'all'
        page_number = int(request.GET.get('page', 1))

        paginator_list = func.get_filter_refer_list(filter_set)
        cache.set(flow_list_cache_key, paginator_list, base.configs('cache')['day'])

        per_page = base.configs('page')['filter']
        paginator = Paginator(paginator_list, per_page)

        try:
            page_list = paginator.page(page_number)
        except EmptyPage:
            # 处理页码超出范围的情况，重定向到最后一页
            page_list = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        cache.set(filter_page_list_cache_key, page_list, base.configs('cache')['day'])

        context = {
            'lists': page_list,
            'set': filter_set,
            'interval': interval,
            'page_number': page_number,
            'page_total': paginator.num_pages
        }

        page_display = func.page_display(session_key, site, False, 'norm')
        context.update(page_display)
        return render(request, 'filter-refer.html', context)

    else:
        request_func = request.POST.get('func')
        if request_func == 'update':
            page_list = list(cache.get(filter_page_list_cache_key))
            data = fetch.Stock.data(page_list)
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
        # elif request_func == 'set':
        else:
            cache.set(filter_set_cache_key, request.POST.get('set'), base.configs('cache')['day'])
            cache.delete(flow_list_cache_key)
            cache.delete(filter_page_list_cache_key)
            return JsonResponse({}, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def filter_view(request, code):
    session_key = request.session.session_key

    follow_up_cache_key = f'follow-up-{session_key}'
    follow_up = cache.get(follow_up_cache_key)
    site_prev = follow_up['site'] if follow_up else None
    site_prev_mapping = ['filter/list', 'filter/view', 'filter/refer', 'filter/refer/view']

    site = 'filter/view'
    if site_prev not in site_prev_mapping:
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)
    elif site_prev == 'filter/refer' or site_prev == 'filter/refer/view':
        site = 'filter/refer/view'

    if request.method != 'POST':
        follow_up = func.set_follow_up(session_key, site, code)
        page_display = func.page_display(session_key, site, True)
        chart_display = func.chart_display(
            session_key, site, follow_up['cat'],
            follow_up['code'], follow_up['name'], follow_up['market']
        )
        navi = func.get_chart_navi(session_key, site, code)

        context = page_display
        context.update(chart_display)
        context.update(navi)

        filter_flow_inst = StockFilterList.objects.get(code=follow_up['code'])
        try:
            StockFocusIndex.objects.get(code=follow_up['code'])
            focus = 1
        except StockFocusIndex.DoesNotExist:
            focus = 0

        context.update({
            'data': filter_flow_inst,
            'focus': focus,
            'mark': filter_flow_inst.mark
        })

        return render(request, 'multi-view.html', context)

    else:
        request_func = request.POST.get('func')

        if '.' in code:
            code = code.split('.')[1]

        if request_func == 'comments':
            try:
                filter_flow_inst = StockFilterList.objects.get(code=code)
                filter_flow_inst.comments = request.POST.get('value')
                filter_flow_inst.save()
                data = {'msg': '备忘保存完成 ！'}
            except StockFilterList.DoesNotExist:
                data = {'msg': '数据库不存在 ！'}

        elif request_func == 'mark':
            grade = int(request.POST.get('grade'))
            data = func.set_mark_focus(session_key, site, code, grade)

        # elif request_func == 'back':
        else:
            url = 'filter/list' if site == 'filter/view' else 'filter/refer'
            flow_list_cache_key = f'{url}-flow-list-{session_key}'
            paginator_list = cache.get(flow_list_cache_key)
            if paginator_list:
                navi_index = base.find_satisfy_index(paginator_list, 'code', code)
                per_page = base.configs('page')['filter']
                page = math.floor(navi_index / per_page) + 1
                url = url if page == 1 else f'{url}?page={page}'
                data = {'url': url}
            else:
                data = {'url': url}

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def filter_config(request):
    site = 'filter/config'
    session_key = request.session.session_key
    func.set_follow_up(session_key, site)

    filter_config_expand_cache_key = f'filter-config-expand-{session_key}'
    expand = {'display': False, 'start': False, 'term': False, 'option': False, 'range': False}

    filter_setting = base.configs('filter')
    if not filter_setting:
        func.filter_init_data('stock')
        func.filter_init_data('fund')
        func.filter_init_data('sector')
        filter_setting = base.configs('filter')

    bases_cat = filter_setting['bases']['cat']

    if request.method != 'POST':
        display = filter_setting['display']
        bases_start_date = filter_setting['start']
        bases_list_active = filter_setting['bases'][bases_cat]['active']
        bases_list_refer = filter_setting['bases'][bases_cat]['refer']
        filters_list_active = filter_setting['filters']['active']

        bases_list = filter_setting['bases'][bases_cat]['list']
        filters_list = filter_setting['filters']['list']

        base_criteria = None
        filter_criteria = None

        ranges = None

        bases = [{
            'index': 0,
            'select': bases_list_active == 0,
            'value': f'{bases_list[0]["date"]}[{bases_list[0]["qty"]}]'
        }]

        filters = [{
            'index': 0,
            'select': filters_list_active == 0,
            'value': f'{filters_list[0]["date"]}'
        }]

        if bases_list_active == 0:
            base_criteria = bases_list[0]['criteria']
            ranges = bases_list[0]['range']
        if filters_list_active == 0:
            filter_criteria = filters_list[0]['criteria']

        bases_count = filter_setting['bases'][bases_cat]['count']
        bases_start_index = max(1, bases_count - display + 1)
        bases_end_index = bases_count

        # start_index 包含，end_index 不包含
        for i in range(bases_start_index, bases_end_index):
            select_base = bases_list_active == i
            select_refer = bases_list_refer == i

            bases.append({
                'index': bases_list[i]['index'],
                'select': select_base,
                'refer': select_refer,
                'value': f'{bases_list[i]["date"]}[{bases_list[i]["qty"]}]'
            })

            if select_base:
                base_criteria = bases_list[i]['criteria']
                ranges = bases_list[i]['range']

        filter_count = filter_setting['filters']['count']
        filter_start_index = max(1, filter_count - display + 1)
        filter_end_index = filter_count
        # start_index 包含，end_index 不包含
        for i in range(filter_start_index, filter_end_index):
            select_filter = filters_list_active == i

            filters.append({
                'index': filters_list[i]['index'],
                'select': select_filter,
                'value': f'{filters_list[i]["date"]}'
            })
            if select_filter:
                filter_criteria = filters_list[i]['criteria']

        expand.update(cache.get(filter_config_expand_cache_key) or {})

        context = {
            # 用于是否显示展开设置
            'expand': expand,
            'display': display,
            'start': bases_start_date,
            'filters': filters,
            'filter_criteria': func.filter_criteria_display(filter_criteria),
            'cat': bases_cat,
            'bases': bases,
            'base_criteria': func.filter_criteria_display(base_criteria),
            'ranges': ranges
        }

        page_display = func.page_display(session_key, site, False, 'norm')
        context.update(page_display)

        return render(request, 'filter-config.html', context)

    else:
        request_func = request.POST.get('func')

        if request_func == 'display':
            display = int(request.POST.get('value'))
            bases_count = filter_setting['bases'][bases_cat]['count']
            filters_count = filter_setting['filters']['count']

            bases_start_index = max(1, bases_count - display + 1)
            filters_start_index = max(1, filters_count - display + 1)

            filters_list_active = filter_setting['filters']['active']
            bases_list_active = filter_setting['bases'][bases_cat]['active']

            if bases_list_active < bases_start_index:
                filter_setting['bases'][bases_cat]['active'] = 0
            if filters_list_active < filters_start_index:
                filter_setting['filters']['active'] = 0

            filter_setting['display'] = display
            base.save_setting('filter', filter_setting)

            this_expand = {'display': True}
            data = {'msg': 'done'}

        elif request_func == 'start':
            start_date = json.loads(request.POST.get('value'))
            filter_setting['start'] = start_date
            base.save_setting('filter', filter_setting)
            this_expand = {'start': True}
            data = {'msg': 'done'}

        elif request_func == 'filter':
            filter_setting['filters']['active'] = int(request.POST.get('value'))
            base.save_setting('filter', filter_setting)
            this_expand = {'term': True}
            data = {'msg': 'done'}

        # cat 为 fund 或 sector 时，仅是对筛选有效，对筛选清单无效，筛选清单仅显示 filter_list 数据库中的筛选结果
        elif request_func == 'cat':
            this_expand = {'option': True}

            if filter_setting['running'] == 0:
                cat = request.POST.get('value')
                filter_setting['bases']['cat'] = cat
                base.save_setting('filter', filter_setting)
                data = {'msg': 'done'}
            else:
                data = {'msg': '正在筛选中，禁止更改！'}

        elif request_func == 'base':
            this_expand = {'option': True}
            if filter_setting['running'] == 0:
                base_index = int(request.POST.get('value'))

                filter_setting['bases'][bases_cat]['active'] = base_index
                func.filter_config_active('base', base_index)
                func.filter_config_active('mark', base_index)
                base.save_setting('filter', filter_setting)

                data = {'msg': 'done'}
            else:
                data = {'msg': '正在筛选中，禁止更改！'}

        elif request_func == 'range':
            this_expand = {'range': True}

            range_index = int(request.POST.get('index'))
            range_select = int(request.POST.get('select'))

            bases_list_active = filter_setting['bases'][bases_cat]['active']
            filter_setting['bases'][bases_cat]['list'][bases_list_active]['range'][range_index]['select'] = range_select

            range_value = filter_setting['bases'][bases_cat]['list'][bases_list_active]['range'][range_index]['value']

            if filter_setting['running'] == 0:
                if bases_cat == 'stock':
                    model = StockFilterList
                elif bases_cat == 'fund':
                    model = StockFundList
                # elif bases_cat == 'sector':
                else:
                    model = StockSectorList

                if range_select == 0:
                    model.objects.filter(code__startswith=range_value).update(base=None, mark=None)
                else:
                    model.objects.filter(
                        code__startswith=range_value,
                        bases__regex=r'\b{}\b'.format(str(bases_list_active))
                    ).update(base='1')

                filter_list_count = model.objects.filter(base=1).count()
                filter_setting['bases'][bases_cat]['list'][bases_list_active]['qty'] = filter_list_count
                base.save_setting('filter', filter_setting)
                data = {'msg': 'done'}
            else:
                data = {'msg': '正在筛选中，禁止更改！'}

        elif request_func == 'refer':
            this_expand = {'refer': True}
            if filter_setting['running'] == 0:
                filter_setting['bases'][bases_cat]['refer'] = int(request.POST.get('value'))
                base.save_setting('filter', filter_setting)

                data = {'msg': 'done'}
            else:
                data = {'msg': '正在筛选中，禁止更改！'}

        # elif request_func == 'handle':
        # bases 的 active 为 0 时，是刷新，并不是删除
        else:
            kind = request.POST.get('kind')
            if kind == 'filter':
                this_expand = {'term': True}
                list_active = filter_setting['filters']['active']

                count = filter_setting['filters']['count']
                lists = filter_setting['filters']['list']

                for i in range(list_active + 1, count):
                    # i 不会为 0，在模板中以及上面条件中已经进行排除了
                    lists[i]['index'] = i - 1

                del lists[list_active]
                count -= 1

                filter_setting['filters']['count'] = count
                filter_setting['filters']['active'] = count - 1
                base.save_setting('filter', filter_setting)
                data = {'msg': 'done'}
            # elif kind == 'base':
            else:
                this_expand = {'option': True, 'more': True}
                list_active = filter_setting['bases'][bases_cat]['active']

                filter_config_expand = cache.get(filter_config_expand_cache_key, {})
                more = True if filter_config_expand.get('more') else False

                if filter_setting['running'] == 0 or more:
                    if list_active == 0:
                        func.filter_init_data(bases_cat)
                    else:
                        func.filter_bases_delete(filter_setting, bases_cat, list_active)
                    data = {'msg': 'done'}
                else:
                    msg = '正在筛选中，禁止更改！' if kind == 'filter' else '若强制执行，请再次操作 ！'
                    data = {'msg': msg}

        expand.update(this_expand)
        cache.set(filter_config_expand_cache_key, expand, base.configs('cache')['short'])

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def filter_run(request):
    site = 'filter/config'
    session_key = request.session.session_key
    func.set_follow_up(session_key, site)

    # 短时间存储
    filter_interim_cache_key = f'filter-interim-{session_key}'

    filter_setting = base.configs('filter')
    if not filter_setting:
        func.filter_init_data('stock')
        func.filter_init_data('fund')
        func.filter_init_data('sector')
        filter_setting = base.configs('filter')

    if request.method != 'POST':
        criteria = cache.get(filter_interim_cache_key)

        if not criteria:
            filters_list_active = filter_setting['filters']['active']
            criteria = filter_setting['filters']['list'][filters_list_active]['criteria']

        context = {
            'running': filter_setting['running'],
            'criteria': criteria,
            'count': len(criteria),
            'default': filter_setting['filters']['default']
        }

        page_display = func.page_display(session_key, site, False, 'norm')
        context.update(page_display)

        return render(request, 'filter-run.html', context)

    else:
        request_func = request.POST.get('func')
        criteria = json.loads(request.POST.get('criteria')) if request.POST.get('criteria') else []

        if request_func == 'run':
            filter_setting = base.configs('filter')

            if not filter_setting:
                func.filter_init_data('stock')
                func.filter_init_data('fund')
                func.filter_init_data('sector')
                filter_setting = base.configs('filter')

            if filter_setting['running'] == 1:
                filter_setting['running'] = 2
                base.save_setting('filter', filter_setting)
                todo = False
                data = {'msg': '正在筛选中，强制终止筛选需再次提交 ！'}
            elif filter_setting['running'] == 2:
                filter_setting['running'] = 0
                todo = False
                data = {'msg': '已强制终止筛选 ！', 'refresh': 1}
            # elif filter_setting['running'] == 0:
            else:
                filter_setting['running'] = 1
                todo = True
                data = {'msg': 'done'}

            base.save_setting('filter', filter_setting)

            if todo:
                filter_criteria_cache_key = f'filter-criteria-{session_key}'
                cache.set(filter_criteria_cache_key, criteria, base.configs('cache')['long'])

                filters_list_active = filter_setting['filters']['active']
                filters_list_criteria = filter_setting['filters']['list'][filters_list_active]['criteria']

                compare_submit_criteria = set(map(frozenset, map(dict.items, criteria)))
                compare_filter_criteria = set(map(frozenset, map(dict.items, filters_list_criteria)))

                if compare_submit_criteria != compare_filter_criteria:
                    filter_count = filter_setting['filters']['count']
                    filter_setting['filters']['count'] = filter_count + 1
                    filter_setting['filters']['active'] = filter_count
                    filter_setting['filters']['refer'] = filters_list_active
                    filter_add = {
                        "index": filter_count,
                        "date": date.today().strftime("%Y-%m-%d"),
                        "criteria": criteria
                    }
                    filter_setting['filters']['list'].append(filter_add)
                    base.save_setting('filter', filter_setting)

                # 使用 threading.Thread 创建一个新线程并启动，实现后台运行
                thread = threading.Thread(target=func.async_filter_run, args=(session_key,))
                thread.start()

        elif request_func == 'del':
            if not criteria:
                criteria = []
                filter_add = {'index': 0}
                filter_add.update(filter_setting['filters']['default'])
                criteria.append(filter_add)
            cache.set(filter_interim_cache_key, criteria, base.configs('cache')['short'])
            data = {'msg': 'done'}

        elif request_func == 'add':
            count = len(criteria)
            filter_add = {'index': count}
            filter_add.update(filter_setting['filters']['default'])
            criteria.append(filter_add)
            cache.set(filter_interim_cache_key, criteria, base.configs('cache')['short'])
            data = {'msg': 'done'}

        # elif request_func == 'check':
        else:
            filter_percent_cache_key = f'filter-percent-{session_key}'
            data = {'running': filter_setting['running'], 'percent': cache.get(filter_percent_cache_key)}

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def trans_list(request):
    site = 'trans/list'
    session_key = request.session.session_key
    func.set_follow_up(session_key, site)
    interval = base.configs('refresh')['interval']

    trans_flow_list = func.get_trans_flow_list()
    flow_list_cache_key = f'{site}-flow-list-{session_key}'
    cache.set(flow_list_cache_key, trans_flow_list, base.configs('cache')['day'])

    if request.method != 'POST':
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)

        context = {
            'lists': trans_flow_list,
            'interval': interval
        }

        page_display = func.page_display(session_key, site, False, 'norm')
        context.update(page_display)

        return render(request, 'trans-list.html', context)

    else:
        data = fetch.Stock.data(trans_flow_list)
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def trans_view(request, code):
    site = 'trans/view'
    session_key = request.session.session_key

    if request.method != 'POST':
        follow_up_cache_key = f'follow-up-{session_key}'
        follow_up = cache.get(follow_up_cache_key)
        site_prev = follow_up['site'] if follow_up else None
        site_prev_mapping = ['trans/list', 'trans/view', 'trans/deal', 'trans/divd']
        if site_prev not in site_prev_mapping:
            chart_navi_cache_key = f'chart-navi-{session_key}'
            pilot_list_cache_key = f'pilot-list-{session_key}'
            cache.delete(chart_navi_cache_key)
            cache.delete(pilot_list_cache_key)

        follow_up = func.set_follow_up(session_key, site, code)
        page_display = func.page_display(session_key, site, True)
        chart_display = func.chart_display(
            session_key, site, follow_up['cat'],
            follow_up['code'], follow_up['name'], follow_up['market']
        )
        navi = func.get_chart_navi(session_key, site, code)

        # 执行 get_chart_navi 时只要 code 在数据库中存在，必然会生成 pilot_list
        pilot_list_cache_key = f'pilot-list-{session_key}'
        pilot_list = cache.get(pilot_list_cache_key)
        pilot_index = navi['pilot_index']

        if not pilot_list or pilot_index == -1:
            try:
                trans_flow_inst = StockTransIndex.objects.get(code=follow_up['code']).Flows.all().last()
            except StockTransIndex.DoesNotExist:
                raise Http404
        else:
            flow = pilot_list[pilot_index]['flow']
            trans_flow_inst = StockTransFlow.objects.get(flow=flow)

        trans_flow_inst.position = abs(float(trans_flow_inst.position))

        context = page_display
        context.update(chart_display)
        context.update(navi)
        context.update({
            'data': trans_flow_inst,
            'deci': 3 if trans_flow_inst.type == 'F' else 2
        })
        return render(request, 'trans-view.html', context)

    else:
        request_func = request.POST.get('func')

        if request_func == 'calc':
            trans_flow_inst = StockTransIndex.objects.get(code=code).Flows.all().last()
            calc_date = request.POST.get('date')
            target = float(request.POST.get('target')) if request.POST.get('target') else None
            stop = float(request.POST.get('stop')) if request.POST.get('stop') else None

            if target and stop:
                gross = float(trans_flow_inst.gross)
                position = float(trans_flow_inst.position)
                risk_exist = float(trans_flow_inst.risk)

                chance = func.get_deal_chance(gross, target, stop)

                risk = func.get_deal_risk(gross, position, stop)
                risk_gap = risk - risk_exist

                with transaction.atomic():
                    cash_flow_inst = StockCashFlow.objects.all().last()
                    risk_new = float(cash_flow_inst.risk) + risk_gap
                    risk_remain = float(cash_flow_inst.permit) - risk_new

                    new_cash_inst = StockCashFlow.objects.create(
                        date=calc_date,
                        event='U',
                        intent=None,
                        total=cash_flow_inst.total,
                        cash=cash_flow_inst.cash,
                        stock=cash_flow_inst.stock,
                        profit=cash_flow_inst.profit,
                        risk=risk_new,
                        permit=cash_flow_inst.permit,
                        remain=risk_remain
                    )

                    # 要排除的字段列表
                    trans_exclude_fields = [
                        'flow', '_state', 'index_id', 'deal_id', 'trans_id', 'cash_id', 'price', 'qty', 'amount'
                    ]
                    trans_fields_dict = {
                        key: value for key, value in vars(trans_flow_inst).items() if key not in trans_exclude_fields
                    }
                    trans_fields_dict.update({
                        'date': calc_date,
                        'event': 'U',
                        'target': target,
                        'stop': stop,
                        'chance': chance,
                        'fee': 0,
                        'risk': risk,
                        'adjusted': None,
                        'comments': None,
                    })

                    StockTransFlow.objects.create(
                        **trans_fields_dict,
                        index=trans_flow_inst.index,
                        trans=trans_flow_inst.trans,
                        cash=new_cash_inst
                    )
            else:
                chance = ''
                risk = ''

            data = {
                'target': target,
                'stop': stop,
                'chance': chance,
                'risk': risk
            }

            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})

        # elif request_func == 'comments':
        else:
            try:
                flow = request.POST.get('flow')
                trans_flow_inst = StockTransFlow.objects.get(flow=flow)
                trans_flow_inst.comments = request.POST.get('value')
                trans_flow_inst.save()
                data = {'msg': '备忘保存完成 ！'}
            except StockFocusFlow.DoesNotExist:
                data = {'msg': '数据库不存在 ！'}
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def trans_deal(request, code):
    site = 'trans/deal'
    session_key = request.session.session_key
    if code and '.' in code:
        code = code.split('.')[1]
    follow_up = func.set_follow_up(session_key, site, code)

    if request.method != 'POST':
        page_display = func.page_display(session_key, site, True)
        chart_display = func.chart_display(
            session_key, site, follow_up['cat'],
            follow_up['code'], follow_up['name'], follow_up['market']
        )
        data = func.handle_trans_deal(session_key, code)

        context = page_display
        context.update(chart_display)
        context.update({'data': data})

        return render(request, 'trans-deal.html', context)
    else:
        if request.POST.get('func') == 'submit':
            values = request.POST
            data = func.handle_trans_deal(session_key, follow_up['code'], 2, None, values)
            return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})

        elif request.POST.get('func') == 'intent':
            intent = request.POST.get('value')
            data = func.handle_trans_deal(session_key, code, 1, intent)

        # elif request.POST.get('func') == 'calc':
        else:
            values = request.POST
            data = func.handle_trans_deal(session_key, code, 1, None, values)

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def trans_divd(request, code):
    site = 'trans/divd'
    session_key = request.session.session_key

    if request.method != 'POST':
        follow_up_cache_key = f'follow-up-{session_key}'
        follow_up = cache.get(follow_up_cache_key)
        site_prev = follow_up['site'] if follow_up else None
        site_prev_mapping = ['trans/list', 'trans/view', 'trans/deal', 'trans/divd']
        if site_prev not in site_prev_mapping:
            chart_navi_cache_key = f'chart-navi-{session_key}'
            pilot_list_cache_key = f'pilot-list-{session_key}'
            cache.delete(chart_navi_cache_key)
            cache.delete(pilot_list_cache_key)

        follow_up = func.set_follow_up(session_key, site, code)
        page_display = func.page_display(session_key, site, False)

        trans_flow_inst = StockTransIndex.objects.get(code=follow_up['code']).Flows.all().last()
        position = abs(float(trans_flow_inst.position))

        kline = fetch.Kline.get_kline(code, 'div', 'day')['klines']
        # 默认为前一天
        divd_kline = kline[len(kline) - 2].split(',')
        divd_date = divd_kline[0]

        data = {
            'date': divd_date,
            'market': trans_flow_inst.market,
            'code': trans_flow_inst.code,
            'name': trans_flow_inst.name,
            'qty': position,
            'cash': 0,
            'fee': 0
        }

        context = page_display
        context.update({'data': data})
        return render(request, 'trans-divd.html', context)

    else:
        # request_func = request.POST.get('func')
        # if request_func == 'submit':
        divd_date = request.POST.get('date')
        divd_qty = abs(float(request.POST.get('qty')))
        divd_cash = abs(float(request.POST.get('cash')))
        divd_fee = float(request.POST.get('fee'))

        trans_flow_list = StockTransIndex.objects.get(code=code.split('.')[1]).Flows.all()
        trans_flow_inst = trans_flow_list.last()
        intent = trans_flow_inst.intent
        position_exist = float(trans_flow_inst.position)
        cost_exist = float(trans_flow_inst.cost)
        gross_exist = float(trans_flow_inst.gross)
        risk_exist = float(trans_flow_inst.risk)
        chance_exist = int(trans_flow_inst.chance)

        deci = 3 if trans_flow_inst.type == 'F' else 2

        if intent == 'S':
            divd_qty = -divd_qty
            divd_cash = -divd_cash

        gross_divd = round((gross_exist * position_exist - divd_cash) / divd_qty, 4)
        cost_divd = round((cost_exist * position_exist - divd_cash + divd_fee) / divd_qty, 4)
        stop_divd = round(gross_divd - risk_exist / divd_qty, deci)
        target_divd = round((gross_divd - chance_exist * stop_divd / 100) / (1 - chance_exist / 100), deci)

        try:
            with transaction.atomic():
                trans_exclude_fields = [
                    'flow', '_state', 'index_id', 'deal_id', 'trans_id', 'cash_id', 'adjusted', 'comments'
                ]
                trans_fields_dict = {
                    key: value for key, value in vars(trans_flow_inst).items() if key not in trans_exclude_fields
                }
                trans_fields_dict.update({
                    'date': divd_date,
                    'event': 'D',
                    'price': None,
                    'qty': None,
                    'amount': None,
                    'target': target_divd,
                    'stop': stop_divd,
                    'chance': chance_exist,
                    'fee': divd_fee,
                    'cost': cost_divd,
                    'gross': gross_divd,
                    'position': divd_qty,
                    'profit': 0,
                    'risk': risk_exist,
                })

                cash_flow_inst = StockCashFlow.objects.all().last()
                cash_new = float(cash_flow_inst.cash) + divd_cash
                stock_new = float(cash_flow_inst.stock) - divd_cash

                new_cash_inst = StockCashFlow.objects.create(
                    date=divd_date,
                    event='D',
                    intent=None,
                    total=cash_flow_inst.total,
                    cash=cash_new,
                    stock=stock_new,
                    profit=cash_flow_inst.profit,
                    risk=cash_flow_inst.risk,
                    permit=cash_flow_inst.permit,
                    remain=cash_flow_inst.remain
                )

                StockTransFlow.objects.create(
                    **trans_fields_dict,
                    index=trans_flow_inst.index,
                    trans=trans_flow_inst.trans,
                    cash=new_cash_inst
                )

                func.adj_deal_data(trans_flow_list, code, deci)

            data = {'msg': 'done'}
        except DatabaseError as e:
            data = {'msg': str(e)}
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def review_list(request, cat):
    site = 'review/focus/list' if cat == 'focus' else 'review/trans/list'
    session_key = request.session.session_key

    stats_config = base.configs('stats')
    flow_list_cache_key = f'review/{cat}/list-flow-list-{session_key}'
    review_page_list_cache_key = f'review/{cat}-page-list-{session_key}'

    if request.method != 'POST':
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)

        page_number = int(request.GET.get('page', 1))
        order_type = request.GET.get('order', 'date')
        paginator_list = func.get_review_flow_list(cat, order_type, stats_config['range'])
        cache.set(flow_list_cache_key, paginator_list, base.configs('cache')['day'])

        # review 结构：
        # {
        # "navi_list": 在 review_list 中生成
        # "pilot_list": review_list 后还未执行过 review_view，则为 None，否则为当前 pilot_list
        # "navi_index": 在 review_list 中设定为 -1，代表 review_list 后还未执行过 review_view
        # "pilot_index": 在 review_list 中设定为 -1，代表 review_list 后还未执行过 review_view
        # "current_model": 若 review_list 后还未执行过 review_view，则为 None，
        #   否则为 StockReviewTrans/StockReviewFocus/StockTransFlow/StockFocusFlow之一
        # "current_flow": 若 review_list 后还未执行过 review_view，则为 None，否则为 current_model 下的 flow
        # "current_code": 若 review_list 后还未执行过 review_view，则为 None，否则为 code
        # "current_market": 若 review_list 后还未执行过 review_view，则为 None，否则为 market
        # "current_name": 若 review_list 后还未执行过 review_view，则为 None，否则为 name
        # }

        review = {
            'navi_list': paginator_list,
            'pilot_list': None,
            'navi_index': -1,
            'pilot_index': -1,
            'current_model': None,
            'current_flow': None,
            'current_code': None,
            'current_market': None,
            'current_name': None
        }
        func.set_follow_up(session_key, site, None, None, None, review)

        interval = base.configs('refresh')['interval']

        per_page = base.configs('page')['review']
        paginator = Paginator(paginator_list, per_page)

        try:
            page_list = paginator.page(page_number)
        except EmptyPage:
            # 处理页码超出范围的情况，重定向到最后一页
            page_list = paginator.page(paginator.num_pages)
            page_number = paginator.num_pages

        cache.set(review_page_list_cache_key, page_list, base.configs('cache')['day'])

        context = {
            'lists': page_list,
            'review_type': cat,
            'interval': interval,
            'page_number': page_number,
            'page_total': paginator.num_pages,
            'order_type': order_type
        }

        page_display = func.page_display(session_key, site, False, 'norm')
        context.update(page_display)
        return render(request, 'review-list.html', context)

    else:
        # request_func = request.POST.get('func')
        # if request_func == 'update':
        page_list = list(cache.get(review_page_list_cache_key))
        data = fetch.Stock.data(page_list)
        for index, each in enumerate(data):
            deci = 3 if page_list[index].type == 'F' else 2
            each.update({'flow': page_list[index].flow, 'deci': deci})
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def review_view(request, cat, code):
    site = 'review/focus/view' if cat == 'focus' else 'review/trans/view'
    current_model = 'StockReviewFocus' if site == 'review/focus/view' else 'StockReviewTrans'

    session_key = request.session.session_key
    follow_up_cache_key = f'follow-up-{session_key}'
    follow_up = cache.get(follow_up_cache_key)

    site_prev_list_mapping = {
        'review/focus/view': 'review/focus/list',
        'review/trans/view': 'review/trans/list'
    }

    site_prev_view_mapping = {
        'review/focus/view': 'review/focus/view',
        'review/trans/view': 'review/trans/view'
    }

    if not follow_up:
        return HttpResponseRedirect(f'/{site_prev_list_mapping[site]}')
    else:
        review = follow_up.get('review')
        if not review:
            return HttpResponseRedirect(f'/{site_prev_list_mapping[site]}')

    # current_flow 只有第一次从 review_list 中跳转过来才有值
    current_flow = request.GET.get('flow')
    if current_flow:
        current_flow = int(current_flow)
        navi_list = review['navi_list']
        navi_index = base.find_satisfy_index(navi_list, 'flow', current_flow)

        if navi_index == -1:
            return HttpResponseRedirect(f'/{site_prev_list_mapping[site]}')

        current_code = navi_list[navi_index].code
        current_market = navi_list[navi_index].market
        current_name = navi_list[navi_index].name
        pilot_list = func.review_pilot_list(current_model, current_flow)
        pilot_index = 0

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

        follow_up = func.set_follow_up(session_key, site, current_code, current_market, current_name, review)

    elif site_prev_view_mapping[site] == site:
        review = follow_up['review']
        current_code = review['current_code']
        current_market = review['current_market']
        current_flow = review['current_flow']
        current_name = review['current_name']
        current_model = review['current_model']

        if f'{current_market}.{current_code}' != code:
            return HttpResponseRedirect(f'/{site_prev_list_mapping[site]}')

    else:
        return HttpResponseRedirect(f'/{site_prev_list_mapping[site]}')

    if request.method != 'POST':
        page_display = func.page_display(session_key, site, True)
        chart_display = func.chart_display(
            session_key, site, follow_up['cat'], current_code, current_name, current_market
        )

        navi = func.review_chart_navi(session_key, site)

        if current_model == 'StockReviewFocus':
            flow_inst = StockReviewFocus.objects.get(flow=current_flow)
            template = 'review-view.html'
            aim = 'focus'
        elif current_model == 'StockReviewTrans':
            flow_inst = StockReviewTrans.objects.get(flow=current_flow)
            template = 'review-view.html'
            aim = 'trans'
        elif current_model == 'StockTransFlow':
            flow_inst = StockTransFlow.objects.get(flow=current_flow)
            flow_inst.position = abs(float(flow_inst.position))
            template = 'trans-view.html'
            if flow_inst.event == 'E':
                aim = 'review'
            else:
                aim = 'update'
        # elif current_model == 'StockFocusFlow':
        else:
            flow_inst = StockFocusFlow.objects.get(flow=current_flow)
            flow_inst.priority = abs(flow_inst.priority)
            flow_inst.qty = abs(float(flow_inst.qty))
            template = 'focus-view.html'
            aim = 'review'

        context = page_display
        context.update(chart_display)
        context.update(navi)
        context.update({
            'data': flow_inst,
            # 用于 review-view 模板，并用于 focus/view 及 trans/view 显示内容
            'aim': aim,
            'deci': 3 if flow_inst.type == 'F' else 2
        })

        return render(request, template, context)

    else:
        request_func = request.POST.get('func')
        if request_func == 'star':
            if current_model == 'StockReviewFocus':
                review_flow_inst = StockReviewFocus.objects.get(flow=current_flow)
            # elif current_model == 'StockReviewTrans':
            else:
                review_flow_inst = StockReviewTrans.objects.get(flow=current_flow)

            try:
                star = request.POST.get('value')
                if star:
                    try:
                        review_flow_inst.star = int(star)
                        review_flow_inst.save()
                        data = {'msg': '星级设定完成 ！'}
                    except ValueError:
                        data = {'msg': '星级填写错误 ！'}
                else:
                    data = {'msg': '星级不能为空 ！'}
            except StockFocusFlow.DoesNotExist:
                data = {'msg': '数据库不存在 ！'}
        # elif request_func == 'comments':
        else:
            if current_model == 'StockReviewFocus':
                review_flow_inst = StockReviewFocus.objects.get(flow=current_flow)
            elif current_model == 'StockReviewTrans':
                review_flow_inst = StockReviewTrans.objects.get(flow=current_flow)
            elif current_model == 'StockFocusFlow':
                review_flow_inst = StockFocusFlow.objects.get(flow=current_flow)
            # elif current_model == 'StockTransFlow':
            else:
                review_flow_inst = StockTransFlow.objects.get(flow=current_flow)

            try:
                review_flow_inst.comments = request.POST.get('value')
                review_flow_inst.save()
                data = {'msg': '备忘保存完成 ！'}
            except StockFocusFlow.DoesNotExist:
                data = {'msg': '数据库不存在 ！'}

        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def link_list(request, cat):
    session_key = request.session.session_key
    if cat == 'sector':
        site = 'link/sector/list'
        link_page_list_cache_key = f'link-sector-page-list-{session_key}'
    else:
        site = 'link/stock/list'
        link_page_list_cache_key = f'link-stock-page-list-{session_key}'

    flow_list_cache_key = f'{site}-flow-list-{session_key}'

    func.set_follow_up(session_key, site)
    interval = base.configs('refresh')['interval']
    code = request.GET.get('code')

    if request.method != 'POST':
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)

        page_number = int(request.GET.get('page', 1))

        paginator_lists = fetch.Link.sectors(code) if cat == 'sector' else fetch.Link.stocks(code)
        if paginator_lists:
            cache.set(flow_list_cache_key, paginator_lists, base.configs('cache')['day'])
        else:
            raise Http404

        link_type = 'sector' if cat == 'sector' else 'filter'
        per_page = base.configs('page')[link_type]
        paginator = Paginator(paginator_lists, per_page)

        try:
            page_list = paginator.page(page_number)
        except EmptyPage:
            # 处理页码超出范围的情况，重定向到最后一页
            page_list = paginator.page(paginator.num_pages)

        cache.set(link_page_list_cache_key, page_list, base.configs('cache')['day'])

        context = {
            'link': True,
            'lists': page_list,
            'page_number': page_number,
            'page_total': paginator.num_pages,
            'interval': interval
        }

        page_display = func.page_display(session_key, site, False, 'norm')
        context.update(page_display)

        template = 'link-sector.html' if cat == 'sector' else 'link-stock.html'
        return render(request, template, context)

    else:
        # request_func = request.POST.get('func')
        # if request_func == 'update':
        page_list = list(cache.get(link_page_list_cache_key))
        data = fetch.Sector.data(page_list) if cat == 'sector' else fetch.Stock.data(page_list)
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def link_view(request, cat, code):
    site = 'link/sector/view' if cat == 'sector' else 'link/stock/view'
    deci = 3 if cat == 'fund' else 2
    session_key = request.session.session_key
    follow_up_cache_key = f'follow-up-{session_key}'

    if request.method != 'POST':
        chart_navi_cache_key = f'chart-navi-{session_key}'
        pilot_list_cache_key = f'pilot-list-{session_key}'
        cache.delete(chart_navi_cache_key)
        cache.delete(pilot_list_cache_key)

        get_close_price = fetch.get_close_price(code, deci)
        if get_close_price:
            name = get_close_price['name']
            market = code.split('.')[0]
            code = code.split('.')[1]
        else:
            raise Http404

        # 由于关联板块中的代码还包含行业板块的代码，因此 StockSectorList 中的代码不全
        # 若带 code 参数执行 set_follow_up 则会 page not found
        # follow_up = func.set_follow_up(session_key, site, code)
        follow_up = {
            'site': site,
            'cat': cat,
            'market': market,
            'code': code,
            'name': name
        }
        cache.set(follow_up_cache_key, follow_up, base.configs('cache')['day'])

        page_display = func.page_display(session_key, site, True)
        chart_display = func.chart_display(session_key, site, cat, code, name, market)
        navi = func.get_chart_navi(session_key, site, code)

        context = page_display
        context.update(chart_display)
        context.update(navi)

        if site == 'link/stock/view':
            filter_flow_inst = StockFilterList.objects.get(code=follow_up['code'])
            try:
                StockFocusIndex.objects.get(code=follow_up['code'])
                focus = 1
            except StockFocusIndex.DoesNotExist:
                focus = 0

            link = False
            mark = filter_flow_inst.mark
            comments = filter_flow_inst.comments
        else:
            focus = False
            link = True
            mark = False
            comments = ''

        data = {
            'code': code,
            'name': name,
            'market': market,
            'mark': mark,
            'comments': comments
        }

        context.update({'data': data, 'focus': focus, 'link': link})
        return render(request, 'multi-view.html', context)


@login_required
def chart_view(request):
    session_key = request.session.session_key

    request_site = request.POST.get('site')
    request_func = request.POST.get('func')
    request_value = request.POST.get('value')

    code = request.POST.get('code')
    if '.' in code:
        code = code.split('.')[1]
    # kline/trend 切换
    if request_func == 'view':
        # 修改缓存的 view 状态
        func.get_chart_view(session_key, request_site, request_value)

    # elif request_func == 'k' or request_func == 'd' or request_func == 'right' or request_func == 'period'
    else:
        # 设置 kline 参数
        func.get_kline_param(session_key, request_func, request_value)

    follow_up_cache_key = f'follow-up-{session_key}'
    follow_up = cache.get(follow_up_cache_key)

    if not follow_up or follow_up["code"] != code:
        raise Http404

    navi_func = request_func if request_func == 'navi' or request_func == 'pilot' else None
    navi_way = request_value if navi_func else None

    if request_site == 'review/focus/view' or request_site == 'review/trans/view':
        navi = func.review_chart_navi(session_key, request_site, navi_func, navi_way)
    else:
        navi = func.get_chart_navi(session_key, request_site, code, navi_func, navi_way)

    context = func.chart_display(
        session_key, request_site, follow_up['cat'],
        follow_up['code'], follow_up['name'], follow_up['market']
    )
    context.update(navi)

    if context['view'] == 'trend':
        trend_act = func.get_trend_action(request_site)
        context.update({'trend_act': trend_act})

    return render(request, 'chart-view.html', context)


@login_required
def chart_data(request):
    session_key = request.session.session_key
    request_site = request.POST.get('site')
    request_func = request.POST.get('func')

    market_with_code = request.POST.get('code')
    deci = 3 if request.POST.get('cat') == 'fund' else 2

    if request_func == 'quote':
        stock = fetch.quote(market_with_code, 'S', deci)
        market = fetch.quote(market_with_code, 'M', deci)

        data = {
            'stock': stock,
            'market': market
        }

        if request_site == 'trans/view':
            code = market_with_code.split('.')[1]
            close = stock['c']
            profit = func.get_dynamic_profit(code, close)
            data.update({'profit': str(round(profit))})

    elif request_func == 'trend':
        is_initial = True if request.POST.get('init') == '1' else False
        data = fetch.trend(request, market_with_code, is_initial, deci)

    elif request_func == 'kline':
        keys_basic = [
            # tp 及 fl 用于第一时间定位纵轴坐标
            'ohlc', 'volume', 'tp', 'fl', 'k', 'd', 'deci',
            'show_std', 'show_max', 'show_min', 'deadline', 'period', 'right'
        ]
        keys_extra = [
            'deal', 'up', 'av', 'lw', 'ma', 'mv'
        ]

        kline_data_cache_key = f'kline-data-{session_key}'
        kline_data = cache.get(kline_data_cache_key)

        # 意味着 basic 阶段
        if not kline_data:
            kline_param = func.get_kline_param(session_key)

            width = int(request.POST.get('width'))
            kline_data = fetch.Kline.view(
                market_with_code,
                kline_param['right'],
                kline_param['period'],
                int(kline_param['k']),
                int(kline_param['d']),
                width,
                deci,
                kline_param['deadline']
            )

            # deadline 只应用一次
            func.get_kline_param(session_key, 'deadline', -1)

            # 设置很短的时间失效，以便 chart_view 后再次获取 kline 时使用
            cache.set(kline_data_cache_key, kline_data, base.configs('cache')['short'])

        # 意味着 extra 阶段
        else:
            cache.delete(kline_data_cache_key)

        data = {}
        stage = request.POST.get('stage')
        keys = keys_basic if stage == 'basic' else keys_extra
        data.update({key: kline_data[key] for key in keys})

    elif request_func == 'screen':
        screen = request.POST.get('value')
        display_screen_cache_key = f'display-screen-{session_key}'
        cache.set(display_screen_cache_key, screen, base.configs('cache')['day'])
        data = {'screen': screen}

    # elif request_func == 'navi' or request_func == 'pilot':
    else:
        request_value = request.POST.get('value')
        # 当 request_func == 'pilot' 时，kline_param 中的 deadline 会修改

        if request_site == 'review/focus/view' or request_site == 'review/trans/view':
            func.review_chart_navi(session_key, request_site, request_func, request_value)
        else:
            func.get_chart_navi(session_key, request_site, market_with_code, request_func, request_value)

        follow_up_cache_key = f'follow-up-{session_key}'
        follow_up = cache.get(follow_up_cache_key)

        data = {
            'market': follow_up['market'],
            'code': follow_up['code']
        }

    return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


def love_view(request):
    return render(request, 'your-love.html')