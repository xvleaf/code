const icon_overall = '<svg width="24" height="24" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M18 16v2a1 1 0 0 1 -1 1h-11l6 -7l-6 -7h11a1 1 0 0 1 1 1v2"></path>' +
	'</svg>';

const icon_focus = '<svg width="24" height="24" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<circle cx="12" cy="12" r=".5" fill="currentColor"></circle>' +
	'<path d="M12 12m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0"></path>' +
	'<path d="M12 3l0 2"></path>' +
	'<path d="M3 12l2 0"></path>' +
	'<path d="M12 19l0 2"></path>' +
	'<path d="M19 12l2 0"></path>' +
	'</svg>';

const icon_trans = '<svg width="24" height="24" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M3.262 10.878l8 8.789c.4 .44 1.091 .44 1.491 0l8 -8.79c.313 -.344 .349 -.859 .087 -1.243l-3.537 ' +
	'-5.194a1 1 0 0 0 -.823 -.436h-8.926a1 1 0 0 0 -.823 .436l-3.54 5.192c-.263 .385 -.227 .901 .087 1.246z"></path>' +
	'</svg>';

const icon_review = '<svg width="24" height="24" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M12 8l0 4l2 2"></path>' +
	'<path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"></path>' +
	'</svg>';

const icon_setting = '<svg width="24" height="24" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 -.94 3.31 .826 ' +
	'2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 ' +
	'1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0' +
	' -2.573 -1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 -.426 -1.756 -2.924 ' +
	'0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 2.37 -2.37c1 .608 2.296 .07 2.572 -1.065z"></path>' +
	'<path d="M9 12a3 3 0 1 0 6 0a3 3 0 0 0 -6 0"></path>' +
	'</svg>';

const icon_maximize = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="1.75" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M3 16m0 1a1 1 0 0 1 1 -1h3a1 1 0 0 1 1 1v3a1 1 0 0 1 -1 1h-3a1 1 0 0 1 -1 -1z">' +
	'</path><path d="M4 12v-6a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-6"></path>' +
	'<path d="M12 8h4v4"></path><path d="M16 8l-5 5"></path>' +
	'</svg>';

const icon_minimize = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="1.75" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M3 16m0 1a1 1 0 0 1 1 -1h3a1 1 0 0 1 1 1v3a1 1 0 0 1 -1 1h-3a1 1 0 0 1 -1 -1z"></path>' +
	'<path d="M4 12v-6a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-6"></path>' +
	'<path d="M15 13h-4v-4"></path><path d="M11 13l5 -5"></path>' +
	'</svg>';

const icon_end = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M4 7l16 0"></path>' +
	'<path d="M10 11l0 6"></path>' +
	'<path d="M14 11l0 6"></path>' +
	'<path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"></path>' +
	'<path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"></path>' +
	'</svg>'

const icon_exit = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M18 6l-12 12"></path><path d="M6 6l12 12"></path>' +
	'</svg>';

const icon_edit = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1"></path>' +
	'<path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z"></path>' +
	'<path d="M16 5l3 3"></path>' +
	'</svg>';

const icon_edit_off = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1"></path>' +
	'<path d="M10.507 10.498l-1.507 1.502v3h3l1.493 -1.498m2 -2.01l4.89 ' +
	'-4.907a2.1 2.1 0 0 0 -2.97 -2.97l-4.913 4.896"></path>' +
	'<path d="M16 5l3 3"></path>' +
	'<path d="M3 3l18 18"></path>' +
	'</svg>';

const icon_divd = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"/>' +
	'<path d="M17 17m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0" />' +
	'<path d="M7 7m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0" />' +
	'<path d="M6 18l12 -12" />' +
	'</svg>';

const icon_deal = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M6 5h12l3 5l-8.5 9.5a.7 .7 0 0 1 -1 0l-8.5 -9.5l3 -5"></path>' +
	'<path d="M10 12l-2 -2.2l.6 -1"></path>' +
	'</svg>';

const icon_deal_off = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M9 5h9l3 5l-3.308 3.697m-1.883 2.104l-3.309 3.699a.7 .7 0 0 1 -1 0l-8.5 -9.5l2.62 -4.368"></path>' +
	'<path d="M10 12l-2 -2.2l.6 -1"></path>' +
	'<path d="M3 3l18 18"></path>' +
	'</svg>';

const icon_plus = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="2" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M12 5l0 14"></path>' +
	'<path d="M5 12l14 0"></path>' +
	'</svg>';

const icon_day = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M5 7.2a2.2 2.2 0 0 1 2.2 -2.2h1a2.2 2.2 0 0 0 1.55 -.64l.7 -.7a2.2 2.2 0 0 1 3.12 0l.7 .7c.412 ' +
	'.41 .97 .64 1.55 .64h1a2.2 2.2 0 0 1 2.2 2.2v1c0 .58 .23 1.138 .64 1.55l.7 .7a2.2 2.2 0 0 1 0 3.12l-.7 ' +
	'.7a2.2 2.2 0 0 0 -.64 1.55v1a2.2 2.2 0 0 1 -2.2 2.2h-1a2.2 2.2 0 0 0 -1.55 .64l-.7 .7a2.2 2.2 0 0 1 -3.12 ' +
	'0l-.7 -.7a2.2 2.2 0 0 0 -1.55 -.64h-1a2.2 2.2 0 0 1 -2.2 -2.2v-1a2.2 2.2 0 0 0 -.64 -1.55l-.7 -.7a2.2 2.2 ' +
	'0 0 1 0 -3.12l.7 -.7a2.2 2.2 0 0 0 .64 -1.55v-1"></path>' +
	'</svg>';

const icon_week = '<svg width="16" height="16" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M11 11h2v2h-2z"></path>' +
	'<path d="M3.634 15.634l1.732 -1l1 1.732l-1.732 1z"></path>' +
	'<path d="M11 19h2v2h-2z"></path>' +
	'<path d="M18.634 14.634l1.732 1l-1 1.732l-1.732 -1z"></path>' +
	'<path d="M17.634 7.634l1.732 -1l1 1.732l-1.732 1z"></path>' +
	'<path d="M11 3h2v2h-2z"></path>' +
	'<path d="M3.634 8.366l1 -1.732l1.732 1l-1 1.732z"></path>' +
	'</svg>';

const icon_month = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1 -8.313 -12.454z"></path>' +
	'</svg>';

const icon_adj = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M10.09 4.01l.496 -.495a2 2 0 0 1 2.828 0l7.071 7.07a2 2 0 0 1 0 2.83l-7.07 7.07a2 2 0 0 1 ' +
	'-2.83 0l-7.07 -7.07a2 2 0 0 1 0 -2.83l3.535 -3.535h-3.988"></path><path d="M7.05 11.038v-3.988">' +
	'</path>' +
	'</svg>';

const icon_div = '<svg width="18" height="18" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" ' +
	'stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M16.964 16.952l-3.462 3.461c-.782 .783 -2.222 .783 -3 0l-6.911 -6.91c-.783 -.783 -.783 -2.223 0 ' +
	'-3l3.455 -3.456m2 -2l1.453 -1.452c.782 -.783 2.222 -.783 3 0l6.911 6.91c.783 .783 .783 2.223 0 3l-1.448 1.45">' +
	'</path><path d="M3 3l18 18"></path>' +
	'</svg>';

const icon_focus_full = '<svg width="20" height="20" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none" />' +
	'<path d="M16 3a1 1 0 0 1 .117 1.993l-.117 .007v4.764l1.894 3.789a1 1 0 0 1 .1 .331l.006 ' +
	'.116v2a1 1 0 0 1 -.883 .993l-.117 .007h-4v4a1 1 0 0 1 -1.993 .117l-.007 -.117v-4h-4a1 ' +
	'1 0 0 1 -.993 -.883l-.007 -.117v-2a1 1 0 0 1 .06 -.34l.046 -.107l1.894 -3.791v-4.762a1 ' +
	'1 0 0 1 -.117 -1.993l.117 -.007h8z" stroke-width="0" fill="currentColor" />' +
	'</svg>';

const icon_focus_empty = '<svg width="20" height="20" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none" />' +
	'<path d="M9 4v6l-2 4v2h10v-2l-2 -4v-6" />' +
	'<path d="M12 16l0 5" />' +
	'<path d="M8 4l8 0" />' +
	'</svg>';

const icon_mark_1st_full = '<svg width="20" height="20" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M10.425 1.414a3.33 3.33 0 0 1 3.216 0l6.775 3.995c.067 .04 .127 .084 .18 .133l.008 .007l.107 ' +
	'.076a3.223 3.223 0 0 1 1.284 2.39l.005 .203v7.284c0 1.175 -.643 2.256 -1.623 2.793l-6.804 4.302c-.98 .538 ' +
	'-2.166 .538 -3.2 -.032l-6.695 -4.237a3.226 3.226 0 0 1 -1.678 -2.826v-7.285a3.21 3.21 0 0 1 1.65 -2.808zm.952 ' +
	'5.803l-.084 .076l-2 2l-.083 .094a1 1 0 0 0 0 1.226l.083 .094l.094 .083a1 1 0 0 0 1.226 0l.094 -.083l.293 ' +
	'-.293v5.586l.007 .117a1 1 0 0 0 1.986 0l.007 -.117v-8l-.006 -.114c-.083 -.777 -1.008 -1.16 -1.617 -.67z" ' +
	'stroke-width="0" fill="currentColor"></path>' +
	'</svg>';

const icon_mark_1st_empty = '<svg width="20" height="20" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path>' +
	'<path d="M19.875 6.27a2.225 2.225 0 0 1 1.125 1.948v7.284c0 .809 -.443 1.555 -1.158 1.948l-6.75 4.27a2.269 ' +
	'2.269 0 0 1 -2.184 0l-6.75 -4.27a2.225 2.225 0 0 1 -1.158 -1.948v-7.285c0 -.809 .443 -1.554 1.158 -1.947l6.75 ' +
	'-3.98a2.33 2.33 0 0 1 2.25 0l6.75 3.98h-.033z"></path>' +
	'<path d="M10 10l2 -2v8"></path>' +
	'</svg>';

const icon_mark_2nd_full = '<svg width="20" height="20" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M10.425 1.414a3.33 3.33 0 0 1 3.216 0l6.775 ' +
	'3.995c.067 .04 .127 .084 .18 .133l.008 .007l.107 .076a3.223 3.223 0 0 1 1.284 2.39l.005 .203v7.284c0 1.175 ' +
	'-.643 2.256 -1.623 2.793l-6.804 4.302c-.98 .538 -2.166 .538 -3.2 -.032l-6.695 -4.237a3.226 3.226 0 0 1 -1.678 ' +
	'-2.826v-7.285a3.21 3.21 0 0 1 1.65 -2.808zm2.575 5.586h-3l-.117 .007a1 1 0 0 0 0 1.986l.117 .007h3v2h-2l-.15 ' +
	'.005a2 2 0 0 0 -1.844 1.838l-.006 .157v2l.005 .15a2 2 0 0 0 1.838 1.844l.157 .006h3l.117 -.007a1 1 0 0 0 0 ' +
	'-1.986l-.117 -.007h-3v-2h2l.15 -.005a2 2 0 0 0 1.844 -1.838l.006 -.157v-2l-.005 -.15a2 2 0 0 0 -1.838 ' +
	'-1.844l-.157 -.006z" stroke-width="0" fill="currentColor"></path>' +
	'</svg>';

const icon_mark_2nd_empty = '<svg width="20" height="20" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M19.875 6.27a2.225 2.225 0 ' +
	'0 1 1.125 1.948v7.284c0 .809 -.443 1.555 -1.158 1.948l-6.75 4.27a2.269 2.269 0 0 ' +
	'1 -2.184 0l-6.75 -4.27a2.225 2.225 0 0 1 -1.158 -1.948v-7.285c0 -.809 .443 -1.554 1.158 -1.947l6.75 ' +
	'-3.98a2.33 2.33 0 0 1 2.25 0l6.75 3.98h-.033z"></path>' +
	'<path d="M10 8h3a1 1 0 0 1 1 1v2a1 1 0 0 1 -1 1h-2a1 1 0 0 0 -1 1v2a1 1 0 0 0 1 1h3"></path>' +
	'</svg>';

const icon_show_comment = '<svg width="20" height="20" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M13 20l7 -7"></path>' +
	'<path d="M13 20v-6a1 1 0 0 1 1 -1h6v-7a2 2 0 0 0 -2 -2h-12a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h7"></path>' +
	'</svg>';

const icon_goback = '<svg width="20" height="20" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none"   stroke-linecap="round"  stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"/>' +
	'<path d="M9 6l11 0" />' +
	'<path d="M9 12l11 0" />' +
	'<path d="M9 18l11 0" />' +
	'<path d="M5 6l0 .01" />' +
	'<path d="M5 12l0 .01" />' +
	'<path d="M5 18l0 .01" />' +
	'</svg>';

const icon_hide = '<svg width="20" height="20" viewBox="0 0 24 24" ' +
	'stroke-width="1.5" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
	'<path stroke="none" d="M0 0h24v24H0z" fill="none"/>' +
	'<path d="M19.875 6.27a2.225 2.225 0 0 1 1.125 1.948v7.284c0 .809 -.443 1.555 -1.158 1.948l-6.75 ' +
	'4.27a2.269 2.269 0 0 1 -2.184 0l-6.75 -4.27a2.225 2.225 0 0 1 -1.158 -1.948v-7.285c0 -.809 .443 ' +
	'-1.554 1.158 -1.947l6.75 -3.98a2.33 2.33 0 0 1 2.25 0l6.75 3.98h-.033z" />' +
	'<path d="M10 8l4 8" />' +
	'<path d="M10 16l4 -8" />' +
	'</svg>'
