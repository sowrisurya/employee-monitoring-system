const {app, BrowserWindow} = require('electron')
const ChildProcess = require('child_process');
const AutoLaunch = require('auto-launch');
const path = require('path')
const log = require('electron-log');
const {autoUpdater} = require("electron-updater");
const { Notification } = require('electron')
var autoLauncher = new AutoLaunch({
    name: "Employee Monitoring System"
});

autoLauncher.isEnabled().then(function(isEnabled) {
	if (isEnabled) {
		return;
	}
	autoLauncher.enable();
}).catch(function (err) {
	throw err;
});

function showNotification (title, body) {
	const notification = {
		title: title,
		body: body,
	};
	new Notification(notification).show();
}

var processes = [];

// require('electron-reload')(__dirname);
autoUpdater.logger = log;
autoUpdater.logger.transports.file.level = 'info';
log.info('App starting...');

function createWindow () {
	const mainWindow = new BrowserWindow({
		width: 480,
		height: 640,
		frame: false,
		webPreferences: {
			nodeIntegration: true,
			nodeIntegrationInWorker	: true,
			devTools: false,
			preload: path.join(__dirname, 'preload.js')
		}
	});
	mainWindow.setResizable(false);
	mainWindow.removeMenu();
	mainWindow.loadFile('index.html');
}

function start_client_app() {
	var newProcess = ChildProcess.exec(`"${__dirname}\\engine\\client_app\\client_app.exe" "${app.getPath("userData")}"`, (err, sout, ster) => {
		console.log(err, sout, ster)
	});
	processes.push(newProcess);

	newProcess.on("exit", function () {
		processes.splice(processes.indexOf(newProcess), 1);
	});
}

function check_stealth_mode() {
	var done = false;
	return new Promise((resolve, reject) => {
		ChildProcess.exec(`"${__dirname}\\engine\\doer\\doer.exe" "${app.getPath("userData")}" check_stealth_mode`, function(err, data){
			if (data == 1)
				done = true;
			resolve(done);
		});
	});
}

let isSingleInstance = app.requestSingleInstanceLock()
if (!isSingleInstance) {
	app.quit()
} else {
	app.whenReady().then(async () => {
		if (isSingleInstance) {
			autoUpdater.checkForUpdatesAndNotify();
			start_client_app();
			const is_stealth_mode = await check_stealth_mode();
			if (!is_stealth_mode){
				createWindow();
			}
			app.on('activate', function () {
				if (BrowserWindow.getAllWindows().length === 0) createWindow()
			});	
		}
	})
}

autoUpdater.on('checking-for-update', () => {
});
autoUpdater.on('update-not-available', () => {
});

autoUpdater.on('update-available', () => {
	showNotification("Update Available", "New update will be downloaded and wil get installed automatically.")
});

autoUpdater.on('update-downloaded', () => {
	showNotification("Update Downloaded", "Application will now quit and start the installation of the new Update.")
	autoUpdater.quitAndInstall(true, true);
});

// Quit when all windows are closed.
app.on('window-all-closed', function () {
	processes.forEach(function(proc) {
		proc.kill();
	});
	if (process.platform !== 'darwin') app.quit()
})