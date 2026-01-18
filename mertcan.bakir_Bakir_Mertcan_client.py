import tkinter as tk
from tkinter import scrolledtext, messagebox
import socket
import threading


class PlayerServer:

    def __init__(self, master: tk.Tk):

        self.master = master
        master.title("Player")
        master.geometry("750x450")

        # Configure grid layout for the GUI
        master.grid_columnconfigure(index=[0, 1, 2, 3], weight=1) 
        master.grid_rowconfigure(index=[0, 1, 2, 3, 4], weight=1)

        # Connection-related variables
        self.player_socket = None
        self.is_connected = False
        self.thread = None

         # IP input field
        tk.Label(master, text="IP:").grid(row=0, column=0, sticky="E", padx=1, pady=5)
        self.ip_box = tk.Entry(master, width=10) 
        self.ip_box.grid(row=0, column=1, columnspan=1, sticky="W", padx=1, pady=5)

         # Port input field
        tk.Label(master, text="Port:").grid(row=0, column=2, sticky="E", padx=1, pady=5)
        self.port_box = tk.Entry(master, width=10) 
        self.port_box.grid(row=0, column=3, columnspan=1, sticky="W", padx=1, pady=5)

         # Username input field
        tk.Label(master, text="Username:").grid(row=1, column=1, sticky="E", padx=1, pady=5)
        self.username_box = tk.Entry(master, width=20)
        self.username_box.grid(row=1, column=2, columnspan=1, sticky="W", padx=1, pady=5)

        # Connect / Disconnect button
        self.Connect_button = tk.Button(master, text="Connect", command= self.toggle_connection)
        self.Connect_button.grid(row=2, column=0,columnspan=4, pady=10)
        
        # Text area to display server messages
        self.text_widget = tk.Text(master, height=20, width=30,state=tk.DISABLED)
        self.text_widget.grid(row=3, column=0, columnspan=4, sticky="NWSE", padx=5, pady=5)

        # Radio buttons for answer selection (A, B, C)
        self.option = tk.StringVar(master, value="A")
        tk.Radiobutton(
            master, 
            text="A", 
            variable=self.option, 
            value="A",                 
        ).grid(row=4, column=0, sticky="E") 

        tk.Radiobutton(
            master, 
            text="B", 
            variable=self.option, 
            value="B",               
        ).grid(row=4, column=1, sticky="E")

        tk.Radiobutton(
            master, 
            text="C", 
            variable=self.option, 
            value="C",             
        ).grid(row=4, column=2, sticky="")
        
        # Button to send selected answer to server
        self.Send_button = tk.Button(master, text="Send", command=self.send_message, state=tk.DISABLED)
        self.Send_button.grid(row=4, column=3, sticky="EW", padx=5, pady=5)

    # Connect or disconnect depending on current state
    def toggle_connection(self):
        if self.is_connected:
            self.disconnect_to_server()
        else:
            self.connect_to_server()

    def connect_to_server(self):
        ip = self.ip_box.get()
        port_str = self.port_box.get()
        username = self.username_box.get()

        # All fields must be filled before connecting
        if not ip or not port_str or not username:
            error_message = "Error: All fields must be field out."
            self.add_message_to_text(error_message) 
            return

        try:
            port = int(port_str)
            self.player_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Try socket for 3 seconds
            self.player_socket.settimeout(3.0)
            self.player_socket.connect((ip, port))
            self.player_socket.settimeout(None)

            # Send username to server immediately after connection
            self.player_socket.sendall(username.encode())

            # Wait for server response (OK or Error)
            self.player_socket.settimeout(2.0)
            initial_response = self.player_socket.recv(1024).decode()
            self.player_socket.settimeout(None)

            if initial_response.startswith("Error:"):
                # Server rejected connection (e.g., duplicate username)
                self.player_socket.close()
                error_message = f"Connection failed: {initial_response[6:].strip()}"
                self.add_message_to_text(error_message)
                return

            elif initial_response == "OK":
                # Successful connection
                self.is_connected = True
                
                 # Start background thread to receive server messages
                self.thread = threading.Thread(target=self.receive_messages, daemon=True)
                self.thread.start()
                
                self.Connect_button.config(text="Disconnect")
                self.add_message_to_text(f"--- Connected to {ip}:{port} ---")
                self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

            else:
                # Unknown response from server
                self.player_socket.close()
                self.is_connected = False
                self.add_message_to_text(f"Connection failed: Server sent unknown response.")
                return
            
        except socket.timeout:
            # Timeout while waiting for server response
            self.player_socket.close()
            error_message = f"Connection failed: Server sent unknown response."
            self.add_message_to_text(error_message)
            self.is_connected = False


        except (socket.error, ValueError) as e:
            # Connection or port parsing error
            error_message = f"Could not connect to server: {e}"
            self.add_message_to_text(error_message)
            self.is_connected = False
            if self.player_socket:
                self.player_socket.close()

    def disconnect_to_server(self):
        # Disconnect safely from the server
        if self.is_connected:
            self.is_connected = False
            self.player_socket.close()
            self.Connect_button.config(text="Connect")
            self.Send_button.config(state=tk.DISABLED)
            self.add_message_to_text("--- Disconnected ---")


    def add_message_to_text(self, message):
        # Append message to the text widget
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, message + "\n")
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.yview(tk.END)

    def send_message(self):
        # Send selected answer (A/B/C) to the server
        if self.is_connected:
            message = self.option.get()
            if message:
                try:
                    self.player_socket.sendall(message.encode())
                except (socket.error, OSError):
                    self.disconnect_to_server()


    def receive_messages(self):
        # Continuously listen for messages from the server
        while self.is_connected:
            try:
                message = self.player_socket.recv(1024).decode()
                if message:
                     # Enable answer sending when game starts
                    if "--- Game Starting ---" in message:
                        self.master.after(0, lambda: self.Send_button.config(state=tk.NORMAL))
                        
                    # Disable answer sending when game ends
                    if "--- Game Ended ---" in message:
                        self.master.after(0, lambda: self.Send_button.config(state=tk.DISABLED))

                    self.add_message_to_text(message)
                else:
                    # Empty message means server disconnected
                    self.disconnect_to_server()
                    break
            except (socket.error, OSError):
                self.disconnect_to_server()
                break


    def on_closing(self):
        # Handle window close event
        if self.is_connected:
            self.disconnect_to_server()
        self.master.destroy()



if __name__ == "__main__":
    root = tk.Tk()
    app = PlayerServer(root)
    root.mainloop()