// Modules to control application life and create native browser window
const {app, BrowserWindow, shell} = require('electron')
const ChildProcess = require('child_process');
const {showNotification} = require('./components')

const path = require('path')
const log = require('electron-log');
const {autoUpdater} = require("electron-updater");

var processes = [];

Object.defineProperty(app, 'isPackaged', {
	get() {
		return true;
	}
});

autoUpdater.logger = log;
autoUpdater.autoDownload = true;
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
	
	showNotification("Client Application Started", "Monitoring your system has started. You will be underf supervision.");
	var newProcess = ChildProcess.exec(`"${__dirname}\\engine\\client_app\\client_app.exe" "${app.getPath("userData")}"`, (err, sout, ster) => {
		console.log(err, sout, ster)
	});
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
	console.log("Feed url: ", autoUpdater.getFeedURL())
	autoUpdater.checkForUpdates();
	app.on('activate', function () {
		// On macOS it's common to re-create a window in the app when the
		// dock icon is clicked and there are no other windows open.
		if (BrowserWindow.getAllWindows().length === 0) createWindow()
	})
})

autoUpdater.on('checking-for-update', () => {
	console.log('Checking for update...');
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

app.on('window-all-closed', function () {
	console.log("Application Closed");
	processes.forEach(function(proc) {
		proc.kill();
	});
	if (process.platform !== 'darwin') app.quit()
})