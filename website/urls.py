# Django提供了身份验证功能，包括登录，注销和密码管理等
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import RedirectView

from stock import views as stock_views
from website import base as base_views

urlpatterns = [
    path('admin', admin.site.urls),
    re_path(r'^favicon.ico$', RedirectView.as_view(url=r'static/icon/favicon.svg')),

    # redirect_authenticated_user=True 作用是已登录用户直接跳转登录后默认页面
    path('', auth_views.LoginView.as_view(redirect_authenticated_user=True,
                                          template_name='web-login.html'), name='login'),
    re_path(r'login', auth_views.LoginView.as_view(redirect_authenticated_user=True,
                                                   template_name='web-login.html')),
    re_path(r'logout', base_views.quit, name='logout'),

    path('setting', base_views.setting),
    path('overall', stock_views.overall_view),
    path('focus', stock_views.focus_list),
    path('fund', stock_views.fund_list),
    path('sector', stock_views.sector_list),
    path('trans', stock_views.trans_list),
    path('filter', stock_views.filter_list),
    path('files', stock_views.files_view),
    path('love', stock_views.love_view),

    path('files/view', stock_views.files_view, name='files'),
    path('files/load', stock_views.files_load),

    re_path(r'link/(?P<cat>\w+)/list', stock_views.link_list),
    re_path(r'link/(?P<cat>\w+)/view/(?P<code>[\w.]+)', stock_views.link_view),

    re_path(r'review/(?P<cat>\w+)/list', stock_views.review_list),
    re_path(r'review/(?P<cat>\w+)/view/(?P<code>[\w.]+)', stock_views.review_view),

    path('focus/list', stock_views.focus_list, name='focus'),
    path('focus/plus', stock_views.focus_plus),
    re_path(r'focus/view/(?P<code>[\w.]+)', stock_views.focus_view),
    re_path(r'focus/edit/(?P<code>[\w.]+)', stock_views.focus_edit),

    path('filter/list', stock_views.filter_list),
    path('filter/refer', stock_views.filter_refer),
    re_path(r'filter/view/(?P<code>[\w.]+)', stock_views.filter_view),
    re_path(r'filter/refer/view/(?P<code>[\w.]+)', stock_views.filter_view),
    path('filter/config', stock_views.filter_config),
    path('filter/run', stock_views.filter_run),

    path('fund/list', stock_views.fund_list,),
    re_path(r'fund/view/(?P<code>[\w.]+)', stock_views.fund_view),

    path('sector/list', stock_views.sector_list),
    re_path(r'sector/view/(?P<code>[\w.]+)', stock_views.sector_view),

    path('trans/list', stock_views.trans_list),
    re_path(r'trans/view/(?P<code>[\w.]+)', stock_views.trans_view),
    re_path(r'trans/deal/(?P<code>[\w.]+)', stock_views.trans_deal),
    re_path(r'trans/divd/(?P<code>[\w.]+)', stock_views.trans_divd),

    path('chart/view', stock_views.chart_view),
    path('chart/data', stock_views.chart_data),

    re_path(r'view/(?P<code>[\w.]+)', stock_views.query_view),

    path('icp', base_views.get_icp_info)
]

# 自定义404异常页面
handler404 = base_views.page_lost
# 设置异常处理器
handler500 = base_views.page_error
