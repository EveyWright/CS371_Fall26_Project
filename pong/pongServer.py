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

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr}")
    client_num = clients[conn]
    while True:
        try:
            msg = conn.recv(1024)
            if not msg:
                break

            msg = f'\nClient {client_num}: ' + msg.decode()
            msg = msg.encode()
            for c in clients:
                if c != conn:
                    c.send(msg)
        except:
            break
    conn.close()
    if conn in clients:
        clients.pop(conn)
    print(f"[DISCONNECTED] {addr}")


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server_socket.bind(("127.0.0.1", 11111))
server_socket.listen()

print("Server listening...")

while True:
    conn, addr = server_socket.accept()
    clients[conn] = count
    count += 1
    if(count >= 2):
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()



