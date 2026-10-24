# =================================================================================================
# Contributing Authors:	    <Anyone who touched the code>
# Email Addresses:          <Your uky.edu email addresses>
# Date:                     <The date the file was last edited>
# Purpose:                  <How this file contributes to the project>
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

import socket
import threading

# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games
clients = {}
count = 1

lock = threading.Lock()

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr}")
    while True:
        try:
            msg = conn.recv(1024)
            if not msg:
                break
            with lock:
                others = [c for c in clients if c != conn]
            for c in others:
                c.send(msg)
        except OSError:
            break
    conn.close()
    with lock:
        clients.pop(conn, None)
    print(f"[DISCONNECTED] {addr}")


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server_socket.bind(("127.0.0.1", 11111))
server_socket.listen()

print("Server listening...")

server_socket.settimeout(1)  # Optional: set a timeout for accept() to allow graceful shutdown checks
try:
    while True:
        try:
            conn, addr = server_socket.accept()
        except socket.timeout:
            continue
        with lock:
            side = "left" if len(clients) == 0 else "right"
            clients[conn] = side
            ready = len(clients) == 2

        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

        if ready:
            # Both players are here, so release them into the game.
            with lock:
                for c, s in clients.items():
                    c.send(f"start,640,480,{s}\n".encode())
except KeyboardInterrupt:
    print("Server shutting down...")
    server_socket.close()
    for c in clients:
        c.close()

