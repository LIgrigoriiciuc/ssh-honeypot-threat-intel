#!/usr/bin/python3
import socket
import threading
import paramiko
class SSHServer(paramiko.ServerInterface):
	def check_auth_password(self, username: str, password: str) -> int:
		print(f"{username}:{password}")
		return paramiko.AUTH_FAILED
		#return super().check_auth_password(username, password)
def handle_connection(client_sock):
	transport = paramiko.Transport(client_sock)
	server_key = paramiko.RSAKey.from_private_key_file('key')
	server_key = paramiko.RSAKey.generate(4096)
	#server_key.write_private_key_file("server_key.pem")
	transport.add_server_key(server_key)
	ssh = SSHServer()
	transport.start_server(server=ssh)
def main():
	try:
		server_sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		server_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		server_sock.bind(('',1313))
		server_sock.listen(13)
		while True:
			client_sock, client_addr = server_sock.accept()
			print(f"connection from {client_addr[0]}, {client_addr[1]}")
			t = threading.Thread(target=handle_connection, args=(client_sock,))
			t.start()
	except socket.error as e:
		print(f"[error] socket error: {e}")	
if __name__ == "__main__":
	main()
