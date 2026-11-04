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
#
# Design: the server is a relay. The "left" client is authoritative for the ball and score; the
# "right" client only reports its paddle. Every message is a single newline-terminated line.

clients = {}        # conn -> "left" | "right"
started = False     # True once both players have been sent their start message
lock = threading.Lock()


def forward(sender: socket.socket, data: bytes) -> None:
    # Relay data to every other client. Holding the lock guarantees nothing is forwarded to a
    # client before its own start message has been sent.
    with lock:
        if not started:
            return
        for c in clients:
            if c is not sender:
                try:
                    c.sendall(data)
                except OSError:
                    pass


def end_game() -> None:
    # Called with the lock held. Tell everyone still connected that the game is over and kick
    # them so the lobby resets cleanly for the next pair of players.
    global started
    started = False
    for c in list(clients):
        try:
            c.sendall(b"quit\n")
            c.shutdown(socket.SHUT_RDWR)   # wakes that client's handler thread out of recv()
        except OSError:
            pass
    clients.clear()


def handle_client(conn: socket.socket, addr) -> None:
    print(f"[NEW CONNECTION] {addr}")
    try:
        while True:
            msg = conn.recv(4096)
            if not msg:
                break
            forward(conn, msg)
    except OSError:
        pass
    finally:
        with lock:
            if conn in clients:
                clients.pop(conn)
                end_game()
        conn.close()
        print(f"[DISCONNECTED] {addr}")


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 0.0.0.0 accepts connections from other machines too, not just localhost
server_socket.bind(("0.0.0.0", 11111))
server_socket.listen()

print("Server listening on port 11111...")

server_socket.settimeout(1)  # lets Ctrl+C be noticed between accept() calls
try:
    while True:
        try:
            conn, addr = server_socket.accept()
        except socket.timeout:
            continue

        with lock:
            if len(clients) >= 2:
                try:
                    conn.sendall(b"full\n")
                except OSError:
                    pass
                conn.close()
                print(f"[REJECTED] {addr} (game full)")
                continue

            taken = set(clients.values())
            side = "left" if "left" not in taken else "right"
            clients[conn] = side

            if len(clients) == 2:
                # Both players are here, so release them into the game.
                started = True
                for c, s in clients.items():
                    c.sendall(f"start,640,480,{s}\n".encode())

        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
except KeyboardInterrupt:
    print("Server shutting down...")
finally:
    server_socket.close()
    with lock:
        for c in clients:
            c.close()
