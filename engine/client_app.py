import datetime
import time
from mss import mss
import boto3
import glob
import os
import threading
import sqlite3
from pywinauto import Desktop
import json
from pynput import keyboard
import sys
import requests
import win32api

strokes = []

ROOT_DIR = sys.argv[1]
# ROOT_DIR = "."

class KeyStrokeWriter(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.date = str(datetime.datetime.now().date())
		self.start_time = str(datetime.datetime.now().strftime("%H %M %S"))
		self.interval_time = 20
		self.kill = False
		print("Created Key stroke writer thread")

	def run(self):
		print("Started Key stroke writer thread")
		global strokes
		while True:
			with open(ROOT_DIR + "\\engine\\user_data\\{}\\{}".format(self.date, self.start_time), 'a+') as fl:
				fl.writelines(strokes)
			strokes = []
			if self.kill:
				print("stopped keyboard thread")
				break
			time.sleep(self.interval_time)

class key_stroke_listener(threading.Thread):
	def __init__(self, mode):
		threading.Thread.__init__(self)
		self.mode = mode
		self.kill = False
		self.listener = keyboard.Listener(on_press=self.on_press)
		self.writer = KeyStrokeWriter()
		print("Created keyboard listener thread")

	def on_press(self, key):
		global strokes
		strokes.append(str(key).replace("Key.", "").replace("'", "")+"\n")

	def start_logger(self):
		self.listener.start()
		self.writer.start()

	def run(self):
		print("Started keyboard listener thread")
		if self.mode in [1, 4]:
			self.start_logger()
			while True and not self.kill:
				time.sleep(2)
			self.listener.stop()
			self.writer.kill = True
			print("Stopped Key stroke listener")
		else:
			print("No need to run key stroke logger in this mode")

class screen_shot_capture(threading.Thread):
	def __init__(self, mode, interval_time = 5):
		threading.Thread.__init__(self)
		self.kill = False
		self.mode = mode
		self.interval_time = interval_time
		self.date = str(datetime.datetime.now().date())
		print("Created screen shot capture thread")

	def capture_screen(self):
		with mss() as sct:
			sct.shot(output = ROOT_DIR + '\\engine\\user_data\\{}\\images/{}.png'.format(self.date, str(datetime.datetime.now().time().strftime("%H %M %S"))))

	def run(self):
		print("Started screen shot capture thread")
		if self.mode in [1, 2]:
			while True and not self.kill:
				self.capture_screen()
				time.sleep(self.interval_time)
			print("Stopped css thread")
		else:
			print("No need to run screen shot capturer in this mode")

class app_usage_tracking(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.date = str(datetime.datetime.now().date())
		self.opened_apps = ( dict(json.load(open(ROOT_DIR + "\\engine\\user_data\\{}\\apps_usage.json".format(self.date), 'r'))) if os.path.isfile(ROOT_DIR + "\\engine\\user_data\\{}\\apps_usage.json".format(self.date)) else {})
		self.interval_time = 5
		self.kill = False
		print("Created App usage tracker thread")

	def get_opened_apps(self):
		for app in [ w.window_text().split("- ")[-1] for w in Desktop(backend="uia").windows() if w.window_text() not in ('', 'Taskbar') ]:
			if app in self.opened_apps.keys():
				self.opened_apps[app] += self.interval_time
			else:
				self.opened_apps[app] = 0
			json.dump(dict(self.opened_apps), open(ROOT_DIR + '\\engine\\user_data\\{}\\apps_usage.json'.format(self.date), "w+"))
		self.opened_apps = {k: v for k,v in sorted(self.opened_apps.items(), key=lambda kv: kv[1], reverse=True)}

	def run(self):
		print("Started App usage tracker thread")
		while True and not self.kill:
			self.get_opened_apps()
			time.sleep(self.interval_time)
		print("Stopped app usage tracking thread")

class browser_track_history(threading.Thread):
	def __init__(self, mode):
		threading.Thread.__init__(self)
		self.kill = False
		self.interval_time = 5
		self.mode = mode
		self.db_loc = r'C:\Users\{}\AppData\Local\Microsoft\Edge Beta\User Data\Default\History'.format(win32api.GetUserName())
		print("Created browser history tracker thread")

	def run(self):
		print("Started browser history tracker thread")
		if self.mode in [1,4]:
			conn = sqlite3.connect(ROOT_DIR + "\\engine\\test.db")
			now = (datetime.datetime.now().timestamp() + 11644473600) * (10**6)
			while True and not self.kill:
				try:
					con = sqlite3.connect(self.db_loc)
					c = con.cursor()
					c.execute("select url, title, visit_count, datetime(last_visit_time/1e6-11644473600,'unixepoch','localtime') from urls WHERE last_visit_time > {} ORDER BY last_visit_time DESC LIMIT 10".format(now)) #Change this to your prefered query
					results = c.fetchall()
					for r in results:
						conn.execute("INSERT INTO browser_history(url, description, visit_time, visit_count) VALUES ('{}', '{}', '{}', {})".format(r[0], r[1], r[3], r[2]))
						conn.commit()
					now = (datetime.datetime.now().timestamp() + 11644473600) * (10**6)
					time.sleep(5)
				except sqlite3.OperationalError:
					time.sleep(10)
					# print("Cannot open databse")
					pass
			print("Stopped browser tracking history thread")
		else:
			print("No need to run browser history tracker in this mode")

class user_client(threading.Thread):
	def __init__(self, mode = 4, interval_time = 5):
		threading.Thread.__init__(self)
		self.date = str(datetime.datetime.now().date())
		if not os.path.isdir(ROOT_DIR + '\\engine\\user_data\\' + self.date):
			os.mkdir(ROOT_DIR + '\\engine\\user_data\\{}'.format(self.date))
			os.mkdir(ROOT_DIR + '\\engine\\user_data\\{}\\images'.format(self.date))
		self.start_time = datetime.datetime.now().time().strftime("%H %M %S")
		self.interval_time = interval_time
		self.exit_time = datetime.datetime.now().time().strftime("%H %M %S")
		self.config = json.load(open(ROOT_DIR + "\\engine\\config.json"))
		self.run_tasks = {}
		self.max_interval_idle = 120
		self.idle_time = 0

		self.mode = mode
		self.modes_tasks = [ ['css', 'ak', 'bth', 'aut'], ['css', 'aut'], ['aut'], ['css', 'aut', 'bth'] ]
		if self.config['css'] and 'css' in self.modes_tasks[self.mode-1]:
			self.run_tasks['css'] = screen_shot_capture(mode = self.mode)
		if self.config['ak'] and 'ak' in self.modes_tasks[self.mode-1]:
			self.run_tasks['ak'] = key_stroke_listener(mode = self.mode)
		if self.config['bth'] and 'bth' in self.modes_tasks[self.mode-1]:
			self.run_tasks['bth'] = browser_track_history(mode = self.mode)
		if self.config['aut'] and 'aut' in self.modes_tasks[self.mode-1]:
			self.run_tasks['aut'] = app_usage_tracking()
		self.kill = False
		conn = sqlite3.connect(ROOT_DIR + "\\engine\\test.db")
		conn.execute(""" INSERT INTO user_active_status (date, start_time, end_time, mode) VALUES ('{}', '{}', '{}', {}); """.format(self.date, self.start_time, self.exit_time, self.mode))
		conn.commit()
		conn.execute("""INSERT INTO kv_pair (key, value) VALUES('mode', '{0}') ON CONFLICT(key) DO UPDATE SET value='{0}';""".format(self.mode))
		conn.execute("""INSERT INTO kv_pair (key, value) VALUES('aut', '0') ON CONFLICT(key) DO UPDATE SET value='0';""")
		conn.commit()
		conn.close()
		print("Started User Monitoring")

	def add_usage_data(self):
		self.exit_time = datetime.datetime.now().strftime("%H %M %S")
		conn = sqlite3.connect(ROOT_DIR + '\\engine\\test.db')
		conn.execute(""" UPDATE user_active_status SET end_time = '{}' WHERE date = '{}' and start_time = '{}' and mode={}; """.format(self.exit_time, self.date, self.start_time, self.mode))
		conn.commit()
		conn.close()

	def kill_child_threads(self):
		for task in self.run_tasks:
			self.run_tasks[task].kill = True

	def is_working(self):
		conn = sqlite3.connect(ROOT_DIR + '\\engine\\test.db')
		global strokes
		if len(strokes) < 1:
				self.idle_time += self.interval_time
		else:
			self.idle_time = 0
		if self.idle_time > self.max_interval_idle:
			print("Are you there")
			conn.execute("UPDATE kv_pair SET value=1 WHERE key = 'aut';")
			conn.commit()
			st = time.perf_counter()
			act = False
			while time.perf_counter() - st < 25 and not act:
				cr = conn.execute("SELECT value FROM kv_pair WHERE key = 'aut';")
				# dt = cr.fetchall()
				if int(cr.fetchone()[0]) == 0:
					self.idle_time = 0
					print("fine you are")
					return True
				time.sleep(1)
			if not act:
				print("nope you aren't")
				conn.execute("UPDATE kv_pair SET value=0 WHERE key = 'aut';")
				conn.commit()
				return False
		return True

	def run(self):
		global strokes
		print("IN {} mode".format(['Working', "Conference", "Call", "Idle / Personal Work"][self.mode-1]))
		for task in self.run_tasks:
			self.run_tasks[task].start()
		while True:
			self.add_usage_data()
			if self.kill:
				print("stopped main thread with mode = {}".format(self.mode))
				self.kill_child_threads()
				break
			else:
				if self.mode == 1 and 'ak' in self.run_tasks:
					if not self.is_working():
						self.kill = True
				time.sleep(self.interval_time)
		print("Stopped user client thread")

class user_image_uploader(threading.Thread):
	def __init__(self, email):
		threading.Thread.__init__(self)
		self.email = email
		self.__bucket_name = "usermonitoringimages"
		self.session = boto3.Session(
			aws_access_key_id = "AKIAXJ3ESTWNQQ2MGMX3",
			aws_secret_access_key = "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"
		)
		self.s3_bucket_client = self.session.client('s3')
		self.base_url = "http://127.0.0.1:8000/api/"
		print("Started Image uploading service.")

	def add_browser_data(self):
		conn = sqlite3.connect(ROOT_DIR + '\\engine\\test.db')
		cr = conn.execute("SELECT * FROM browser_history")
		data = cr.fetchall()
		for db in data:
			query = 'mutation add_browser_usage{addBrowserUsage(email: "' + self.email + '", url: "' + db[0] +'", description: "' + db[1] + '", visitTime: "' + db[2] + '", vstCnt: ' + str(db[3]) + ') { result } }'
			res = requests.post(url = self.base_url, data = {'query': query})
		conn.execute("DELETE FROM browser_history;")
		conn.commit()
		conn.close()

	def run(self):
		while True:
			self.add_browser_data()
			img_fls = glob.glob(ROOT_DIR + "\\engine\\user_data\\*\\images\\*.png")
			dat_files = glob.glob(ROOT_DIR + "\\engine\\user_data\\*\\*")
			for file in img_fls:
				self.s3_bucket_client.upload_file(file, self.__bucket_name, self.email + file.split("user_data")[1].replace("\\", "/"))
				os.remove(file)
			for file in dat_files:
				nm = file.split("user_data")[1]
				if not nm.startswith("\\{}".format(datetime.datetime.now().date())) and "images" not in nm:
					self.s3_bucket_client.upload_file(file, self.__bucket_name, self.email + file.split("user_data")[1].replace("\\", "/"))
					try:
						os.remove(file)
					except:
						os.rmdir(file)
			time.sleep(60)


class mode_listener(threading.Thread):
	def __init__(self, mode = 4):
		threading.Thread.__init__(self)
		self.monitor_thread = user_client(mode = mode)
		self.base_url = "http://127.0.0.1:8000/api/"
		conn = sqlite3.connect(ROOT_DIR + '\\engine\\test.db')
		cr = conn.execute("SELECT value FROM kv_pair WHERE key = 'email';")
		self.email = cr.fetchone()[0]
		conn.close()

	def stop_main_thread(self):
		self.monitor_thread.kill = True
		# self.monitor_thread.join()

	def create_new_thread(self, mode):
		self.monitor_thread = user_client(mode = mode)
	
	def start_new_thread(self):
		self.monitor_thread.start()

	def upload_usage_data(self):
		crnt_date = datetime.datetime.now().date()

		conn = sqlite3.connect(ROOT_DIR + '\\engine\\test.db')
		cr = conn.execute("SELECT * FROM user_active_status WHERE date != '{}';".format(crnt_date))
		data = cr.fetchall()
		data = [ (_[0], str(datetime.datetime.strptime(_[1], '%H %M %S').time()), int((datetime.datetime.strptime(_[2], '%H %M %S') - datetime.datetime.strptime(_[1], '%H %M %S')).total_seconds()), _[3]) for _ in data ]
		for db in data:
			query = 'mutation add_user_usage{addUserUsage(email: "' + self.email + '", date: "' + db[0] + '", startTime: "' + db[1] + '", workTime: ' + str(db[2]) + ", mode: " + str(db[3]) + ") { result } } "
			res = requests.post(url = self.base_url, data = {'query': query})
			conn.execute("DELETE FROM user_active_status WHERE date != '{}';".format(crnt_date))
			conn.commit()
		conn.close()

	def run(self):
		if self.email:
			print("Please wait while syncing data to the cloud")
			self.upload_usage_data()
			print("Finished Uploading data to the server")
			self.monitor_thread.start()
			conn = sqlite3.connect(ROOT_DIR + "\\engine\\test.db")
			cr = conn.execute(""" SELECT value FROM kv_pair WHERE key='mode'; """)
			crnt_mode = int(cr.fetchone()[0])
			while True:
				cr = conn.execute(""" SELECT value FROM kv_pair WHERE key='mode'; """)
				ch_mode = int(cr.fetchone()[0])
				if ch_mode != crnt_mode:
					self.stop_main_thread()
					self.create_new_thread(mode = ch_mode)
					self.start_new_thread()

				if self.monitor_thread.kill: # The thread will only be killed iff the thread mentions it to do (in this desktop is unresponsive. So switching back to idle)
					self.stop_main_thread()
					self.create_new_thread(mode = 4) 
					self.start_new_thread()
				crnt_mode = ch_mode
				time.sleep(1)
		else:
			print("The app is unregistered. Please download from the site again.")

if __name__ == "__main__":
	conn = sqlite3.connect(ROOT_DIR + '\\engine\\test.db')
	conn.execute(""" CREATE TABLE IF NOT EXISTS kv_pair (key STRING primary key, value STRING); """)

	conn.execute(""" CREATE TABLE IF NOT EXISTS user_active_status (date DATE, start_time TIME, end_time TIME, mode INT)""")
	conn.execute(""" CREATE TABLE IF NOT EXISTS browser_history (url TEXT, description TEXT, visit_time DATETIME, visit_count INT)""")
	
	cr = conn.execute("SELECT value FROM kv_pair WHERE key = 'email';")
	email = cr.fetchone()
	if email == None:
		print("not working")
		conn.execute("INSERT INTO kv_pair (key, value) VALUES ('register', 0) ON CONFLICT(key) DO UPDATE set value = 0;")
	else:
		email = email[0]
		if not os.path.isfile(ROOT_DIR + "\\engine\\config.json"):
			query = 'query getConfig{ getConfig(email: "' + email + '"){ role, css, ak, aut, bth, sm } }'
			res = requests.post(url = "http://127.0.0.1:8000/api/", data = {'query': query})
			resp = json.loads(res.text)['data']['getConfig'][0]
			config = {"role": resp['role'], "css": resp['css'], "ak": resp['ak'], "bth": resp['bth'], "aut": resp['aut'], "sm": resp['sm'] }
			json.dump(config, open(ROOT_DIR + "\\engine\\config.json", "w+"))
		conn.execute("INSERT INTO kv_pair (key, value) VALUES ('register', 1) ON CONFLICT(key) DO UPDATE set value = 1;")
		conn.execute("DELETE FROM kv_pair WHERE key != 'email' and key != 'register';")
		conn.commit()
		image_uploader_thread = user_image_uploader(email)
		md_lstn_thread = mode_listener(mode = 4)

		image_uploader_thread.start()
		md_lstn_thread.start()	
	# conn.close()