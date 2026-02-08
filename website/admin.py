from django.contrib import admin
from models.models import WebConfigs
from models.models import StockCashFlow
from models.models import StockFilterList
from models.models import StockFocusIndex, StockFocusFlow
from models.models import StockFundList, StockSectorList
from models.models import StockTransIndex, StockTransFlow, StockTransDeal
from models.models import StockReviewFocus, StockReviewTrans


@admin.register(WebConfigs)
class WebConfigsAdmin(admin.ModelAdmin):
    list_display = (
        'index',
        'item',
        'config',
        'remark'
    )


@admin.register(StockCashFlow)
class StockCashFlowAdmin(admin.ModelAdmin):
    list_display = (
        'flow',
        'date',
        'event',
        'intent',
        'total',
        'cash',
        'stock',
        'profit',
        'risk',
        'permit',
        'remain',
        'remark'
    )


@admin.register(StockReviewFocus)
class StockReviewFocusAdmin(admin.ModelAdmin):
    list_display = (
        'flow',
        'batch',
        'date',
        'type',
        'market',
        'code',
        'name',
        'price',
        'target',
        'star',
        'comments'
    )


@admin.register(StockReviewTrans)
class StockReviewTransAdmin(admin.ModelAdmin):
    list_display = (
        'flow',
        'batch',
        'date',
        'type',
        'market',
        'code',
        'name',
        'cost',
        'price',
        'percent',
        'profit',
        'star',
        'comments'
    )


@admin.register(StockFilterList)
class StockFilterListAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'market',
        'bases',
        'marks',
        'base',
        'mark',
        'hide',
        'comments'
    )


@admin.register(StockFocusIndex)
class StockFocusIndexAdmin(admin.ModelAdmin):
    list_display = (
        'index',
        'code'
    )


@admin.register(StockFocusFlow)
class StockFocusFlowAdmin(admin.ModelAdmin):
    list_display = (
        'flow',
        'batch',
        'index',
        'focus',
        'trans',
        'market',
        'code',
        'name',
        'under',
        'type',
        'date',
        'event',
        'settle',
        'intent',
        'priority',
        'price',
        'qty',
        'target',
        'stop',
        'chance',
        'comments'
    )


@admin.register(StockFundList)
class StockFundListAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'market',
        'type',
        'bases',
        'marks',
        'base',
        'mark',
        'hide',
        'stock',
        'comments'
    )


@admin.register(StockSectorList)
class StockSectorListAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'market',
        'bases',
        'marks',
        'base',
        'mark',
        'hide',
        'comments'
    )


@admin.register(StockTransDeal)
class StockTransDealAdmin(admin.ModelAdmin):
    list_display = (
        'flow',
        'code',
        'name',
        'market',
        'day',
        'week',
        'month'
    )


@admin.register(StockTransIndex)
class StockTransIndexAdmin(admin.ModelAdmin):
    list_display = (
        'index',
        'code'
    )


@admin.register(StockTransFlow)
class StockTransFlowAdmin(admin.ModelAdmin):
    list_display = (
        'flow',
        'batch',
        'index',
        'deal',
        'trans',
        'cash',
        'market',
        'code',
        'name',
        'under',
        'type',
        'date',
        'event',
        'settle',
        'intent',
        'price',
        'qty',
        'amount',
        'target',
        'stop',
        'chance',
        'fee',
        'cost',
        'gross',
        'position',
        'profit',
        'risk',
        'adjusted',
        'comments'
    )
