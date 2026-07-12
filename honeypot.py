#!/usr/bin/python3
import socket
def main():
	try:
		server_sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		server_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		server_sock.bind(('0.0.0.0',2222))
		server_sock.listen(100)
		input()
	except socket.error as e:
		print(f"[error] socket error: {e}")	
if __name__ == "__main__":
	main()
