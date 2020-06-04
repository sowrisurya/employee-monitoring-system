function get_apps_usage_time() {
	
	var python = require('child_process').exec;
	var jsonData;
	python("python ../engine/apps_usage_time.py", function(err, data){
		if(err){
			throw err;
		}
		jsonData = JSON.parse(data);
		var tasks_table = document.getElementById("tasks_list");
		Object.keys(jsonData).forEach(function(key) {
			tasks_table.innerHTML += '<tr style="width: 100%;"> \
			<td style="width: 60%;" class="mr-2">' + key + '</td>\
			<td style="width: 40%;" class="ml-2">' + jsonData[key] + '</td>\
			</tr>';	
		});
	
		}
	);
}