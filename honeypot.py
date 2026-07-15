#!/usr/bin/python3
import socket
import threading
import paramiko
import time as time_module
import datetime
import uuid
import json
import sys
import logging
server_key = None
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
class SSHServer(paramiko.ServerInterface):
	def __init__(self, client_addr: Tuple[str,int], session_id : uuid.UUID):
		self.src_ip = client_addr[0]
		self.src_port = client_addr[1]		
		self.session_id = session_id
	def check_auth_password(self, username: str, password: str) -> int:
		print(json.dumps({"event" : "password_auth", "uuid" : str(self.session_id), "username" : username, "password" : password, "src_ip" : self.src_ip, "src_port" : self.src_port, "ts" : datetime.datetime.now(datetime.timezone.utc).isoformat()}))
		return paramiko.AUTH_FAILED
		#return super().check_auth_password(username, password)
	def get_allowed_auths(self, username: str) -> str:
		return "password,publickey"
	def check_auth_publickey(self, username: str, key: PKey) -> int:
		print(json.dumps({"event" : "publickey_auth", "uuid" : str(self.session_id), "username" : username, "key_name" : key.get_name(), "public_key" : key.get_base64(), "key_fp" : key.fingerprint, "src_ip" : self.src_ip, "src_port" : self.src_port, "ts" : datetime.datetime.now(datetime.timezone.utc).isoformat()}))	
		return paramiko.AUTH_FAILED 
def handle_connection(client_sock, client_addr, session_id, time):
	try:
		transport = paramiko.Transport(client_sock)
		if server_key is None:
			server_key = paramiko.RSAKey.from_private_key_file('server_key.pem')
		#server_key = paramiko.RSAKey.generate(4096)
		#server_key.write_private_key_file("server_key.pem")
		transport.add_server_key(server_key)
		ssh = SSHServer(client_addr,session_id)
		transport.start_server(server=ssh)
		print(json.dumps({"event" : "ssh_handshake", "version" : transport.remote_version, "uuid" : str(session_id), "src_ip" : client_addr[0], "src_port" : client_addr[1], "ts" : datetime.datetime.now(datetime.timezone.utc).isoformat()}))
		while transport.is_active(): 
			time_module.sleep(0.01)
		print(json.dumps({"event" : "disconnect", "uuid" : str(session_id), "src_ip" : client_addr[0], "src_port" : client_addr[1], "ts" : datetime.datetime.now(datetime.timezone.utc).isoformat(), "spent" : (datetime.datetime.now(datetime.timezone.utc)-time).total_seconds()}))		
	except Exception as e:
		print(json.dumps({"event" : "error", "error_msg" : str(e), "uuid" : str(session_id), "src_ip" : client_addr[0], "src_port" : client_addr[1], "ts" : datetime.datetime.now(datetime.timezone.utc).isoformat()}))
def main():
	server_sock = None
	session_id = None
	client_addr=(None,None)
	try:
		server_sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		server_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		server_sock.bind(('',22))
		server_sock.listen(13)
		while True:
			client_sock, client_addr = server_sock.accept()
			session_id = uuid.uuid4()
			print(json.dumps({"event" : "new_conn", "uuid" : str(session_id), "src_ip" : client_addr[0], "src_port" : client_addr[1], "ts" : datetime.datetime.now(datetime.timezone.utc).isoformat()}))
			t = threading.Thread(target=handle_connection, args=(client_sock,client_addr, session_id, datetime.datetime.now(datetime.timezone.utc)))
			t.start()
	except KeyboardInterrupt:
		print("shutting down honeypot...")
	except socket.error as e:
		print(json.dumps({"event" : "error", "error_msg" : str(e), "uuid" : str(session_id), "src_ip" : client_addr[0], "src_port" : client_addr[1], "ts" : datetime.datetime.now(datetime.timezone.utc).isoformat()}))
	finally:
		if server_sock is not None: 
			server_sock.close()	
if __name__ == "__main__":
	main()
