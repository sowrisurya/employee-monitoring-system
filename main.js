// Modules to control application life and create native browser window
const {app, BrowserWindow} = require('electron')
const ChildProcess = require('child_process');

const path = require('path')
const log = require('electron-log');
const {autoUpdater} = require("electron-updater");
const { Notification } = require('electron')


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
			devTools: true,
			preload: path.join(__dirname, 'preload.js')
		}
	});
	// mainWindow.setResizable(false);
	// mainWindow.removeMenu();
	mainWindow.loadFile('index.html');
}


function start_client_app() {
	var newProcess = ChildProcess.exec(`"${__dirname}\\engine\\client_app\\client_app.exe" "${app.getPath("userData")}"`, (err, sout, ster) => {
		console.log(err, sout, ster)
	});
	showNotification("Client Application Started", "Monitoring your system has started. You will be underf supervision.");
	processes.push(newProcess);

	newProcess.on("exit", function () {
		processes.splice(processes.indexOf(newProcess), 1);
	});
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.

app.whenReady().then(() => {
	createWindow();
	start_client_app();
	app.on('activate', function () {
		// On macOS it's common to re-create a window in the app when the
		// dock icon is clicked and there are no other windows open.
		if (BrowserWindow.getAllWindows().length === 0) createWindow()
	})
})

app.on('ready-to-show', () => {
	autoUpdater.checkForUpdatesAndNotify();
  }
);

autoUpdater.on('update-available', () => {
	mainWindow.webContents.send('update_available');
});

autoUpdater.on('update-downloaded', () => {
	mainWindow.webContents.send('update_downloaded');
});

// Quit when all windows are closed.
app.on('window-all-closed', function () {
	console.log("Application Closed");
	processes.forEach(function(proc) {
		proc.kill();
	});
	if (process.platform !== 'darwin') app.quit()
})