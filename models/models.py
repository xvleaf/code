from django.db import models

EVENT_DISPLAY = (
    # 对应 StockCashFlow 的增减资金，及风险资金限额
    ('C', '资金'),
    ('F', '关注'),
    ('T', '交易'),
    ('D', '分红'),
    ('U', '更新'),
    ('E', '结束')
)

UNDER_DISPLAY = (
    ('SH', '上海'),
    ('SZ', '深圳'),
    ('BJ', '北京')
)

TYPE_DISPLAY = (
    ('S', '股票'),
    ('F', '基金'),
    ('B', '债券')
)

INTENT_DISPLAY = (
    # L - long, S - short
    ('L', '买入'),
    ('S', '卖出')
)

SETTLE_DISPLAY = (
    ('0', 'T+0'),
    ('1', 'T+1')
)

MARK_DISPLAY = (
    (1, '√'),
    (2, '√'),
)


# null: 数据库相关，定义数据库字段的值是否接受空值，设置 null=True 后，空值将设为 Null
# blank: 验证相关，当调用 form.is_valid() 时，将会判断值是否为空
# 默认值 blank=False，null=False
# 当设置 blank=False，null=True 时，表单验证时必须非空，但数据存储时可以为空值，blank=False 可不填
class WebConfigs(models.Model):
    index = models.IntegerField(db_column='Index', primary_key=True)
    item = models.CharField(db_column='Item', max_length=20)
    config = models.TextField(db_column='Config', blank=True, null=True)
    remark = models.TextField(db_column='Remark', blank=True, null=True)

    class Meta:
        managed = True
        # 自定义模型在数据库中的显示名称
        db_table = 'web_configs'
        # 自定义模型在 admin 页面显示名称
        verbose_name = 'Web Configs'
        # 自定义模型在 admin 页面显示复数名称
        verbose_name_plural = 'Web Configs'


class StockCashFlow(models.Model):
    flow = models.AutoField(db_column='Flow', primary_key=True)
    date = models.DateField(db_column='Date', null=True)
    event = models.CharField(db_column='Event', max_length=10, choices=EVENT_DISPLAY)
    intent = models.CharField(db_column='Intent', max_length=10, choices=INTENT_DISPLAY, null=True)
    # 账户总资产，total = cash + stock
    total = models.CharField(db_column='Total', max_length=20)
    # 现金
    cash = models.CharField(db_column='Cash', max_length=20)
    # 在手所有股票总市值
    stock = models.CharField(db_column='Stock', max_length=20,)
    # 总收益
    profit = models.CharField(db_column='Profit', max_length=20)
    # 当前风险资金
    risk = models.CharField(db_column='Risk', max_length=20)
    # 允许总风险资金额度
    permit = models.CharField(db_column='Permit', max_length=20)
    # 当前剩余风险资金额度
    remain = models.CharField(db_column='Remain', max_length=20, null=True)
    remark = models.TextField(db_column='Remark', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'stock_cash_flow'
        verbose_name = 'Stock Cash Flow'
        verbose_name_plural = 'Stock Cash Flow'


# 由于两个数据库不能同时关联同一个数据库，因此需要分为 StockReviewFocus 和 StockReviewTrans
class StockReviewFocus(models.Model):
    flow = models.AutoField(db_column='Flow', primary_key=True)
    # 关注的股票若交易了，则算作交易里面，不在此记录
    batch = models.IntegerField(db_column='Batch', unique=True)

    # 结束关注日期
    date = models.DateField(db_column='Date')
    type = models.CharField(db_column='Type', max_length=20, choices=TYPE_DISPLAY)
    market = models.CharField(db_column='Market', max_length=10)
    code = models.CharField(db_column='Code', max_length=10)
    name = models.CharField(db_column='Name', max_length=20)
    price = models.CharField(db_column='Price', max_length=20, blank=True, null=True)
    target = models.CharField(db_column='Target', max_length=20, blank=True, null=True)
    # 交易评定星级规则：
    # 0-未进行评级
    # 1-预判与趋势完全相反
    # 2-近期趋势不符合预判，但远期趋势符合预判
    # 3-近期趋势符合预判，但远期趋势不符合预判
    # 4-无法预判
    # 5-预判与趋势完全相同
    star = models.IntegerField(db_column='Star', blank=True, null=True)
    comments = models.TextField(db_column='Comments', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'stock_review_focus'
        verbose_name = 'Stock Review Focus'
        verbose_name_plural = 'Stock Review Focus'


class StockReviewTrans(models.Model):
    flow = models.AutoField(db_column='Flow', primary_key=True)
    # 关注的股票若交易了，在此记录
    batch = models.IntegerField(db_column='Batch', unique=True)

    # 结束交易日期
    date = models.DateField(db_column='Date')
    type = models.CharField(db_column='Type', max_length=20, choices=TYPE_DISPLAY)
    market = models.CharField(db_column='Market', max_length=10)
    code = models.CharField(db_column='Code', max_length=10)
    name = models.CharField(db_column='Name', max_length=20)
    # 成本价
    cost = models.CharField(db_column='Cost', max_length=20, blank=True, null=True)
    # 成交成本价，考虑到费用
    price = models.CharField(db_column='Price', max_length=20, blank=True, null=True)
    # 盈利比例
    percent = models.CharField(db_column='Percent', max_length=20, blank=True, null=True)
    # 总收益
    profit = models.CharField(db_column='Profit', max_length=20, blank=True, null=True)
    # 交易评定星级规则：
    # 0-未进行评级
    # 1-亏损，且未及时止损
    # 2-亏损，但及时止损
    # 3-盈利，但未及时止损
    # 4-盈利，未及时止盈
    # 5-盈利，且及时止盈
    star = models.IntegerField(db_column='Star', blank=True, null=True)
    comments = models.TextField(db_column='Comments', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'stock_review_trans'
        verbose_name = 'Stock Review Trans'
        verbose_name_plural = 'Stock Review Trans'


class StockFilterList(models.Model):
    code = models.CharField(db_column='Code', max_length=10, primary_key=True)
    name = models.CharField(db_column='Name', max_length=20)
    market = models.CharField(db_column='Market', max_length=20)
    # 筛选集合记录，存储形式为：0,2,4,5，代表第0/2/4/5次筛选时被使用作为基础数据
    # 总筛选次数记录在 web_configs 数据库中
    bases = models.CharField(db_column='Bases', max_length=200, blank=True, null=True)
    # 筛选选中记录，存储最近 n 次被筛选出来的记录(包括当前筛选)，存储形式为：2,4,5，代表第2/4/5次筛选时被选中
    marks = models.CharField(db_column='Marks', max_length=200, blank=True, null=True)
    # 当前筛选集合，用 1 表示
    base = models.IntegerField(db_column='Base', blank=True, null=True)
    # mark 分为 2 级标记，在当前筛选集合下被选中，分别用 1 和 2 表示
    mark = models.IntegerField(db_column='Mark', choices=MARK_DISPLAY, blank=True, null=True)
    # hide 用于隐藏不希望看到的股票, '1' 为隐藏，为空不隐藏
    hide = models.CharField(db_column='Hide', max_length=10, blank=True, null=True)
    comments = models.TextField(db_column='Comments', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'stock_filter_list'
        verbose_name = 'Stock Filter List'
        verbose_name_plural = 'Stock Filter List'


class StockFocusIndex(models.Model):
    index = models.AutoField(db_column='Index', primary_key=True)
    code = models.CharField(db_column='Code', max_length=10, unique=True)

    class Meta:
        managed = True
        db_table = 'stock_focus_index'
        verbose_name = 'Stock Focus Index'
        verbose_name_plural = 'Stock Focus Index'


class StockFocusFlow(models.Model):
    flow = models.AutoField(db_column='Flow', primary_key=True)
    # focus 针对所有股票的关注批次,后续的交易使用同样的批次
    batch = models.IntegerField(db_column='Batch')

    index = models.ForeignKey(
        StockFocusIndex,
        related_name='Flows',
        on_delete=models.DO_NOTHING,
        db_column='Index',
        blank=True,
        null=True
    )

    # 结束关注时，需要将整个 batch 的 focus 字段都更新为 StockReviewFocus 的 batch 字段
    focus = models.ForeignKey(
        StockReviewFocus,
        # 关联到 StockReviewFocus 的 batch 字段
        to_field='batch',
        related_name='Focus',
        on_delete=models.DO_NOTHING,
        db_column='Focus',
        blank=True,
        null=True
    )
    # 关注转变为交易后，交易完成后，需要将整个 batch 的 trans 字段都更新为 StockReviewFocus 的 batch 字段
    trans = models.ForeignKey(
        StockReviewTrans,
        to_field='batch',
        related_name='Focus',
        on_delete=models.DO_NOTHING,
        db_column='Trans',
        blank=True,
        null=True
    )

    # 股票所属市场
    market = models.CharField(db_column='Market', max_length=10)
    code = models.CharField(db_column='Code', max_length=10)
    name = models.CharField(db_column='Name', max_length=20)
    # 隶属证券市场，用于计算交易费用
    under = models.CharField(db_column='Under', max_length=20, choices=UNDER_DISPLAY)
    # 种类，用于定义股票/基金/债券，用于交易时计算交易费用
    type = models.CharField(db_column='Type', max_length=20, choices=TYPE_DISPLAY)
    date = models.DateField(db_column='Date')
    event = models.CharField(db_column='Event', max_length=10, choices=EVENT_DISPLAY)
    # 交易结算期 T+0/T+1
    settle = models.CharField(db_column='Settle', max_length=10, choices=SETTLE_DISPLAY, blank=True, null=True)
    # 交易方向
    intent = models.CharField(db_column='Intent', max_length=10, choices=INTENT_DISPLAY, blank=True, null=True)
    priority = models.IntegerField(db_column='Priority', blank=True, null=True)
    price = models.CharField(db_column='Price', max_length=20, blank=True, null=True)
    qty = models.CharField(db_column='Qty', max_length=20, blank=True, null=True)
    target = models.CharField(db_column='Target', max_length=20, blank=True, null=True)
    stop = models.CharField(db_column='Stop', max_length=20, blank=True, null=True)
    chance = models.CharField(db_column='Chance', max_length=20, blank=True, null=True)
    comments = models.TextField(db_column='Comments', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'stock_focus_flow'
        verbose_name = 'Stock Focus Flow'
        verbose_name_plural = 'Stock Focus Flow'


class StockFundList(models.Model):
    code = models.CharField(db_column='Code', max_length=10, primary_key=True)
    name = models.CharField(db_column='Name', max_length=20)
    market = models.CharField(db_column='Market', max_length=20)
    # ETF/LOF/CBF
    type = models.CharField(db_column='Type', max_length=20)
    bases = models.CharField(db_column='Bases', max_length=200, blank=True, null=True)
    # 筛选选中记录，存储最近 n 次被筛选出来的记录(包括当前筛选)，存储形式为：2,4,5，代表第2/4/5次筛选时被选中
    marks = models.CharField(db_column='Marks', max_length=200, blank=True, null=True)
    # 当前筛选集合，用 1 表示
    base = models.IntegerField(db_column='Base', blank=True, null=True)
    # mark 分为 2 级标记，分别用 1 和 2 表示
    mark = models.IntegerField(db_column='Mark', choices=MARK_DISPLAY, blank=True, null=True)
    # hide 用于隐藏不希望看到的股票, 1 为隐藏，为空不隐藏
    hide = models.CharField(db_column='Hide', max_length=10, blank=True, null=True)
    # 可转债 CB 对应的正股代码
    stock = models.CharField(db_column='Stock', max_length=20, blank=True, null=True)
    comments = models.TextField(db_column='Comments', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'stock_fund_list'
        verbose_name = 'Stock Fund List'
        verbose_name_plural = 'Stock Fund List'


class StockSectorList(models.Model):
    code = models.CharField(db_column='Code', max_length=10, primary_key=True)
    name = models.CharField(db_column='Name', max_length=20)
    market = models.CharField(db_column='Market', max_length=20)
    bases = models.CharField(db_column='Bases', max_length=200, blank=True, null=True)
    # 筛选选中记录，存储最近 n 次被筛选出来的记录(包括当前筛选)，存储形式为：2,4,5，代表第2/4/5次筛选时被选中
    marks = models.CharField(db_column='Marks', max_length=200, blank=True, null=True)
    # 当前筛选集合，用 1 表示
    base = models.IntegerField(db_column='Base', blank=True, null=True)
    # mark 分为 2 级关注，分别用 1 和 2 表示
    mark = models.IntegerField(db_column='Mark', choices=MARK_DISPLAY, blank=True, null=True)
    # hide 用于隐藏不希望看到的股票, 1 为隐藏，为空不隐藏
    hide = models.CharField(db_column='Hide', max_length=10, blank=True, null=True)
    comments = models.TextField(db_column='Comments', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'stock_sector_list'
        verbose_name = 'Stock Sector List'
        verbose_name_plural = 'Stock Sector List'


class StockTransDeal(models.Model):
    flow = models.AutoField(db_column='Flow', primary_key=True)
    code = models.CharField(db_column='Code', max_length=10)
    name = models.CharField(db_column='Name', max_length=20)
    market = models.CharField(db_column='Market', max_length=20)
    # {
    # "adj": {
    #     "long": [[1709881200000, 价格], [1709881200001, 价格], ...],
    #     "short": [[1709881200000, 价格], [1709881200001, 价格], ...],
    #     "dual": [[1709881200000, 价格], [1709881200001, 价格], ...],
    #     "info": [{"stamp": 1709881200000, "deal": [["mm/dd", "L/S", 价格, 数量], ["mm/dd", "L/S", 价格, 数量]]}, ...]
    # },
    # "div": {...}
    # }
    day = models.TextField(db_column='Day')
    week = models.TextField(db_column='Week')
    month = models.TextField(db_column='Month')

    class Meta:
        managed = True
        db_table = 'stock_trans_deal'
        verbose_name = 'Stock Trans Deal'
        verbose_name_plural = 'Stock Trans Deal'


class StockTransIndex(models.Model):
    index = models.AutoField(db_column='Index', primary_key=True)
    code = models.CharField(db_column='Code', max_length=10, unique=True)

    class Meta:
        managed = True
        db_table = 'stock_trans_index'
        verbose_name = 'Stock Trans Index'
        verbose_name_plural = 'Stock Trans Index'


class StockTransFlow(models.Model):
    flow = models.AutoField(db_column='Flow', primary_key=True)
    # 与 focus 批次相同
    batch = models.IntegerField(db_column='Batch')

    index = models.ForeignKey(
        StockTransIndex,
        related_name='Flows',
        on_delete=models.DO_NOTHING,
        db_column='Index',
        blank=True,
        null=True
    )

    deal = models.ForeignKey(
        StockTransDeal,
        related_name='Flows',
        on_delete=models.DO_NOTHING,
        db_column='Deal',
        blank=True,
        null=True
    )

    trans = models.ForeignKey(
        StockReviewTrans,
        to_field='batch',
        related_name='Trans',
        on_delete=models.DO_NOTHING,
        db_column='Trans',
        blank=True,
        null=True
    )

    # StockTransFlow 的 flow 对应 StockCashFlow 的 flow，但反过来不一定对应，所以需要放在 StockTransFlow 模型
    cash = models.OneToOneField(
        StockCashFlow,
        related_name='Trans',
        on_delete=models.DO_NOTHING,
        db_column='Cash',
        blank=True,
        null=True
    )

    market = models.CharField(db_column='Market', max_length=10)
    code = models.CharField(db_column='Code', max_length=10)
    name = models.CharField(db_column='Name', max_length=20)
    # 隶属证券市场，用于计算交易费用
    under = models.CharField(db_column='Under', max_length=20, choices=UNDER_DISPLAY)
    # 种类，用于定义股票/基金/债券，同样用于计算交易费用
    type = models.CharField(db_column='Type', max_length=20, choices=TYPE_DISPLAY)
    date = models.DateField(db_column='Date', null=True)
    event = models.CharField(db_column='Event', max_length=10, choices=EVENT_DISPLAY)
    settle = models.CharField(db_column='Settle', max_length=10, choices=SETTLE_DISPLAY)

    # ################### 本次部分 ################### #
    intent = models.CharField(db_column='Intent', max_length=10, choices=INTENT_DISPLAY, blank=True, null=True)
    # 成交时的价格（价格永远为正）及数量（买入为正，卖出为负）
    price = models.CharField(db_column='Price', max_length=20, blank=True, null=True)
    qty = models.CharField(db_column='Qty', max_length=20, blank=True, null=True)
    # 成交时的股票市值（与 qty 同符号）,如果 intent == L，代表给出去的现金（正值），反之为收到的现金（为负）
    # 因此计算实际收益时，将所有 amount 加起来，再加上说有的交易费用，取相反数就是收益
    amount = models.CharField(db_column='Amount', max_length=20, blank=True, null=True)
    target = models.CharField(db_column='Target', max_length=20, blank=True, null=True)
    stop = models.CharField(db_column='Stop', max_length=20, blank=True, null=True)
    chance = models.CharField(db_column='Chance', max_length=20, blank=True, null=True)
    # 本次交易费用（始终为正）
    fee = models.CharField(db_column='Fee', max_length=20, blank=True, null=True)

    # ################### 汇总部分 ################### #
    # 总的持仓成本价（包含交易费用，可正可负），保留 4 位小数，页面仅显示 2 位小数。当平仓时（position = 0），cost = 0，转化为了收益
    # 复权时需要重新计算
    cost = models.CharField(db_column='Cost', max_length=20, blank=True, null=True)
    # 总的持仓毛成本价（不包含费用，可正可负，用于计算 StockCashFlow 股票市值），保留 4 位小数，当平仓时（position = 0），gross = 0
    # 复权时需要重新计算
    gross = models.CharField(db_column='Gross', max_length=20, blank=True, null=True)
    # 股票数大于零：交易状态为买入；股票数等于零：交易状态为平仓；股票数小于零：交易状态为卖出
    # 复权时需要重新计算
    position = models.CharField(db_column='Position', max_length=10, blank=True, null=True)
    # 此 batch 交易的总收益（盈利为正，亏损为负），过程中不计算收益，均摊到 cost 中，仅结束交易时填写
    profit = models.CharField(db_column='Profit', max_length=20, null=True)
    # 此 batch 交易的当前风险（始终大于等于 0）
    risk = models.CharField(db_column='Risk', max_length=20, null=True)
    # adjusted 格式为：
    #     {'price': 复权后的价格,
    #     'qty': 复权后的股数（用于显示，因此始终为正）,
    #     'open': 记录成交当天日k线开盘价格，以便计算复权后的等效价格及股数，计算时 open 价格也要改为复权后的价格
    #     }
    adjusted = models.TextField(db_column='Adjusted ', blank=True, null=True)
    comments = models.TextField(db_column='Comments', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'stock_trans_flow'
        verbose_name = 'Stock Trans Flow'
        verbose_name_plural = 'Stock Trans Flow'
