import argparse
from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server, udp_client
from threading import Thread, Lock
from queue import Queue
import tkinter as tk
import pyperclip

textBox = ""
beforeSend = ""
dominant_hand_right = True
gesture_queue = Queue()
gesture_lock = Lock()
gestureLeftValue = 0
gestureRightValue = 0
end_program = True
chengeFlag = False

handsign_dict = {
    (0, 1): "e", (0, 2): "t", (0, 3): "i", (0, 4): "r", (0, 5): "u", (0, 6): "BackSpace", (0, 7): "Enter", 
    (1, 1): "a", (1, 2): "o", (1, 3): "s", (1, 4): "l", (1, 5): "f", (1, 6): "v", (1, 7): " ",
    (2, 1): "n", (2, 2): "h", (2, 3): "c", (2, 4): "w", (2, 5): "x", (2, 6): "(", (2, 7): ".",
    (3, 1): "d", (3, 2): "m", (3, 3): "g", (3, 4): "j", (3, 5): "↑", (3, 6): ")", (3, 7): ",",
    (4, 1): "p", (4, 2): "b", (4, 3): "q", (4, 4): "←", (4, 5): "↓", (4, 6): "→", (4, 7): "-",
    (5, 1): "y", (5, 2): "z", (5, 3): "\"", (5, 4): "_", (5, 5): ":", (5, 6): ";", (5, 7): "!",
    (6, 1): "k", (6, 2): "6", (6, 3): "7", (6, 4): "8", (6, 5): "9", (6, 6): "*", (6, 7): "?",
    (7, 1): "0", (7, 2): "1", (7, 3): "2", (7, 4): "3", (7, 5): "4", (7, 6): "5", (7, 7): "ShiftUp"
}
shiftup_dict = {
    "a": "A","b": "B","c": "C","d": "D","e": "E","f": "F","g": "G",
    "h": "H","i": "I","j": "J","k": "K","l": "L","m": "M","n": "N",
    "o": "O","p": "P","q": "Q","r": "R","s": "S","t": "T","u": "U",
    "v": "V","w": "W","x": "X","y": "Y","z": "Z",
    "0": ")","9": "(","8": "*","7": "&","6": "^","5": "%","4": "$","3": "#","2": "@","1": "!",
    ";": ":","(": "[",")": "]",".": ">",",": "<"
}

# OSC Send parser 
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--ip", default="127.0.0.1", help="The IP of the OSC server")
arg_parser.add_argument("--port", type=int, default=9000, help="The port the OSC server is listening on")
args = arg_parser.parse_args([])
print(f"OSC Server ( ip:{args.ip} port:{args.port} )")

# OSC Send chat
def sendChat(text: str):
    client = udp_client.SimpleUDPClient(args.ip, args.port)
    client.send_message("/chatbox/input", [text, True])
    print(f"[OSC Send] :'{text}'")
    pyperclip.copy(text)
    return

# Input processing
def getWord():
    global textBox, beforeSend,  chengeFlag
    while True:
        gesturePatterns = gesture_queue.get()
        
        if gesturePatterns[1] == 0:
            continue
        
        selectText = handsign_dict.get(gesturePatterns, "")
        if not textBox and gesturePatterns in [(0, 6), (0, 7),  (7, 7)]:
            continue
        
        lastText = textBox[-1] if textBox else ""

        if selectText == "ShiftUp" and lastText != "":
            convertedText = shiftup_dict.get(lastText, "")
            if convertedText:
                textBox = textBox[:-1] + convertedText
                chengeFlag = True

        elif selectText == "BackSpace" and lastText != "":
            textBox = textBox[:-1]
            chengeFlag = True

        elif selectText == "Enter" and lastText != "":
            sendChat(textBox)
            beforeSend = textBox
            textBox = ""
            chengeFlag = True

        elif selectText:
            textBox += selectText
            chengeFlag = True

        print(f"[input] : {textBox}")

# OSC GestureLeft
def gestureLeft(address: str, left_value: int):
    global gestureLeftValue
    with gesture_lock:
        gestureLeftValue = left_value
        if not dominant_hand_right:
            gesture_queue.put((gestureRightValue, gestureLeftValue))
    return

# OSC gestureRight
def gestureRight(address: str, right_value: int):
    global gestureRightValue
    with gesture_lock:
        gestureRightValue = right_value
        if dominant_hand_right:
            gesture_queue.put((gestureLeftValue, gestureRightValue))
    return

# OSC Get
def start_osc_server():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1", help="The ip to listen on")
    parser.add_argument("--port", type=int, default=9001, help="The port to listen on")
    args = parser.parse_args()
    oscDispatcher = Dispatcher()
    oscDispatcher.map("/avatar/parameters/GestureLeft", gestureLeft)
    oscDispatcher.map("/avatar/parameters/GestureRight", gestureRight)
    print(f"OSC Server ( ip:{args.ip} port:{args.port} )")
    server = osc_server.ThreadingOSCUDPServer((args.ip, args.port), oscDispatcher)
    server.serve_forever()


class GUI():
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("input")
        self.root.geometry("600x80+100+100")
        self.root.config(bg="gray")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.label0 = tk.Label(self.root, text="Input：", font=("Arial", 25), bg="gray", fg="white")
        self.label0.grid(row=0, column=0, sticky="w")

        self.Entry = tk.Entry(self.root, text="Loading...", font=("Arial", 25), bg="gray", fg="white")
        self.Entry.grid(row=0, column=1, sticky="w")
        
        self.label2 = tk.Label(self.root, text="", font=("Arial", 15), bg="gray", fg="white")
        self.label2.grid(row=1, column=0)
        
        self.send_button = tk.Button(self.root, text="Send", command=self.send, width=10, height=1)
        self.send_button.place(relx=1.0, y=20, anchor="e")
        
        self.quit_button = tk.Button(self.root, text="Exit", command=self.stop, width=10, height=1)
        self.quit_button.place(relx=1.0, y=60, anchor="e")
        
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.update_label()
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.move_window)
        self.root.mainloop()

    def update_label(self):
        global textBox, beforeSend, chengeFlag
        if(chengeFlag):
            self.Entry.delete(0, tk.END)
            self.Entry.insert(0, textBox)
            chengeFlag = False
        textBox = self.Entry.get()
        self.label2.config(text="Sended：" + beforeSend)  

        self.root.after(100, self.update_label)  

    def send(self):
        global textBox, beforeSend, chengeFlag
        sendChat(textBox)
        textBox = ""
        chengeFlag = True
        
        
    def stop(self):
        self.running = False
        self.root.destroy()
        global end_program
        end_program = False
        
    def start_move(self, event):
            self.root.x = event.x
            self.root.y = event.y

    def move_window(self, event):
            x = self.root.winfo_pointerx() - self.root.x
            y = self.root.winfo_pointery() - self.root.y
            self.root.geometry(f"+{x}+{y}")
        
def main():
    Thread(target=start_osc_server, daemon=True).start()
    Thread(target=getWord, daemon=True).start()
    GUI()
    while end_program:
        pass
    print("Exit.")
    
if __name__ == "__main__":
    main()
