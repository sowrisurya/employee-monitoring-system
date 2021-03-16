from pywinauto import Desktop

windows = Desktop(backend="uia").windows()
print([ _ for w in windows if (_ := w.window_text()) if (_ != "")])

titles = []
try:
	import ctypes
	
	EnumWindows = ctypes.windll.user32.EnumWindows
	EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
	GetWindowText = ctypes.windll.user32.GetWindowTextW
	GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
	IsWindowVisible = ctypes.windll.user32.IsWindowVisible
	def foreach_window(hwnd, lParam):
		if IsWindowVisible(hwnd) == 1:
			length = GetWindowTextLength(hwnd)
			buff = ctypes.create_unicode_buffer(length + 1)
			GetWindowText(hwnd, buff, length + 1)
			if buff.value != "" and buff.value not in titles:
				titles.append(buff.value)
		return True
	EnumWindows(EnumWindowsProc(foreach_window), 0)
except ImportError:
	pass
print(titles)
