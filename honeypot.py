#!/usr/bin/python3
import socket
import paramiko
def main():
	try:
		server_sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		server_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		server_sock.bind(('',1313))
		server_sock.listen(13)
		client_sock, client_addr = server_sock.accept()
		print(f"connection from {client_addr[0]}, {client_addr[1]}")
		transport = paramiko.Transport(client_sock)
		server_key = paramiko.RSAKey.generate(1313)
		transport.add_server_key(server_key)
		ssh = paramiko.ServerInterface()
		transport.start_server(server=ssh)
	except socket.error as e:
		print(f"[error] socket error: {e}")	
if __name__ == "__main__":
	main()
