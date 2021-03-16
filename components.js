const { Notification } = require('electron')


function showNotification (title, body) {
	const notification = {
		title: title,
		body: body,
	};
	new Notification(notification).show();
}
