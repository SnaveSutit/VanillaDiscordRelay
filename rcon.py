import mcrcon
import os

def execute_all(commands, ip, port, password):
	with mcrcon.MCRcon(ip, password, port=port) as rcon:
		try:
			output = []
			for command in commands:
				if len(command) > 1460:
					print("[rcon.execute] ERROR: Max command lenght exceeded")
					output.append(False)
					continue
				#print("[rcon.execute_all] sending command to {} [length:{}, type:{}]:\n{}".format(host[0], len(command), "Undefined", command))
				try:
					out = rcon.command(command)
					output.append(out if out != '' else None)
				except:
					output.append(False)
			return output
		except KeyboardInterrupt:
			pass

def execute(command, ip, port, password):
	if len(command) > 1460:
		print("[rcon.execute] ERROR: Max command lenght exceeded")
		return False
	with mcrcon.MCRcon(ip, password, port=port) as rcon:
		try:
			#print("[rcon.execute] sending command to {} [length:{}, type:{}]:\n{}".format(host[0], len(command), "Undefined", command))
			try:
				output = rcon.command(command)
			except ConnectionRefusedError:
				output = False
			return output
		except KeyboardInterrupt:
			pass

class RconHandler():
	def __init__(self, ip, port, password):
		self.ip = ip
		self.port = port
		self.password = password

	def execute_all(commands):
		with mcrcon.MCRcon(self.ip, self.password, port=self.port) as rcon:
			try:
				output = []
				for command in commands:
					if len(command) > 1460:
						print("[rcon.execute] ERROR: Max command lenght exceeded")
						output.append(False)
						continue
					#print("[rcon.execute_all] sending command to {} [length:{}, type:{}]:\n{}".format(host[0], len(command), "Undefined", command))
					try:
						out = rcon.command(command)
						output.append(out if out != '' else None)
					except:
						output.append(False)
				return output
			except KeyboardInterrupt:
				pass

	def execute(command):
		if len(command) > 1460:
			print("[rcon.execute] ERROR: Max command lenght exceeded")
			return False
		with mcrcon.MCRcon(self.ip, self.password, port=self.port) as rcon:
			try:
				#print("[rcon.execute] sending command to {} [length:{}, type:{}]:\n{}".format(host[0], len(command), "Undefined", command))
				try:
					output = rcon.command(command)
				except ConnectionRefusedError:
					output = False
				return output
			except KeyboardInterrupt:
				pass
