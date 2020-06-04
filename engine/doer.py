import json
import datetime
import sys
import sqlite3
import requests 

dir_name = str(sys.argv[1])
# dir_name = "."
conn = sqlite3.connect(dir_name + '\\engine\\test.db')

def get_usage_data():
	cr = conn.execute("SELECT * FROM user_active_status WHERE date = '{}';".format(datetime.datetime.now().date()))
	data = cr.fetchall()
	modes = {'1': 'Working', '2': "Conference", '3': "Call", '4': "Idle"}
	mode_time = {'Working': 0, "Conference": 0, "Call": 0, "Idle": 0}
	usage = []

	for times in data:
		on_time = (datetime.datetime.strptime(times[2], "%H %M %S") - datetime.datetime.strptime(times[1], "%H %M %S")).seconds
		usage.append([ modes[str(times[3])], times[1].replace(" ", ":"), ( str(datetime.timedelta(seconds=on_time)) if on_time else "<5" )])
		mode_time[modes[str(times[3])]] += on_time

	cr = conn.execute("SELECT value FROM kv_pair where key='aut';")
	aut = cr.fetchone()

	out = {"data": usage, "modes": mode_time, "uptime": sum([ value for key, value in mode_time.items() ]), "aut": aut}

	out["apps"] = json.load(open(dir_name + "\\engine\\user_data\\{}\\apps_usage.json".format(str(datetime.datetime.now().date()))))

	cr = conn.execute(""" SELECT value FROM kv_pair WHERE key='mode'; """)
	mode = int(cr.fetchone()[0])
	out['mode'] = mode

	print(json.dumps(out))

process = str(sys.argv[2])
if process == "get_data":
	get_usage_data()

elif process == "mode_change":
	mode = sys.argv[3]
	conn.execute(""" UPDATE kv_pair SET value = '{}' where key = 'mode'; """.format(mode))
	conn.commit()

elif process == "active":
	conn.execute("UPDATE kv_pair SET VALUE = 0 WHERE key = 'aut';")
	conn.commit()
	conn.close()

elif process == "is_registered":
	cr = conn.execute("SELECT value FROM kv_pair WHERE key='register';")
	is_reg = cr.fetchone()
	# is_reg = None
	if is_reg == None:
		print(0)
	else:
		print(1)

elif process == "do_reg":
	email = str(sys.argv[3])
	pass_word = str(sys.argv[4])
	resp = requests.post
	query = 'query doLogin{ isLoginTrue(email: "' + email + '", password: "' + pass_word + '"){ result } }'
	res = requests.post(url = "http://127.0.0.1:8000/api/", data = {'query': query})
	resp = json.loads(res.text)
	if resp['data']['isLoginTrue'][0]['result'] == "1":
		conn.execute("INSERT INTO kv_pair (key, value) VALUES ('register', 1) ON CONFLICT(key) DO UPDATE set value = 1;")
		conn.execute("INSERT INTO kv_pair (key, value) VALUES ('email', '{}') ON CONFLICT(key) DO UPDATE set value = '{}';".format(email, email))
		conn.commit()
		print(1)
	else:
		print(0)

sys.stdout.flush()