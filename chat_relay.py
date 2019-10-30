import re
import time
import rcon
import json
import select
import urllib3
import threading
import subprocess

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
http = urllib3.PoolManager()

def regex(reg, text):
	try:
		match = reg.match(text).groupdict()
		return match
	except (AttributeError, ValueError):
		return False


def parse_player_message(comp):
	prefix = comp['prefix']+" " if comp['prefix'] else ""
	message = comp['message']

	return f"<:Minecraft:580859447409246223> `<{prefix}{comp['username']}> {message}`"



class ChatRelay():
	def __init__(self, relay):
		self.relay = relay
		self.connection_info = relay['server_info']
		self._lock = threading.Lock()

		self.parser_que = []
		self.sender_que = []

		self.log_formats = {
			"player_message":{
			"thread_name":"Server Info",
			"message_type":"INFO",
			"regex":re.compile(r"^<(?P<prefix>\[[^\]>]+\])? ?(?P<username>[^\]>]+)> (?P<content>.+)"),
			"parser":parse_player_message
			}
		}

		threads = []
		threads.append(threading.Thread(target=self.log_thread))
		threads.append(threading.Thread(target=self.parser_thread))

		for t in threads:
			t.start()

		try:
			for t in threads:
				t.join()
		except KeyboardInterrupt:
			for t in threads:
				t.terminate()


	def log_thread(self):
			print(f"{self.relay['server_folder']}logs/latest.log")
			console = subprocess.Popen(["tail", "-F", f"{self.relay['server_folder']}logs/latest.log"], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			p = select.poll()
			p.register(console.stdout)

			while True:
				#? If there is new data, read it
				if p.poll(1):
					out = console.stdout.readline()
					#? Append New data to parser_que
					self._lock.acquire()
					self.parser_que.append(out)
					self._lock.release()
					#? Debugging
					time.sleep(0.05)

	def parser_thread(self):

		log_prefix = re.compile(r"\[(?P<timestamp>[\d:]+)\] \[(?P<full_prefix>(?P<type>Server thread|RCON Listener|User Authenticator) ?(?P<thread_id>#\d+)?\/(?P<info_type>INFO|WARN))\]: (?P<message>.+)")

		while True:
			#? Clean local ques
			local_que = []
			local_output = []
			#? Move parser_que to local_que
			self._lock.acquire()
			local_que = self.parser_que
			self.parser_que = []
			self._lock.release()

			for line in local_que:
				line = line.decode("utf-8").strip()
				timestamp, prefix, thread_name, thread_id, message_type, message = regex(log_prefix, line)

				for k, v in self.log_formats.items():
					if v['thread_name'] == thread_name and x['message_type'] == message_type:
						match = v['regex'](message)
						if match:
							x = v['parser'](match)
							print(x)
							local_output.append(x)









