const {remote} = require('electron');
const {app} = remote;
const { Notification } = require('electron')

function showNotification (title, body) {
	const notification = {
		title: title,
		body: body,
	};
	new Notification(notification).show();
}

function get_data() {
	var jsonData;
	var shell = require('child_process').exec;
	shell(`"${__dirname}\\engine\\doer\\doer.exe" "${app.getPath("userData")}" get_data`, function(err, data){
		if(err){
			throw err;
		}
		jsonData = JSON.parse(data);
		var mode_usage = jsonData["modes"];
		wk_hr = parseInt(mode_usage['Working']/3600);
		wk_mn = parseInt((mode_usage['Working']%3600) / 60);
		wk_sec = (mode_usage['Working']%3600) % 60;
		document.getElementById("work_time").innerHTML = wk_hr.toString() + ':' + wk_mn.toString() + ':' + wk_sec.toString();
		cf_hr = parseInt(mode_usage['Conference']/3600);
		cf_mn = parseInt((mode_usage['Conference']%3600) / 60);
		cf_sec = (mode_usage['Conference']%3600) % 60;
		document.getElementById("conf_time").innerHTML = cf_hr.toString() + ':' + cf_mn.toString() + ':' + cf_sec.toString();
		cl_hr = parseInt(mode_usage['Call']/3600);
		cl_mn = parseInt((mode_usage['Call']%3600) / 60);
		cl_sec = (mode_usage['Call']%3600) % 60;
		document.getElementById("call_time").innerHTML = cl_hr.toString() + ':' + cl_mn.toString() + ':' + cl_sec.toString();
		id_hr = parseInt(mode_usage['Idle']/3600);
		id_mn = parseInt((mode_usage['Idle']%3600) / 60);
		id_sec = (mode_usage['Idle']%3600) % 60;
		document.getElementById("idle_time").innerHTML = id_hr.toString() + ':' + id_mn.toString() + ':' + id_sec.toString();
		up_hr = parseInt(jsonData['uptime']/3600);
		up_mn = parseInt((jsonData['uptime']%3600) / 60);
		up_sec = (jsonData['uptime']%3600) % 60;

		document.getElementById("up_time").innerHTML = up_hr.toString() + ' hr ' + up_mn.toString() + ' min ' + up_sec.toString() + " sec";

		var icon_dct = {
			'Working': "assets/icons/working.png",
			'Conference': "assets/icons/conference.png",
			'Call': "assets/icons/call.png",
			'Idle': "assets/icons/idle.png"
		};
		var modes_lst = ['', 'Working', 'Conference', 'Call', 'Idle'];
		var tasks_table = document.getElementById("tasks_list");
		tasks_table.innerHTML = "";
		Object.keys(jsonData["apps"]).forEach(function(key) {
			tasks_table.innerHTML += `
			<li class="list-group-item d-flex justify-content-between align-items-center " style="background-color: rgb(17, 17, 17);">
				<span style="max-width: 90px; overflow: hidden; white-space:nowrap">${key}</span>
				<span class="badge badge-primary badge-pill" style="font-size: 10px;">${parseInt(jsonData['apps'][key])}</span>
			</li>`;
		});
		document.getElementById("wh_md").innerHTML =  modes_lst[jsonData['mode']];
		
		var usg_lst = document.getElementById("usage_list");
		usg_lst.innerHTML = "";
		jsonData["data"].forEach(function(item, index){
			usg_lst.innerHTML += `
			<li class="list-group-item d-flex justify-content-between align-items-center ">
				<img src="${icon_dct[item[0]]}" width="20px" height"20px"/>
				<span style="max-width: 90px; overflow: hidden;">${item[1]}</span>
				<span class="badge badge-primary badge-pill" style="font-size: 10px;">${item[2]}</span>
			</li>`;	
		});
		var rad_lst = ['', 'work', 'conf', 'call', 'idle'];
		document.getElementById(rad_lst[jsonData["mode"]]).checked = true;

		if (jsonData["aut"][0] != 0	){
			showNotification('You are Inactive', 'Looks like you have been Inactive for the past couple minutes. Please go to the application.');
			document.getElementById("aut_dialog").style.visibility = 'visible';
		}
		else {
			document.getElementById("aut_dialog").style.visibility = 'hidden';
		}

	});
}

function check_reg() {
	var shell = require('child_process').exec;
	return new Promise((resolve, reject) => {
		shell(`"${__dirname}\\engine\\doer\\doer.exe" "${app.getPath("userData")}" is_registered`, function(err, data){
			console.log("Checking for registration", data);
			if(err){
				throw err;
			}
			if (data == 0){
				$('#regForm').modal("show");
			}
			resolve(data);
		});
	});
}

jQuery.fn.shakeit = function(intShakes, intDistance, intDuration) {
	this.each(function() {
		$(this).css("position","absolute");
		$(this).css("left","20%");
		for (var x=1; x<=intShakes; x++) {
			$(this).animate({left:(intDistance*-1)}, (((intDuration/intShakes)/4)))
			.animate({left:intDistance}, ((intDuration/intShakes)/2))
			.animate({left:0}, (((intDuration/intShakes)/4)));
		}
	});
	return this;
};

function do_reg(){
	const shell = require('child_process').exec;
	var email = document.getElementById("email").value;
	var password = document.getElementById("password").value;
	shell(`"${__dirname}\\engine\\doer\\doer.exe" "${app.getPath("userData")}" do_reg "${email}" "${password}"`, function(err, data){
		if(err){
			throw err;
		}
		if (data == 1){
			document.getElementById("eml").innerHTML = email;
			$('#regForm').modal("hide");
			$('#login_success').modal("show");
		}
		else {
			$("#regForm").shakeit(3, 7, 800);
		}
	});
}


function aut_yes(mode) {
	var shell = require('child_process').exec;
	shell(`"${__dirname}\\engine\\doer\\doer.exe" "${app.getPath("userData")}" active`, function(err, data){
		if(err){
			throw err;
		}
		document.getElementById("aut_dialog").style.visibility = 'hidden';
		}
	);
}

function change_mode(mode) {
	document.getElementById('wh_md').innerHTML = ( (mode == 1) ? 'Working' : ((mode == 2) ? 'Conference' : ((mode == 3) ? 'Call' : "Idle")));
	var shell = require('child_process').exec;
	shell(`"${__dirname}\\engine\\doer\\doer.exe" "${app.getPath("userData")}" mode_change ${mode}`, function(err, data){
		if(err) {
			throw err;
		}
	});
}