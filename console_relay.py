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

class ConsoleRelay():
	def parse_player_message(self, comp):
		prefix = comp['prefix']+" " if comp.get('prefix') else ""
		content = self.message_formats['player_message']
		content = content\
			.replace("$PREFIX$", prefix)\
			.replace("$USERNAME$", comp['username'])\
			.replace("$CONTENT$", comp['content'])
		return {"content":content}

	def parse_player_me(self, comp):
		prefix = comp['prefix']+" " if comp.get('prefix') else ""
		content = self.message_formats['player_/me']
		content = content\
			.replace("$PREFIX$", prefix)\
			.replace("$USERNAME$", comp['username'])\
			.replace("$CONTENT$", comp['content'])
		return {"content":content}

	def parse_player_change(self, comp):
		prefix = comp['prefix']+" " if comp.get('prefix') else ""
		content = self.message_formats['player_change']
		content = content\
			.replace("$PREFIX$", prefix)\
			.replace("$USERNAME$", comp['username'])\
			.replace("$ACTION_EMOJI$", '<:joined:580872620598362113>' if comp['action'] == 'joined' else '<:left:580872521599942683>')\
			.replace("$ACTION$", comp['action'])
		return {"content":content}

	def parse_server_starting(self, comp):
		content = self.message_formats['server_starting']
		content = content\
			.replace("$VERSION$", comp['version'])
		return {"content":content}

	def parse_server_started(self, comp):
		content = self.message_formats['server_started']
		content = content\
			.replace("$TIME$", comp['time'])
		return {"content":content}

	def parse_server_stopped(self, comp):
		content = self.message_formats['server_stopped']
		return {"content":content}

	def parse_authentication_uuid(self, comp):
		prefix = comp['prefix']+" " if comp.get('prefix') else ""
		content = self.message_formats['authentication_uuid']
		content = content\
			.replace("$PREFIX$", prefix)\
			.replace("$USERNAME$", comp['username'])\
			.replace("$UUID$", comp['uuid'])
		return {"content":content}

	def parse_authentication_info(self, comp):
		prefix = comp['prefix']+" " if comp.get('prefix') else ""
		content = self.message_formats['authentication_info']
		content = content\
			.replace("$PREFIX$", prefix)\
			.replace("$USERNAME$", comp['username'])\
			.replace("$IP$", comp['ip'])\
			.replace("$PORT$", comp['port'])\
			.replace("$ENTITY_ID$", comp['entity_id'])\
			.replace("$POS$", comp['pos'])
		return {"content":content}

	def parse_rcon_connection(self, comp):
		content = self.message_formats['rcon_connection']
		content = content\
			.replace("$IP$", comp['ip'])
		return {"content":content}

	def parse_player_moved_wrongly(self, comp):
		content = self.message_formats['player_moved_wrongly']
		content = content\
			.replace("$USERNAME$", comp['username'])
		return {"content":content}

	def parse_player_moved_too_quickly(self, comp):
		content = self.message_formats['player_moved_too_quickly']
		content = content\
			.replace("$USERNAME$", comp['username'])\
			.replace("$POS$", ' '.join(comp['pos'].split(',')))
		return {"content":content}

	def parse_server_overloaded(self, comp):
		content = self.message_formats['server_overloaded']
		content = content\
			.replace("$MILLISECONDS$", comp['milliseconds'])\
			.replace("$TICKS$", comp['ticks'])
		return {"content":content}

	def parse_player_disconnection_info(self, comp):
		content = self.message_formats['player_disconnection_info']
		properties = comp['properties'] if comp['properties'] else ""
		content = content\
			.replace("$ID$", comp['id'])\
			.replace("$USERNAME$", comp['username'])\
			.replace("$PROPERTIES$", properties)\
			.replace("$LEGACY$", comp['legacy'])\
			.replace("$IP$", comp['ip'])\
			.replace("$PORT$", comp['port'])\
			.replace("$REASON$", comp['reason'])
		return {"content":content}

	def parse_player_trigger(self, comp):
		content = self.message_formats['player_trigger']
		value = comp['value'] if comp['value'] else "1"
		content = content\
			.replace("$USERNAME$", comp['username'])\
			.replace("$OBJECTIVE$", comp['objective'])\
			.replace("$VALUE$", value)
		return {"content":content}

	def update_config(self, relay):
		self.relay = relay
		self.connection_info = relay['server_info']
		self.message_formats = relay['connections']['console_relay']['message_formats']

	def __init__(self, relay):
		self.update_config(relay)
		self._lock = threading.Lock()
		self.FINISH = False

		self.parser_que = []
		self.sender_que = []


		self.log_formats = {
			"player_message":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"^<(?P<prefix>\[[^\]>]+\])? ?(?P<username>[^\]>]+)> (?P<content>.+)"),
			"parser":self.parse_player_message
			},
			"player_/me":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"^\* (?P<prefex>\[[^\]]\])? ?(?P<username>[\S]+) (?P<content>.+)$"),
			"parser":self.parse_player_me
			},
			"player_change":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"^(?P<prefex>\[[^\]]\])? ?(?P<username>[\S]+) (?P<action>joined|left) the game"),
			"parser":self.parse_player_change
			},
			"server_started":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"Done \((?P<time>[\d\.]+s)\)\! For help, type \"help\""),
			"parser":self.parse_server_started
			},
			"server_stopped":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"^(?P<placeholder>Stopping) server$"),
			"parser":self.parse_server_stopped
			},
			"server_starting":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"^Starting minecraft server version (?P<version>.+)"),
			"parser":self.parse_server_starting
			},
			"player_authentication_uuid":{
			"thread_name":"User Authenticator",
			"message_type":"INFO",
			"regex":re.compile(r"^UUID of player (?P<prefix>\[[^\]>]+\])? ?(?P<username>[^\]>]+) is (?P<uuid>.+$)"),
			"parser":self.parse_authentication_uuid
			},
			"player_authentication_info":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"^(?P<username>.+)\[\/(?P<ip>[\d\.]+)\:(?P<port>\d+)\] logged in with entity id (?P<entity_id>\d+) at \((?P<pos>[\d\.-]+, [\d\.-]+, [\d\.-]+)\)"),
			"parser":self.parse_authentication_info
			},
			"rcon_connection":{
			"thread_name":"RCON Listener",
			"message_type":"INFO",
			"regex":re.compile(r"^Rcon connection from: \/(?P<ip>[\d.]+)"),
			"parser":self.parse_rcon_connection
			},
			"player_moved_wrongly":{
			"thread_name":"Server thread",
			"message_type":"WARN",
			"regex":re.compile(r"^(?P<username>\S+) moved wrongly!$"),
			"parser":self.parse_player_moved_wrongly
			},
			"player_moved_too_quickly":{
			"thread_name":"Server thread",
			"message_type":"WARN",
			"regex":re.compile(r"^(?P<username>\w+) moved too quickly! (?P<pos>[\d.]+,[\d.]+,[\d.]+)"),
			"parser":self.parse_player_moved_too_quickly
			},
			"server_overloaded":{
			"thread_name":"Server thread",
			"message_type":"WARN",
			"regex":re.compile(r"^Can't keep up! Is the server overloaded\? Running (?P<milliseconds>\d+)ms or (?P<ticks>\d+) ticks behind"),
			"parser":self.parse_server_overloaded
			},
			"player_disconnection_info":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"^com\.mojang\.authlib\.GameProfile@\w+\[id=<(?P<id>[^>]+)>,name=(?P<username>[^,]+),properties=\{(?P<properties>[^\}]+)?\},legacy=(?P<legacy>true|false)\] \(\/(?P<ip>[\d\.]+)\:(?P<port>\d+)\) lost connection: (?P<reason>.+)"),
			"parser":self.parse_player_disconnection_info
			},
			"player_trigger":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"\[(?P<username>.+?): Triggered \[(?P<objective>[^\]]+)\](\]| \(set value to (?P<value>\d+)\)\])"),
			"parser":self.parse_player_trigger
			}
		}

		threads = []
		threads.append(threading.Thread(target=self.log_thread))
		threads.append(threading.Thread(target=self.parser_thread))
		threads.append(threading.Thread(target=self.sender_thread))

		for t in threads:
			t.start()

		try:
			for t in threads:
				t.join()
		except KeyboardInterrupt:
			self.FINISH = True

	def send(self, content):
		r = None
		while not r:
			try:
				r = http.urlopen('POST', self.relay['connections']['console_relay']['webhook'], headers={"Content-Type":"application/json"}, body=json.dumps(content))
			except:
				continue
		if r.data != b'':
			try:
				f = json.loads(r.data)
				f = f['retry_after'] / 1000
			except:
				print("Failed to parse json responce: ", r.data)
				return
			#print(f"Being rate limited. Pausing for {f} seconds...")
			time.sleep(f)
			#print("Re-trying...")
			self.send(content)

	def log_threadDISABLED(self):
		#print(f"{self.relay['server_folder']}logs/latest.log")
		with open(f"{self.relay['server_folder']}logs/latest.log", 'r') as file:
			out = file.readlines()
			#? Append New data to parser_que
			for o in out:
				self._lock.acquire()
				self.parser_que.append(o)
				self._lock.release()
			

	def log_thread(self):
		#print(f"{self.relay['server_folder']}logs/latest.log")
		console = subprocess.Popen(["tail", "-F", f"{self.relay['server_folder']}logs/latest.log"], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		p = select.poll()
		p.register(console.stdout)

		while not self.FINISH:
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

		log_prefix = re.compile(r"\[(?P<timestamp>[\d:]+)\] \[(?P<full_prefix>(?P<type>Server thread|RCON Listener|User Authenticator|main) ?(?P<thread_id>#\d+)?\/(?P<info_type>INFO|WARN))\]: (?P<message>.+)")
		local_que = []
		local_output = []

		while not self.FINISH:
			self._lock.acquire()
			self.sender_que += local_output
			#? Move parser_que to local_que
			local_que = self.parser_que
			self.parser_que = []
			self._lock.release()
			local_output = []

			for line in local_que:
				line = line.decode("utf-8").strip()
				#line = line.strip()
				try:
					timestamp, prefix, thread_name, thread_id, message_type, message = regex(log_prefix, line).values()
				except (TypeError, AttributeError):
					#print(f"Failed to parse line: {line}")
					time.sleep(0.5)
					continue

				for k, v in self.log_formats.items():
					if v['thread_name'] == thread_name and v['message_type'] == message_type:
						if match := regex(v['regex'], message.strip()):
							x = v['parser'](match)
							#print(x)
							local_output.append(x)


	def sender_thread(self):
		while not self.FINISH:
			self._lock.acquire()
			local_que = self.sender_que
			self.sender_que = []
			self._lock.release()
			for message in generate_clumps(local_que):
				self.send(message)
				#print(f"[SENT]: {message}")




def generate_clumps(messages):
	clumps = []
	clump = {'content':''}
	for message in messages:
		clump['content'] += message['content']+'\n'
		if len(clump['content']) > 1000:
			clumps.append(clump)
			clump = []

	if clump['content']: clumps.append(clump)
	return clumps

