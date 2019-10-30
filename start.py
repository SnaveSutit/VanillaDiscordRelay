import json
import threading
from chat_relay import ChatRelay

def read_json_file(f):
	with open(f, 'r') as f:
		return json.loads(f.read())

def write_json_file(f, data):
	with open(f, 'w') as f:
		return json.dump(data, f)





config = read_json_file('config.json')

threads = []

for relay in config['relays']:
	print(f"------ Starting Relay for {relay['name']} ------")
	if relay['connections'].get('chat_relay'):
		threads.append(threading.Thread(target=ChatRelay, args=(relay,)))

for t in threads:
	t.start()

try:
	for t in threads:
		t.join()
except KeyboardInterrupt:
	for t in threads:
		t.terminate()

