import json, datetime, sys, requests, os
import sqlite3
from typing import List

class DbConnector():
	def __init__(self, name="engine.db", init = True):
		self.name = name
		if init:
			self.init()

	def init(self):
		try:
			self.conn = sqlite3.connect(self.name, check_same_thread=False, detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
			self.conn.isolation_level = None
			self.transaction(commands = [
				""" CREATE TABLE IF NOT EXISTS kv_pair (key STRING primary key ON CONFLICT REPLACE, value STRING); """,
				""" CREATE TABLE IF NOT EXISTS user_active_status (start_time TIMESTAMP, end_time TIMESTAMP, mode INT, active BOOLEAN, uploaded BOOLEAN DEFAULT 0) """,
				""" CREATE TABLE IF NOT EXISTS browser_history (url TEXT, description TEXT, visit_time DATETIME, visit_count INT)""",
				""" CREATE TABLE IF NOT EXISTS user_apps_usage (app_name STRING, date DATE, usage_time REAL DEFAULT 0, uploaded BOOLEAN DEFAULT 0) """,
				]
			)

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
			print(f"Error executing command {command} in DB. {e}")

	def fetch_one(self, command: str):
		try:
			cursor = self.conn.cursor()
			ftchr = cursor.execute(command)
			return ftchr.fetchone()
		except Exception as e:
			print(f"Error executing command {command} in DB. {e}")

	def fetch_all(self, command: str):
		try:
			cursor = self.conn.cursor()
			ftchr = cursor.execute(command)
			return ftchr.fetchall()
		except sqlite3.OperationalError:
			pass
		except Exception as e:
			print(f"Error executing command {command} in DB. {e}")
	
	def close(self):
		try:
			self.conn.close()
		except Exception as e:
			pass

if len(sys.argv) < 3:
	exit()

dir_name = str(sys.argv[1])
def get_usage_data():
	db_conn = DbConnector(name = f"{dir_name}\\engine.db")

	data = db_conn.fetch_all(f"SELECT * FROM user_active_status WHERE start_time > '{datetime.date.today()}';")
	modes = {'1': 'Working', '2': "Conference", '3': "Call", '4': "Idle"}
	mode_time = {'Working': 0, "Conference": 0, "Call": 0, "Idle": 0}
	usage = []

	for times in data:
		on_time = int((times[1] - times[0]).total_seconds())
		usage.append([
			modes[str(times[2])],
			times[0].strftime("%I:%M %p"),
			( str(datetime.timedelta(seconds = on_time)) if on_time else "<5" )
		])
		mode_time[modes[str(times[2])]] += on_time

	aut = db_conn.fetch_one("SELECT value FROM kv_pair where key='aut';")

	out = {"data": usage, "modes": mode_time, "uptime": sum([ value for key, value in mode_time.items() ]), "aut": aut}
	out["apps"] = {}
	for app_name, usage_time in db_conn.fetch_all(f"SELECT app_name, usage_time FROM user_apps_usage WHERE date = '{datetime.date.today()}'; "):
		out["apps"][app_name] = usage_time

	cr = db_conn.fetch_one(""" SELECT value FROM kv_pair WHERE key='mode'; """)
	mode = int(cr[0])
	out['mode'] = mode
	print(json.dumps(out))

process = str(sys.argv[2])
if process == "get_data":
	get_usage_data()

elif process == "mode_change":
	mode = sys.argv[3]
	db_conn = DbConnector(name = f"{dir_name}\\engine.db")
	db_conn.execute(f""" UPDATE kv_pair SET value = '{mode}' where key = 'mode'; """, commit = True)

elif process == "active":
	db_conn = DbConnector(name = f"{dir_name}\\engine.db")
	db_conn.execute("UPDATE kv_pair SET VALUE = 0 WHERE key = 'aut';", commit = True)

elif process == "is_registered":
	db_conn = DbConnector(name = f"{dir_name}\\engine.db")
	is_reg = db_conn.fetch_one("SELECT value FROM kv_pair WHERE key='register';")
	if is_reg and is_reg[0] == 1:
		print(1)
	else:
		print(0)

elif process == "do_reg":
	db_conn = DbConnector(name = f"{dir_name}\\engine.db")
	email = str(sys.argv[3])
	pass_word = str(sys.argv[4])
	query = f'query doLogin{{ login(email: "{email}", password: "{pass_word}"){{ token }} }}'
	res = requests.post(url = "https://ems.cloudadda.com/api/", json = {'query': query})
	if res.status_code == 200:
		resp = res.json()
		if resp.get("data", None) and resp["data"].get("login", None) and resp["data"]["login"].get('token', None) and resp["data"]["login"]["token"]:
			token = resp["data"]["login"]["token"]
			if token != "0":
				db_conn.transaction(commands = [
					"INSERT INTO kv_pair (key, value) VALUES ('register', 1) ON CONFLICT(key) DO UPDATE set value = 1;",
					f"INSERT INTO kv_pair (key, value) VALUES ('email', '{email}') ON CONFLICT(key) DO UPDATE set value = '{email}'; ", 
					f"INSERT INTO kv_pair (key, value) VALUES ('token', '{token}') ON CONFLICT(key) DO UPDATE set value = '{token}';",
				])
				print(1)
			else:
				print(0)
		else:
			print(0)
	else:
		print(0)

elif process == "check_stealth_mode":
	file_name = f"{dir_name}\\config.json"
	if os.path.isfile(file_name):
		with open(file_name) as fl:
			data = json.load(fl)
			if "sm" in data and data["sm"]:
				print(1)
			else:
				print(0)
	else:
		print(0)

sys.stdout.flush()