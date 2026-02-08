function overall_value_changed(type) {
	layer.confirm('<p style="text-align:center">请确认是否修改？</p>', {
		title: '确认',
		btnAlign: 'c', //按钮居中
		btn: ['确定', '取消'],
		shade: 0.5 //遮罩透明度
	// 按钮1事件
	}, function () {
		layer.close(layer.index);

		let value = $(`#${type}`).val();
		let url = `overall`;
		let post = {'func': type, 'value': value};
		let data = ajax_sync(url, post);
		if (data['msg'] === 'done') {
			window.location.href = `/overall`;
		} else {
			layer.msg(data['msg'], {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
		// 按钮2事件
	}, function () {
	});
}


function update_stock_list() {
	let url, post, data;
	url = `${site}`;
	post = {"func": "update"};
	data = ajax_sync(url, post);

	if (data) {
		for (let {code, name, close, change} of data) {
			let deci = parseInt(document.getElementById(`deci-${code}`).innerText);
			document.getElementById(`name-${code}`).innerText = name;
			document.getElementById(`close-${code}`).innerText = value_with_deci(close, deci);
			document.getElementById(`change-${code}`).innerText = value_with_deci(change, 2);
		}
	} else {
		layer.msg('获取数据失败 ！', {
			icon: 7,
			time: 2000 //2秒关闭，若不配置默认3秒
		}, function(){
		});
	}
}


function focus_code_change() {
	let code = $("#code").val()
	if (code) {
		let url, post, data;
		url = `focus/plus`;
		post = {"func": "plus", "code": code}
		data = ajax_sync(url, post);
		if (data) {
			if (data['msg']) {
				layer.msg(data['msg'], {
					icon: 7,
					time: 2000 //2秒关闭，若不配置默认3秒
				}, function(){
				});
			} else {
				window.location.href = `/focus/plus?code=${data['market']}.${data['code']}`;
			}
		}
	}
}


function calc_permit_chance(code) {
	let url, post, data;
	let intent = $("#intent").val(),
		price = $("#price").val(),
		target = $("#target").val(),
		stop = $("#stop").val();

	if (Number(price) > 0 && Number(target) > 0 && Number(stop) > 0){
		if (!code) {
			code = $("#code").val()
		}

		let site_mapping = {
			"focus/edit": "focus/edit",
			"focus/plus": "focus/edit",
			"trans/deal": "trans/deal"
		}

		url = `${site_mapping[site]}/${code}`;
		post = {"func": "calc", "intent": intent, "price": price, "target": target, "stop": stop}
		data = ajax_sync(url, post);

		if (data['msg'] === 'done') {
			$("#permit").val(data['permit']);
			$("#chance").val(data['chance']);
			$("#permit, #chance, #price, #target, #stop").css("color", "#206bc4");

			let qty_element = $("#qty")
			qty_element.css("color", Number(qty_element.val()) <= Number(data['permit']) ? "#206bc4" : "orange");
		} else if (data["msg"]) {
			$("#target, #stop, #chance, #permit").css("color", "orange");

			layer.msg(data['msg'], {
				icon: 7,
				time: 2000 //2秒关闭，若不配置默认3秒
			}, function(){
			});
		} else {
			layer.msg("服务器错误 ！", {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	}
}


function focus_cancel(code){
	if (code) {
		window.location.href = `/focus/view/${code}`;
	} else {
		window.location.href = `/focus/list`;
	}
}


function focus_submit(kind, code) {
	let url, post, data;
	let priority = $("#priority").val(),
		price = $("#price").val(),
		target = $("#target").val(),
		stop = $("#stop").val(),
		qty = $("#qty").val();

	if (Number(priority) === 999) {
		layer.msg("关注顺序有误 ！", {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
	else if (Number(priority) > 0 && Number(price) > 0 && Number(target) > 0 && Number(stop) > 0 && Number(qty) >= 0) {
		tinymce.activeEditor.save();

		let date = $("#date").val(),
			under = $("#under").val(),
			type = $("#type").val(),
			settle = $("#settle").val(),
			intent = $("#intent").val(),
			chance = $("#chance").val(),
			comments = $("#comments").val();

		if (!code) {
			code = $("#code").val()
		}
		url = `focus/edit/${code}`;
		post = {
			"func": "submit",
			'kind': kind,
			"date": date,
			'under': under,
			'type': type,
			"priority": priority,
			"settle": settle,
			"intent": intent,
			"price": price,
			"target": target,
			"stop": stop,
			"qty": qty,
			"chance": chance,
			"comments": comments
		}

		data = ajax_sync(url, post);

		if (data['msg'] === 'done') {
			window.location.href = `/focus/view/${data['market']}.${data['code']}`;
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
	}
	else {
		layer.msg('内容填写错误 ！', {
			icon: 7,
			time: 2000 //2秒关闭，若不配置默认3秒
		}, function(){
		});
	}
}


function priority_change(market_with_code) {
	layer.confirm('<p style="text-align:center">确定修改吗？</p>', {
		title: '确认',
		btnAlign: 'c', //按钮居中
		btn: ['确定', '取消'],
		shade: 0.5 //遮罩透明度
	// 按钮1事件
	}, function () {
		layer.close(layer.index);

		let url = `focus/view/${market_with_code}`;
		let post = {"func": 'priority', "value": $("#priority").val()}
		let data = ajax_sync(url, post);
		if (data) {
			$('#priority').val(data['priority']);

			layer.msg(data['msg'], {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	// 按钮2事件
	}, function () {
	});
}


function filter_type_select() {
	let filter_type = document.getElementById('filter-type').value;
	let url, post, data;
	url = `filter/list`;
	post = {"func": 'type', "type": filter_type};
	data = ajax_sync(url, post);
	if (data) {
		window.location.href = `/filter/list`;
	} else {
		layer.msg('服务器错误 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function filter_set_select() {
	let filter_set = document.getElementById('filter-set').value;
	let url, post, data;
	url = `filter/refer`;
	post = {"func": 'set', "set": filter_set};
	data = ajax_sync(url, post);
	if (data) {
		window.location.href = `/filter/refer`;
	} else {
		layer.msg('服务器错误 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function filter_config(func) {
	let todo = true;
	let value;
	if (func === 'display') {
		value = document.getElementById('display-config').value
		if (parseInt(value) < 1) {
			todo = false;
			layer.msg('数据填写错误 ！', {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	} else if (func === 'start') {
		let value_day = document.getElementById(`${func}-day-config`).value;
		let value_week = document.getElementById(`${func}-week-config`).value;
		let value_month = document.getElementById(`${func}-month-config`).value;
		value = JSON.stringify({"day": value_day, "week": value_week, "month": value_month});
	}
	else {
		value = document.getElementById(`${func}-config`).value
	}

	if (todo) {
		let url, post, data;
		url = `filter/config`;
		post = {"func": func, "value": value};
		data = ajax_sync(url, post);

		if (data) {
			layer.msg( data['msg'] === 'done' ? '操作完成 ！' : data['msg'], {
				icon: 7,
				time: 499
			}, function(){
				window.location.href = `/filter/config`;
			});
		} else {
			layer.msg('服务器错误 ！', {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	}
}


function filter_config_range(checkbox) {
	layer.confirm('<p style="text-align:center">确定更改选股集合吗？</p>', {
		title: '确认',
		btnAlign: 'c', //按钮居中
		btn: ['确定', '取消'],
		shade: 0.5 //遮罩透明度
	// 按钮1事件
	}, function () {
		layer.close(layer.index);
		let index = checkbox.id.split('-')[1]
		let url, post, data;
		url = `filter/config`;
		post = {"func": "range", "index": index, "select": checkbox.checked? '1' : '0'};
		data = ajax_sync(url, post);

		if (data) {
			layer.msg( data['msg'] === 'done' ? '操作完成 ！' : data['msg'], {
				icon: 7,
				time: 500
			}, function(){
				window.location.href = `/filter/config`;
			});
		} else {
			layer.msg('服务器错误 ！', {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	// 按钮2事件
	}, function () {
		checkbox.checked = !checkbox.checked;
	});
}


function filter_config_handle(kind, status) {
	let msg;
	if (kind === 'base' && status === 1) {
		msg = "确定刷新数据吗？";
	} else {
		msg = "确定删除记录吗？";
	}

	layer.confirm(`<p style="text-align:center">${msg}</p>`, {
		title: '确认',
		btnAlign: 'c', //按钮居中
		btn: ['确定', '取消'],
		shade: 0.5 //遮罩透明度
	// 按钮1事件
	}, function () {
		let url, post, data;
		url = `filter/config`;
		post = {"func": 'handle', "kind": kind};
		data = ajax_sync(url, post);

		if (data) {
			layer.msg( data['msg'] === 'done' ? '操作完成 ！' : data['msg'], {
				icon: 7,
				time: 501
			}, function(){
				window.location.href = `/filter/config`;
			});
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


function filter_mapping(req) {
	let mapping;

	if (req === 'cat') {
		let cat_p = {
			"right": {"value": "right"},
			"cat-em": {"show": false},
			"cat-pv": {"show": true},
			"exist": {"value": "exist"},
			"range": {"value": "range"},
			"period": {"value": "period"},
			"filter-em": {"show": false},
			"filter-pv": {"show": true},
			// cat-pv 显示
			"adjust": {"value": "adjust"},
			"gap": {"value": "gap"},
			"pv-link": {"value": "link"},
			"price-filter": {"show": true, "value": "filter"},
			"volume-filter": {"show": false}
		};

		let cat_v = {
			"right": {"value": "right"},
			"cat-em": {"show": false},
			"cat-pv": {"show": true},
			"exist": {"value": "exist"},
			"range": {"value": "range"},
			"period": {"value": "period"},
			"filter-em": {"show": false},
			"filter-pv": {"show": true},
			// cat-pv 显示
			"adjust": {"value": "adjust"},
			"gap": {"value": "gap"},
			"pv-link": {"value": "link"},
			"price-filter": {"show": false},
			"volume-filter": {"show": true, "value": "filter"}
		};

		let cat_e = {
			"right": {"value": "right"},
			"cat-em": {"show": true},
			"cat-pv": {"show": false},
			"exist": {"value": "exist"},
			"range": {"value": "range"},
			"period": {"value": "period"},
			"filter-em": {"show": true},
			"filter-pv": {"show": false},
			// cat-em 显示
			"k1-label": {"show": true},
			"k1-value": {"show": true, "value": "k1"},
			"em-split": {"show": true},
			"d1-value": {"show": true, "value": "d1"},
			"em-link": {"value": "link"}
		};

		let cat_m = {
			"right": {"value": "right"},
			"cat-em": {"show": true},
			"cat-pv": {"show": false},
			"exist": {"value": "exist"},
			"range": {"value": "range"},
			"period": {"value": "period"},
			"filter-em": {"show": true},
			"filter-pv": {"show": false},
			// cat-em 显示
			"k1-label": {"show": false},
			"k1-value": {"show": false},
			"em-split": {"show": false},
			"d1-value": {"show": true, "value": "d1"},
			"em-link": {"value": "link"}
		};

		mapping = {
			'cat-P': cat_p,
			'cat-V': cat_v,
			'cat-E': cat_e,
			'cat-M': cat_m
		};
	} else if (req === 'link') {
		let em_link_ls = {
			"link-ls": {"show": true, "value": "filter"},
			"link-b": {"show": false}
		};

		let em_link_b = {
			"link-ls": {"show": false},
			"link-b": {"show": true},
			"link-b-value": {"value": "set"}
		};

		mapping = {
			'em-link-L': em_link_ls,
			'em-link-S': em_link_ls,
			'em-link-B': em_link_b
		};
	// else if (req === 'filter')
	} else {
		let pv_filter_e = {
			"option-pa": {"show": false},
			"option-em": {"show": true},
			// "set-value": {"show": false},
			// "set-label": {"show": false},
			"cat-pv": {"show": true},
			"k2-label": {"show": true},
			"k2-value": {"show": true, "value": "k2"},
			"option-split-1": {"show": true},
			"d2-value": {"show": true, "value": "d2"},
			"option-split-2": {"show": true},
			"curve-select": {"show": true, "value": "curve"}
		};

		let pv_filter_m = {
			"option-pa": {"show": false},
			"option-em": {"show": true},
			// "set-value": {"show": false},
			// "set-label": {"show": false},
			"cat-pv": {"show": true},
			"k2-label": {"show": false},
			"k2-value": {"show": false},
			"option-split-1": {"show": false},
			"d2-value": {"show": true, "value": "d2"},
			"option-split-2": {"show": false},
			"curve-select": {"show": false}
		};

		let pv_filter_a = {
			"option-pa": {"show": true},
			"option-em": {"show": false},
			"set-value": {"value": 'set'},
			"set-label": {"show": true},
			// 条件为振幅时，不需要考虑 gap
			"cat-pv": {"show": false},
			// "k2-label": {"show": false},
			// "k2-value": {"show": false},
			// "option-split-1": {"show": false},
			// "d2-value": {"show": false},
			// "option-split-2": {"show": false},
			// "curve-select": {"show": false}
		};

		let pv_filter_p = {
			"option-pa": {"show": true},
			"option-em": {"show": false},
			"set-value": {"value": 'set'},
			"set-label": {"show": false},
			"cat-pv": {"show": true}
			// "k2-label": {"show": false},
			// "k2-value": {"show": false},
			// "option-split-1": {"show": false},
			// "d2-value": {"show": false},
			// "option-split-2": {"show": false},
			// "curve-select": {"show": false}
		};

		mapping = {
			'pv-filter-E': pv_filter_e,
			'pv-filter-M': pv_filter_m,
			'pv-filter-A': pv_filter_a,
			'pv-filter-P': pv_filter_p
		};
	}

	return mapping;
}


function filter_changed(index, type, defaults) {
	if (type === 'cat') {
		let cat_mapping = filter_mapping('cat');
		let cat_value = document.getElementById('cat-' + index).value;
		let cat_selected = cat_mapping['cat-' + cat_value];
		filter_set_element(index, cat_selected, defaults);

		if (cat_value === 'E' || cat_value === 'M') {
			let em_link_mapping = filter_mapping('link');
			let em_link_default_value = defaults['link'];
			let em_link_selected = em_link_mapping['em-link-' + em_link_default_value];
			filter_set_element(index, em_link_selected, defaults);
		// else if (cat_value === 'P' || cat_value === 'V')
		} else {
			let pv_filter_mapping = filter_mapping('filter');
			let filter_value, filter_element;
			if (cat_selected['price-filter'].hasOwnProperty('value')) {
				filter_value = 'E'
				filter_element = document.getElementById('price-filter-' + index);
			} else {
				filter_value = 'M'
				filter_element = document.getElementById('volume-filter-' + index);
			}
			filter_element.value = filter_value
			filter_element.classList.add('filter-select');
			let pv_filter_selected = pv_filter_mapping['pv-filter-' + filter_value]
			filter_set_element(index, pv_filter_selected, defaults);
		}
	} else if (type === 'em-link') {
		let em_link_mapping = filter_mapping('link');
		let em_link_value = document.getElementById('em-link-' + index).value;
		let em_link_selected = em_link_mapping['em-link-' + em_link_value];
		filter_set_element(index, em_link_selected, defaults);
	} else if (type === 'filter-p') {
		let pv_filter_mapping = filter_mapping('filter');
		let filter_value;
		filter_value = document.getElementById('price-filter-' + index).value;
		let pv_filter_selected = pv_filter_mapping['pv-filter-' + filter_value]
		filter_set_element(index, pv_filter_selected, defaults);
	// else if (type === 'filter-v')
	}  else {
		let pv_filter_mapping = filter_mapping('filter');
		let filter_value;
		filter_value = document.getElementById('volume-filter-' + index).value;
		let pv_filter_selected = pv_filter_mapping['pv-filter-' + filter_value]
		filter_set_element(index, pv_filter_selected, defaults);
	}
}


function filter_set_element(index, mapping, defaults) {
	for (let key in mapping) {
		let element = document.getElementById(key + '-' + index)
		let feature = mapping[key];
		if (feature.hasOwnProperty('value')) {
			element.classList.remove('disp-none');
			element.classList.add('disp-flex-left');
			element.value = defaults[feature['value']]
		} else if (feature.hasOwnProperty('show') && feature['show']) {
			element.classList.remove('disp-none');
			element.classList.add('disp-flex-left');
		} else {
			element.classList.remove('disp-flex-left');
			element.classList.add('disp-none');
		}
	}
}


function filter_get_values(func, index, count) {
	let data = [];

	for (let i = 0; i < count; i++) {
		if (func !== "del" || (func === "del" && i !== index)) {
			let cat_value = document.getElementById('cat-' + i).value;
			let cat_mapping = filter_mapping('cat');
			let each = {'index': i <= index ? i : i - 1, 'cat': cat_value};
			let cat_mapping_selected = cat_mapping['cat-' + cat_value]
			for (let key in cat_mapping_selected) {
				let element_value = document.getElementById(key + '-' + i).value
				let feature = cat_mapping_selected[key];
				if (feature.hasOwnProperty('value')) {
					each = Object.assign(each, {[feature['value']]: element_value})
				}
			}

			if (cat_mapping_selected.hasOwnProperty('em-link')) {
				let em_link_value = document.getElementById('em-link-' + i).value;
				let em_link_mapping = filter_mapping('link');
				let em_link_mapping_selected = em_link_mapping['em-link-' + em_link_value]
				for (let key in em_link_mapping_selected) {
					let element_value = document.getElementById(key + '-' + i).value
					let feature = em_link_mapping_selected[key];
					if (feature.hasOwnProperty('value')) {
						each = Object.assign(each, {[feature['value']]: element_value})
					}
				}
			} else {
				let pv_filter_value;
				if (cat_mapping_selected['price-filter'].hasOwnProperty('value')) {
					pv_filter_value = document.getElementById('price-filter-' + i).value;
				} else {
					pv_filter_value = document.getElementById('volume-filter-' + i).value;
				}

				let pv_filter_mapping = filter_mapping('filter');
				let pv_filter_mapping_selected = pv_filter_mapping['pv-filter-' + pv_filter_value]
				for (let key in pv_filter_mapping_selected) {
					let element_value = document.getElementById(key + '-' + i).value
					let feature = pv_filter_mapping_selected[key];
					if (feature.hasOwnProperty('value')) {
						each = Object.assign(each, {[feature['value']]: element_value})
					}
				}
			}

			data.push(each);
		}
	}

	return data;
}


function filter_pick_up(type) {
	let url, post, data;
	url = `filter/list`;
	post = {"func": "pick", "type": type};
	data = ajax_sync(url, post);
	if (data['msg'] === 'done') {
		window.location.href = `/filter/list`;
	} else {
		layer.msg(data['msg'] ? data['msg'] : '服务器错误 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function filter_run_func (func, index, count) {
	let criteria = JSON.stringify(filter_get_values(func, index, count));
	let url, post, data;
	url = `filter/run`;
	post = {"func": func, "criteria": criteria};
	data = ajax_sync(url, post);
	if (data['msg'] === 'done') {
		window.location.href = `/filter/run`;
	} else {
		layer.msg(data['msg'] ? data['msg'] : '服务器错误 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function filter_run_submit (count) {
	let criteria_list = filter_get_values('run', count, count)
	let to_submit = true;

	for (let i = 0; i < criteria_list.length; i++) {
		if (criteria_list[i]['cat'] === "V" && criteria_list[i]['filter'] === "A" && parseInt(criteria_list[i]['range']) <= 1) {
			to_submit = false;
		} else if (criteria_list[i]['cat'] === "E" && parseInt(criteria_list[i]['range']) <= 1) {
			to_submit = false;
		} else if (criteria_list[i]['cat'] === "M" && parseInt(criteria_list[i]['range']) <= 1) {
			to_submit = false;
		}

		if (!to_submit) {
			layer.msg('周期数需大于1 ！', {
				icon: 7,
				time: 2000
			}, function(){
			});

			break;
		}
	}

	if(to_submit) {
		layer.confirm('<p style="text-align:center">确定提交吗？</p>', {
			title: '确认',
			btnAlign: 'c', //按钮居中
			btn: ['确定', '取消'],
			shade: 0.5 //遮罩透明度
		// 按钮1事件
		}, function () {
			layer.close(layer.index);
			let criteria = JSON.stringify(criteria_list);
			let url, post, data;
			url = `filter/run`;
			post = {"func": 'run', "criteria": criteria};
			data = ajax_sync(url, post);
			if (data['msg'] === 'done') {
				layer.msg('已提交服务器 ！', {
					icon: 7,
					time: 2000
				}, function(){
					location.reload();
				});
			} else {
				layer.msg(data['msg'] ? data['msg'] : '服务器错误 ！', {
					icon: 7,
					time: 2000
				}, function(){
					if (data['refresh']) {
						location.reload();
					}
				});
			}
		// 按钮2事件
		}, function () {
		});
	}
}


function fund_list_order(order_prev, order_new) {
	if (order_new === "code") {
		if (order_prev === "code-asc") {
			order_new = "code-desc";
		} else {
			order_new = "code-asc"
		}
		window.location.href = `/fund/list?order=${order_new}`;
	} else if (order_new === "change") {
		if (order_prev === "change-desc") {
			order_new = "change-asc";
		} else {
			order_new = "change-desc"
		}
		window.location.href = `/fund/list?order=${order_new}`;
	} else if (order_new === "mark") {
		if (order_prev === "mark") {
			order_new = "code-asc";
		} else {
			order_new = "mark"
		}
		window.location.href = `/fund/list?order=${order_new}`;
	} else if (order_new === "cap") {
		if (order_prev === "cap-desc") {
			order_new = "cap-asc";
		} else {
			order_new = "cap-desc"
		}
		window.location.href = `/fund/list?order=${order_new}`;
	}
}


function fund_list_update() {
	let url, post, data;
	url = `fund/list`;
	post = {"func": "update"};
	data = ajax_sync(url, post);
	if (data) {
		for (let {code, price, change, cap} of data) {
			document.getElementById(`price-${code}`).innerText = value_with_deci(price, 3);
			document.getElementById(`change-${code}`).innerText = value_with_deci(change, 2);
			if (cap) {
				document.getElementById(`cap-${code}`).innerText = cap;
			}
		}
	} else {
		layer.msg('获取数据失败 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function sector_list_order (order_prev, order_new) {
	if (order_new === "code") {
		if (order_prev === "code-asc") {
			order_new = "code-desc";
		} else {
			order_new = "code-asc"
		}
		window.location.href = `/sector/list?order=${order_new}`;
	} else if (order_new === "change") {
		if (order_prev === "change-desc") {
			order_new = "change-asc";
		} else {
			order_new = "change-desc"
		}
		window.location.href = `/sector/list?order=${order_new}`;
	} else if (order_new === "mark") {
		if (order_prev === "mark") {
			order_new = "code-asc";
		} else {
			order_new = "mark"
		}
		window.location.href = `/sector/list?order=${order_new}`;
	} else if (order_new === "rise") {
		if (order_prev !== "rise") {
			window.location.href = `/sector/list?order=${order_new}`;
		}
	} else if (order_new === "fall") {
		if (order_prev !== "fall") {
			window.location.href = `/sector/list?order=${order_new}`;
		}
	}
}


function sector_list_update() {
	let url, post, data;
	url = site;
	post = {"func": "update"};
	data = ajax_sync(url, post);
	if (data) {
		for (let {code, change, rise, fall} of data) {
			document.getElementById(`change-${code}`).innerText = change;
			document.getElementById(`rise-${code}`).innerText = rise;
			document.getElementById(`fall-${code}`).innerText = fall;
		}
	} else {
		layer.msg('获取数据失败 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function fund_list_refresh() {
	const fund_type_element = document.getElementById('fund-type');
	let fund_type = fund_type_element.value
	let url, post, data;
	url = `fund/list`;
	post = {"func": "refresh", 'type': fund_type};
	data = ajax_sync(url, post);

	if (data) {
		window.location.href = `/fund/list`;
	} else {
		layer.msg('获取数据失败 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function sector_list_refresh() {
	let url, post, data;
	url = `sector/list`;
	post = {"func": "refresh"};
	data = ajax_sync(url, post);

	if (data) {
		window.location.href = `/sector/list`;
	} else {
		layer.msg('获取数据失败 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function fund_type_select() {
	let fund_type = $("#fund-type").val();
	let url, post, data;
	url = `fund/list`;
	post = {"func": "type", "type": fund_type};
	data = ajax_sync(url, post);
	if (data) {
		window.location.href = `/fund/list`;
	} else {
		layer.msg('服务器错误 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function list_page_action(func, direction, value, order_type) {
	let page_number, page;
	if (func === "click") {
		if (direction === "prev") {
			page_number = parseInt(value) - 1;
		} else {
			page_number = parseInt(value) + 1;
		}
	} else {
		page_number = value
	}

	if (site === 'link/sector/list' || site === 'link/stock/list') {
		let link_code = localStorage.getItem('link_code').split(',');
		let cat_convert = link_code[0] === 'sector' ? 'stock' : 'sector';
		let market = link_code[1];
		let code = link_code[2];
		if (site.includes(cat_convert)) {
			code = site === 'link/sector/list' ? `${market}.${code}` : `${code}`;
			page = parseInt(page_number) === 1 ? '' : `&page=${page_number}`
			window.location.href = `/${site}?code=${code}${page}`;
		} else {
			layer.msg('数据错误 ！', {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	} else {
		if (window.location.href.includes("order")) {
			page = parseInt(page_number) === 1 ? '' : `&page=${page_number}`
			window.location.href = `/${site}?order=${order_type}${page}`;
		} else {
			page = page_number === 1 ? '' : `?page=${page_number}`
			window.location.href = `/${site}${page}`;
		}
	}
}


function list_page_listen (pageNumberDiv, page_total, order_type) {
	const value_old = pageNumberDiv.textContent;

	const range = document.createRange();
	range.selectNodeContents(pageNumberDiv);

	const selection = window.getSelection();
	selection.removeAllRanges();
	selection.addRange(range);

	$(pageNumberDiv).keydown(e => {
		if (e.keyCode === 13) {
			e.preventDefault();
			e.currentTarget.blur();
		}
	});

	$(pageNumberDiv).blur(function() {
		const value_new = pageNumberDiv.innerText;

		if (/^-?[0-9]+$/.test(value_new)) {
			if (value_new !== value_old) {
				if (value_new > 0 && value_new <= page_total) {
					list_page_action('fill', '', value_new, order_type);
				} else if (value_new > page_total){
					pageNumberDiv.textContent = page_total;
					list_page_action('fill', '', page_total, order_type);
				} else {
					pageNumberDiv.textContent = 1;
					list_page_action('fill', '', 1, order_type);
				}
			}
		} else {
			layer.msg('页码输入错误 ！', {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	});
}


function mark_focus_action (market_with_code, grade) {
	if (grade === '0' || grade === '-1') {
		let msg = grade === '0' ? '确定更改关注状态吗？' : '确定不再显示吗？';
		layer.confirm('<p style="text-align:center">' + msg + '</p>', {
			title: '确认',
			btnAlign: 'c', //按钮居中
			btn: ['确定', '取消'],
			shade: 0.5 //遮罩透明度
		// 按钮1事件
		}, function () {
			layer.close(layer.index);
			mark_focus_ajax (market_with_code, grade)
		// 按钮2事件
		}, function () {
		});
	} else {
		mark_focus_ajax (market_with_code, grade)
	}
}


function mark_focus_ajax (market_with_code, grade) {
	let url = site === 'link/stock/view' ? `filter/view/${market_with_code}` : `${site}/${market_with_code}`;
	let post = {"func": "mark", "grade": grade};
	let data = ajax_sync(url, post);
	if (data) {
		if (data['delete']) {
			// site = 'link/stock/view' 时，不会出现 data['delete']
			window.location.href = `/${site}/${data['market']}.${data['code']}`;
		} else {
			mark_focus_set (data['grades']);
		}
	} else {
		layer.msg('获取数据失败 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function mark_focus_set (grades) {
	const focus_element = $("#focus");
	if (focus_element.length) {
		if (parseInt(grades[0]) === 1) {
			focus_element.html(icon_focus_full);
		} else {
			focus_element.html(icon_focus_empty);
		}
	}

	const mark_1st_element = $("#mark-1st");
	const mark_2nd_element = $("#mark-2nd");

	if (parseInt(grades[1]) === 1) {
		mark_1st_element.html(icon_mark_1st_full);
		mark_2nd_element.html(icon_mark_2nd_empty);
	} else if (parseInt(grades[1]) === 2) {
		mark_1st_element.html(icon_mark_1st_empty);
		mark_2nd_element.html(icon_mark_2nd_full);
	// else if (parseInt(grades[1]) === -1)
	} else {
		mark_1st_element.html(icon_mark_1st_empty);
		mark_2nd_element.html(icon_mark_2nd_empty);
	}

	const hide_element = $("#hide");
	if (hide_element.length) {
		hide_element.html(icon_hide);
	}
}


function deal_intent_changed(deal_cat, code) {
	let url, post, data;
	url = `trans/deal/${code}`;
	post = {"func": "intent", "value": $("#intent").val()};
	data = ajax_sync(url, post);

	if (data) {
		const stock_under = document.getElementById("stock-under");
		const stock_guide = document.getElementById("stock-guide");
		const stock_profit = document.getElementById("stock-profit");
		const stock_cost = document.getElementById("stock-cost");

		if (deal_cat === 'plus') {
			stock_under.classList.remove('disp-none');
			$("#under").val(data['under']);
			$("#type").val(data['type']);
		} else {
			stock_under.classList.add('disp-none');
			$("#under").val('');
			$("#type").val('');
		}

		if (data['position'] === 0) {
			stock_guide.classList.add('disp-none');
			stock_profit.classList.remove('disp-none');
			stock_cost.classList.add('disp-none');
			deal_update_field("target", '');
			deal_update_field("stop", '');
			deal_update_field("chance",'');
			deal_update_field("risk", '');
			deal_update_field("profit", value_with_deci(data['profit'], 2));
		} else {
			stock_guide.classList.remove('disp-none');
			stock_cost.classList.remove('disp-none');
			stock_profit.classList.add('disp-none');
			deal_update_field("target", value_with_deci(data['target'], data['deci']));
			deal_update_field("stop", value_with_deci(data['stop'], data['deci']));
			deal_update_field("chance", value_with_deci(data['chance'], 0));
			deal_update_field("risk", value_with_deci(data['risk'], 2));
			deal_update_field("cost", value_with_deci(data['cost'], 2));
		}

		deal_update_field("price", value_with_deci(data['price'], 2));
		deal_update_field("qty", value_with_deci(data['qty'], 2));
		deal_update_field("amount", value_with_deci(data['amount'], 2));
		deal_update_field("fee", value_with_deci(data['fee'], 2));
	}
}


function submit_deal_data(code) {
	layer.confirm('<p style="text-align:center">是否现在提交？</p>', {
		title: '确认',
		btnAlign: 'c', //按钮居中
		btn: ['是', '否'],
		shade: 0.5 //遮罩透明度
	// 按钮1事件
	}, function () {
		layer.close(layer.index);

		let url, post, data;
		url = `trans/view/${code}`;
		let date = $("#date").val();
		let target = $("#target").val();
		let stop =  $("#stop").val();

		post = {
			"func": "calc",
			'date': date,
			'target': target,
			'stop': stop
		};
		data = ajax_sync(url, post);

		if (data) {
			deal_update_field("chance", value_with_deci(data['chance'], 0));
			deal_update_field("risk", value_with_deci(data['risk'], 2));
			deal_update_field("target", value_with_deci(target, 2));
			deal_update_field("stop", value_with_deci(stop, 2));
			$("#target, #stop").css("color", "purple");
		} else {
			layer.msg('数据填写错误 ！', {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	// 按钮2事件
	}, function () {
	});
}


function calc_deal_data(deal_cat, code, type) {
	let url = `trans/deal/${code}`;
	let target = $("#target").val();
	let stop =  $("#stop").val();

	let post = {
		"func": "calc",
		"type": type,
		"cat": deal_cat,
		'intent': $("#intent").val(),
		'price': $("#price").val(),
		'qty': $("#qty").val(),
		'target': target,
		'stop': stop,
		'fee': $("#fee").val()
	};

	let data = ajax_sync(url, post);

	if (data) {
		const deci = data['deci'];
		const stock_profit = document.getElementById("stock-profit");
		const stock_cost = document.getElementById("stock-cost");
		const stock_guide = document.getElementById("stock-guide");

		if (data['status'] === 0) {
			stock_cost.classList.add('disp-none');
			stock_profit.classList.remove('disp-none');
			stock_guide.classList.add('disp-none');
			deal_update_field("profit", value_with_deci(data['profit'], 2));
			deal_update_field("target", '');
			deal_update_field("stop", '');
		} else {
			stock_guide.classList.remove('disp-none');
			deal_update_field("target", value_with_deci(data['target'], deci));
			deal_update_field("stop", value_with_deci(data['stop'], deci));
			$("#target, #stop").css("color", "inherit");

			if (data['status'] === 1) {
				stock_profit.classList.add('disp-none');
				stock_cost.classList.remove('disp-none');
				deal_update_field("cost", value_with_deci(data['cost'], deci));
			} else {
				stock_profit.classList.remove('disp-none');
				stock_cost.classList.add('disp-none');
				deal_update_field("profit", value_with_deci(data['profit'], 2));
			}
		}

		deal_update_field("price", value_with_deci(data['price'], deci));
		deal_update_field("qty", value_with_deci(data['qty'], 2));
		deal_update_field("chance", value_with_deci(data['chance'], 0));
		deal_update_field("risk", value_with_deci(data['risk'], 2));
		deal_update_field("amount", value_with_deci(data['amount'], 2));
		deal_update_field("fee", value_with_deci(data['fee'], 2));
	} else {
		layer.msg('数据填写错误 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function deal_update_field(field, value) {
	let element = $("#" + field);

	try {
		if (element.val() !== value.toString()) {
			element.val(value);
			element.css("color", "#206bc4");
		} else {
			element.css("color", "inherit");
		}
	} catch (error) {
		element.val("");
	}
}


function deal_cancel() {
	window.location.href = `/trans/list`;
}


function deal_submit(market_with_code) {
	let url, post, data;
	let date = $("#date").val(),
		intent = $("#intent").val(),
		price = $("#price").val(),
		qty = $("#qty").val(),
		target = $("#target").val(),
		stop = $("#stop").val(),
		fee = $("#fee").val(),
		profit = $("#profit").val();

	if (Number(price) > 0 && Number(qty) >= 0) {
		tinymce.activeEditor.save();
		let comments = $("#comments").val();
		url = `trans/deal/${market_with_code}`;
		post = {
			"func": "submit",
			"date": date,
			"intent": intent,
			"price": price,
			"qty": qty,
			"target": target,
			"stop": stop,
			"fee": fee,
			"profit": profit,
			"comments": comments
		}

		data = ajax_sync(url, post);

		if (data['msg'] === 'done') {
			if (data['status'] === 0) {
				window.location.href = `/trans/list`;
			} else {
				window.location.href = `/trans/view/${market_with_code}`;
			}
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
	}
	else {
		layer.msg('内容填写错误 ！', {
			icon: 7,
			time: 2000 //2秒关闭，若不配置默认3秒
		}, function(){
		});
	}
}


function divd_cancel(market_with_code) {
	window.location.href = `/trans/view/${market_with_code}`;
}


function divd_submit(market_with_code) {
	let url = `trans/divd/${market_with_code}`;
	let post = {
			"func": "submit",
			"date": $("#date").val(),
			"qty": $("#qty").val(),
			"cash": $("#cash").val(),
			"fee": $("#fee").val()
		}

	let data = ajax_sync(url, post);
	if (data['msg'] === 'done') {
		layer.msg("登记已完成 ！", {
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
}


function review_type_select() {
	let review_type = $("#review-type").val();
	window.location.href = review_type === 'focus'? `/review/focus/list` : `/review/trans/list`;
}


function review_list_update(review_type) {
	let url, post, data;
	url = `${site}`;
	post = {"func": "update"};
	data = ajax_sync(url, post);

	if (data) {
		for (let each of data) {
			document.getElementById(`name-${each['flow']}`).innerText = each['name'];
			document.getElementById(`close-${each['flow']}`).innerText = value_with_deci(each['close'], 2);

			let price = document.getElementById(`price-${each['flow']}`).innerText;
			document.getElementById(`price-${each['flow']}`).innerText = value_with_deci(price, each['deci']);

			if (review_type === "focus") {
				let target = document.getElementById(`target-${each['flow']}`).innerText;
				document.getElementById(`target-${each['flow']}`).innerText = value_with_deci(target, each['deci']);
			} else {
				let cost = document.getElementById(`cost-${each['flow']}`).innerText;
				document.getElementById(`cost-${each['flow']}`).innerText = value_with_deci(cost, each['deci']);
			}
		}
	} else {
		layer.msg('获取数据失败 ！', {
			icon: 7,
			time: 2000 //2秒关闭，若不配置默认3秒
		}, function(){
		});
	}
}


function review_list_order(order_type) {
	let order_new;
	if (order_type === 'date') {
		order_new = 'star-desc'
	} else if (order_type === 'star-desc') {
		order_new = 'star-asc'
	} else {
		order_new = 'date'
	}

	window.location.href = `/${site}?order=${order_new}`;
}


function set_review_star(flow) {
	let url = `${site}/${flow}`;
	let post = {"func": 'star', "value": $("#star").val()}

	let data = ajax_sync(url, post);

	if (data) {
		layer.msg(data['msg'], {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function save_temp_form_data() {
	try {
		let data = [];
		let form = document.getElementById("main-form");
		if (form) {
			for (let element of form) {
				if (element.type === "text" || element.type === "select-one") {
					data.push([element.type, element.id, element.value]);
				} else if (element.type === "radio") {
					data.push([element.type, element.name, element.checked]);
				}
			}
		}

		tinymce.activeEditor.save();
		data.push(["textarea", "comments", $("#comments").val()]);
		const form_data = {
			time: new Date().getTime(),
			data: data,
		};
		localStorage.setItem("form", JSON.stringify(form_data));
	} catch (error) {
	}
}


function refill_temp_form_data() {
	let saved_data = localStorage.getItem("form")

	if (saved_data) {
		saved_data = JSON.parse(saved_data);

		// 时间单位为毫秒，超过设定的1分钟，将不将数据回填表单，并销毁数据
		if(new Date().getTime() - saved_data.time < 6000){
			let data = saved_data.data;

			for (let each of data) {
				const [element_type, element_id_or_name, element_value] = each
				if (element_type === "text" || element_type === "select-one" || element_type === "textarea") {
					let element = document.getElementById(element_id_or_name);
					element.value = element_value;
				} else {
					let element = document.getElementsByName(element_id_or_name);
					element.checked = element_value;
				}
			}
		}

		localStorage.removeItem("form");
	}
}


function init_tinymce() {
	// http://tinymce.ax-z.cn/
	// https://download.tiny.cloud/tinymce/community/tinymce_6.4.2.zip
	// https://download.tiny.cloud/tinymce/community/languagepacks/6/zh-Hans.zip
	// 1. 解压zh-Hans.js放入langs文件夹
	// 2. icons\default\icons.min.js修改save按钮：'<svg width="24" height="24"><path d="M6 4h10l4 4v10a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2M12 14m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0M14 4l0 4l-6 0l0 -4" fill-rule="evenodd"/></svg>'
	// 3. skins\ui\oxide\skin.min.css修改.tox-tinymce{border: 0px solid #eee;border-radius: 4px;}
	let options = {
		selector: '#comments',
		language:'zh-Hans',
		height: 200,
		menubar: false,
		statusbar: false,
		plugins: 'save',
		toolbar: 'save bold italic forecolor removeformat'
	}

	tinyMCE.init(options);
}


function view_goback_list (code) {
	localStorage.setItem("size", '');
	
	if (site === 'link/sector/view') {
		let link_code = localStorage.getItem("link_code").split(',');
		window.location.href = `/link/sector/list?code=${link_code[1]}.${link_code[2]}`;
	} else if (site === 'link/stock/view') {
		let link_code = localStorage.getItem("link_code").split(',');
		window.location.href = `/link/stock/list?code=${link_code[2]}`;
	} else {
		let url, post, data;
		url = `${site}/${code}`;
		post = {"func": "back"};
		data = ajax_sync(url, post);
		if (data) {
			window.location.href = `/${data['url']}`;
		} else {
			layer.msg('服务器错误 ！', {
				icon: 7,
				time: 2000
			}, function(){
			});
		}
	}
}


function show_comment() {
    const comments_area = document.getElementById("comments-area");
    comments_area.classList.toggle("disp-none");
}


function save_comment(market_with_code, flow) {
	let url = site === 'link/stock/view' ? `filter/view/${market_with_code}` : `${site}/${market_with_code}`;
	let post = {"func": 'comments', "flow": flow, "value": $("#comments").val()}
	let data = ajax_sync(url, post);

	if (data) {
		layer.msg(data['msg'], {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function folder_path(action, folder, name) {
	if (!editing) {
		if (action === 'set') {
			folder = document.getElementById('folder').value
		}

		let url = `files/view`;
		let post = {'func': 'path', 'action': action, 'folder': folder, 'name': name};
		let data = ajax_sync(url, post);
		file_handle_alert(data, true);
	}
}


function file_handle_alert(data, refresh) {
	if (data) {
		if (data['msg'] === 'done') {
			if (refresh) {
				location.reload();
			}
		} else if (data['msg'] === 'isfile') {
			window.open(`/files/load?index=${data['index']}`);
		} else {
			layer.msg(data['msg'], {
				icon: 7,
				time: 4000
			}, function(){
			});
		}
	} else {
		layer.msg('请求失败 ！', {
			icon: 7,
			time: 2000
		}, function(){
		});
	}
}


function file_new_item(action, folder) {
	let table_body = document.getElementById('table-body');
	let new_row = document.createElement('tr');

	new_row.innerHTML = `
		<td class="table-cell-text disp-flex-left">
			<label>
				<input type="checkbox" name="filename" class="form-check-input margin-right-2">
			</label>
			<span id="new-row-span" class="${action === 'new-folder' ? 'color-royalblue' : ''}"
				>${action === 'new-folder' ? '新建文件夹' : '新建文件'}</span>
		</td>
		<td class="table-cell-text"></td>
		<td class="table-cell-text"></td>
		<td class="table-cell-text"></td>`;

	table_body.appendChild(new_row);

	let span = document.getElementById('new-row-span');
	span.contentEditable = 'true';
	span.focus();
	span.classList.add('file-selected');

	span.addEventListener('keydown', function(event) {
		if (event.key === 'Enter') {
			set_span_blur(span, action);
		}
	});

	span.addEventListener('blur', function() {
		set_span_blur(span, action);
	});

	function set_span_blur(span, itemType) {
		let name = span.textContent;
		span.blur();
		span.contentEditable = 'false';
		span.classList.remove('file-selected');
		let url = 'files/view';
		let post = {'func': itemType, 'folder': folder, 'name': name};
		let data = ajax_sync(url, post);
		file_handle_alert(data, true);
	}
}


function file_rename_action(folder) {
	let editing = true;
	let checkboxes = document.querySelectorAll('input[name="filename"]:checked');
	checkboxes.forEach(function(checkbox) {
		let span = checkbox.closest('td').querySelector('span');
		let name = span.textContent;
		let input = checkbox.closest('td').querySelector('input');
		let file_rename_element = document.getElementById('file-rename');

		span.contentEditable = 'true';
		span.focus();
		span.classList.add('file-selected');
		span.classList.remove('pointer');
		file_rename_element.classList.remove('color-dimgrey');

		span.addEventListener('keydown', function(event) {
			if (event.key === 'Enter') {
				set_span_blur(span, input)
			}
		});

		span.addEventListener('blur', function() {
			set_span_blur(span, input)
		});

		function set_span_blur(span, input) {
			let newname = span.textContent;
			span.blur();
			span.contentEditable = 'false';
			span.classList.remove('file-selected');
			span.classList.add('pointer');
			input.checked = false;
			editing = false;
			set_file_toolbar(get_selected_files());
			let url = `files/view`;
			let post = {'func': 'rename', 'folder': folder, 'name': name, 'new': newname}
			let data = ajax_sync(url, post);
			file_handle_alert(data, true);
		}
	});

	return editing;
}


function file_copy_or_cut(action, folder, selected_files, selected_count) {
    let storage_key = (action === 'copy') ? 'files-copy' : 'files-cut';
    let element_id = (action === 'copy') ? 'file-copy' : 'file-cut';
    let opposite_key = (action === 'copy') ? 'files-cut' : 'files-copy';
    let opposite_element_id = (action === 'copy') ? 'file-cut' : 'file-copy';

    let storage = localStorage.getItem(storage_key);
    let opposite_storage = localStorage.getItem(opposite_key);

    if (!storage && selected_count > 0) {
        if (opposite_storage) {
            localStorage.removeItem(opposite_key);
            document.getElementById(opposite_element_id).classList.add('color-dimgrey');
        }
        let source_files = {'source': folder, 'files': selected_files};
        localStorage.setItem(storage_key, JSON.stringify(source_files));
        document.getElementById(element_id).classList.remove('color-lightgrey');
        document.getElementById(element_id).classList.remove('color-dimgrey');
    } else if (storage) {
        if (opposite_storage) {
            localStorage.removeItem(opposite_key);
            document.getElementById(opposite_element_id).classList.add('color-dimgrey');
        }
        localStorage.removeItem(storage_key);
        let source_files = JSON.parse(storage);
        let files_name = JSON.stringify(source_files['files']);
        let url = 'files/view';
        let post = {'func': action, 'source': source_files['source'], 'target': folder, 'files': files_name};
        let data = ajax_sync(url, post);
        file_handle_alert(data, true);
        set_file_toolbar(selected_files);
    }
}


function file_delete_action(folder, selected_files, selected_count) {
	if (selected_count > 0) {
		layer.confirm('<p style="text-align:center">请确认是否删除？</p>', {
			title: '确认',
			btnAlign: 'c',
			btn: ['确定', '取消'],
			shade: 0.5
		}, function () {
			layer.close(layer.index);
			let url = 'files/view';
			let post = {"func": 'delete', "folder": folder ,"files": JSON.stringify(selected_files)};
			let data = ajax_sync(url, post);
			file_handle_alert(data, true);
		}, function () {
		});
	}
}


function file_download_action(folder, selected_files, selected_count) {
	if (selected_count > 0) {
		layer.confirm('<p style="text-align:center">请确认是否下载？</p>', {
			title: '确认',
			btnAlign: 'c',
			btn: ['确定', '取消'],
			shade: 0.5
		}, function () {
			layer.close(layer.index);
			let url = 'files/view';
			let post = {"func": 'download', "folder": folder ,"files": JSON.stringify(selected_files)};
			let data = ajax_sync(url, post);

			if (data) {
				window.location.href = `files?id=${data['id']}`;
			} else {
				layer.msg('请求失败 ！', {
					icon: 7,
					time: 2000
				}, function(){
				});
			}
		}, function () {
		});
	}
}


function select_files_click() {
	 let selected_files = get_selected_files();
	 set_file_toolbar(selected_files);
}


function get_selected_files() {
	let selected_files = [];
	const checkboxes = document.querySelectorAll('input[name="filename"]:checked');
	checkboxes.forEach(each => {
		selected_files.push(each.value);
	});

	return selected_files
}


function set_file_toolbar(selected_files) {
	let selected_count = selected_files.length;

	let file_rename_element = document.getElementById('file-rename');
	let file_copy_element = document.getElementById('file-copy');
	let file_cut_element = document.getElementById('file-cut');
	let file_delete_element = document.getElementById('file-delete');
	let file_download_element = document.getElementById('file-download');

	if (selected_count === 1) {
		file_rename_element.classList.remove('color-lightgrey');
		file_rename_element.classList.add('color-dimgrey');
		file_rename_element.classList.add('pointer');
		file_copy_element.classList.remove('color-lightgrey');
		file_copy_element.classList.add('color-dimgrey');
		file_copy_element.classList.add('pointer');
		file_cut_element.classList.remove('color-lightgrey');
		file_cut_element.classList.add('color-dimgrey');
		file_cut_element.classList.add('pointer');
		file_delete_element.classList.remove('color-lightgrey');
		file_delete_element.classList.add('color-dimgrey');
		file_delete_element.classList.add('pointer');
		file_download_element.classList.remove('color-lightgrey');
		file_download_element.classList.add('color-dimgrey');
		file_download_element.classList.add('pointer');
	} else if (selected_count > 0) {
		file_rename_element.classList.add('color-lightgrey');
		file_rename_element.classList.remove('color-dimgrey');
		file_rename_element.classList.remove('pointer');
	} else {
		file_rename_element.classList.add('color-lightgrey');
		file_rename_element.classList.remove('color-dimgrey');
		file_rename_element.classList.remove('pointer');
		file_copy_element.classList.add('color-lightgrey');
		file_copy_element.classList.remove('color-dimgrey');
		file_copy_element.classList.remove('pointer');
		file_cut_element.classList.add('color-lightgrey');
		file_cut_element.classList.remove('color-dimgrey');
		file_cut_element.classList.remove('pointer');
		file_delete_element.classList.add('color-lightgrey');
		file_delete_element.classList.remove('color-dimgrey');
		file_delete_element.classList.remove('pointer');
		file_download_element.classList.add('color-lightgrey');
		file_download_element.classList.remove('color-dimgrey');
		file_download_element.classList.remove('pointer');
	}

    let copy_storage_key = 'files-copy';
    let copy_storage = localStorage.getItem(copy_storage_key);
	if (copy_storage) {
		file_copy_element.classList.remove('color-lightgrey');
		file_copy_element.classList.remove('color-dimgrey');
	}

    let cut_storage_key = 'files-cut';
    let cut_storage = localStorage.getItem(cut_storage_key);
	if (cut_storage) {
		file_cut_element.classList.remove('color-lightgrey');
		file_cut_element.classList.remove('color-dimgrey');
	}
}


function monaco_init(vs, path, data) {
	let language = get_file_language(path);

	require.config({
		paths: {'vs': vs}
	});

	require(['vs/editor/editor.main'], function (monaco) {
		// files-load 页面已经定义了
		editor = monaco.editor.create(document.getElementById('editor'), {
			// 设置初始值
			value: data,
			// 设置语言模式
			language: language,
			theme: 'vs',
			// 自动调整布局
			automaticLayout: true
		});

		editor.layout({ height: frame_height - 40 });

		// 添加自定义命令并绑定到保存操作
		editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, function() {
			let content = editor.getValue();
			let url = `files/load`;
			let post = {'func': 'save', 'path': path, 'content': content};
			let data = ajax_sync(url, post);
			if (data) {
				Swal.fire({
					title: data['msg'],
					timer: 1000, // 毫秒
					width: '150px',
					showConfirmButton: false,
					customClass: {
						title: 'swal-title',
						popup: 'swal-bg'
					}
				});
			} else {
				Swal.fire({
					title: '请求失败 ！',
					timer: 1000, // 毫秒
					width: '150px',
					showConfirmButton: false,
					customClass: {
						title: 'swal-title',
						popup: 'swal-bg'
					}
				});
			}
		});
	});
}


function get_file_language(path) {
	const extension = path.split('.').pop().toLowerCase();
	switch (extension) {
		case 'py':
			return 'python';
		case 'html':
			return 'html';
		case 'js':
			return 'javascript';
		case 'java':
			return 'java';
		case 'cpp':
		case 'cxx':
		case 'cc':
		case 'c++':
			return 'c++';
		case 'cs':
			return 'c#';
		case 'rb':
			return 'ruby';
		case 'php':
			return 'php';
		case 'swift':
			return 'swift';
		case 'go':
			return 'go';
		case 'rs':
			return 'rust';
		case 'kotlin':
			return 'kotlin';
		case 'scala':
			return 'scala';
		default:
			return 'plaintext';
	}
}
