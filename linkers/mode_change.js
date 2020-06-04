function change_mode(mode) {
	console.log("Changing mode");
	document.getElementById('wh_md').innerHTML = ( (mode == 1) ? 'Working' : ((mode == 2) ? 'Conference' : ((mode == 3) ? 'Call' : "Idle")));
	var shell = require('child_process').exec;
	shell(__dirname + "\\engine\\doer.exe " + __dirname +  " mode_change " + mode.toString(), function(err, data){
		if(err){
			throw err;
		}
		}
	);
}