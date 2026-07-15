#!/usr/bin/python3
import socket
import threading
import paramiko
import datetime
import uuid
import json
import logging
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
class SSHServer(paramiko.ServerInterface):
	def __init__(self, client_addr: Tuple[str,int], UUID : uuid.UUID):
		self.src_ip = client_addr[0]
		self.src_port = client_addr[1]		
		self.UUID = UUID
	def check_auth_password(self, username: str, password: str) -> int:
		print(f"{username}:{password}")
		return paramiko.AUTH_FAILED
		#return super().check_auth_password(username, password)
	def get_allowed_auths(self, username: str) -> str:
		return "password,publickey"
	def check_auth_publickey(self, username: str, key: PKey) -> int:
		print(json.dumps({"event" : "publickey_auth", "uuid" : str(self.UUID), "username" : username, "key_name" : key.get_name(), "public_key" : key.get_base64(), "src_ip" : self.src_ip, "src_port" : self.src_port, "ts" : datetime.datetime.now(datetime.timezone.utc).isoformat()}))
		return paramiko.AUTH_FAILED 
def handle_connection(client_sock):
	try:
		UUID = uuid.uuid1()
		transport = paramiko.Transport(client_sock)
		server_key = paramiko.RSAKey.from_private_key_file('server_key.pem')
		#server_key = paramiko.RSAKey.generate(4096)
		#server_key.write_private_key_file("server_key.pem")
		transport.add_server_key(server_key)
		ssh = SSHServer(client_sock[1],uuid)
		transport.start_server(server=ssh)
	except Exception as e:
		print(f"[error] ssh error: {str(e)}", file=sys.stderr)
def main():
	try:
		server_sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		server_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		server_sock.bind(('',22))
		server_sock.listen(13)
		while True:
			client_sock, client_addr = server_sock.accept()
			print(f"connection from {client_addr[0]}, {client_addr[1]} timestamp: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
			t = threading.Thread(target=handle_connection, args=(client_sock,))
			t.start()
	except KeyboardInterrupt:
		print("shutting down honeypot...")
	except socket.error as e:
		print(f"[error] socket error: {e}", file=sys.stderr)
	finally:
		server_sock.close()	
if __name__ == "__main__":
	main()
