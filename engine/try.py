# import time
# import ctypes

# user32 = ctypes.windll.User32
# DESKTOP_SWITCHDESKTOP = 0x0100

# # user32.LockWorkStation ()
# #
# # Slight pause to overcome what appears to
# # be a grace period during which a switch
# # *will* succeed.
# #
# time.sleep (1.0)

# crnt_num = None
# while 1:
# 	# print(user32.GetForegroundWindow() == 0)
# 	tmp = (user32.GetForegroundWindow() == 0)
# 	if tmp != crnt_num:
# 		print(time.asctime(),tmp)
# 		crnt_num = tmp
# 	time.sleep (0.1)

import subprocess, time

a = subprocess.Popen("timeout 100", shell = True)
time.sleep(5)
print("Hello")
a.kill()
print("World")
