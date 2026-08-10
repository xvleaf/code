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

    path('test', stock_views.test),

    path('focus', stock_views.focus_list),
    path('focus/view', stock_views.focus_view),
    path('chart/data', stock_views.chart_data),
    # path('chart/view', stock_views.chart_view)
]

# 自定义404异常页面
handler404 = base_views.page_lost
# 设置异常处理器
handler500 = base_views.page_error
