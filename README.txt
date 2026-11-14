Contact Info
============

Group Members & Email Addresses:

    Jacky Lin, jli340@uky.edu
    Evey Wright, elwr223@uky.edu
    James Pennington, jfpe228@uky.edu

Versioning
==========

Github Link: https://github.com/EveyWright/CS371_Fall26_Project

General Info
============
This file describes how to install/run this program.

Install Instructions
====================

Run the following line to install the required libraries for this project:
`pip3 install -r requirements.txt`

First, to run the server, run pongServer.py by changing directories to where it is stored
and run 'python pongServer.py'. This will have the server to start listening.

After the server is listening, player1 can then run pongServer.py and enter in the necessary
IP address and port number. Player2 will do the same.

Once both, player1 and player2, have joined, the server will then start the game and will end 
once one of the players have earned 5 points. Once the game is over, you can replay the game
if both players press r on the game over screen.


Known Bugs
==========
- If the left side client gets corrupted, it could send corrupted information to the server
allowing both clients to be corrupted.

