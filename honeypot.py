#!/usr/bin/python3
import socket
import threading
import paramiko
import datetime
import logging
logging.getLogger("paramiko").setLevel(logging.CRITICAL)
class SSHServer(paramiko.ServerInterface):
	def check_auth_password(self, username: str, password: str) -> int:
		print(f"{username}:{password}")
		return paramiko.AUTH_FAILED
		#return super().check_auth_password(username, password)
	def get_allowed_auths(self, username: str) -> str:
		return "password,publickey"
	def check_auth_publickey(self, username: str, key: PKey) -> int:
		print(f"{username}:{key}")
		return paramiko.AUTH_FAILED 
def handle_connection(client_sock):
	try:
		transport = paramiko.Transport(client_sock)
		server_key = paramiko.RSAKey.from_private_key_file('server_key.pem')
		#server_key = paramiko.RSAKey.generate(4096)
		#server_key.write_private_key_file("server_key.pem")
		transport.add_server_key(server_key)
		ssh = SSHServer()
		transport.start_server(server=ssh)
	except Exception as e:
		print(f"[error] ssh error: {str(e)}")
def main():
	try:
		server_sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		server_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		server_sock.bind(('',22))
		server_sock.listen(13)
		while True:
			client_sock, client_addr = server_sock.accept()
			print(f"connection from {client_addr[0]}, {client_addr[1]} timestamp: {datetime.datetime.now()}")
			t = threading.Thread(target=handle_connection, args=(client_sock,))
			t.start()
	except KeyboardInterrupt:
		print("shutting down honeypot...")
	except socket.error as e:
		print(f"[error] socket error: {e}")
	finally:
		server_sock.close()	
if __name__ == "__main__":
	main()
