import argparse
from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server, udp_client
from threading import Thread, Lock
from queue import Queue
import mozcpy
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
beforeHenkan = 0
henkanList = []
chengeFlag = False

handsign_dict = {
    (0, 1): "あ", (0, 2): "い", (0, 3): "う", (0, 4): "え", (0, 5): "お", (0, 6): "BackSpace", (0, 7): "Enter", 
    (1, 1): "か", (1, 2): "き", (1, 3): "く", (1, 4): "け", (1, 5): "こ", (1, 6): "や", (1, 7): "Komoji",
    (2, 1): "さ", (2, 2): "し", (2, 3): "す", (2, 4): "せ", (2, 5): "そ", (2, 6): "ゆ", (2, 7): "、",
    (3, 1): "た", (3, 2): "ち", (3, 3): "つ", (3, 4): "て", (3, 5): "と", (3, 6): "よ", (3, 7): "。",
    (4, 1): "な", (4, 2): "に", (4, 3): "ぬ", (4, 4): "ね", (4, 5): "の", (4, 6): "ん", (4, 7): "Dakuten",
    (5, 1): "は", (5, 2): "ひ", (5, 3): "ふ", (5, 4): "へ", (5, 5): "ほ", (5, 6): "わ", (5, 7): "HanDakuten",
    (6, 1): "ま", (6, 2): "み", (6, 3): "む", (6, 4): "め", (6, 5): "も", (6, 6): "を", (6, 7): "ー",
    (7, 1): "ら", (7, 2): "り", (7, 3): "る", (7, 4): "れ", (7, 5): "ろ", (7, 6): "w", (7, 7): "Henkan"
}
dakuten_dict = {
    "か":"が","き":"ぎ","く":"ぐ","け":"げ","こ":"ご",
    "さ":"ざ","し":"じ","す":"ず","せ":"ぜ","そ":"ぞ",
    "た":"だ","ち":"ぢ","つ":"づ","て":"で","と":"ど",
    "は":"ば","ひ":"び","ふ":"ぶ","へ":"べ","ほ":"ぼ",
    "う":"ゔ",
    "カ":"ガ","キ":"ギ","ク":"グ","ケ":"ゲ","コ":"ゴ",
    "サ":"ザ","シ":"ジ","ス":"ズ","セ":"ゼ","ソ":"ゾ",
    "タ":"ダ","チ":"ヂ","ツ":"ヅ","テ":"デ","ト":"ド",
    "ハ":"バ","ヒ":"ビ","フ":"ブ","ヘ":"ベ","ホ":"ボ",
    "ウ":"ヴ"
}
handakuten_dict = {
    "は":"ぱ","ひ":"ぴ","ふ":"ぷ","へ":"ぺ","ほ":"ぽ",
    "ハ":"パ","ヒ":"ピ","フ":"プ","ヘ":"ペ","ホ":"ポ"
}
komozi_dict = {
    "あ": "ぁ",    "い":"ぃ",    "う":"ぅ",    "え":"ぇ",    "お":"ぉ",
    "ア": "ァ",    "イ":"ィ",    "ウ":"ゥ",    "エ":"ェ",    "オ":"ォ",
    "け": "ヶ",    "つ": "っ",    "や": "ゃ",    "ゆ": "ゅ",    "よ": "ょ",    "わ": "ゎ",
    "ケ": "ヶ",    "ツ": "ッ",    "ヤ": "ャ",    "ユ": "ュ",    "ヨ": "ョ",    "ワ": "ヮ"
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

# Hiragana -> Japanese
def hiragana_to_japanese(text):
    converter = mozcpy.Converter()
    japanese = converter.convert(text, n_best=10)
    print("予測変換：", japanese)
    return japanese

# Input processing
def getWord():
    global textBox, beforeSend, beforeHenkan, henkanList, chengeFlag
    while True:
        gesturePatterns = gesture_queue.get()
        
        if gesturePatterns[1] == 0:
            continue

        selectText = handsign_dict.get(gesturePatterns, "")
        if not textBox and gesturePatterns in [(0, 6), (0, 7), (1, 7), (4, 7), (5, 7), (7, 7)]:
            continue

        lastText = textBox[-1] if textBox else ""

        if selectText in {"Dakuten", "HanDakuten", "Komoji"} and lastText != "":
            conversion_dict = {
                "Dakuten": dakuten_dict,
                "HanDakuten": handakuten_dict,
                "Komoji": komozi_dict,
            }
            convertedText = conversion_dict[selectText].get(lastText, "")
            if convertedText:
                textBox = textBox[:-1] + convertedText
                chengeFlag = True

        elif selectText == "BackSpace" and lastText != "":
            textBox = textBox[:-1]
            chengeFlag = True

        elif selectText == "Henkan" and lastText != "":
            if beforeHenkan >= len(henkanList) - 1:
                beforeHenkan = 0
            if beforeHenkan == 0:
                henkanList = hiragana_to_japanese(textBox)
            if henkanList:
                textBox = henkanList[beforeHenkan]
                beforeHenkan += 1
                chengeFlag = True

        elif selectText == "Enter" and lastText != "":
            sendChat(textBox)
            textBox = ""
            chengeFlag = True

        elif selectText:
            textBox += selectText
            beforeHenkan = 0
            henkanList.clear()
            chengeFlag = True

        print(f"[input] : {textBox}")
        print(beforeHenkan)

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
        self.label0 = tk.Label(self.root, text="入力：", font=("Arial", 25), bg="gray", fg="white")
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
        self.label2.config(text="送信済み：" + beforeSend)  

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
