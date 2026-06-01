import socket
import threading
import random
import time
import os

def print_tcp_socket_info(client_socket, addr):
    """提取並印出作業系統底層的 TCP 連線資訊"""
    try:
        # 1. 取得連線雙方的 IP 與 Port (TCP 連線四元組)
        remote_ip, remote_port = addr
        local_ip, local_port = client_socket.getsockname()

        # 2. 取得作業系統為這個 TCP 連線分配的接收與發送緩衝區大小 (Byte)
        recv_buf = client_socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        send_buf = client_socket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)

        # 3. 檢查 Nagle 演算法狀態 (TCP_NODELAY)
        try:
            nodelay = client_socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
            nodelay_status = "開啟 (即時傳送，適合遊戲)" if nodelay else "關閉 (合併傳送，節省頻寬)"
        except:
            nodelay_status = "未知"

        print("\n=== 📡 [網路層監控] TCP 連線底層資訊 ===")
        print(f"🔗 連線四元組 (4-Tuple):")
        print(f"   [Local]  {local_ip}:{local_port}")
        print(f"   [Remote] {remote_ip}:{remote_port}")
        print(f"📦 TCP 緩衝區 (Buffer Size):")
        print(f"   接收緩衝區 (SO_RCVBUF): {recv_buf} Bytes")
        print(f"   發送緩衝區 (SO_SNDBUF): {send_buf} Bytes")
        print(f"⚡ 延遲最佳化 (Nagle Algorithm): {nodelay_status}")
        print("=======================================\n")
    except Exception as e:
        print(f"無法取得 TCP 資訊: {e}")
SERVER_PORT = 5555
BUFFER_SIZE = 1024

# --- 終極系統全域狀態 ---
# clients 存放: { socket: {"name": "Alice", "room": "Room1", "last_pong": timestamp} }
clients = {}
# rooms 存放: { "房名": {"players": [sock1, sock2], "active": False, "answer": "", "N": 4, "host": sock1, "start_time": 0} }
rooms = {}
records = {}

# 為了多執行緒安全，加入 Lock
lock = threading.Lock()

# --- 戰績與邏輯功能 ---
def load_records():
    global records
    if os.path.exists("tcp_records.txt"):
        with open("tcp_records.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    parts = line.split(',')
                    if len(parts) == 3:
                        records[parts[0]] = {"wins": int(parts[1]), "losses": int(parts[2])}

def save_records():
    with open("tcp_records.txt", "w", encoding="utf-8") as f:
        for name, data in records.items():
            f.write(f"{name},{data['wins']},{data['losses']}\n")

def ab(message, answer):
    a, b = 0, 0
    check_len = min(len(message), len(answer))
    for i in range(check_len):
        if message[i] == answer[i]: a += 1
        else:
            for j in range(len(answer)):
                if message[i] == answer[j]: b += 1
    return f"{a}A{b}B"

def broadcast_room(room_name, message):
    """【功能2：房間系統】只將訊息廣播給特定房間內的玩家"""
    if room_name not in rooms: return
    for sock in rooms[room_name]["players"]:
        try:
            sock.sendall(message.encode('utf-8'))
        except:
            pass

# --- 【功能3：TCP 心跳偵測 (Heartbeat)】 ---
def heartbeat_monitor():
    """背景巡邏執行緒：每 5 秒發送 PING，超過 10 秒沒 PONG 就踢除"""
    while True:
        time.sleep(5)
        current_time = time.time()
        with lock:
            disconnected_sockets = []
            for sock, info in clients.items():
                if current_time - info["last_pong"] > 10:
                    print(f"[心跳偵測] 玩家 {info['name']} 逾時無回應，強制剔除。")
                    disconnected_sockets.append(sock)
                else:
                    try:
                        sock.sendall("PING\n".encode('utf-8'))
                    except:
                        disconnected_sockets.append(sock)
            
            for sock in disconnected_sockets:
                handle_disconnect(sock)

def handle_disconnect(sock):
    """處理玩家斷線與退出房間的邏輯"""
    if sock in clients:
        room_name = clients[sock]["room"]
        name = clients[sock]["name"]
        
        if room_name in rooms and sock in rooms[room_name]["players"]:
            rooms[room_name]["players"].remove(sock)
            broadcast_room(room_name, f"SYS,玩家 {name} 已斷線離開房間。\n")
            
            # 如果房間空了就刪除房間
            if not rooms[room_name]["players"]:
                del rooms[room_name]
                print(f"[系統] 房間 {room_name} 已解散。")
            # 如果房主斷線，將權限移交給下一個人 (Host Migration)
            elif rooms[room_name]["host"] == sock:
                rooms[room_name]["host"] = rooms[room_name]["players"][0]
                new_host_name = clients[rooms[room_name]["host"]]["name"]
                broadcast_room(room_name, f"SYS,房主已離開，【{new_host_name}】成為新房主。\n")

        del clients[sock]
        try:
            sock.close()
        except:
            pass

# --- 處理玩家請求 ---
def handle_client(client_socket, addr):
    client_socket.settimeout(None)
    with lock:
        clients[client_socket] = {"name": "Unknown", "room": None, "last_pong": time.time()}

    try:
        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data: break
            
            messages = data.decode('utf-8').strip().split('\n')
            for msg in messages:
                if not msg: continue
                parts = msg.split(',')
                tag = parts[0]

                # 【功能3：處理心跳回應】
                if tag == "PONG":
                    with lock:
                        clients[client_socket]["last_pong"] = time.time()
                    continue

                # 初始化名字
                if tag == "NAME":
                    name = parts[1]
                    with lock:
                        clients[client_socket]["name"] = name
                        if name not in records:
                            records[name] = {"wins": 0, "losses": 0}
                    client_socket.sendall("LOBBY,已連線至大廳，請創建或加入房間。\n".encode('utf-8'))
                    continue

                # 【功能2 & 4：創建房間與動態難度】
                if tag == "CREATE":
                    room_name, n_digits = parts[1], int(parts[2])
                    with lock:
                        if room_name in rooms:
                            client_socket.sendall("SYS,該房名已存在！\n".encode('utf-8'))
                        else:
                            rooms[room_name] = {
                                "players": [client_socket], "active": False,
                                "answer": "", "N": n_digits, "host": client_socket, "start_time": 0
                            }
                            clients[client_socket]["room"] = room_name
                            client_socket.sendall(f"JOINED,成功創建並加入房間 [{room_name}]，難度: {n_digits}位數\n".encode('utf-8'))
                    continue

                # 加入房間
                if tag == "JOIN":
                    room_name = parts[1]
                    with lock:
                        if room_name not in rooms:
                            client_socket.sendall("SYS,找不到該房間！\n".encode('utf-8'))
                        elif rooms[room_name]["active"]:
                            client_socket.sendall("SYS,該房間遊戲已在進行中！\n".encode('utf-8'))
                        else:
                            rooms[room_name]["players"].append(client_socket)
                            clients[client_socket]["room"] = room_name
                            n_digits = rooms[room_name]["N"]
                            client_socket.sendall(f"JOINED,成功加入房間 [{room_name}]，難度: {n_digits}位數\n".encode('utf-8'))
                            p_name = clients[client_socket]["name"]
                            broadcast_room(room_name, f"SYS,玩家 {p_name} 加入了房間。\n")

                            # 滿兩人自動開局
                            if len(rooms[room_name]["players"]) >= 2:
                                pool = "0123456789ABCDEF"
                                rooms[room_name]["answer"] = "".join(random.sample(pool, n_digits))
                                rooms[room_name]["active"] = True
                                rooms[room_name]["start_time"] = time.perf_counter()
                                print(f"[系統] 房間 {room_name} 遊戲開始！謎底：{rooms[room_name]['answer']}")
                                broadcast_room(room_name, f"START,{n_digits}位數 遊戲開始！請輸入搶答！\n")
                    continue

                # 以下指令需在房間內才能執行
                room_name = clients[client_socket]["room"]
                if not room_name or room_name not in rooms: continue
                p_name = clients[client_socket]["name"]
                room = rooms[room_name]

                # 【功能1：即時聊天室】
                if tag == "CHAT":
                    chat_msg = parts[1]
                    broadcast_room(room_name, f"CHAT,{p_name}: {chat_msg}\n")
                    continue

                # 處理猜測
                if tag == "GUESS":
                    guess = parts[1].upper()
                    if not room["active"]:
                        client_socket.sendall("SYS,遊戲尚未開始或已結束。\n".encode('utf-8'))
                        continue
                    
                    if len(guess) != room["N"] or len(set(guess)) != room["N"]:
                        client_socket.sendall("SYS,格式錯誤！\n".encode('utf-8'))
                        continue

                    result = ab(guess, room["answer"])
                    client_socket.sendall(f"RES,你的猜測: {guess} ➜ {result}\n".encode('utf-8'))
                    broadcast_room(room_name, f"CHAT,[戰況] {p_name} 猜了 {guess} ➜ {result}\n") # 用聊天室廣播戰況

                    # 判斷獲勝
                    if result == f"{room['N']}A0B":
                        room["active"] = False
                        elapsed_time = time.perf_counter() - room["start_time"]
                        print(f"[系統] 房間 {room_name} 玩家 {p_name} 獲勝！")

                        with lock:
                            for sock in room["players"]:
                                sock_name = clients[sock]["name"]
                                if sock_name == p_name:
                                    records[sock_name]["wins"] += 1
                                    sock.sendall(f"OVER,WIN,{elapsed_time:.2f},{records[sock_name]['wins']},{records[sock_name]['losses']}\n".encode('utf-8'))
                                else:
                                    records[sock_name]["losses"] += 1
                                    sock.sendall(f"OVER,LOSE,{p_name},{records[sock_name]['wins']},{records[sock_name]['losses']}\n".encode('utf-8'))
                            save_records()
                        
                        time.sleep(0.5)
                        broadcast_room(room_name, "SYS,--- 遊戲結束，請由房主重新創房或加入新房 ---\n")
                        
                        # 遊戲結束，解散房間，將玩家踢回大廳
                        with lock:
                            for sock in list(room["players"]):
                                clients[sock]["room"] = None
                                try:
                                    sock.sendall("KICKED\n".encode('utf-8'))
                                except: pass
                            del rooms[room_name]

    except Exception as e:
        pass
    finally:
        with lock:
            handle_disconnect(client_socket)

def main():
    load_records()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    server_socket.bind(('', SERVER_PORT))
    server_socket.listen(10)
    print(f"=== TCP 終極版 競技伺服器啟動 (Port {SERVER_PORT}) ===")
    
    # 啟動心跳偵測執行緒
    threading.Thread(target=heartbeat_monitor, daemon=True).start()

    try:
        while True:
            client_socket, addr = server_socket.accept()
            print_tcp_socket_info(client_socket, addr)
            threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n伺服器關閉中...")
    finally:
        server_socket.close()
        save_records()

if __name__ == "__main__":
    main()