function check_reg() {
	var shell = require('child_process').exec;
	return new Promise((resolve, reject) => {
		shell(__dirname + "\\engine\\doer.exe " + __dirname + " is_registered", function(err, data){
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
	var shell = require('child_process').exec;
	var email = document.getElementById("email").value;
	var password = document.getElementById("password").value;
	console.log(email, password);
	shell(__dirname + "\\engine\\doer.exe " + __dirname + ' do_reg "' + email + '" "' + password + '"', function(err, data){
		if(err){
			throw err;
		}
		console.log(data);
		if (data == 1){
			document.getElementById("eml").innerHTML = email;
			$('#regForm').modal("hide");
			$('#login_success').modal("show");
		}
		else {
			console.log("not working");
			$("#regForm").shakeit(3, 7, 800);
		}
	});
}

