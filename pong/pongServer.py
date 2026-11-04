# =================================================================================================
# Contributing Authors:	    Jacky Lin, James Pennington, Evey Wright
# Email Addresses:          jli340@uky.edu, jfpe228@uky.edu, elwr223@uky.edu
# Date:                     11/04/2026
# Purpose:                  Matchmaking/relay server: pairs any number of clients into games
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
# Design:
#   * Any number of clients may connect. They wait in a lobby and are paired up two at a time;
#     every pair gets its own Game room, so any number of games run at once, independently.
#   * Inside a room the server is a relay. The "left" client is authoritative for the ball and
#     score; the "right" client only reports its paddle. Every message is one newline-terminated
#     line.
#   * Control messages (server <-> client):
#       start,W,H,side  server -> client   you have been paired, here is your side
#       again           client -> server   I want a rematch (server forwards it to the opponent)
#       restart         server -> client   both players want a rematch, reset and play again
#       quit            server -> client   your opponent left, the game is over


class Player:
    def __init__(self, conn: socket.socket, addr) -> None:
        self.conn = conn
        self.addr = addr
        self.game = None         # the Game this player is in, None while waiting in the lobby
        self.side = ""           # "left" or "right"
        self.wantsAgain = False  # has asked for a rematch since the last (re)start


class Game:
    def __init__(self, gameId: int, left: Player, right: Player) -> None:
        self.id = gameId
        self.players = [left, right]
        self.lock = threading.Lock()  # serializes all sends to this room's two sockets
        self.over = False

    def opponent(self, player: Player) -> Player:
        return self.players[1] if player is self.players[0] else self.players[0]

    def start(self) -> None:
        with self.lock:
            for p in self.players:
                try:
                    p.conn.sendall(f"start,640,480,{p.side}\n".encode())
                except OSError:
                    pass  # that player already left; their handler thread will call end()

    def forward(self, sender: Player, data: bytes) -> None:
        # Relay game data to the sender's opponent
        with self.lock:
            if self.over:
                return
            try:
                self.opponent(sender).conn.sendall(data)
            except OSError:
                pass

    def requestAgain(self, player: Player) -> None:
        # Once both players have asked for a rematch, tell both to restart. Holding the lock
        # guarantees "restart" reaches each client before any data from the new round.
        with self.lock:
            if self.over:
                return
            player.wantsAgain = True
            other = self.opponent(player)
            if other.wantsAgain:
                for p in self.players:
                    p.wantsAgain = False
                    try:
                        p.conn.sendall(b"restart\n")
                    except OSError:
                        pass
                print(f"[GAME {self.id}] rematch started")
            else:
                try:
                    other.conn.sendall(b"again\n")   # let the opponent know a rematch was asked for
                except OSError:
                    pass

    def end(self, leaver: Player) -> None:
        # A player disconnected: tell the other one and kick them so their client stops cleanly
        with self.lock:
            if self.over:
                return
            self.over = True
            other = self.opponent(leaver)
            try:
                other.conn.sendall(b"quit\n")
                other.conn.shutdown(socket.SHUT_RDWR)  # wakes their handler thread out of recv()
            except OSError:
                pass
        print(f"[GAME {self.id}] ended")


lobbyLock = threading.Lock()
waiting = None      # a Player waiting for an opponent, or None
nextGameId = 1
allPlayers = set()  # every connected Player, so they can be closed on shutdown


def joinLobby(player: Player) -> None:
    # Pair this player with whoever is waiting, or wait for the next player to arrive
    global waiting, nextGameId
    with lobbyLock:
        if waiting is None:
            waiting = player
            print(f"[LOBBY] {player.addr} waiting for an opponent")
            return
        left, right = waiting, player
        waiting = None
        left.side, right.side = "left", "right"
        game = Game(nextGameId, left, right)
        nextGameId += 1
        left.game = right.game = game
    print(f"[GAME {game.id}] {left.addr} (left) vs {right.addr} (right)")
    game.start()


def handleClient(player: Player) -> None:
    global waiting
    print(f"[NEW CONNECTION] {player.addr}")
    joinLobby(player)
    buffer = b""
    try:
        while True:
            data = player.conn.recv(4096)
            if not data:
                break
            game = player.game
            if game is None:        # not paired yet, nothing to relay to
                continue
            buffer += data
            # Pull out control messages, relay everything else as-is in one send
            relay = b""
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if line.strip() == b"again":
                    if relay:
                        game.forward(player, relay)
                        relay = b""
                    game.requestAgain(player)
                else:
                    relay += line + b"\n"
            if relay:
                game.forward(player, relay)
    except OSError:
        pass
    finally:
        with lobbyLock:
            if waiting is player:
                waiting = None
            allPlayers.discard(player)
        if player.game is not None:
            player.game.end(player)
        player.conn.close()
        print(f"[DISCONNECTED] {player.addr}")


serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 0.0.0.0 accepts connections from other machines too, not just localhost
serverSocket.bind(("0.0.0.0", 11111))
serverSocket.listen()

print("Server listening on port 11111...")

serverSocket.settimeout(1)  # lets Ctrl+C be noticed between accept() calls
try:
    while True:
        try:
            conn, addr = serverSocket.accept()
        except socket.timeout:
            continue
        conn.settimeout(None)  # accepted sockets inherit the listener's timeout; undo that
        player = Player(conn, addr)
        with lobbyLock:
            allPlayers.add(player)
        threading.Thread(target=handleClient, args=(player,), daemon=True).start()
except KeyboardInterrupt:
    print("Server shutting down...")
finally:
    serverSocket.close()
    with lobbyLock:
        for p in allPlayers:
            p.conn.close()
