import socket
import threading
import re

UNIX_SOCKET = '/var/run/docker.sock'
LISTEN_PORT = 2375

def handle_client(client_socket):
    try:
        data = client_socket.recv(4096)
        if not data:
            return
        
        request = data.decode('utf-8', errors='ignore')
        
        # Strip /v1.xx entirely. Docker Engine handles unversioned requests.
        new_request = re.sub(r'/v1\.[0-9]+', '', request)
        # Also rewrite Api-Version header if present
        new_request = re.sub(r'Api-Version: [0-9.]+', 'Api-Version: 1.44', new_request)
        # Rewrite User-Agent to hide the old version
        new_request = re.sub(r'User-Agent: Docker-Client/[0-9.]+', 'User-Agent: Docker-Client/1.44', new_request)
        
        # Connect to Docker unix socket
        docker_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        docker_socket.connect(UNIX_SOCKET)
        
        # Send (potentially modified) request
        if isinstance(new_request, str):
            new_request = new_request.encode('utf-8')
        docker_socket.sendall(new_request)
        
        # Forward everything else back and forth
        def forward(src, dst, is_client_to_docker=False):
            try:
                while True:
                    chunk = src.recv(4096)
                    if not chunk:
                        break
                    
                    if is_client_to_docker:
                        # REWRITE SUBSEQUENT REQUESTS IN THE SAME CONNECTION
                        decoded = chunk.decode('utf-8', errors='ignore')
                        if ' /v1.' in decoded:
                            chunk = re.sub(r'/v1\.[0-9]+', '', decoded).encode('utf-8')
                    
                    dst.sendall(chunk)
            except:
                pass
            finally:
                try:
                    dst.shutdown(socket.SHUT_WR)
                except:
                    pass

        t1 = threading.Thread(target=forward, args=(docker_socket, client_socket))
        t1.start()
        forward(client_socket, docker_socket, is_client_to_docker=True)
        t1.join()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', LISTEN_PORT))
    server.listen(100)
    print(f"Proxy listening on port {LISTEN_PORT}...")
    
    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_client, args=(client,)).start()

if __name__ == '__main__':
    main()
