Multi-Player Trivia Game (CS408 Project)
This project is a multi-player quiz application developed as part of the CS408 - Computer Networks course. It demonstrates the use of TCP/IP sockets for real-time, bidirectional communication between a central server and multiple clients.

✨ Features

  TCP/IP Networking: Reliable communication using Python's socket library.
  
  Multi-Client Support: Handles multiple concurrent players using threading.
  
  Custom Game Engine: * Server can load custom question files (.txt).
  
  Dynamic scoring system where the first correct answer earns a bonus (Number of Players - 1).
  
  Real-time scoreboard broadcasting.
  
  GUI Interface: Developed with Tkinter for both Server and Player clients.
  
  Robust Error Handling: Managed socket timeouts, duplicate username detection, and unexpected disconnections.

🚀 How to Run

1. Start the Server
Run mertcan.bakir_Bakır_Mertcan_server.py.

Enter a Port number and click Listen.

Load the quiz_qa.txt file using the "File name" box.

Set the QA number (total questions to ask).

2. Connect Players
Run mertcan.bakir_Bakir_Mertcan_client.py for each player.

Enter the IP (server's local IP) and Port.

Enter a unique Username and click Connect.

3. Play
Once at least 2 players are connected, the server can click Start Game.

Players select their answers (A, B, or C) and click Send.

The game moves to the next question automatically once everyone has answered.


📄 File Structure


server.py: Central hub managing game state, players, and scoring.

client.py: Player interface for connecting and submitting answers.

quiz_qa.txt: Sample question bank.
