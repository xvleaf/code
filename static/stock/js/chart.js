	// 曲线区域高度
let chart_height,
	// 曲线区域导航条距离父元素（chart_height）顶部的高度
	navbar_top,
	// 曲线图及报价栏的高度（在chart_height内）
	trend_height,
	// 曲线图宽度
	trend_width,
	// 报价栏宽度
	quote_width,
	// 报价行高度
	quote_row_height,
	// kline图的高度
	kline_height,
	// 页面渲染框架距离上边距离
	page_top,
	// 页面内容距离定边距离
	content_top;

let trends, klines;
let quote_itv, trend_itv;
let trends_index, trends_index_new;
let ohlc, volume, ohlc_new, volume_new;
let pc, high, low, deci, tick_itv, tick_max, tick_min;
let deal, tp, up, av, lw, fl, ma, mv, k, d, period, right;
let show_std, show_max, show_min, deadline;
let trend_act_exit, trend_act_edit, trend_act_deal;


function set_content_top(screen, chart) {
	page_top = screen === "full" ? Math.floor((body_height - chart_height) / 4) : 58;
	content_top = chart === "True" ? chart_height + 5 : 0;
	doc.style.setProperty("--page-top", page_top + "px");
	doc.style.setProperty("--content-top", content_top + "px");
}


function set_chart_height() {
	const calc_chart_height = Math.round(body_height * chart_height_setting_scale);

	if (calc_chart_height > chart_height_setting_max) {
		chart_height = chart_height_setting_max;
	} else if (calc_chart_height < chart_height_setting_min) {
		chart_height = (body_height > chart_height_setting_min) ? chart_height_setting_min : body_height;
	} else {
		chart_height = calc_chart_height;
	}

	doc.style.setProperty("--chart-height", chart_height + "px");
}


function set_chart_inside(navi) {
	if (navi === 'True') {
		trend_height = chart_height - 25;
		kline_height =  chart_height - 25;
		navbar_top = chart_height - 45;
	} else {
		trend_height = chart_height;
		kline_height =  chart_height;
		navbar_top = 0;
	}

	quote_row_height = (chart_height >= 600) ? 28 : Math.round((chart_height - 150) / 16);

	doc.style.setProperty("--trend-height", trend_height + "px");
	doc.style.setProperty("--kline-height", kline_height + "px");
	doc.style.setProperty("--navbar-top", navbar_top + "px");
	doc.style.setProperty("--quote-row-height", quote_row_height + "px");
}


function set_trend_width() {
	let quote_width_ratio;

	if(is_mobile()) {
		quote_width_ratio = (body_height > body_width) ? quote_width_setting_max : quote_width_setting_min;
	}
	else {
		if (frame_width <= 400) {
			quote_width_ratio = quote_width_setting_max;
		} else if (frame_width <= 700) {
			quote_width_ratio = quote_width_setting_max - Math.round(quote_width_setting_gap * (frame_width - 400) / 400);
		}
		else {
			quote_width_ratio = quote_width_setting_min;
		}
	}
	quote_width = (quote_width_ratio * frame_width / 100).toFixed(0);
	trend_width = frame_width - quote_width;

	doc.style.setProperty("--quote-width", quote_width + "px");
	doc.style.setProperty("--trend-width", trend_width + "px");
}


function full_screen(market_with_code, screen) {
	screen = screen === "full"? "norm" : "full";
	let url = "chart/data";
	let post = {"site": site, "code": market_with_code, "func": 'screen', "value": screen};
	let data = ajax_sync(url, post);
	if (data) {
		if (data['screen'] === "full") {
			save_temp_form_data();
		}
		localStorage.setItem("size", '');
		location.reload();
	}
}


function page_chart_init(market_with_code, view) {
	let data = get_chart_view(market_with_code, 'view', view);
	if (data) {
		$("#page-chart").html(data);
	}
}


function get_chart_view(market_with_code, func, value) {
	let url = "chart/view";
	let post = {"site": site, "code": market_with_code, "func": func, "value": value};
	let data = ajax_sync(url, post);
	if (data) {
		return data;
	} else {
		return false;
	}
}


function overall_chart_init(data) {
	Highcharts.chart('page-chart', {
		chart: {
			type: 'line',
			style: {
				fontFamily: 'Arial'
			},
			marginTop: 20,
			marginLeft: 35,
			marginRight: 10,
			backgroundColor: null
		},
		title: {
			text: ''
		},
		xAxis: {
			lineWidth: 1, // 设置 x 轴坐标轴的线宽度
			lineColor: 'gray', // 设置 x 轴坐标轴的颜色
			type: 'datetime',
			showEmpty: true, // 设置为 true，即使所有数据都隐藏了，x 轴的日期标签也会显示出来
			categories: data['label'],
			// tickWidth: 1, // 刻度线宽度
			// tickColor: 'gray', // 刻度线颜色
			tickLength: 0, // 刻度线长度
			labels: {
				step: 1, // 表示每个标签都显示，避免 x 轴日期显示不全
				rotation: 0, // 日期旋转方向
				align: 'center',
				// 在横轴上显示所有日期，但若太密集，就会自动隐藏部分日期，以保持整体视觉效果。
				formatter: function () {
					return data['label'][this.pos];
				}
			}
		},
		yAxis: {
			tickLength: -100, // 刻度线超出标签的长度
			lineWidth: 1, // 设置 y 轴坐标轴的线宽度
			lineColor: 'gray', // 设置 y 轴坐标轴的颜色
			gridLineColor: 'gray', // 设置 y 轴栅格线颜色
			gridLineWidth: 0, // 设置 y 轴栅格线宽度
			title: {
				text: ''
			},
			labels: {
				align: 'right',
				x: -5,
				formatter: function() {
					return this.value === 0 ? 0 : Math.round(this.value / 1000) +'K';
				}
			},
			tickAmount: 5, // 设置 y 轴的刻度数量为 5
			min: data['min'], // 设置 y 轴的起始坐标
			// max: data['max'], // 设置 y 轴的结束坐标
			softMax: 1.1  // 允许自动扩展最大值
		},
		credits:{
			enabled: false
		},
		legend: {
			layout: 'vertical',
			align: 'right',
			verticalAlign: 'top',
			floating: true,
			x: -10,
			y: 0,
			itemMarginTop: 5, // 设置图例项之间的上间距
			itemMarginBottom: 5, // 设置图例项之间的下间距
			itemStyle: {
				fontWeight: 'normal' // 设置图例项文本的字体不加粗
			}
		},
		plotOptions: {
            series: {
				states: {hover: { enabled: false }},
				animation: false,	// 全局取消动画效果
				dataGrouping: { enabled: false }
			}
        },
		tooltip: {
			enabled: true,
			backgroundColor: 'rgba(255,255,255,0.85)',	// 背景颜色
			borderColor: 'black',         				// 边框颜色
			borderRadius: 10,             				// 边框圆角
			borderWidth: 1,               				// 边框宽度
			shadow: false,                				// 是否显示阴影
			animation: false,             				// 是否启用动画效果
			split: false,
			shared: true,
			followTouchMove: false,       				// false 为单指平移，true 为双指平移
			valueDecimals: 0,
			useHTML: true,
			crosshairs: [{width: 1, color: 'gray', dashStyle: 'dash'}, false], // 指示线
			formatter: function () {
				let index = this.points[0].point.index;
				let final = data['tips'][index]['final'];
				let deal = data['tips'][index]['deal'];

				let html = `<b>${final['date']}</b>
					<table>
						<tr><td>资产 ${final['total']}</td><td class="pad-left-1">资金 ${final['cash']}</td></tr>
						<tr><td>股票 ${final['stock']}</td><td class="pad-left-1">收益 ${final['profit']}</td></tr>`;

				if (deal !== '') {
					html += `<tr class="height-5px"></tr><tr><td colspan="2" class="overall-divider"></td></tr><tr class="height-5px"></tr>
							<tr><td>代码 ${deal['code']}</td><td class="pad-left-1">名称 ${deal['name']}</td></tr>`;
					if (deal['amount'].toString() !== '') {
						html += `<tr><td>事件 ${deal['event']}</td><td class="pad-left-1">方向 ${deal['intent']}</td></tr>
								<tr><td>金额 ${deal['amount']}</td><td class="pad-left-1">费用 ${deal['fee']}</td></tr>
								<tr><td>收益 ${deal['profit']}</td><td class="pad-left-1">风险 ${deal['risk']}</td></tr>`;
					} else {
						html += `<tr><td>事件 ${deal['event']}</td><td class="pad-left-1">风险 ${deal['risk']}</td></tr>`;
					}
				}

				html += `</table>`;
				return html;
			}
		},
		series: [{
				name: '资产',
				data: data['total'],
				visible: false,
				color: '#333333', // 曲线颜色
				marker: {
					symbol: 'diamond', // 标记形状
					radius: 3 // 形状大小
				}
			},{
				name: '资金',
				visible: false,
				data: data['cash'],
				color: '#808080',
				marker: {
					symbol: 'diamond',
					radius: 3
				}
			},{
				name: '股票',
				data: data['stock'],
				color: '#B0C4DE',
				marker: {
					symbol: 'diamond',
					radius: 3
				}
			},{
				name: '收益',
				data: data['profit'],
				color: 'purple',
				marker: {
					symbol: 'diamond',
					radius: 3
				}
			}
		],
		navigation: {
			buttonOptions: {
				enabled: true
			}
		},
		exporting: {
			enabled: false
		}
	});
}


function get_page_scroll() {
	let scroll_top = document.querySelector('.base-root').scrollTop.toString();
	localStorage.setItem('scroll', scroll_top);
	localStorage.removeItem('scroll');
}


function set_page_scroll() {
    document.querySelector('.base-root').scrollTop = parseFloat(localStorage.getItem('scroll')) || 0;
    localStorage.removeItem('scroll');
}


function chart_show_comment() {
	let comment_element = document.getElementById('chart-comments');
    comment_element.classList.toggle("disp-none");
}


function chart_goback_list() {
	if (site === 'focus/view') {
		window.location.href = `/focus/list`;
	} else if (site === 'trans/view') {
		window.location.href = `/trans/list`;
	} else if (site === 'review/focus/view') {
		window.location.href = `/review/focus/list`;
	} else if (site === 'review/trans/view') {
		window.location.href = `/review/trans/list`;
	}
}


function navi_view_change(market_with_code, func, way) {
	let url = "chart/data";
	let post = {"site": site, "code": market_with_code, "func": func, "value": way};
	let data = ajax_sync(url, post);

	if (data) {
		get_page_scroll();
		window.location.href = `/${site}/${data['market']}.${data['code']}`;
	}
}


function trend_init(cat, market_with_code, trend_act) {
	trends_index = 0;
	trends_index_new = 0;
	set_trend_act(trend_act);
	get_quote_data(cat, market_with_code);
	get_trend_data(cat, market_with_code) && create_trend();
}


function set_trend_act(trend_act) {
	const exit_element = $("#exit-action");
	const edit_element = $("#edit-action");
	const deal_element = $("#deal-action");

	if (trend_act === 'None') {
		exit_element.hide();
		edit_element.hide();
		deal_element.hide();
	} else {
		trend_act_exit = trend_act['exit'].toString();
		trend_act_edit = trend_act['edit'].toString();
		trend_act_deal = trend_act['deal'].toString();

		if (trend_act_exit === 'exit') {
			exit_element.html(icon_exit);
		} else if (trend_act_exit === 'end') {
			exit_element.html(icon_end);
		} else {
			exit_element.hide();
		}

		if (trend_act_edit === 'edit') {
			edit_element.html(icon_edit);
		} else if (trend_act_edit === 'off') {
			edit_element.html(icon_edit_off);
		} else if (trend_act_edit === 'plus') {
			edit_element.html(icon_plus);
		} else if (trend_act_edit === 'divd') {
			edit_element.html(icon_divd);
		} else {
			edit_element.hide();
		}

		if (trend_act_deal === 'deal') {
			deal_element.html(icon_deal);
		} else if (trend_act_deal === 'off') {
			deal_element.html(icon_deal_off);
		} else {
			deal_element.hide();
		}
	}
}


function get_quote_data(cat, market_with_code) {
	let url = "chart/data";
	let post = {"site": site, "cat": cat, "code": market_with_code, "func": "quote"};
	let data = ajax_sync(url, post);
	if (data) {
		set_quote_data(data);
	} else {
		layer.msg('获取报价数据失败 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function set_quote_data(data) {
    let stock = data['stock'];
    let market = data['market'];
	const deci = stock['deci'];
    const price_fields = ['sq5', 'sq4', 'sq3', 'sq2', 'sq1', 'bq1', 'bq2', 'bq3', 'bq4', 'bq5', 'pc', 'c', 'h', 'l'];
    const volume_fields = ['ss5', 'ss4', 'ss3', 'ss2', 'ss1', 'bs1', 'bs2', 'bs3', 'bs4', 'bs5'];

    for (const field of price_fields) {
        const value = stock[field];
        $(`#${field}`).html(value !== "-" ? Number(value).toFixed(deci) : "-");
    }

    for (const field of volume_fields) {
        const value = stock[field];
        $(`#${field}`).html(value !== "-" ? Number(value).toFixed(0) : "");
	}

	$("#p").html(stock['p'] !== "-" && stock['p'].toFixed(2));
	$("#pe").html(stock['pe'] !== "-" && stock['pe']);

    $("#market-name").html(market['n']);
	$("#market-price").html(market['c'] !== "-" && Number(market['c']).toFixed(2));
    $("#market-change").html(market['p'] !== "-" && (market['p'].toString() + '%'));
}


function get_trend_data(cat, market_with_code) {
	let status = true;
    const is_initial = trends_index === 0 ? '1' : '0';

	let url = "chart/data";
	let post = {"site": site, "cat": cat, "code": market_with_code, "func": "trend", "init": is_initial};
	let data = ajax_sync(url, post);
	if (data) {
		if (is_initial === '1') {
			ohlc = data['ohlc'];
			volume = data['volume'];
			trends_index = data['index'];
		}
		else {
			ohlc_new = data['ohlc']
			volume_new = data['volume'];
			trends_index_new = data['index'];
		}

		if (trends_index + trends_index_new > 0) {
			pc = data['pc'];
			high = data['high'];
			low = data['low'];
			deci = data['deci'];
			tick_itv = data['tick_itv'];
			tick_max = data['tick_max'];
			tick_min = data['tick_min'];
		}
		else {
			status = false;
		}
	} else {
		status = false;
		layer.msg('获取分时数据失败 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}

	return status;
}


function create_trend() {
	const padding_left_values = [30, 35, 40, 45, 55];
    const length_pc = pc.toFixed(deci).length;
    const padding_left = length_pc >= 5 ? padding_left_values[length_pc - 4 < 4 ? length_pc - 4 : 4] : padding_left_values[0];

	let series_ohlc = {
		type: 'spline',
		data: ohlc,
		yAxis: 1,
		lineColor: 'grey',
		keys: ['x', 'y', 'percent', 'delta']
	}
	let series_volume = {
		type: 'column',
		data: volume,
		yAxis: 2,
		color: 'grey'
	}

	function set_chart_appearance() {
		return {
			spacingRight: 0,
			spacingLeft: 0,
			spacingTop: 0,
			spacingBottom: 0,
			borderWidth: 0,
			plotBorderColor: '#ccd6eb',
			plotBorderWidth: 0
		}
	}

	function set_plot_options() {
		return {
			series: {
				states: {hover: { enabled: false }},
				animation: false,	// 全局取消动画效果
				dataGrouping: { enabled: false }
			}
		}
	}

	function set_xAxis_appearance() {
		return {
			connectNulls: true,
			type: 'datetime',
			ordinal: true
		}
	}

	function set_yAxis_appearance() {
		return [{
			height: '75%',
			lineWidth: 2,
			min: tick_min,	// 最小值
			max: tick_max,	// 最大值
			tickInterval: tick_itv,
			labels: {
				x: -2,		// 右侧偏移距离
				formatter: function () {
					let percent = ((this.value - pc) / pc * 100).toFixed(1);
					let flag = percent > 0;
					let color = flag ? 'purple' : 'gray';
					let sign = flag ? '+' : '';
					return `<span style="color: ${color}">${sign}${percent}</span>`;
				}
			}
		}, {
			height: '75%',
			linkedTo: 0,
			opposite: false,
			labels: {
				x: padding_left,	// 左侧偏移距离
				formatter: function () {
					return this.value.toFixed(deci);
				}
			}
		}, {
			top: '75%',
			height: '25%',
			offset: 0,
			lineWidth: 2,
			labels: {x: -2}
		}]
	}

	function set_tooltip_appearance() {
		return {
			enabled: true,
			backgroundColor: 'rgba(255,255,255,0.85)',	// 背景颜色
			borderColor: 'black',         				// 边框颜色
			borderRadius: 10,             				// 边框圆角
			borderWidth: 1,               				// 边框宽度
			shadow: false,                				// 是否显示阴影
			animation: false,             				// 是否启用动画效果
			split: true,
			shared: true,
			followTouchMove: false,       				// false 为单指平移，true 为双指平移
			valueDecimals: 0,
			useHTML: true,
			formatter: function () {
                const point = this.points;
                const tm = new Date(point[0].x);

                return `
                    <b>${tm.getHours().toString().padStart(2, '0')}:${tm.getMinutes().toString().padStart(2, '0')}</b>
                    <table>
                        <tr><td>成交价 ${point[0].y.toFixed(deci)}</td></tr>
                        <tr><td>涨跌额 ${point[0].point['delta'].toFixed(deci)}</td></tr>
                        <tr><td>涨跌幅 ${point[0].point['percent'].toFixed(2)}</td></tr>
                        <tr><td>成交量 ${point[1].y}</td></tr>
                    </table>
                `;
			}
		}
	}

	Highcharts.setOptions({
		global: {useUTC: false, timezone: 'Asia/Shanghai'}
	});

	trends = Highcharts.stockChart('container',{
		chart: set_chart_appearance(),
		navigator: { enabled: false },
		scrollbar: { enabled: false },
		exporting: { enabled: false },
		credits: { enabled: false },
		title: { enabled: false },
		rangeSelector: { enabled: false },
		plotOptions: set_plot_options(),
		tooltip: set_tooltip_appearance(),
		xAxis: set_xAxis_appearance(),
		yAxis: set_yAxis_appearance(),
		series: [series_ohlc, series_volume]
	});
}


function update_trend() {
	if (trends_index_new > 0) {
		let len_init = volume.length;
		let len_new = volume_new.length

		for (let i = 0; i < len_new ; i++) {
			if (trends_index < len_init){
				ohlc[trends_index] = ohlc_new[i];
				volume[trends_index] = volume_new[i];
			} else {
				ohlc.push(ohlc_new[i]);
				volume.push(volume_new[i]);
			}
			trends_index += 1;
		}
		trends_index = trends_index_new;
	} else {
		trends_index_new = trends_index;
	}

	if (trends) {
		trends.update({
			series: [{data: ohlc}, {data: volume}],
			yAxis: [{
				min: tick_min,
				max: tick_max,
				tickInterval: tick_itv
			}]
		});
	}
}


function kline_init(cat, market_with_code) {
	if (create_kline_basic(cat, market_with_code)) {
		create_kline_extra(cat, market_with_code);
	}
}


function create_kline_basic(cat, market_with_code) {
	if (get_kline_data(cat, market_with_code, 'basic')) {
		let series_ohlc = {
			//maxPointWidth: 10, //柱最大宽度
			type: 'candlestick',
			data: ohlc,
			yAxis: 0,
			color: 'gray',
			lineColor: 'gray',
			upColor: 'white',
			upLineColor: 'purple'
		};
		let series_volume = {
			type: 'column',
			data: volume,
			yAxis: 1,
			// 阻止鼠标悬停或点击交互
			enableMouseTracking: false
		};
		// tp 及 fl 用于第一时间定位纵轴坐标
		let series_tp = {
			type: 'spline',
			data: tp,
			yAxis: 0,
			enableMouseTracking: false,
			color: '#c0c0c0',
			lineWidth: 1
		};
		let series_fl = {
			type: 'spline',
			data: fl,
			yAxis: 0,
			enableMouseTracking: false,
			color: '#c0c0c0',
			lineWidth: 1
		};

		function set_chart_appearance() {
			return {
				spacingRight: 5,
				spacingLeft: 5,
				spacingTop: 0,
				spacingBottom: 0,
				borderWidth: 0,

				plotBorderColor: '#cfd1ee',
				plotBorderWidth: 1,
				events: {
					// 用于设置 volume 颜色与 ohlc 一致
					render: function () {
						set_volume_color(this.series[0], this.series[1]);
					}
				}
			}
		}

		function set_volume_color(ohlc_series, volume_series) {
			ohlc_series.points.forEach(function (ohlc_point, i) {
				let volume_point = volume_series.points[i];
				if (ohlc_point && typeof ohlc_point.close !== 'undefined') {
					let color = (ohlc_point.close >= ohlc_point.open) ? 'purple' : 'gray';
					volume_point.graphic.element.setAttribute('fill', color);
				}
			});
		}

		function set_range_selector() {
			return {
				enabled: true,
				inputEnabled: false,	// 不显示input标签选框
				buttonSpacing: 2,
				buttonPosition: {
					align: 'left',
					x: 0,
					y: 35
				},
				buttonTheme: {
					//display: 'none',	// 不显示按钮
					width: 20,
					// height: 0,
					fill: '#ffffff',	//按钮背景
					//stroke: '#000000',
					style : {
						color : "gray",	//文字样式
						fontFamily: "Arial",
						fontSize: 15
					},
					states: {
						select: {
							fill: "#ffffff",	//激活按钮样式
							//"fill-width": 1
							style: {
								color: 'black',	//激活文字样式
							}
						},
						hover: {
							fill: "#F0F0F0",
							//stroke :"gray",
							//"stroke-width": 1,
						}
					},
				},
				buttons: [{
					type: 'day',
					count: show_min,
					text: ' + '
				}, {
					type: 'day',
					count: show_std,	//屏幕显示的天数
					text: ' · '
				}, {
					type: 'day',
					count: show_max,
					text: ' − '
				}],
				selected: 1		// 默认选择域：0（缩放按钮中的第一个）、1（缩放按钮中的第二个）……
			}
		}

		function set_plot_options() {
			return {
				series: {
					// pointWidth: 5, 柱子的宽度，设置后pointPadding参数无效
					// pointPadding: 0.1, 柱子之间的距离值,默认此值为0.1
					// 去掉曲线和蜡烛上的hover事件
					states: {
						inactive: {enabled: false},
						hover: {enabled: false}
					},
					line: {
						marker: {enabled: false},
						connectNulls: true
					},
					animation: false,	// 全局取消动画效果
					dataGrouping: { enabled: false }
				}
			}
		}

		function set_tooltip_appearance() {
			return {
				enabled: true,
				backgroundColor: 'rgba(255,255,255,0.85)',	// 背景颜色
				borderColor: 'black',      	// 边框颜色
				borderRadius: 10,          	// 边框圆角
				borderWidth: 1,           	// 边框宽度
				shadow: false,             	// 是否显示阴影
				animation: false,      		// 是否启用动画效果
				split: true,
				shared: true,
				followTouchMove: false,		//false为单指平移，true为双指平移
				valueDecimals: 2,
				useHTML: true,
				formatter: function () {
					return set_tooltip_content(this.points[0].point)
				}
			}
		}

		function set_tooltip_content(point) {
			try {
				let i = point.index;
				set_ema_show(i);
				let date = date_convert(ohlc[i][0]);
				let change = ohlc[i][5];
				let html = `<b>${date}</b>
							<table>
								<tr>
									<td>收盘 ${point['close'].toFixed(deci)}</td>
									<td class="pad-left-1">开盘 ${point['open'].toFixed(deci)}</td>
								</tr>
								<tr>
									<td>最高 ${point['high'].toFixed(deci)}</td>
									<td class="pad-left-1">最低 ${point['low'].toFixed(deci)}</td>
								</tr>
								<tr>
									<td>涨幅 ${change.toFixed(2)}</td>
									<td class="pad-left-1">成交 ${(volume[i][1] / 1000).toFixed(0)}K</td>
								</tr>`;

				if (ohlc[i][6] !== null && ohlc[i][7] !== null) {
					html += `<tr>
								<td>振幅 ${ohlc[i][6].toFixed(2)}</td>
								<td class="pad-left-1">换手 ${ohlc[i][7].toFixed(2)}</td>
							</tr>`;
				}

				html += `</table>`;

				if (deal['info']) {
					let j = deal['info'].findIndex(f => f['stamp'] === ohlc[i][0]);
					if (j !== -1) {
						html += `<div class="stats-divider"></div>
									<table>`;
						let each = deal['info'][j]['deal'];
						for (let e of each) {
							html += `<tr>
										<td>${e[1] === "L" ? "买入" : "卖出"}：${e[0]} ${e[2]}*${e[3]}</td>
									</tr>`;
						}
						html += `</table>`;
					}
				}

				return html;
			} catch {
				return ''
			}

		}

		function set_xAxis_appearance() {
			return {
				type: 'date',
				ordinal: true, //X轴不显示空缺时间
				//min: Date.UTC(2018, 0, 1), //视图显示的起始日期
				max: deadline, //视图显示的终止日期
				dateTimeLabelFormats: {
					day: '%m-%d',
					week: '%m-%d',
					month: '%y-%m',
					year: '%Y'
				}
			}
		}

		function set_yAxis_appearance() {
			return [{
				labels: {
					align: 'right',
					x: -3
				},
				height: '80%',
				resize: {
					enabled: true
				},
				lineWidth: 1
			}, {
				labels: {
					align: 'right',
					x: -3
				},
				top: '80%',
				height: '20%',
				offset: 0,
				lineWidth: 1
			}]
		}

		Highcharts.setOptions({
			lang: {rangeSelectorZoom: ''},
			//需与settings中的TIME_ZONE时区一致, 默认UTC时区
			global: {useUTC: false, timezone: 'Asia/Shanghai'}
		});

		klines = Highcharts.stockChart('container', {
			chart: set_chart_appearance (),
			navigator: {enabled: false},
			scrollbar: {enabled: false},
			exporting: {enabled: false},
			credits: {enabled: false},	//去掉版权信息Highcharts.com
			rangeSelector: set_range_selector(),
			plotOptions: set_plot_options(),
			tooltip: set_tooltip_appearance(),
			xAxis: set_xAxis_appearance (),
			yAxis: set_yAxis_appearance(),
			series: [series_ohlc, series_volume, series_tp, series_fl],
		});

		return true;
	} else {
		return false;
	}
}


function create_kline_extra(cat, market_with_code) {
	if (get_kline_data(cat, market_with_code, 'extra')) {
		let series_up = {
			type: 'spline',
			data: up,
			yAxis: 0,
			enableMouseTracking: false,
			color: '#1aadce',
			lineWidth: 1
		};
		let series_av = {
			type: 'spline',
			data: av,
			yAxis: 0,
			enableMouseTracking: false,
			color: '#000000',
			lineWidth: 1
		};
		let series_lw = {
			type: 'spline',
			data: lw,
			yAxis: 0,
			enableMouseTracking: false,
			color: '#1aadce',
			lineWidth: 1
		};
		let series_ma = {
			type: 'spline',
			data: ma,
			yAxis: 0,
			enableMouseTracking: false,
			color: 'Orange',
			lineWidth: 1
		};
		let series_mv = {
			type: 'spline',
			data: mv,
			yAxis: 1,
			enableMouseTracking: false,
			color: 'black',
			lineWidth: 1
		};
		let series_buy = {
			type: 'scatter',
			data: deal['long'],
			yAxis: 0,
			enableMouseTracking: false,
			color: 'red',
			marker: {
				symbol: 'triangle',
				radius: 4
			}
		};
		let series_sell = {
			type: 'scatter',
			data: deal['short'],
			yAxis: 0,
			enableMouseTracking: false,
			color: 'green',
			marker: {
				symbol: 'triangle-down',
				radius: 4
			}
		};
		let series_dual = {
			type: 'scatter',
			data: deal['dual'],
			yAxis: 0,
			enableMouseTracking: false,
			color: 'orange',
			marker: {
				symbol: 'diamond',
				radius: 4
			}
		}

		klines.addSeries(series_av);
		klines.addSeries(series_up);
		klines.addSeries(series_lw);
		klines.addSeries(series_ma);
		klines.addSeries(series_mv);
		klines.addSeries(series_buy);
		klines.addSeries(series_sell);
		klines.addSeries(series_dual);
	}
}


function get_kline_data(cat, market_with_code, stage) {
	let status = true;
	let url = "chart/data";
	let post = {"site": site, "cat": cat, "code": market_with_code, "func": "kline", 'stage': stage, "width": frame_width};

	let data = ajax_sync(url, post);
	if (data) {
		if (stage === "basic") {
			ohlc = data['ohlc'];
			volume = data['volume'];
			tp = data['tp'];
			fl = data['fl'];

			k = data['k'];
			d = data['d'];
			deci = data['deci'];

			show_std = data['show_std'];
			show_max = data['show_max'];
			show_min = data['show_min'];

			deadline = data['deadline'];
			period = data['period'];
			right = data['right'];
		} else {
			deal = data['deal'];
			up = data['up'];
			av = data['av'];
			lw = data['lw'];
			ma = data['ma'];
			mv = data['mv'];

			set_ema_show(av.length - 1)
		}
	} else {
		status = false;
		layer.msg('获取K线数据失败 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}

	return status;
}


function set_kline_param() {
	// 为了使视觉效果好些，先隐藏，否则图标文字不全，此处显示出来
	document.getElementById("kline-param").style.display = "block";

	document.getElementById('k-value').innerHTML = k;
	document.getElementById('d-value').innerHTML = d;
	document.getElementById('right').innerHTML = right === "adj" ? icon_adj : icon_div;

    const periods = ["day", "week", "month"];
    const icons = [icon_day, icon_week, icon_month];

    for (let i = 0; i < periods.length; i++) {
        const periodElement = document.getElementById(`period-${periods[i]}`);
        periodElement.innerHTML = icons[i];
        periodElement.style.color = period === periods[i] ? "black" : "lightgray";
    }
}


function set_ema_show(i) {
	// 由于 ohlc 增加空值，每组数据仅 5 个值，因此将 percent 放前面为了触发上一层调用程序的 try 异常
	$("#percent").html(ohlc[i][5].toString() + '%');

	$("#close").html(ohlc[i][4]);
	$("#s1").html(',');
	$("#s2").html(',');
	$("#ma").html(ma[i][1] ? ma[i][1] : '-');
	$("#s3").html(',');
	$("#mv").html((mv[i][1] / 10000).toFixed(0) + 'W');

	$("#tp").html(tp[i][1]);
	$("#s4").html(',');
	$("#up").html(up[i][1]);
	$("#s5").html(',');
	$("#av").html(av[i][1]);
	$("#s6").html(',');
	$("#lw").html(lw[i][1]);
	$("#s7").html(',');
	$("#fl").html(fl[i][1]);
}


function ema_param_change(market_with_code, param, element) {
	const value_old = element.textContent;

	const range = document.createRange();
	range.selectNodeContents(element);

	const selection = window.getSelection();
	selection.removeAllRanges();
	selection.addRange(range);

	$(element).keydown(e => {
		if (e.keyCode === 13) {
			e.preventDefault();
			e.currentTarget.blur();
		}
	});

	$(element).blur(function() {
		const value_new = element.innerText;

		if (/^[0-9]+$/.test(value_new)) {
			if (value_new !== value_old && value_new > 0) {
				let data = get_chart_view(market_with_code, param, value_new);
				if (data) {
					$("#page-chart").html(data);
				}
			}
		} else {
			layer.msg('输入错误 ！', {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	});
}


function view_mode_change(market_with_code, view) {
	view = view === "kline" ? "trend" : "kline";
	let data = get_chart_view(market_with_code, 'view', view);
	if (data) {
		clearInterval(quote_itv);
		clearInterval(trend_itv);
		$("#page-chart").html(data);
	}
}


function right_change(market_with_code) {
	let data = get_chart_view(market_with_code, 'right', '');
	if (data) {
		$("#page-chart").html(data);
	}
}


function period_change(market_with_code, period) {
	let data = get_chart_view(market_with_code, 'period', period);
	if (data) {
		$("#page-chart").html(data);
	}
}


function exit_action(market_with_code) {
	let url, post, data;

	if (site === "focus/view") {
		layer.confirm('<p style="text-align:center">确定要结束关注吗？</p>', {
			title: '确认',
			btnAlign: 'c', //按钮居中
			btn: ['确定', '取消'],
			shade: 0.5 //遮罩透明度
		// 按钮1事件
		}, function () {
			layer.close(layer.index);

			url = `focus/edit/${market_with_code}`;
			post = {"func": "end"};
			data = ajax_sync(url, post);

			if (data["msg"] === "done") {
				window.location.href = `/focus/list`;
			} else if (data["msg"]) {
				layer.msg(data['msg'], {
					icon: 7,
					time: 2000
				}, function(){
				});
			} else {
				layer.msg("服务器错误 ！", {
					icon: 7,
					time: 2000
				}, function(){
				});
			}
		// 按钮2事件
		}, function () {
		});

	// else if (site === "focus/plus")
	} else{
		layer.confirm('<p style="text-align:center">确定要取消添加吗？</p>', {
			title: '确认',
			btnAlign: 'c', //按钮居中
			btn: ['确定', '取消'],
			shade: 0.5 //遮罩透明度
		// 按钮1事件
		}, function () {
			layer.close(layer.index);
			window.location.href = `/focus/list`;
		// 按钮2事件
		}, function () {
		});
	}
}


function edit_action(market_with_code) {
	if (site === "query" || site === "review/focus/view" || site === "review/trans/view") {
		window.location.href = `/focus/plus?code=${market_with_code}`;
	} else if (site === "focus/view") {
		window.location.href = `/focus/edit/${market_with_code}`;
	} else if (site === "focus/edit") {
		window.location.href = `/focus/view/${market_with_code}`;
	} else if (site === 'trans/view') {
		window.location.href = `/trans/divd/${market_with_code}`;
	}
}


function deal_action(market_with_code) {
	if (site === "focus/view" || site === "trans/view") {
		window.location.href = `/trans/deal/${market_with_code}`;
	}
}


function jump_to_link(cat, market, code) {
	localStorage.setItem('link_code', `${cat},${market},${code}`);

	if (cat === 'stock') {
		window.location.href = `/link/sector/list?code=${market}.${code}`;
	// else if (cat === 'sector')
	} else {
		window.location.href = `/link/stock/list?code=${code}`;
	}
}
