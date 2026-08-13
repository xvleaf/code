import { debounceLayout } from '../../base/js/base.js';
import { initTrendChart, renderTrendActionButtons, clearTrendTimer } from './trend.js';
import { initKlineChart } from './kline.js';

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

export const request = { async: postRequest, sync: postRequest };
export const layer = window.layer || {
    msg: () => {},
    confirm: (text, opts, okCb) => {
        if (confirm(String(text).replace(/<[^>]+>/g, ''))) okCb();
    },
    close: () => {}
};
export const Highcharts = window.Highcharts;

// ========== 公共全局状态变量 ==========
export let pageConfig = {};
export let priceDecimal = 2;
export function setPriceDecimal(val) {
    priceDecimal = Number(val) || 2;
}
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

export function showChartError(text) {
    const placeholderId = pageConfig.view === 'trend' ? 'trendPlaceholder' : 'klinePlaceholder';
    const placeholder = document.getElementById(placeholderId);
    if (placeholder) {
        placeholder.querySelector('.chart-placeholder-text').textContent = text;
        placeholder.style.display = 'flex';
    }
}

/* 隐藏占位层，显示图表 */
export function hideChartPlaceholder() {
    const placeholderId = pageConfig.view === 'trend' ? 'trendPlaceholder' : 'klinePlaceholder';
    const placeholder = document.getElementById(placeholderId);
    if (placeholder) {
        placeholder.style.display = 'none';
    }
}

/**
 * 计算布局 CSS 变量
 */
function calcChartLayout() {
    const doc = document.documentElement;
    const viewHeight = window.innerHeight;
    const scale = 0.9;
    const minHeight = 400;
    const maxHeight = 900;
    let chartHeight = Math.round(viewHeight * scale);
    chartHeight = Math.min(Math.max(chartHeight, minHeight), maxHeight);
    chartHeight = viewHeight < minHeight ? viewHeight : chartHeight;
    doc.style.setProperty('--chart-height', `${chartHeight}px`);
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
            case 'm': changeFreq(code, 'M'); break;
            case 'w': changeFreq(code, 'W'); break;
            case 'd': changeFreq(code, 'D'); break;
            case 'f': toggleFullscreen(code, pageConfig.screen); break;
            case 'r': toggleRight(code); break;
        }
    });
}

window.viewModeChange = function (marketCode) {
    const targetView = pageConfig.view === 'kline' ? 'trend' : 'kline';
    reloadChartView('view', targetView);
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


window.changeFreq = function (marketCode, freq) {
    reloadChartView('freq', freq);
};

window.toggleRight = function (marketCode) {
    reloadChartView('right', '');
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

// ==================== 内部工具函数 ====================
export function reloadChartView(func, value) {
    clearTrendTimer();
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