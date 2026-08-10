import { debounceLayout } from '../../base/js/base.js';

// ========== 全局依赖兼容层 ==========
function getCsrfToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

async function postRequest(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            console.error(`请求失败：${url}，状态码 ${response.status}`);
            return null;
        }
        return await response.json();
    } catch (err) {
        console.error('接口请求异常：', err);
        return null;
    }
}

const request = { async: postRequest, sync: postRequest };

const layer = window.layer || {
    msg: () => {},
    confirm: (text, opts, okCb) => {
        if (confirm(String(text).replace(/<[^>]+>/g, ''))) okCb();
    },
    close: () => {}
};

const Highcharts = window.Highcharts;

// ========== 全局状态变量 ==========
// let quoteTimer = null;
let trendTimer = null;
let trendChart = null;
let klineChart = null;
let trendIndex = 0;
let trendIndexNew = 0;
let ohlcData = [];
let volumeData = [];
let ohlcNewData = [];
let volumeNewData = [];
let preClosePrice = 0;
let priceDecimal = 2;
let tickInterval = 0;
let tickMax = 0;
let tickMin = 0;
let klineBasic = {};
// let klineExtra = {};
let pageConfig = {};

/**
 * 页面入口初始化
 */
export function initChartPage(config) {
    pageConfig = config;
    calcChartLayout();
    initPageElements();
    bindGlobalKeyboard();
    initScrollFold(); // 滚动收起交互
    
    // 图表库检测
    if (!Highcharts || typeof Highcharts.stockChart !== 'function') {
        showChartError('图表库加载失败');
        return;
    }
    
    if (config.view === 'kline') {
        initKlineChart();
    } else {
        initTrendChart();
    }

    window.addEventListener('resize', () => {
        debounceLayout(calcChartLayout, 150);
    });
}

function showChartError(text) {
    const placeholderId = pageConfig.view === 'trend' ? 'trendPlaceholder' : 'klinePlaceholder';
    const placeholder = document.getElementById(placeholderId);
    if (placeholder) {
        placeholder.querySelector('.chart-placeholder-text').textContent = text;
        placeholder.style.display = 'flex';
    }
}

/* 隐藏占位层，显示图表 */
function hideChartPlaceholder() {
    const placeholderId = pageConfig.view === 'trend' ? 'trendPlaceholder' : 'klinePlaceholder';
    const placeholder = document.getElementById(placeholderId);
    if (placeholder) {
        placeholder.style.display = 'none';
    }
}

/**
 * 计算布局 CSS 变量（移除导航栏top计算，纯CSS保证位置）
 */
function calcChartLayout() {
    const doc = document.documentElement;
    const viewHeight = window.innerHeight;
    const viewWidth = window.innerWidth;

    const scale = 0.9;
    const minHeight = 400;
    const maxHeight = 800;
    let chartHeight = Math.round(viewHeight * scale);
    chartHeight = Math.min(Math.max(chartHeight, minHeight), maxHeight);
    chartHeight = viewHeight < minHeight ? viewHeight : chartHeight;
    doc.style.setProperty('--chart-height', `${chartHeight}px`);
    // doc.style.setProperty('--frame-width', `${viewWidth}px`);
}

/**
 * 初始化页面所有UI元素
 */
function initPageElements() {
    // 导航序号

    if (pageConfig.navi) {
        const indicator = document.getElementById('naviIndicator');
        if (indicator) {
            const idx = parseInt(pageConfig.naviIndex) + 1;
            const total = parseInt(pageConfig.naviCount);
            indicator.textContent = total > 1 ? `(${idx}/${total})` : '';
        }
    }

    // 全屏按钮图标
    const fullscreenBtn = document.getElementById('btnFullscreen');
    if (fullscreenBtn) {
        fullscreenBtn.innerHTML = pageConfig.screen === 'full' 
            ? '<i class="fas fa-compress"></i>' 
            : '<i class="fas fa-expand"></i>';
    }

    // 分时操作按钮
    if (pageConfig.view === 'trend') {
        renderTrendActionButtons();
    }

    // K线参数栏默认占位
    if (pageConfig.view === 'kline') {
        document.getElementById('kValue').textContent = '--';
        document.getElementById('dValue').textContent = '--';
    }
}

/**
 * 渲染分时操作按钮
 */
function renderTrendActionButtons() {
    const act = pageConfig.trendAct;
    const exitBtn = document.getElementById('btnExit');
    const editBtn = document.getElementById('btnEdit');
    const dealBtn = document.getElementById('btnDeal');

    if (!act || act === 'None') {
        exitBtn.style.visibility = 'hidden';
        editBtn.style.visibility = 'hidden';
        dealBtn.style.visibility = 'hidden';
        return;
    }

    if (act.exit === 'exit') exitBtn.innerHTML = '<i class="fas fa-xmark"></i>';
    else if (act.exit === 'end') exitBtn.innerHTML = '<i class="fas fa-trash-can"></i>';
    else exitBtn.style.visibility = 'hidden';

    if (act.edit === 'edit') editBtn.innerHTML = '<i class="fas fa-pen-to-square"></i>';
    else if (act.edit === 'plus') editBtn.innerHTML = '<i class="fas fa-plus"></i>';
    else if (act.edit === 'divd') editBtn.innerHTML = '<i class="fas fa-coins"></i>';
    else editBtn.style.visibility = 'hidden';

    if (act.deal === 'deal') dealBtn.innerHTML = '<i class="fas fa-cart-shopping"></i>';
    else dealBtn.style.visibility = 'hidden';
}

// ==================== 分时图逻辑 ====================
async function initTrendChart() {
    trendIndex = 0;
    trendIndexNew = 0;

    await Promise.all([
        fetchTrendData(true)
    ]);

    if (ohlcData.length > 0) {
        renderTrendChart();
        hideChartPlaceholder();
    } else {
        showChartError('数据加载失败');
    }

    trendTimer = setInterval(async () => {
        const hasNew = await fetchTrendData(false);
        if (hasNew && trendChart) updateTrendChart();
    }, pageConfig.interval);
}

/**
async function fetchMarketQuote() {
    const data = await request.async('/chart/data', {
        site: pageConfig.site,
        cat: pageConfig.cat,
        code: pageConfig.marketCode,
        func: 'quote'
    });
    if (!data) return;

    const market = data.market;
    document.getElementById('marketName').textContent = market.n || '--';
    document.getElementById('marketPrice').textContent = 
        market.c !== '-' ? Number(market.c).toFixed(2) : '--';
    document.getElementById('marketChange').textContent = 
        market.p !== '-' ? market.p + '%' : '--';
}
 */

async function fetchTrendData(isInitial) {
    const data = await request.async('/chart/data', {
        site: pageConfig.site,
        cat: pageConfig.cat,
        code: pageConfig.marketCode,
        func: 'trend',
        init: isInitial ? '1' : '0'
    });

    if (!data) return false;

    if (isInitial) {
        ohlcData = data.ohlc;
        volumeData = data.volume;
        trendIndex = data.index;
    } else {
        ohlcNewData = data.ohlc;
        volumeNewData = data.volume;
        trendIndexNew = data.index;
    }

    preClosePrice = data.pc;
    priceDecimal = data.deci;
    tickInterval = data.tick_itv;
    tickMax = data.tick_max;
    tickMin = data.tick_min;

    return trendIndex > 0;
}

function renderTrendChart() {
    const container = document.getElementById('chartContainer');
    const priceLen = preClosePrice.toFixed(priceDecimal).length;
    const paddingLeft = priceLen >= 5 ? 45 : 30;

    Highcharts.setOptions({
        global: { useUTC: false, timezone: 'Asia/Shanghai' }
    });

    trendChart = Highcharts.stockChart(container, {
        chart: { spacing: [0, 0, 0, 0], borderWidth: 0 },
        navigator: { enabled: false },
        scrollbar: { enabled: false },
        exporting: { enabled: false },
        credits: { enabled: false },
        rangeSelector: { enabled: false },
        plotOptions: {
            series: {
                animation: false,
                dataGrouping: { enabled: false },
                states: { hover: { enabled: false } }
            }
        },
        xAxis: { type: 'datetime', ordinal: true, connectNulls: true },
        yAxis: [
            {
                height: '75%',
                min: tickMin,
                max: tickMax,
                tickInterval: tickInterval,
                labels: {
                    x: -2,
                    formatter: function () {
                        const percent = ((this.value - preClosePrice) / preClosePrice * 100).toFixed(1);
                        const isUp = percent > 0;
                        const color = isUp ? 'purple' : 'gray';
                        const sign = isUp ? '+' : '';
                        return `<span style="color:${color}">${sign}${percent}</span>`;
                    }
                }
            },
            {
                height: '75%',
                linkedTo: 0,
                opposite: false,
                labels: {
                    x: paddingLeft,
                    formatter: function () {
                        return this.value.toFixed(priceDecimal);
                    }
                }
            },
            { top: '75%', height: '25%', offset: 0, labels: { x: -2 } }
        ],
        tooltip: {
            shared: true,
            split: true,
            animation: false,
            useHTML: true,
            formatter: function () {
                const point = this.points[0];
                const time = new Date(point.x);
                const hour = String(time.getHours()).padStart(2, '0');
                const minute = String(time.getMinutes()).padStart(2, '0');
                return `
                    <b>${hour}:${minute}</b>
                    <table>
                        <tr><td>成交价 ${point.y.toFixed(priceDecimal)}</td></tr>
                        <tr><td>涨跌额 ${point.point.delta.toFixed(priceDecimal)}</td></tr>
                        <tr><td>涨跌幅 ${point.point.percent.toFixed(2)}%</td></tr>
                        <tr><td>成交量 ${this.points[1].y}</td></tr>
                    </table>
                `;
            }
        },
        series: [
            { type: 'spline', data: ohlcData, yAxis: 1, lineColor: 'gray', keys: ['x', 'y', 'percent', 'delta'] },
            { type: 'column', data: volumeData, yAxis: 2, color: 'gray' }
        ]
    });
}

function updateTrendChart() {
    if (trendIndexNew <= 0 || !trendChart) return;

    for (let i = 0; i < ohlcNewData.length; i++) {
        if (trendIndex < ohlcData.length) {
            ohlcData[trendIndex] = ohlcNewData[i];
            volumeData[trendIndex] = volumeNewData[i];
        } else {
            ohlcData.push(ohlcNewData[i]);
            volumeData.push(volumeNewData[i]);
        }
        trendIndex++;
    }
    trendIndexNew = trendIndex;

    trendChart.update({
        series: [{ data: ohlcData }, { data: volumeData }],
        yAxis: [{ min: tickMin, max: tickMax, tickInterval: tickInterval }]
    });
}

// ==================== K线图逻辑 ====================
function initKlineChart() {
    fetchKlineData('basic').then(success => {
        if (!success) {
            showChartError('K线数据加载失败');
            return;
        }
        renderKlineBasic();
        hideChartPlaceholder();
        renderKlineParamBar();
        /** 
        fetchKlineData('extra').then(() => {
            renderKlineExtra();
            renderKlineParamBar();
        });
        */
    });
}

async function fetchKlineData(stage) {
    const data = await request.async('/chart/data', {
        site: pageConfig.site,
        cat: pageConfig.cat,
        code: pageConfig.marketCode,
        func: 'kline',
        stage: stage,
        width: window.innerWidth
    });

    if (!data) return false;
    klineBasic = data;
    /** 
    if (stage === 'basic') {
        klineBasic = data;
    } else {
        klineExtra = data;
    }
    */
    return true;
}

function renderKlineBasic() {
    const { ohlc, volume, tp, fl, up, av, lw, ma, mv, deal, show_min, show_std, show_max, deadline, deci } = klineBasic;
    priceDecimal = deci;

    Highcharts.setOptions({
        lang: { rangeSelectorZoom: '' },
        global: { useUTC: false, timezone: 'Asia/Shanghai' }
    });

    klineChart = Highcharts.stockChart('chartContainer', {
        chart: {
            spacing: [0, 5, 0, 5],
            borderWidth: 0,
            plotBorderColor: '#cfd1ee',
            plotBorderWidth: 1,
            events: { render: function () { syncVolumeColor(this); } }
        },
        navigator: { enabled: false },
        scrollbar: { enabled: false },
        exporting: { enabled: false },
        credits: { enabled: false },
        rangeSelector: {
            inputEnabled: false,
            buttonSpacing: 2,
            buttonPosition: { align: 'left', x: 0, y: 35 },
            buttons: [
                { type: 'day', count: show_min, text: ' + ' },
                { type: 'day', count: show_std, text: ' · ' },
                { type: 'day', count: show_max, text: ' − ' }
            ],
            selected: 1
        },
        plotOptions: {
            series: {
                animation: false,
                dataGrouping: { enabled: false },
                states: { hover: { enabled: false }, inactive: { enabled: false } }
            }
        },
        xAxis: {
            type: 'date',
            ordinal: true,
            max: deadline,
            dateTimeLabelFormats: {
                day: '%m-%d', week: '%m-%d', month: '%y-%m', year: '%Y'
            }
        },
        yAxis: [
            { height: '80%', resize: { enabled: true }, labels: { align: 'right', x: -3 } },
            { top: '80%', height: '20%', offset: 0, labels: { align: 'right', x: -3 } }
        ],
        tooltip: {
            shared: true,
            split: true,
            animation: false,
            useHTML: true,
            formatter: function () {
                const point = this.points[0].point;
                updateKlineMetrics(point.index);
                const date = new Date(point.x);
                const dateStr = `${date.getMonth() + 1}-${date.getDate()}`;
                return `
                    <b>${dateStr}</b>
                    <table>
                        <tr><td>收盘 ${point.close.toFixed(priceDecimal)}</td>
                            <td style="padding-left:10px">开盘 ${point.open.toFixed(priceDecimal)}</td></tr>
                        <tr><td>最高 ${point.high.toFixed(priceDecimal)}</td>
                            <td style="padding-left:10px">最低 ${point.low.toFixed(priceDecimal)}</td></tr>
                        <tr><td>涨幅 ${klineBasic.ohlc[point.index][5]}%</td>
                            <td style="padding-left:10px">成交 ${(klineBasic.volume[point.index][1] / 1000).toFixed(0)}K</td></tr>
                    </table>
                `;
            }
        },
        series: [
            // 主图：K线本体
            { type: 'candlestick', data: ohlc, keys: ['x', 'open', 'high', 'low', 'close'], yAxis: 0, color: 'gray', lineColor: 'gray', upColor: 'white', upLineColor: 'purple' },
            // 副图：成交量
            { type: 'column', data: volume, yAxis: 1, enableMouseTracking: false },
            // 外轨 tp/fl（灰色）
            { type: 'spline', data: tp, yAxis: 0, enableMouseTracking: false, color: '#c0c0c0', lineWidth: 1 },
            { type: 'spline', data: fl, yAxis: 0, enableMouseTracking: false, color: '#c0c0c0', lineWidth: 1 },
            // 中轨 av（黑色）
            { type: 'spline', data: av, yAxis: 0, color: '#000', lineWidth: 1, enableMouseTracking: false },
            // 内轨 up/lw（青色）
            { type: 'spline', data: up, yAxis: 0, color: '#1aadce', lineWidth: 1, enableMouseTracking: false },
            { type: 'spline', data: lw, yAxis: 0, color: '#1aadce', lineWidth: 1, enableMouseTracking: false },
            // MA20 均线（橙色）
            { type: 'spline', data: ma, yAxis: 0, color: 'orange', lineWidth: 1, enableMouseTracking: false },
            // 成交量均线（黑色，副图）
            { type: 'spline', data: mv, yAxis: 1, color: '#000', lineWidth: 1, enableMouseTracking: false },
            // 交易信号：买入
            { type: 'scatter', data: deal.long, yAxis: 0, color: 'red', enableMouseTracking: false, marker: { symbol: 'triangle', radius: 4 } },
            // 交易信号：卖出
            { type: 'scatter', data: deal.short, yAxis: 0, color: 'green', enableMouseTracking: false, marker: { symbol: 'triangle-down', radius: 4 } },
            // 交易信号：双向
            { type: 'scatter', data: deal.dual, yAxis: 0, color: 'orange', enableMouseTracking: false, marker: { symbol: 'diamond', radius: 4 } },
            // 交易信号：分红
            { type: 'scatter', data: deal.divd, yAxis: 0, color: 'blue', enableMouseTracking: false, marker: { symbol: 'diamond', radius: 4 } }
        ]
    });
}

function syncVolumeColor(chart) {
    const ohlcSeries = chart.series[0];
    const volumeSeries = chart.series[1];
    ohlcSeries.points.forEach((point, index) => {
        const volPoint = volumeSeries.points[index];
        if (!volPoint) return;
        const color = point.close >= point.open ? 'purple' : 'gray';
        volPoint.graphic.element.setAttribute('fill', color);
    });
}

/** 
function renderKlineExtra() {
    if (!klineChart) return;
    const { up, av, lw, ma, mv, tp, fl, deal } = klineExtra;
    
    const addSeries = (config) => klineChart.addSeries(config);

    addSeries({ type: 'spline', data: tp, yAxis: 0, enableMouseTracking: false, color: '#c0c0c0', lineWidth: 1 });
    addSeries({ type: 'spline', data: up, yAxis: 0, color: '#1aadce', lineWidth: 1, enableMouseTracking: false });
    addSeries({ type: 'spline', data: av, yAxis: 0, color: '#000', lineWidth: 1, enableMouseTracking: false });
    addSeries({ type: 'spline', data: lw, yAxis: 0, color: '#1aadce', lineWidth: 1, enableMouseTracking: false });
    addSeries({ type: 'spline', data: fl, yAxis: 0, enableMouseTracking: false, color: '#c0c0c0', lineWidth: 1 });
    addSeries({ type: 'spline', data: ma, yAxis: 0, color: 'orange', lineWidth: 1, enableMouseTracking: false });
    addSeries({ type: 'spline', data: mv, yAxis: 1, color: '#000', lineWidth: 1, enableMouseTracking: false });

    const scatterConfig = (data, color, symbol) => ({
        type: 'scatter', data: data, yAxis: 0, color: color,
        enableMouseTracking: false, marker: { symbol: symbol, radius: 4 }
    });
    addSeries(scatterConfig(deal.long, 'red', 'triangle'));
    addSeries(scatterConfig(deal.short, 'green', 'triangle-down'));
    addSeries(scatterConfig(deal.dual, 'orange', 'diamond'));
    addSeries(scatterConfig(deal.divd, 'blue', 'diamond'));
}
*/

function renderKlineParamBar() {
    const paramBar = document.getElementById('klineParam');
    if (!paramBar) return;

    // K/D 值判空
    const kEl = document.getElementById('kValue');
    const dEl = document.getElementById('dValue');
    if (kEl) kEl.textContent = klineBasic.k ?? '-';
    if (dEl) dEl.textContent = klineBasic.d ?? '-';

    // 复权按钮判空
    const rightBtn = document.getElementById('btnRight');
    if (rightBtn) {
        const rightVal = klineBasic.right === 'adj' ? 'adj' : 'normal';
        rightBtn.innerHTML = rightVal === 'adj' 
            ? '<i class="fas fa-sync"></i>' 
            : '<i class="fas fa-ban"></i>';
    }

    paramBar.classList.add('is-loaded');
}

function updateKlineMetrics(index) {
    const ohlc = klineBasic.ohlc;
    // 基础数据不存在或索引越界，直接退出
    if (!ohlc || index < 0 || index >= ohlc.length) return;

    // 全部指标统一从 klineExtra 取值，未加载完成则兜底为空对象
    // const extra = klineExtra || {};
    // const { ma, mv, tp, up, av, lw, fl } = extra;
    const { ma, mv, tp, up, av, lw, fl } = klineBasic;

    // 封装安全取值：数组存在 + 索引合法 + 值存在
    const getVal = (arr, idx) => arr && idx < arr.length ? arr[idx][1] : undefined;
    
    // 收盘价、涨跌幅来自基础数据
    document.getElementById('klineClose').textContent = ohlc[index][4] ?? '--';
    document.getElementById('klinePercent').textContent = (ohlc[index][5] ?? '--') + '%';
    document.getElementById('klineMa').textContent = getVal(ma, index) ?? '--';
    document.getElementById('klineMv').textContent = getVal(mv, index) ? (getVal(mv, index) / 10000).toFixed(0) + 'W' : '--';
    document.getElementById('klineTp').textContent = getVal(tp, index) ?? '--';
    document.getElementById('klineUp').textContent = getVal(up, index) ?? '--';
    document.getElementById('klineAv').textContent = getVal(av, index) ?? '--';
    document.getElementById('klineLw').textContent = getVal(lw, index) ?? '--';
    document.getElementById('klineFl').textContent = getVal(fl, index) ?? '--';
}

// ==================== 全局交互函数 ====================
function bindGlobalKeyboard() {
    document.addEventListener('keydown', (e) => {
        const active = document.activeElement;
        if (active.isContentEditable) return;

        const code = pageConfig.marketCode;
        switch (e.key) {
            case 'ArrowUp':
                if (pageConfig.showPilot && pageConfig.pilotPrev) {
                    naviSwitch(code, 'pilot', 'prev');
                    e.preventDefault();
                }
                break;
            case 'ArrowDown':
                if (pageConfig.showPilot && pageConfig.pilotNext) {
                    naviSwitch(code, 'pilot', 'next');
                    e.preventDefault();
                }
                break;
            case 'ArrowLeft':
                if (pageConfig.navi && pageConfig.naviPrev) {
                    naviSwitch(code, 'navi', 'prev');
                    e.preventDefault();
                }
                break;
            case 'ArrowRight':
                if (pageConfig.navi && pageConfig.naviNext) {
                    naviSwitch(code, 'navi', 'next');
                    e.preventDefault();
                }
                break;
            case 'm': changePeriod(code, 'month'); break;
            case 'w': changePeriod(code, 'week'); break;
            case 'd': changePeriod(code, 'day'); break;
            case 'f': toggleFullscreen(code, pageConfig.screen); break;
            case 'r': toggleRight(code); break;
        }
    });
}

window.viewModeChange = function (marketCode) {
    const targetView = pageConfig.view === 'kline' ? 'trend' : 'kline';
    reloadChartView('view', targetView);
};

window.changePeriod = function (marketCode, period) {
    reloadChartView('period', period);
};

window.toggleRight = function (marketCode) {
    reloadChartView('right', '');
};

window.toggleFullscreen = function (marketCode, screen) {
    const newScreen = screen === 'full' ? 'norm' : 'full';
    request.async('/chart/data', {
        site: pageConfig.site,
        code: marketCode,
        func: 'screen',
        value: newScreen
    }).then(() => location.reload());
};

window.naviSwitch = function (marketCode, type, direction) {
    request.async('/chart/data', {
        site: pageConfig.site,
        code: marketCode,
        func: type,
        value: direction
    }).then(res => {
        if (res) {
            saveScrollPosition();
            window.location.href = `/${pageConfig.site}/${res.market}.${res.code}`;
        }
    });
};

window.exitAction = function (marketCode) {
    const msg = pageConfig.site === 'focus/view' ? '确定要结束关注吗？' : '确定要取消添加吗？';
    layer.confirm(msg, {
        title: '确认', btnAlign: 'c', btn: ['确定', '取消'], shade: 0.5
    }, function () {
        if (pageConfig.site === 'focus/view') {
            request.async(`/focus/edit/${marketCode}`, { func: 'end' }).then(res => {
                if (res.msg === 'done') window.location.href = '/focus/list';
            });
        } else {
            window.location.href = '/focus/list';
        }
    });
};

window.editAction = function (marketCode) {
    const routeMap = {
        'focus/view': `/focus/edit/${marketCode}`,
        'focus/plus': `/focus/view/${marketCode}`,
        'trans/view': `/trans/divd/${marketCode}`
    };
    const url = routeMap[pageConfig.site] || `/focus/plus?code=${marketCode}`;
    window.location.href = url;
};

window.dealAction = function (marketCode) {
    window.location.href = `/trans/deal/${marketCode}`;
};

window.jumpToLink = function (cat, market, code) {
    localStorage.setItem('link_code', `${cat},${market},${code}`);
    const url = cat === 'stock'
        ? `/link/sector/list?code=${market}.${code}`
        : `/link/stock/list?code=${code}`;
    window.location.href = url;
};

window.backToList = function () {
    const routeMap = {
        'focus/view': '/focus/list',
        'trans/view': '/trans/list',
        'review/focus/view': '/review/focus/list',
        'review/trans/view': '/review/trans/list'
    };
    window.location.href = routeMap[pageConfig.site] || '/focus/list';
};

window.toggleComment = function () {
    const area = document.getElementById('comments-area');
    area?.classList.toggle('disp-none');
};

// ==================== 内部工具函数 ====================
function reloadChartView(func, value) {
    // clearInterval(quoteTimer);
    clearInterval(trendTimer);

    request.async('/chart/view', {
        site: pageConfig.site,
        code: pageConfig.marketCode,
        func: func,
        value: value
    }).then(html => {
        document.getElementById('chartPage').innerHTML = html;
        initPageElements();
        if (pageConfig.view === 'kline') {
            initKlineChart();
        } else {
            initTrendChart();
        }
    });
}

function saveScrollPosition() {
    const scrollTop = document.querySelector('.base-root')?.scrollTop || 0;
    localStorage.setItem('chart_scroll', scrollTop);
}

// 滚动防抖
function debounce(fn, delay = 16) {
    let timer = null;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

// 滚动监听：上滑隐藏，下滑显示
let lastScrollTop = 0;
function initScrollFold() {
    const trendCanvas = document.querySelector('.chart-trend-canvas');
    const klineParam = document.querySelector('.chart-param');
    
    const handleScroll = debounce(() => {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const isFold = scrollTop > lastScrollTop && scrollTop > 60;

        // 同步切换收起状态
        trendCanvas?.classList.toggle('is-fold', isFold);
        klineParam?.classList.toggle('is-fold', isFold);

        // 图表自适应重绘（可选，高度变化后让Highcharts重新适配）
        if (window.Highcharts) {
            const chart = Highcharts.charts.find(c => c);
            chart?.reflow();
        }

        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
    });

    window.addEventListener('scroll', handleScroll, { passive: true });
}