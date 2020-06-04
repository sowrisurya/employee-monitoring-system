function aut_yes(mode) {

	var shell = require('child_process').exec;
	shell(__dirname + "\\engine\\doer.exe " + __dirname + " active", function(err, data){
		if(err){
			throw err;
		}
		document.getElementById("aut_dialog").style.visibility = 'hidden';
		}
	);
}