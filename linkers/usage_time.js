function get_usage_time() {
	
	var python = require('child_process').exec;
	var jsonData;
	python("python ../engine/usage_time.py", function(err, data){
		if(err){
			throw err;
		}
		jsonData = JSON.parse(data);
		var mode_usage = jsonData["modes"];
		console.log(mode_usage);
		wk_hr = parseInt(mode_usage['Working']/3600);
		wk_mn = parseInt((mode_usage['Working']%3600) / 60);
		wk_sec = (mode_usage['Working']%3600) % 60;
		document.getElementById("work_time").innerHTML = wk_hr.toString() + ':' + wk_mn.toString() + ':' + wk_sec.toString();
		wk_hr = parseInt(mode_usage['Conference']/3600);
		wk_mn = parseInt((mode_usage['Conference']%3600) / 60);
		wk_sec = (mode_usage['Conference']%3600) % 60;
		document.getElementById("conf_time").innerHTML = wk_hr.toString() + ':' + wk_mn.toString() + ':' + wk_sec.toString();
		wk_hr = parseInt(mode_usage['Call']/3600);
		wk_mn = parseInt((mode_usage['Call']%3600) / 60);
		wk_sec = (mode_usage['Call']%3600) % 60;
		document.getElementById("call_time").innerHTML = wk_hr.toString() + ':' + wk_mn.toString() + ':' + wk_sec.toString();
		wk_hr = parseInt(mode_usage['Idle']/3600);
		wk_mn = parseInt((mode_usage['Idle']%3600) / 60);
		wk_sec = (mode_usage['Idle']%3600) % 60;
		document.getElementById("idle_time").innerHTML = wk_hr.toString() + ':' + wk_mn.toString() + ':' + wk_sec.toString();
		up_hr = parseInt(jsonData['uptime']/3600);
		up_mn = parseInt((jsonData['uptime']%3600) / 60);
		up_sec = (jsonData['uptime']%3600) % 60;

		document.getElementById("up_time").innerHTML = up_hr.toString() + ' hr ' + up_mn.toString() + ' min ' + up_sec.toString() + " sec";
		// var tasks_table = document.getElementById("tasks_list");
		// Object.keys(jsonData).forEach(function(key) {
		// 	tasks_table.innerHTML += '<tr style="width: 100%;"> \
		// 	<td style="width: 60%;" class="mr-2">' + key + '</td>\
		// 	<td style="width: 40%;" class="ml-2">' + jsonData[key] + '</td>\
		// 	</tr>';	
		// });
	
		}
	);
}