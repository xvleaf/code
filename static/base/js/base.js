let doc = document.documentElement,

	frame_width_setting_scale,
	frame_width_setting_min,
	frame_width_setting_max,

	chart_height_setting_scale,
	chart_height_setting_min,
	chart_height_setting_max,

	quote_width_setting_min,
	quote_width_setting_max,
	quote_width_setting_gap,

	// 页面渲染框架宽度，chart 宽度与 frame 宽度一致
	frame_width,
	// 页面渲染框架高度
	frame_height,
	// 页面渲染框架距离左边距离
	frame_left;


function is_mobile() {
	return !!(navigator.userAgent.match(/(phone|iPhone|ios|iPad|Android|Mobile|WebOS)/i));
}


function setting_config_changed(item, key) {
	layer.confirm('<p style="text-align:center">确定修改参数 ？</p>', {
		title: '确认',
		btnAlign: 'c', //按钮居中
		btn: ['确定', '取消'],
		shade: 0.5 //遮罩透明度
	// 按钮1事件
	}, function () {
		let path = [];
		let value;
		let mapping;

		if (item !== 'kline') {
			mapping = {
				'icp': {'path': [], 'aim': {'name': 'icp-name', 'url': 'icp-url'}},
				'viewport': {'path': [], 'aim': {'fit': 'viewport-fit'}},
				'frame': {
					'path': ['frame-screen', 'frame-device'],
					'aim': {'scale': 'frame-scale', 'min': 'frame-min', 'max': 'frame-max'}
				},
				'chart': {
					'path': ['chart-screen', 'chart-device'],
					'aim': {'scale': 'chart-scale', 'min': 'chart-min', 'max': 'chart-max'}
				},
				'quote': {
					'path':['quote-device'],
					'aim': {'min': 'quote-min', 'max': 'quote-max'}
				},
				'view': {
					'path': [],
					'aim': {
						'focus': 'view-focus', 'fund': 'view-fund', 'sector': 'view-sector',
						'filter': 'view-filter', 'trans': 'view-trans', 'review': 'view-review', 'query': 'view-query'
					}
				},
				'page': {
					'path': [],
					'aim': {
						'fund': 'page-fund:int', 'sector': 'page-sector:int',
						'filter': 'page-filter:int', 'review': 'page-review:int'
					}
				},
				'time': {
					'path': [],
					'aim': {
						'auction': 'time-auction', 'open': 'time-open', 'break': 'time-break',
						'resume': 'time-resume', 'close': 'time-close'
					}
				},
				'cache': {
					'path': [],
					'aim': {'day': 'cache-day:int', 'long': 'cache-long:int', 'short': 'cache-short:int'}
				},
				'refresh': {
					'path': [],
					'aim': {'interval': 'refresh-interval:int'}
				},
				'stats': {
					'path': [],
					'aim': {'range': 'stats-range:int'}
				},
				'fee': {
					'path': ['fee-market', 'fee-type', 'fee-intent'],
					'aim': {
						'stamp': 'fee-stamp:float', 'trans': 'fee-trans:float',
						'commi-rate': 'commi-rate:float', 'commi-min': 'commi-min:float'
					}
				},
			}
		} else {
			if (key.includes('ema-')) {
				mapping = {
					'kline': {
						'path': ['ema-period'],
						'aim': {'ema-k': 'ema-k', 'ema-d': 'ema-d'}
					}
				}
			}
			else if (key.includes('ma-')) {
				mapping = {
					'kline': {
						'path': ['ma-period'],
						'aim': {'ma-a': 'ma-a', 'ma-v': 'ma-v'}
					}
				}
			// else if (key.includes('density')
			// || key.includes('start')
			// || key.includes('end')
			// || key === 'right'
			// || key === 'period')
			} else {
				mapping = {
					'kline': {
						'path': [],
						'aim': {
							'density-std': 'density-std', 'density-min': 'density-min', 'density-max': 'density-max',
							'start-day': 'start-day', 'start-week': 'start-week', 'start-month': 'start-month',
							'end-day': 'end-day', 'end-week': 'end-week', 'end-month': 'end-month',
							'right': 'kline-right', 'period': 'kline-period'
						}
					}
				}
			}
		}

		let element = mapping[item]['aim'][key]
		if (element.includes(':int') || element.includes(':float')) {
			let elements = element.split(':')
			value = document.getElementById(elements[0]).value + ':' + elements[1];
		} else {
			value = document.getElementById(element).value;
		}

		if (key.includes('ema-') || key.includes('ma-')) {
			let keys = key.split('-')
			path.push(keys[0])
			path.push(document.getElementById(mapping[item]['path'][0]).value);
			path.push(keys[1])
		} else {
			for (let each of mapping[item]['path']) {
				path.push(document.getElementById(each).value);
			}
			path.push(...key.split('-'));
		}

		let url = `setting?r=${random()}`;
		let post = {"func": "set", 'item': item, 'path': JSON.stringify(path), 'value': value};

		let data = ajax_sync(url, post);
		if (data) {
			if (data['msg'] === 'done') {
				if (item === 'frame' || item === 'chart' || item === 'quote') {
					localStorage.removeItem('size');
					if (item === 'frame') {
						window.location.href = `/setting`;
					}
				}

				layer.msg('参数修改完成 ！', {
					icon: 7,
					time: 2000
				}, function(){
				});
			} else {
				layer.msg(data['msg'], {
					icon: 7,
					time: 2000
				}, function(){
				});
			}
		} else {
			layer.msg('服务器错误 ！', {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	// 按钮2事件
	}, function () {
	});
}


function get_setting_config(item, key) {
	let values;
	if (item === 'frame') {
		values = {'screen': $("#frame-screen").val(), 'device': $("#frame-device").val()};
	} else if (item === 'chart') {
		values = {'screen': $("#chart-screen").val(), 'device': $("#chart-device").val()};
	} else if (item === 'quote') {
		values = {'device': $("#quote-device").val()};
	} else if (item === 'kline') {
		if (key === 'ema-period') {
			values = {'ema-period': $("#ema-period").val()};
		} else {
			values = {'ma-period': $("#ma-period").val()};
		}
	// else if (item === 'fee')
	} else {
		values = {'market': $("#fee-market").val(), 'type': $("#fee-type").val(), 'intent': $("#fee-intent").val()};
	}

	let url = `setting?r=${random()}`;
	let post = {"func": "get", 'item': item, 'key': key, 'values': JSON.stringify(values)};
	let data = ajax_sync(url, post);

	if (data) {
		if (item === 'frame') {
			$("#frame-scale").val(data[item]['scale']);
			$("#frame-min").val(data[item]['min']);
			$("#frame-max").val(data[item]['max']);
		} else if (item === 'chart') {
			$("#chart-scale").val(data[item]['scale']);
			$("#chart-min").val(data[item]['min']);
			$("#chart-max").val(data[item]['max']);
		} else if (item === 'quote') {
			$("#quote-min").val(data[item]['min']);
			$("#quote-max").val(data[item]['max']);
		} else if (item === 'kline') {
			if (key === 'ema-period') {
				$("#ema-k").val(data[item]['ema']['k']);
				$("#ema-d").val(data[item]['ema']['d']);
			} else {
				$("#ma-a").val(data[item]['ma']['a']);
				$("#ma-v").val(data[item]['ma']['v']);
			}
		// else if (item === 'fee')
		} else {
			$("#fee-stamp").val(data[item]['stamp']);
			$("#fee-trans").val(data[item]['trans']);
			$("#commi-rate").val(data[item]['commi']['rate']);
			$("#commi-min").val(data[item]['commi']['min']);
		}
	} else {
		layer.msg('服务器错误 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function get_icp_config() {
	let url = 'icp';
	let post = {'query': 'icp'};
	return ajax_sync(url, post);
}


function get_size_config(screen) {
	let url = `setting?r=${random()}`;
	let post = {"func": "get", 'query': 'size'};
	let data = ajax_sync(url, post);

	const device = is_mobile() ? 'mb' : 'pc';
	const frame_width_setting = data['frame'];
	const chart_height_setting = data['chart'];
	const quote_width_setting = data['quote'];
	const frame_width_settings = frame_width_setting[screen === "full" ? 'full' : 'norm'][device];
	const chart_height_settings = chart_height_setting[screen === "full" ? 'full' : 'norm'][device];
	frame_width_setting_scale = parseFloat(frame_width_settings['scale']);
	frame_width_setting_min = parseInt(frame_width_settings['min']);
	frame_width_setting_max = parseInt(frame_width_settings['max']);

	chart_height_setting_scale = parseFloat(chart_height_settings['scale']);
	chart_height_setting_min = parseInt(chart_height_settings['min']);
	chart_height_setting_max = parseInt(chart_height_settings['max']);

	quote_width_setting_min = parseFloat(quote_width_setting[device]['min']) * 100;
	quote_width_setting_max = parseFloat(quote_width_setting[device]['max']) * 100;
	quote_width_setting_gap = quote_width_setting_max - quote_width_setting_min;
}


function set_frame_size() {
	let body_width = window.innerWidth;
	let calc_frame_width = Math.round(body_width * frame_width_setting_scale);
	if (calc_frame_width > frame_width_setting_max){
		frame_width = frame_width_setting_max;
	} else if (calc_frame_width < frame_width_setting_min){
		if (body_width > frame_width_setting_min){
			frame_width = frame_width_setting_min;
		} else {
			frame_width = body_width;
		}
	} else {
		frame_width = calc_frame_width;
	}
	frame_left = Math.round((body_width - frame_width) / 2);
	frame_height = window.innerHeight;

	doc.style.setProperty("--frame-width", frame_width + "px");
	doc.style.setProperty("--frame-height", frame_height + "px");
	doc.style.setProperty("--frame-left", frame_left + "px");
}


function set_local_storage() {
	let setting = frame_width_setting_scale.toString() + ','
				+ frame_width_setting_min.toString() + ','
				+ frame_width_setting_max.toString() + ','
		 		+ chart_height_setting_scale.toString() + ','
				+ chart_height_setting_min.toString() + ','
				+ chart_height_setting_max.toString() + ','
				+ quote_width_setting_min.toString() + ','
				+ quote_width_setting_max.toString() + ','
				+ quote_width_setting_gap.toString() + ','
				+ frame_width.toString() + ','
				+ frame_height.toString() + ','
				+ frame_left.toString();
	localStorage.setItem("size", setting);
}


function get_local_storage() {
	let settings = localStorage.getItem("size").split(',')

    frame_width_setting_scale = parseFloat(settings[0]);
    frame_width_setting_min = parseInt(settings[1]);
    frame_width_setting_max = parseInt(settings[2]);

    chart_height_setting_scale = parseFloat(settings[3]);
    chart_height_setting_min = parseInt(settings[4]);
    chart_height_setting_max = parseInt(settings[5]);

    quote_width_setting_min = parseFloat(settings[6]);
    quote_width_setting_max = parseFloat(settings[7]);
    quote_width_setting_gap = parseFloat(settings[8]);

	frame_width = parseInt(settings[9]);
	frame_left = parseInt(settings[10]);
	frame_height = parseInt(settings[11]);
}


function ajax_sync(url, post) {
	let get;

	$.ajax({
		cache: false,
		type: "POST",
		url: `/${url}?r=${random()}`,
		data: post,
		dateType: "json",
		async: false,
		beforeSend: function(xhr){
			xhr.setRequestHeader("X-CSRFToken", csrf_token);
		},
		success: function(data) {
			get = data;
		},
		error: function () {
			get = null;
		}
	});

	return get;
}


function date_convert(timestamp) {
	let date = new Date(timestamp);
    let year = date.getFullYear();
    let month = ('0' + (date.getMonth() + 1)).slice(-2);
    let day = ('0' + date.getDate()).slice(-2);
    return year + '-' + month + '-' + day;
}


function value_with_deci(value, deci) {
	if (value) {
		value = Number(value).toFixed(deci)
	}
	return value
}


function random() {
    return new Date().getTime().toString();
}
