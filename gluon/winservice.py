"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
and Limodou <limodou@gmail.com>
License: GPL v2
"""
import time, os
import win32serviceutil
import win32service
import win32event
import servicemanager
import _winreg
from main import HttpServer

__all__=['web2py_windows_service_handler']

class Service(win32serviceutil.ServiceFramework):
	_svc_name_ = '_unNamed'
	_svc_display_name_ = '_Service Template'
	def __init__(self, *args):
		win32serviceutil.ServiceFramework.__init__(self, *args)
		self.stop_event = win32event.CreateEvent(None, 0, 0, None)
	def log(self, msg):		
		servicemanager.LogInfoMsg(str(msg))
	def SvcDoRun(self):
		self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
		try:
			self.ReportServiceStatus(win32service.SERVICE_RUNNING)
			self.start()
			win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
		except Exception, x:
			self.log('Exception : %s' % x)
			self.SvcStop()
	def SvcStop(self):
		self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
		self.stop()
		win32event.SetEvent(self.stop_event)
		self.ReportServiceStatus(win32service.SERVICE_STOPPED)
	# to be overridden
	def start(self): pass
	# to be overridden
	def stop(self): pass

class Web2pyService(Service):
    _svc_name_ = 'web2py'
    _svc_display_name_ = 'web2py service'
    server = None
    
    def start(self):
        self.log("web2py server starting")
        try:
            h = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\web2py')
            cls = _winreg.QueryValue(h, 'PythonClass')
            dir = os.path.dirname(cls)
            os.chdir(dir)
        except:
            self.log("Cann't change to web2py working path, server is stopped")
            return
        try:
             exec('import options')
        except:
             print 'Error: unable to open or parse options.py'
        self.server = HttpServer(ip=options.ip,port=options.port,password=options.password,
                          pid_filename=options.pid_filename,
                          log_filename=options.log_filename,
                          ssl_certificate=options.ssl_certificate,
                          ssl_private_key=options.ssl_private_key,
                          numthreads=options.numthreads,
                          server_name=options.server_name,
                          request_queue_size=options.request_queue_size,
                          timeout=options.timeout,
                          shutdown_timeout=options.shutdown_timeout,
                          path=options.path)
        try: 
            self.server.start()
        except KeyboardInterrupt:
            self.server.stop()
            self.server = None
            
    def stop(self):
        self.log("web2py server stopping")
        if self.server:
            self.server.stop()
        time.sleep(1)

def web2py_window_service_handler():
    win32serviceutil.HandleCommandLine(Web2pyService)

if __name__=='__main__':
    web2py_windows_service_handler():
