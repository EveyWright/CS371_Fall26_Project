# =================================================================================================
# Contributing Authors:	    Jacky Lin, James Pennington, Evey Wright
# Email Addresses:          jli340@uky.edu, jfpe228@uky.edu, elwr223@uky.edu
# Date:                     11/04/2026
# Purpose:                  Pong client: connects to the server, plays, and offers rematches
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

import pygame
import tkinter as tk
import sys
import socket

from assets.code.helperCode import *

# This is the main game loop.  For the most part, you will not need to modify this.  The sections
# where you should add to the code are marked.  Feel free to change any part of this project
# to suit your needs.
def playGame(screenWidth:int, screenHeight:int, playerPaddle:str, client:socket.socket, buffer:str = "") -> None:
    
    # Pygame inits
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    # Constants
    WHITE = (255,255,255)
    clock = pygame.time.Clock()
    scoreFont = pygame.font.Font("./assets/fonts/pong-score.ttf", 32)
    winFont = pygame.font.Font("./assets/fonts/visitor.ttf", 48)
    pointSound = pygame.mixer.Sound("./assets/sounds/point.wav")
    bounceSound = pygame.mixer.Sound("./assets/sounds/bounce.wav")

    # Display objects
    screen = pygame.display.set_mode((screenWidth, screenHeight))
    winMessage = pygame.Rect(0,0,0,0)
    topWall = pygame.Rect(-10,0,screenWidth+20, 10)
    bottomWall = pygame.Rect(-10, screenHeight-10, screenWidth+20, 10)
    centerLine = []
    for i in range(0, screenHeight, 10):
        centerLine.append(pygame.Rect((screenWidth/2)-5,i,5,5))

    # Paddle properties and init
    paddleHeight = 50
    paddleWidth = 10
    paddleStartPosY = (screenHeight/2)-(paddleHeight/2)
    leftPaddle = Paddle(pygame.Rect(10,paddleStartPosY, paddleWidth, paddleHeight))
    rightPaddle = Paddle(pygame.Rect(screenWidth-20, paddleStartPosY, paddleWidth, paddleHeight))

    ball = Ball(pygame.Rect(screenWidth/2, screenHeight/2, 5, 5), -5, 0)

    if playerPaddle == "left":
        opponentPaddleObj = rightPaddle
        playerPaddleObj = leftPaddle
    else:
        opponentPaddleObj = leftPaddle
        playerPaddleObj = rightPaddle

    lScore = 0
    rScore = 0

    sync = 0

    # The left player is the authority: it runs the real ball physics and scoring and sends them.
    # The right player predicts the ball locally for smooth motion, but always snaps to the
    # authority's ball/score when an update arrives.
    isAuthority = playerPaddle == "left"
    gameRound = 0           # bumped on every rematch; data tagged with an old round is ignored
    wantsAgain = False      # we pressed R to ask for a rematch
    opponentWantsAgain = False
    infoFont = pygame.font.Font("./assets/fonts/visitor.ttf", 24)
    outBuffer = b""         # bytes not yet accepted by the socket (handles partial sends)
    opponentGone = False    # set when the server or opponent disconnects
    # `buffer` holds partial lines between recv() calls (may start with data that arrived
    # together with the start message)
    client.setblocking(False)  # recv()/send() won't freeze the game waiting on the network

    while True:
        # Wiping the screen
        screen.fill((0,0,0))

        # Getting keypress events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    playerPaddleObj.moving = "down"

                elif event.key == pygame.K_UP:
                    playerPaddleObj.moving = "up"

                # Play again: only once the game has been won and the opponent is still here
                elif (event.key == pygame.K_r and not wantsAgain and not opponentGone
                      and (lScore > 4 or rScore > 4)):
                    wantsAgain = True
                    outBuffer += b"again\n"

                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            elif event.type == pygame.KEYUP:
                playerPaddleObj.moving = ""

        # =========================================================================================
        # Your code here to send an update to the server on your paddle's information,
        # where the ball is and the current score.
        # Feel free to change when the score is updated to suit your needs/requirements

        # Message formats (one line each), tagged with the round so stale data from a previous
        # game is ignored after a rematch:
        #   left  -> round,sync,paddleY,ballX,ballY,ballXVel,ballYVel,lScore,rScore
        #   right -> round,sync,paddleY
        if not opponentGone:
            if isAuthority:
                msg = (f"{gameRound},{sync},{playerPaddleObj.rect.y},{ball.rect.x},{ball.rect.y},"
                       f"{ball.xVel},{ball.yVel},{lScore},{rScore}\n")
            else:
                msg = f"{gameRound},{sync},{playerPaddleObj.rect.y}\n"
            outBuffer += msg.encode()
            try:
                sent = client.send(outBuffer)
                outBuffer = outBuffer[sent:]   # keep whatever didn't fit for next frame
            except BlockingIOError:
                pass
            except OSError:
                opponentGone = True

        # Drain everything that has arrived, not just one chunk, so we never fall behind
        while not opponentGone:
            try:
                data = client.recv(4096)
            except BlockingIOError:
                break
            except OSError:
                opponentGone = True
                break
            if not data:            # server closed the connection
                opponentGone = True
                break
            buffer += data.decode()

        # Handle messages in order. Of the game-data lines, only the newest one for the current
        # round matters; older ones are stale.
        latest = None
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if line == "quit":
                opponentGone = True
                continue
            if line == "again":         # opponent asked for a rematch
                opponentWantsAgain = True
                continue
            if line == "restart":       # both players asked for a rematch: reset everything
                gameRound += 1
                lScore = rScore = 0
                sync = 0
                ball.reset(nowGoing="left")     # same start as a fresh game
                for paddle in (leftPaddle, rightPaddle):
                    paddle.rect.y = paddleStartPosY
                    paddle.moving = ""
                wantsAgain = opponentWantsAgain = False
                latest = None           # anything before this line belongs to the old game
                continue
            parts = line.split(",")
            if len(parts) in (3, 9):
                try:
                    values = [int(p) for p in parts]
                except ValueError:
                    continue
                if values[0] == gameRound:
                    latest = values[1:]

        if latest is not None:
            opponentPaddleObj.rect.y = latest[1]
            if not isAuthority and len(latest) == 8:
                ball.rect.x, ball.rect.y = latest[2], latest[3]
                ball.xVel, ball.yVel = latest[4], latest[5]
                if (latest[6], latest[7]) != (lScore, rScore):
                    pointSound.play()
                lScore, rScore = latest[6], latest[7]
                sync = latest[0]     # adopt the authority's clock

        # =========================================================================================

        # Update the player paddle and opponent paddle's location on the screen
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            if paddle.moving == "down":
                if paddle.rect.bottomleft[1] < screenHeight-10:
                    paddle.rect.y += paddle.speed
            elif paddle.moving == "up":
                if paddle.rect.topleft[1] > 10:
                    paddle.rect.y -= paddle.speed

        # If the opponent left, say so and stop the game
        if opponentGone:
            textSurface = winFont.render("Opponent disconnected", False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)
        # If the game is over, display the win message
        elif lScore > 4 or rScore > 4:
            winText = "Player 1 Wins! " if lScore > 4 else "Player 2 Wins! "
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)

            # Play-again prompt under the win message
            if wantsAgain:
                prompt = "Waiting for opponent to accept..."
            elif opponentWantsAgain:
                prompt = "Opponent wants a rematch! Press R to accept"
            else:
                prompt = "Press R to play again, Esc to quit"
            promptSurface = infoFont.render(prompt, False, WHITE, (0,0,0))
            promptRect = promptSurface.get_rect()
            promptRect.center = ((screenWidth/2), screenHeight/2 + 45)
            screen.blit(promptSurface, promptRect)
        else:

            # ==== Ball Logic =====================================================================
            ball.updatePos()

            # If the ball makes it past the edge of the screen, update score, etc.
            # Only the authority scores; the other client gets the score from its updates.
            if isAuthority:
                if ball.rect.x > screenWidth:
                    lScore += 1
                    pointSound.play()
                    ball.reset(nowGoing="left")
                elif ball.rect.x < 0:
                    rScore += 1
                    pointSound.play()
                    ball.reset(nowGoing="right")
                
            # If the ball hits a paddle
            if ball.rect.colliderect(playerPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(playerPaddleObj.rect.center[1])
            elif ball.rect.colliderect(opponentPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(opponentPaddleObj.rect.center[1])
                
            # If the ball hits a wall
            if ball.rect.colliderect(topWall) or ball.rect.colliderect(bottomWall):
                bounceSound.play()
                ball.hitWall()
            
            pygame.draw.rect(screen, WHITE, ball)
            # ==== End Ball Logic =================================================================

        # Drawing the dotted line in the center
        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        
        # Drawing the player's new location
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            pygame.draw.rect(screen, WHITE, paddle)

        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
        pygame.display.update()
        clock.tick(60)
        
        # This number should be synchronized between you and your opponent.  If your number is larger
        # then you are ahead of them in time, if theirs is larger, they are ahead of you, and you need to
        # catch up (use their info)
        sync += 1
        # =========================================================================================
        # Send your server update here at the end of the game loop to sync your game with your
        # opponent's game

        # =========================================================================================




# This is where you will connect to the server to get the info required to call the game loop.  Mainly
# the screen width, height and player paddle (either "left" or "right")
# If you want to hard code the screen's dimensions into the code, that's fine, but you will need to know
# which client is which
def joinServer(ip:str, port:str, errorLabel:tk.Label, app:tk.Tk) -> None:
    # Purpose:      This method is fired when the join button is clicked
    # Arguments:
    # ip            A string holding the IP address of the server
    # port          A string holding the port the server is using
    # errorLabel    A tk label widget, modify it's text to display messages to the user (example below)
    # app           The tk window object, needed to kill the window
    
    # Create a socket and connect to the server
    # You don't have to use SOCK_STREAM, use what you think is best
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((ip, int(port)))
    except Exception as e:
        errorLabel.config(text=f"Failed to connect to server: {e}")
        errorLabel.update()
        return

    # Get the required information from your server (screen width, height & player paddle, "left or "right)
    errorLabel.config(text="Waiting for opponent...")
    errorLabel.update()

    # Read until we have one full line. Game data from the opponent may arrive in the same
    # recv() as the start message, so anything after the first newline is kept for playGame.
    client.settimeout(0.05)
    data = b""
    while b"\n" not in data:
        try:
            chunk = client.recv(1024)
        except socket.timeout:
            app.update()     # keep the window responsive while waiting
            continue
        except OSError as e:
            errorLabel.config(text=f"Connection error: {e}")
            return
        if not chunk:
            errorLabel.config(text="Server closed the connection")
            return
        data += chunk
    client.settimeout(None)

    firstLine, leftover = data.split(b"\n", 1)
    parts = firstLine.decode().strip().split(",")
    if parts == ["quit"]:
        errorLabel.config(text="Opponent left before the game started, please join again")
        client.close()
        return
    if len(parts) != 4 or parts[0] != "start" or parts[3] not in ("left", "right"):
        errorLabel.config(text="Failed to receive start message from server")
        client.close()
        return
    screenWidth = int(parts[1])
    screenHeight = int(parts[2])
    side = parts[3]

    # Close this window and start the game with the info passed to you from the server
    app.withdraw()     # Hides the window (we'll kill it later)
    # Receive the initial message from the server to determine the player's side
    
    playGame(screenWidth, screenHeight, side, client, leftover.decode())  # User will be either left or right paddle
    app.quit()         # Kills the window


# This displays the opening screen, you don't need to edit this (but may if you like)
def startScreen():
    app = tk.Tk()
    app.title("Server Info")

    image = tk.PhotoImage(file="./assets/images/logo.png")

    titleLabel = tk.Label(image=image)
    titleLabel.grid(column=0, row=0, columnspan=2)

    ipLabel = tk.Label(text="Server IP:")
    ipLabel.grid(column=0, row=1, sticky="W", padx=8)

    ipEntry = tk.Entry(app)
    ipEntry.grid(column=1, row=1)

    portLabel = tk.Label(text="Server Port:")
    portLabel.grid(column=0, row=2, sticky="W", padx=8)

    portEntry = tk.Entry(app)
    portEntry.grid(column=1, row=2)

    errorLabel = tk.Label(text="")
    errorLabel.grid(column=0, row=4, columnspan=2)

    joinButton = tk.Button(text="Join", command=lambda: joinServer(ipEntry.get(), portEntry.get(), errorLabel, app))
    joinButton.grid(column=0, row=3, columnspan=2)

    app.mainloop()

if __name__ == "__main__":
    #startScreen()
    
    # Uncomment the line below if you want to play the game without a server to see how it should work
    # the startScreen() function should call playGame with the arguments given to it by the server this is
    # here for demo purposes only
    startScreen()
    # playGame(640, 480,"left",socket.socket(socket.AF_INET, socket.SOCK_STREAM))