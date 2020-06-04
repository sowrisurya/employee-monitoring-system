var electronInstaller = require('electron-winstaller');

var settings = {
    appDirectory: './ems-win32-x64',
    outputDirectory: './ems-installers',
    authors: 'Sowri Surya',
    exe: './ems.exe'
};

resultPromise = electronInstaller.createWindowsInstaller(settings);
 
resultPromise.then(() => {
    console.log("The installers of your application were succesfully created !");
}, (e) => {
    console.log(`Well, sometimes you are not so lucky: ${e.message}`)
});