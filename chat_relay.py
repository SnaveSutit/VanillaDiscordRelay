import re
import time
import rcon
import json
import select
import urllib3
import minecraft
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

def clean_text(text):
	return text.replace('"', '\\"')

class Match:
	def __init__(self, comp):
		self.comp = comp
	def groupdict(self):
		return self.comp

class DeathMessageDetector:
	def __init__(self, d):
		self.d = d
	def match(self, text):
		for x,y in self.d.items():
			if x in text:
				return Match({"death_message":x,"content":text,"pvp":y})


class ChatRelay():
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
		#print(comp)
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
		self.chunk_update_in_progress = False
		content = self.message_formats['server_started']
		content = content\
			.replace("$TIME$", comp['time'])
		return {"content":content}

	def parse_server_stopped(self, comp):
		content = self.message_formats['server_stopped']
		return {"content":content}

	def parse_chunk_update_init(self, comp):
		self.chunk_update_in_progress = True
		content = self.message_formats['chunk_update_init']
		return {"content":content}

	def parse_chunk_update_prep(self, comp):
		content = self.message_formats['chunk_update_prep']
		return {"content":content}

	def parse_chunk_update_progress(self, comp):
		if comp['perc_completed'] != self.last_upgrade_perc and self.chunk_update_in_progress:
			self.last_upgrade_perc = comp['perc_completed']
			content = self.message_formats['chunk_update_progress']
			content = content\
				.replace("$PERC_COMPLTED$", comp['perc_completed'])\
				.replace("$UPDATED_CHUNKS$", comp['updated_chunks'])\
				.replace("$TOTAL_CHUNKS$", comp['total_chunks'])
			return {"content":content}
		else:
			return False

	def parse_player_banned_message(self, comp):
		content = self.message_formats['player_banned_message']
		content = content\
			.replace("$PREFIX$", comp['prefix'])\
			.replace("$USERNAME$", comp['username'])\
			.replace("$BANNED_PLAYER$", comp['banned_player'])\
			.replace("$REASON$", comp['reason'])\
			.replace("$LENGTH$", comp['length'])
		return {"content":content}

	def parse_player_death_message(self, comp):
		pvp = '<:pvp:584024528879878167>' if comp['pvp'] else ':skull_crossbones:'
		content = f"{pvp} `{comp['content']}`"
		return {"content":content}


	def __init__(self, relay):
		self.relay = relay
		self.connection_info = relay['server_info']
		self.message_formats = relay['connections']['chat_relay']['message_formats']
		self._lock = threading.Lock()
		self.FINISH = False
		self.last_upgrade_perc = 0
		self.chunk_update_in_progress = False

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
			"chunk_update_init":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"^(?P<placeholder>Upgrading) all chunks\.\.\."),
			"parser":self.parse_chunk_update_init
			},
			"chunk_update_prep":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"^(?P<placeholder>Forcing) world upgrade"),
			"parser":self.parse_chunk_update_prep
			},
			"chunk_update_progress":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"^(?P<perc_completed>\d+)% completed \((?P<updated_chunks>\d+) \/ (?P<total_chunks>\d+) chunks\)\.\.\."),
			"parser":self.parse_chunk_update_progress
			},
			"player_banned_message":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":re.compile(r"\[\[(?P<prefix>[^\]]+)\] (?P<username>[_a-zA-Z0-9]+): Banned (?P<banned_player>[_a-zA-Z0-9]+): (?P<reason>[^\|]+?) ?\| ?(?P<length>.+)\]"),
			"parser":self.parse_player_banned_message
			},
			"player_death_message":{
			"thread_name":"Server thread",
			"message_type":"INFO",
			"regex":DeathMessageDetector(minecraft.death_messages),
			"parser":self.parse_player_death_message
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
				r = http.urlopen('POST', self.relay['connections']['chat_relay']['webhook'], headers={"Content-Type":"application/json"}, body=json.dumps(content))
			except:
				continue
		if r.data != b'':
			try:
				f = json.loads(r.data)
				f = f['retry_after'] / 1000
			except:
				print("Failed to parse json response: ", r.data)
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
			if p.poll(1000):
				out = console.stdout.readline()
				#? Append New data to parser_que
				self._lock.acquire()
				self.parser_que.append(out)
				self._lock.release()
				#? Debugging
			time.sleep(0.05)

	def parser_thread(self):

		log_prefix = re.compile(r"\[(?P<timestamp>[\d:]+)\] \[(?P<full_prefix>(?P<type>Server thread|RCON Listener|User Authenticator) ?(?P<thread_id>#\d+)?\/(?P<info_type>INFO|WARN))\]: (?P<message>.+)")
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
							if x: local_output.append(x)


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




