import tkinter as tk
from tkinter import scrolledtext, messagebox
import socket
import threading
import time 

# Returns the local IP address to display in the server GUI
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

# Server class that handles GUI, networking, and game logic
class Server:
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("Server")
        master.geometry("750x450")
        
        master.grid_columnconfigure(index=[0, 1, 2 ,3], weight=1) 
        master.grid_rowconfigure(index=[0, 1, 2, 3], weight=1)

        # Game start conditions
        self.game_button_condition = False
        self.file_found = False
        self.qa_valid = False
        
        # Game state variables
        self.question_number = 0
        self.questions = []
        self.current_question_index = -1
        self.questions_asked_count = 0 

        # Server socket and connection state
        self.server_socket = None
        self.is_listening = False
        self.players = {}  
        self.thread = None

        # Scoring and answer tracking
        self.scores = {}
        self.waiting_for_answers = False 
        self.answered_players = set()    
        self.answer_sequence = []
        self.current_question_lock = threading.Lock() 
        self.player_answers = {}


        # GUI widgets
        tk.Label(master, text="Port:").grid(row=0, column=0, sticky="E", padx=2, pady=5)
        self.port_box = tk.Entry(master, width=20) 
        self.port_box.grid(row=0, column=1, columnspan=1, sticky="W", pady=5) 
    
        self.Listen_button = tk.Button(master, text="Listen", command= self.toggle_listening)
        self.Listen_button.grid(row=0, column=3)

        self.Start_button = tk.Button(master, text="Start Game", command= self.toggle_game_button)


        tk.Label(master, text="File name:").grid(row=1, column=0, sticky="E", padx=3, pady=5)
        self.file_name_box = tk.Entry(master, width=20) 
        self.file_name_box.grid(row=1, column=1, columnspan=2, sticky="EW", padx=2, pady=5) 

        self.file_send_button = tk.Button(master, text="Send", command=self.send_file_name)
        self.file_send_button.grid(row=1, column=3, sticky="EW", padx=5, pady=5)

        tk.Label(master, text="QA number:").grid(row=2, column=0, sticky="E", padx=3, pady=5)
        self.qa_box = tk.Entry(master, width=20)
        self.qa_box.grid(row=2, column=1, columnspan=2, sticky="EW", padx=2, pady=5)
        self.qa_send_button = tk.Button(master, text="Send", command=self.set_qa_number)
        self.qa_send_button.grid(row=2, column=3, sticky="EW", padx=5, pady=5)

    
        self.listbox = tk.Listbox(master, height=20, width=30)
        self.listbox.grid(row=3, column=0, columnspan=4, sticky="NWSE", padx=5, pady=5)


    # Start or stop server listening
    def toggle_listening(self):
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()

    # Start or stop the game
    def toggle_game_button(self):
        if self.game_button_condition:
            self.close_game_button()
        else:
            can_start = (self.file_found and self.qa_valid and len(self.players) >= 2)
            if can_start:
                self.start_game_button()

    # Stop the game and show final scoreboard
    def close_game_button(self):
        self.game_button_condition = False
        
        self.Start_button.config(text="Start Game")
        
        self.waiting_for_answers = False
        self.player_answers.clear() 
        self.answered_players.clear()
        
        final_scoreboard_text = self.generate_final_scoreboard()
        self.add_message_to_text(final_scoreboard_text)
        self.broadcast(final_scoreboard_text)
        
        self.add_message_to_text("--- Game Ended ---")
        self.broadcast("--- Game Ended ---")


    # Initialize a new game session
    def start_game_button(self):
            self.game_button_condition = True
            
            self.Start_button.config(text="Stop Game")

            self.current_question_index = -1
            self.questions_asked_count = 0 
            
            # Reset answer-related state
            self.waiting_for_answers = False
            self.answered_players.clear()
            self.player_answers.clear()
            
            self.add_message_to_text("--- Game Starting ---")
            self.broadcast("--- Game Starting ---")

            self.add_message_to_text("Scoreboard:")
            self.broadcast("Scoreboard:")
            
             # Reset scores
            for username in self.players.values():
                self.scores[username] = 0

            scoreboard_text = self.generate_scoreboard()
            self.add_message_to_text(scoreboard_text)
            self.broadcast(scoreboard_text)

            self.ask_next_question()

    # Send the next question to all players
    def ask_next_question(self):
        
        # Check if total number of questions is reached
        if self.questions_asked_count >= self.question_number:
            self.add_message_to_text("--- Game Over---")
            self.broadcast("--- Game Over ---")
            self.close_game_button()
            return

        # Enable answer collection and clear previous answers
        self.waiting_for_answers = True
        self.answered_players.clear()
        self.player_answers.clear()
        
        
        # Loop back to start if end of file is reached
        if self.current_question_index + 1 >= len(self.questions):
            self.current_question_index = 0 
        else:
            self.current_question_index += 1 
            
        self.questions_asked_count += 1
        
        # Get current question from list
        current_q = self.questions[self.current_question_index]
        
        broadcast_message = (
            f"--- Question {self.questions_asked_count} / {self.question_number} ---\n"
            f"{current_q['question']}\n"
            f"A - {current_q['A']}\n"
            f"B - {current_q['B']}\n"
            f"C - {current_q['C']}"
        )
        
        self.add_message_to_text(f"Asking Question {self.questions_asked_count}: {current_q['question']}")
        self.broadcast(broadcast_message)

    def accept_connections(self):
        # Accept incoming player connections while server is listening
        while self.is_listening:
            try:
                player_socket, player_address = self.server_socket.accept()

                # Reject new connections if game already started
                if self.game_button_condition:
                    message = "Error: Game already started."
                    player_socket.sendall(message.encode()) 
                    player_socket.close()
                    self.add_message_to_text(f"Connection attempt rejected: Game in progress.")
                    continue

                # Receive username with timeout
                player_socket.settimeout(1.0)
                name = player_socket.recv(1024).decode()
                player_socket.settimeout(None)

                # Reject duplicate usernames
                if name in self.players.values():
                    error_msg = f"Error: Username '{name}' is already taken."
                    player_socket.sendall(error_msg.encode()) 
                    
                    player_socket.close()
                    self.add_message_to_text(f"Connection attempt by '{name}' rejected (Name taken).")
                    continue

                # Accept connection
                player_socket.sendall("OK".encode())
                
                # Store socket-username mapping
                self.players[player_socket] = name
                self.add_message_to_text(f"New connection from {player_address[0]} as '{name}'")
                self.check_start_conditions()

                # Start a thread for this player
                player_thread = threading.Thread(target=self.handle_player, args=(player_socket, name), daemon=True)
                player_thread.start()
            except (socket.error, OSError):
                try: player_socket.close() 
                except: pass
                break
    
    def handle_player(self, player, name):
        # Listen for messages from a specific player
        while self.is_listening:
            try:

                message = player.recv(1024).decode().strip() 
                if message:
                    
                    # Check if message is a valid answer
                    is_answer = (
                        self.game_button_condition and 
                        self.waiting_for_answers and
                        len(message) == 1 and
                        message in ['A', 'B', 'C']
                    )

                    if is_answer:
                        self.handle_player_answer(name, message)
                else:
                    # Empty message means player disconnected
                    self.remove_player(player)
                    break
            except (socket.error, OSError):
                self.remove_player(player)
                break

    def handle_player_answer(self, username, answer):
        # Handle answer submission with thread safety
        with self.current_question_lock:
            if not self.waiting_for_answers:
                return
            
            # Prevent multiple answers from same player
            if username in self.answered_players:
                self.add_message_to_text(f"Error: '{username}' already answered.")
                self.send_to_player(username, "You already answered")
                return

            # Store player's answer
            self.player_answers[username] = answer 
            self.answered_players.add(username)

            # Track order of answers
            self.answer_sequence.append(username)
            
            # Acknowledge answer receipt
            self.send_to_player(username, f"Your answer: '{answer}' is received")
            
            # Check if all players answered
            if len(self.answered_players) == len(self.players):
                self.add_message_to_text("----------------------")
                self.evaluate_answers_and_next_question()
                

    def evaluate_answers_and_next_question(self):
        
        # Stop accepting answers
        self.waiting_for_answers = False 
        
        # Get correct answer for current question
        current_q = self.questions[self.current_question_index]
        correct_choice = current_q['answer']
        
        self.add_message_to_text(f"Correct Answer: {correct_choice}")
        self.broadcast(f"Correct Answer: {correct_choice}")

        first_correct_answerer = None
        
        # Answer evaluation section
        self.add_message_to_text("\n--- Answer Evaluation ---")

        # Find first correct answerer
        for username_in_order in self.answer_sequence:
            player_answer = self.player_answers.get(username_in_order)
            
            if player_answer == correct_choice:
                first_correct_answerer = username_in_order
                break
        
        # Score calculation
        for username, player_answer in self.player_answers.items():
            if player_answer == correct_choice:
                if username == first_correct_answerer:
                    bonus = len(self.players) - 1
                    self.scores[username] += 1 + bonus
                    message = f"{username} is first and correct +1 point and (bonus +{len(self.players) - 1 } Points)."
                    self.add_message_to_text(message)
                    self.send_to_player(username, message)
                else:
                    self.scores[username] += 1 
                    message = f"{username} your answer is correct +1 Point."
                    self.send_to_player(username, message)
                    self.add_message_to_text(f"{username} your answer is correct +1 Point.")
            else:
                message = f"{username} your answer is wrong 0 Point."
                self.send_to_player(username, message)
                self.add_message_to_text(f"{username} your answer is wrong 0 Point.")
        self.add_message_to_text("\n--- ------ -------- ---")
        

        # Clear stored answers
        self.player_answers.clear() 

        # Broadcast updated scoreboard
        scoreboard_text = self.generate_scoreboard()
        self.add_message_to_text(scoreboard_text)
        self.broadcast(scoreboard_text)

        self.ask_next_question()

    def send_to_player(self, username, message):

        target_socket = None
        
        # Find the socket that belongs to the given username (self.players maps socket -> username)
        # Iterate over (socket, username) pairs and pick the socket whose username matches the target
        for player_socket, player_name in self.players.items():
            if player_name == username:
                target_socket = player_socket
                break
        
        if target_socket:
            try:
                 # Append newline so the client prints messages on separate lines
                message_with_newline = message + "\n"
                target_socket.send(message_with_newline.encode())
                
            except (socket.error, OSError) as e:
                 # If sending fails, log the error and remove the disconnected player
                self.add_message_to_text(f"Error sending message to '{username}'. Disconnecting.")
                self.remove_player(target_socket)
            
        else:
            # Username not found in current players list
            self.add_message_to_text(f"Error: Player '{username}' not found.")
        


    def broadcast(self, message, sender_socket=None):
         # Send a message to every connected player
        new_message = message + "\n"
        for player_socket in list(self.players.keys()):
            try:
                player_socket.send(new_message.encode())
            except (socket.error, OSError):
                # If a socket fails, remove that player from the server
                self.remove_player(player_socket)

    def on_closing(self):
        # Handle GUI close: stop server if running, then destroy the window
        if self.is_listening:
            self.stop_listening()
        if self.game_button_condition:
            self.game_button_condition = False
        self.master.destroy()

    def remove_player(self, player_socket):
        # Remove a disconnected player and update game state if needed
        if player_socket in self.players:
            name = self.players[player_socket]
            
            try:
                player_socket.close()
                self.players.pop(player_socket)
            except (socket.error, OSError):
                pass
            
             # If a player disconnects during a question, update answer tracking safely
            with self.current_question_lock:
                 if name in self.answered_players:
                     self.answered_players.remove(name)
                # If remaining players have all answered, move on automatically
                 if self.waiting_for_answers and len(self.answered_players) == len(self.players):
                     self.master.after(50, self.evaluate_answers_and_next_question)
                     
            # Log disconnect and notify remaining players
            self.add_message_to_text(f"'{name}' has disconnected.")
            self.broadcast(f"'{name}' has left the chat.")

            # Re-check whether the game can be started (needs file + QA + at least 2 players)
            self.check_start_conditions()


    def add_message_to_text(self, message):
        
        # Split multi-line messages and insert each line into the GUI listbox
        lines = message.splitlines()
        
        # Handle single-line messages that may not contain '\n'
        if not lines and message.strip():
             lines = [message]
        elif not lines:
             return 

        for line in lines:
            self.listbox.insert(tk.END, line)
            
         # Auto-scroll to the newest entry
        self.listbox.see(tk.END)



    def generate_scoreboard(self):
        
        # Build a sorted scoreboard string (highest score first)
        if not self.scores:
            return "Scoreboard is Empty"
        
        sorted_scores = sorted(self.scores.items(), key=lambda item: item[1], reverse=True)
        
        scoreboard_lines = []
        
        rank = 1
        for username, score in sorted_scores:
            scoreboard_lines.append(f"{rank}. {username} : {score} Point")
            rank += 1
            
        return "\n".join(scoreboard_lines)

    def generate_final_scoreboard(self):

        # Build a final scoreboard with rank suffixes (st/nd/rd/th) and handle ties
        if not self.scores:
            return "Final Scoreboard is Empty"
        
        sorted_scores = sorted(self.scores.items(), key=lambda item: item[1], reverse=True)
        
        scoreboard_lines = []
        
        current_rank = 1  
        num_players_ranked = 0 
        last_score = -1 

        for username, score in sorted_scores:
            num_players_ranked += 1
            
            # If the score drops, update rank (keeps same rank for ties)
            if score < last_score:
                current_rank = num_players_ranked
            
            last_score = score

             # Rank suffix formatting
            if current_rank == 1:
                rank_suffix = "st"
            elif current_rank == 2:
                rank_suffix = "nd"
            elif current_rank == 3:
                rank_suffix = "rd"
            else:
                rank_suffix = "th"
            
            final_rank_display = f"{current_rank}{rank_suffix}"
            
            scoreboard_lines.append(f"{final_rank_display} {username} : {score} Point")
            
        final_output = "\n--- FINAL SCOREBOARD ---\n" + "\n".join(scoreboard_lines)
        
        return final_output
    
    def check_start_conditions(self):
        # Game can start only if: file is loaded + QA number set + at least 2 players connected
        can_start = (self.file_found and 
                     self.qa_valid and 
                     len(self.players) >= 2)
        
        if self.is_listening:
            if can_start:
                # Show the Start Game button only when all conditions are satisfied
                self.Start_button.grid(row=0, column=2, sticky="EW", pady=10)
                if not self.game_button_condition:
                    self.Start_button.config(text="Start Game")
            else:
                # If conditions are not satisfied, hide Start Game button
                if self.game_button_condition:
                    self.close_game_button()
                
                self.Start_button.grid_forget()

    def set_qa_number(self):
        # Read and validate the number of questions to ask in the game
        qa_input = self.qa_box.get()
        self.qa_valid = False
        
        if not qa_input:
            self.add_message_to_text("Error: Please enter a QA number.")
            return

        try:
            number = int(qa_input)
            
            # QA number must be positive
            if number <= 0:
                self.add_message_to_text("Error: QA number must be a positive integer (greater than 0).")
                return

            self.question_number = number 
            self.qa_valid = True
            self.add_message_to_text(f"Success: QA number set to {self.question_number}.")
                
        except ValueError:
            self.add_message_to_text("Error: QA number must be a valid integer.")

        # Update Start Game button visibility
        self.check_start_conditions()

    def send_file_name(self):
        # Read question file and parse it into self.questions list
        file_name = self.file_name_box.get()
        self.file_found = False
        self.questions = []
        
        if not file_name:
            self.add_message_to_text("Error: Please enter a file name.")
            return

        try:
            with open(file_name, 'r') as file:
                lines = [line.strip() for line in file]

                # Temporary storage for one question block until "Answer:" line is found
                question_block = [] 
                
                for line in lines:
                    if line.startswith("Answer:"):
                         # Found the correct answer line for the current question block
                        
                         # Extract correct answer letter (A/B/C)
                        correct_answer = line.split(":", 1)[1].strip().upper()
                        
                        # Parse question text and options from accumulated lines
                        question_text = question_block[0].strip()
                        options = {}
                        
                        for q_line in question_block[1:]:
                            if q_line.startswith('A -'):
                                options['A'] = q_line[3:].strip()
                            elif q_line.startswith('B -'):
                                options['B'] = q_line[3:].strip()
                            elif q_line.startswith('C -'):
                                options['C'] = q_line[3:].strip()
                                
                        # Save parsed question into the list
                        if question_text and 'A' in options:
                            self.questions.append({
                                "question": question_text,
                                "A": options.get('A'),
                                "B": options.get('B'),
                                "C": options.get('C'),
                                "answer": correct_answer # Stores only the correct option letter
                            })
                            
                         # Reset block for the next question
                        question_block = []
                    else:
                        # Accumulate lines until the "Answer:" marker is reached
                        question_block.append(line)

                # Validate that at least one question was parsed successfully
                if not self.questions:
                    self.add_message_to_text(f"Error: No questions found or file format is incorrect.")
                    self.file_found = False
                else:
                    self.file_found = True
                    self.add_message_to_text(f"Success: File '{file_name}' read successfully.")

        except FileNotFoundError:
            # File does not exist in the current working directory
            self.add_message_to_text(f"Error: File '{file_name}' not found in the current directory.")
            self.file_found = False
            
        except Exception as e:
            # Any other parsing/IO error
            self.add_message_to_text(f"Error: Could not process file '{file_name}'. Reason: {e}")
            self.file_found = False

        # Update Start Game button visibility
        self.check_start_conditions()

    def start_listening(self):
        
        # Read and validate port input, then start the TCP server
        string_input_port = self.port_box.get()
        
        if not string_input_port:
            error_message = "Error: Please enter a port number"
            self.add_message_to_text(error_message) 
            return 
        
        try:
            port = int(string_input_port)
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

             # Bind to all interfaces so clients on the same network can connect
            self.server_socket.bind(('0.0.0.0', port))
            self.server_socket.listen(5)
            self.is_listening = True

            self.Listen_button.config(text="Stop Listening")

             # Update Start Game button visibility
            self.check_start_conditions()

            # Display IP + port info in GUI
            local_ip = get_local_ip()
            self.add_message_to_text(f"--- Server listening on port {port} with {local_ip} ---")
            
            # Start accept thread to handle incoming connections
            self.thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.thread.start()
            
             # Register window close handler
            self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
            
        except (socket.error, ValueError) as e:
            # Port invalid or bind/listen failed
            error_message = "Could not start server: " + str(e)
            self.add_message_to_text(error_message)
            self.add_message_to_text("Try another port")
            return


    def stop_listening(self):
        if self.is_listening:
            # Stop accepting new connections and disconnect all players
            self.is_listening = False
            
            for player_socket in list(self.players.keys()):
                name = self.players.get(player_socket)                
                try:
                    player_socket.close()
                except:
                    pass
                
                try:
                    del self.players[player_socket]
                except KeyError:
                    pass

                self.add_message_to_text(f"'{name}' has disconnected.")

            # Close server socket and reset GUI state
            self.server_socket.close()

            self.Start_button.grid_forget()

            self.Listen_button.config(text="Listen")

            self.add_message_to_text("--- Server stopped ---")


if __name__ == "__main__":
    # Launch the Tkinter application
    root = tk.Tk()
    app = Server(root)
    root.mainloop()