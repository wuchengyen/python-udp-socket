import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import socket
import threading


SERVER_PORT = 5555
BUFFER_SIZE = 1024

class UltimateGameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("1A2B 終極競技場 (聊天/多房間/動態難度)")
        self.root.geometry("500x650")
        self.client_socket = None
        self.is_connected = False
        self.N_digits = 4 # 預設難度
        
        self.setup_ui()

    def setup_ui(self):
        # 使用 Notebook (分頁) 來管理「連線大廳」與「遊戲房間」
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # --- 頁籤 1: 連線與大廳 ---
        self.tab_lobby = tk.Frame(self.notebook)
        self.notebook.add(self.tab_lobby, text="連線大廳")

        # 連線區
        conn_frame = tk.LabelFrame(self.tab_lobby, text="1. 伺服器連線", padx=10, pady=10)
        conn_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(conn_frame, text="IP:").grid(row=0, column=0)
        self.ip_entry = tk.Entry(conn_frame, width=15)
        self.ip_entry.insert(0, "")
        self.ip_entry.grid(row=0, column=1)
        tk.Label(conn_frame, text="暱稱:").grid(row=0, column=2)
        self.name_entry = tk.Entry(conn_frame, width=10)
        self.name_entry.grid(row=0, column=3)
        self.connect_btn = tk.Button(conn_frame, text="連線", command=self.connect_server)
        self.connect_btn.grid(row=0, column=4, padx=5)

        # 房間區 (初期隱藏)
        self.room_frame = tk.LabelFrame(self.tab_lobby, text="2. 房間管理", padx=10, pady=10)
        tk.Label(self.room_frame, text="房名:").grid(row=0, column=0)
        self.room_entry = tk.Entry(self.room_frame, width=10)
        self.room_entry.grid(row=0, column=1)
        
        tk.Label(self.room_frame, text="難度(3-6位):").grid(row=0, column=2)
        self.digit_entry = tk.Entry(self.room_frame, width=5)
        self.digit_entry.insert(0, "4")
        self.digit_entry.grid(row=0, column=3)

        tk.Button(self.room_frame, text="創建房間 (成為房主)", bg="lightgreen", command=self.create_room).grid(row=1, column=0, columnspan=2, pady=5)
        tk.Button(self.room_frame, text="加入房間", bg="lightblue", command=self.join_room).grid(row=1, column=2, columnspan=2, pady=5)

        # --- 頁籤 2: 遊戲房間 (包含聊天室) ---
        self.tab_game = tk.Frame(self.notebook)
        self.notebook.add(self.tab_game, text="遊戲房間", state="disabled")

        # 歷史/聊天顯示區
        self.text_area = scrolledtext.ScrolledText(self.tab_game, state='disabled', wrap=tk.WORD, height=20)
        self.text_area.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.score_label = tk.Label(self.tab_game, text="戰績：勝 0 | 敗 0", fg="blue", font=("Arial", 10, "bold"))
        self.score_label.pack(pady=2)

        # 互動操作區
        action_frame = tk.Frame(self.tab_game)
        action_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(action_frame, text="猜數字:").grid(row=0, column=0)
        self.guess_entry = tk.Entry(action_frame, width=10, font=("Arial", 12))
        self.guess_entry.grid(row=0, column=1)
        self.guess_entry.bind("<Return>", lambda e: self.send_guess())
        tk.Button(action_frame, text="送出猜測", bg="yellow", command=self.send_guess).grid(row=0, column=2, padx=5)

        tk.Label(action_frame, text="聊天:").grid(row=1, column=0, pady=5)
        self.chat_entry = tk.Entry(action_frame, width=20)
        self.chat_entry.grid(row=1, column=1, columnspan=2, sticky="we", pady=5)
        self.chat_entry.bind("<Return>", lambda e: self.send_chat())
        tk.Button(action_frame, text="送出對話", command=self.send_chat).grid(row=1, column=3, padx=5)

    def append_text(self, text):
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, text + "\n")
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')

    def connect_server(self):
        ip = self.ip_entry.get().strip()
        name = self.name_entry.get().strip()
        if not ip or not name: return messagebox.showwarning("警告", "請輸入 IP 與暱稱！")
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((ip, SERVER_PORT))
            self.client_socket.sendall(f"NAME,{name}\n".encode('utf-8'))
            self.is_connected = True

            self.connect_btn.config(state='disabled')
            self.ip_entry.config(state='disabled')
            self.name_entry.config(state='disabled')
            
            # 開啟背景接收執行緒
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            messagebox.showerror("錯誤", f"連線失敗: {e}")

    def create_room(self):
        r_name = self.room_entry.get().strip()
        d_val = self.digit_entry.get().strip()
        if r_name and d_val.isdigit() and 3 <= int(d_val) <= 6:
            self.client_socket.sendall(f"CREATE,{r_name},{d_val}\n".encode('utf-8'))
        else:
            messagebox.showwarning("警告", "請輸入房名，難度限 3-6 位數")

    def join_room(self):
        r_name = self.room_entry.get().strip()
        if r_name:
            self.client_socket.sendall(f"JOIN,{r_name}\n".encode('utf-8'))

    def receive_messages(self):
        while self.is_connected:
            try:
                data = self.client_socket.recv(BUFFER_SIZE)
                if not data: break
                
                messages = data.decode('utf-8').strip().split('\n')
                for msg in messages:
                    if not msg: continue
                    
                    # 【功能3：自動回應心跳】
                    if msg == "PING":
                        self.client_socket.sendall("PONG\n".encode('utf-8'))
                        continue
                        
                    parts = msg.split(',')
                    tag = parts[0]

                    if tag == "LOBBY":
                        self.room_frame.pack(fill="x", padx=10, pady=10) # 顯示房間區塊
                        messagebox.showinfo("連線成功", parts[1])
                    
                    elif tag == "JOINED":
                        # 成功加入房間，切換頁籤
                        self.notebook.tab(self.tab_game, state="normal")
                        self.notebook.select(self.tab_game)
                        self.text_area.config(state='normal')
                        self.text_area.delete(1.0, tk.END) # 清空看板
                        self.text_area.config(state='disabled')
                        self.append_text(f"🏠 {parts[1]}")
                        
                    elif tag == "SYS":
                        self.append_text(f"⚙️ [系統] {parts[1]}")
                    elif tag == "CHAT":
                        self.append_text(f"💬 {parts[1]}")
                    elif tag == "START":
                        self.append_text(f"🏁 {parts[1]}")
                        self.guess_entry.focus()
                    elif tag == "RES":
                        self.append_text(f"💡 {parts[1]}")
                        
                    elif tag == "OVER":
                        status, wins, losses = parts[1], parts[3], parts[4]
                        self.score_label.config(text=f"戰績：勝 {wins} | 敗 {losses}")
                        if status == "WIN":
                            messagebox.showinfo("勝利！", f"你最先猜出答案！\n花費時間：{parts[2]} 秒")
                        else:
                            messagebox.showinfo("落敗", f"玩家 {parts[2]} 已經先猜出答案了。")
                            
                    elif tag == "KICKED":
                        # 被踢回大廳
                        self.notebook.select(self.tab_lobby)
                        self.notebook.tab(self.tab_game, state="disabled")
                        
            except Exception as e:
                break
        self.is_connected = False

    def send_guess(self):
        guess = self.guess_entry.get().strip()
        self.guess_entry.delete(0, tk.END)
        if guess:
            self.client_socket.sendall(f"GUESS,{guess}\n".encode('utf-8'))

    def send_chat(self):
        msg = self.chat_entry.get().strip()
        self.chat_entry.delete(0, tk.END)
        if msg:
            self.client_socket.sendall(f"CHAT,{msg}\n".encode('utf-8'))

if __name__ == "__main__":
    root = tk.Tk()
    app = UltimateGameClient(root)
    root.mainloop()