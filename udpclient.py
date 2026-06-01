import socket
import sys
import time

# =====================================================
# 常數設定
# SERVER_PORT : 伺服器監聽的 UDP 埠號
# BUFFER_SIZE : 每次接收資料的緩衝區大小（位元組）
# =====================================================
SERVER_PORT = 5555
BUFFER_SIZE = 1024

# =====================================================
# 建立 UDP Socket
# AF_INET     : 使用 IPv4 位址族
# SOCK_DGRAM  : 使用 UDP（無連線、資料報）協定
# 若建立失敗則印出錯誤訊息並結束程式
# =====================================================
try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error as msg:
    print(f'無法創建 Socket. 錯誤訊息：{msg}')
    sys.exit()

# 取得玩家暱稱，用於最後顯示勝利訊息與戰報
name = input("請輸入你的遊戲暱稱：")

# =====================================================
# 驗證伺服器 IP 格式
# 將輸入字串以 '.' 分割成四段，確認每段都是 0~255 的數字
# 格式不正確時持續要求重新輸入
# =====================================================
while True:
    server_ip = input("請輸入伺服器 IP 地址: ")
    parts = server_ip.split('.')
    if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
        break 
    else:
        print("IP 地址格式不正確，請重新輸入。")

# 組合伺服器位址 tuple，供 sendto / recvfrom 使用
server_address = (server_ip, SERVER_PORT)
print(f"\n準備連線至 {server_ip}:{SERVER_PORT} ...")

# =====================================================
# 遊戲狀態變數
# visit      : 是否已完成「敲門」握手，取得謎底位數
# start      : 是否已開始計時（第一次送出猜測時啟動）
# count      : 本局累計猜測次數
# N          : 謎底的字元位數（由伺服器回傳）
# =====================================================
visit = False
start = False
count = 0
N = 0

# =====================================================
# 主遊戲迴圈
# 分為兩個階段：
#   第一階段（visit=False）：發送 HELLO_SERVER 敲門，取得位數 N
#   第二階段（visit=True） ：進入猜數字互動循環
# =====================================================
while True:
    try:
        # ─────────────────────────────────────────────
        # 第一階段：敲門並獲取位數
        # 向伺服器發送 ip 作為連線請求
        # 伺服器回傳謎底的字元位數 N
        # ─────────────────────────────────────────────
        if not visit:
            print("發送連線請求...")
             # --- 新增：自動獲取本機 IP 的程式碼 ---
            try:
                # 建立一個暫時的 socket 來偵測真實的對外 IP
                temp_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                temp_s.connect(("8.8.8.8", 80)) # 假裝連線到 Google DNS
                my_ip = temp_s.getsockname()[0] # 取得系統分配的本機 IP
                temp_s.close()                  # 關閉暫時的 socket
            except Exception:
                # 如果完全沒網路，就退回到本機迴環位址
                my_ip = "127.0.0.1"

            message = my_ip # 將要發送的訊息設定為自己的 IP
            print(f"自動取得本機 IP: {message}，準備傳送給伺服器...")
            # --------------------------------------
            
            #message=input("輸入你的(ip address)給server")
            

            # 將訊息編碼為字節
            message_bytes = message.encode('utf-8')
            # 發送數據到指定的伺服器地址
            client_socket.sendto(message_bytes, server_address)
            
            data, addr = client_socket.recvfrom(BUFFER_SIZE)
            N = int(data.decode('utf-8'))
            print(f"\n連線成功！遊戲開始！")
            print(f" 謎底為【{N}】位數不重複字元 (範圍 0-9, A-F)。")
            visit = True

        # ─────────────────────────────────────────────
        # 第二階段：猜數字循環
        # 讀取玩家輸入並轉為大寫，統一格式
        # ─────────────────────────────────────────────
        else:
            user_input = input(f"\n請輸入 {N} 位數字/文字 (輸入 0 結束)：").upper()
            
            # 玩家輸入離開指令時，通知伺服器並結束程式
            if user_input in ['QUIT', 'EXIT', '0']:
                client_socket.sendto("QUIT".encode('utf-8'), server_address)
                print("客戶端關閉中...")
                break
            
            # ─────────────────────────────────────────
            #  嚴格防呆機制
            # 條件一：輸入長度必須等於 N
            # 條件二：所有字元必須不重複（set 長度等於 N）
            # 不符合時直接 continue，不計入猜測次數，也不傳給伺服器
            # ─────────────────────────────────────────
            if len(user_input) != N or len(set(user_input)) != N:
                print(f" 格式錯誤！請輸入剛好 {N} 個『不重複』的字元。")
                continue # 擋下來，不傳給伺服器，也不算次數
            
            # 累計猜測次數，並在第一次猜測時啟動計時器
            count += 1
            if not start:
                start_time = time.perf_counter()
                start = True
            
            # ─────────────────────────────────────────
            # 開始計算延遲 (RTT, Round-Trip Time)
            # 記錄送出時間，收到回應後計算來回延遲毫秒數
            # ─────────────────────────────────────────
            rtt_start = time.perf_counter()
            client_socket.sendto(user_input.encode('utf-8'), server_address)
            
            # 接收伺服器回傳的 ?A?B 比對結果
            data, addr = client_socket.recvfrom(BUFFER_SIZE)
            rtt_end = time.perf_counter()
            rtt_ms = (rtt_end - rtt_start) * 1000  # 轉換為毫秒
            
            received_message = data.decode('utf-8')
            print(f"比對結果: {received_message} [連線延遲: {rtt_ms:.2f} ms]")

            # ─────────────────────────────────────────
            # 判斷是否勝利
            # 勝利條件：伺服器回傳 "{N}A0B"，代表全部猜中
            # ─────────────────────────────────────────
            if received_message == f"{N}A0B":
                end_time = time.perf_counter()
                elapsed_time = end_time - start_time  # 計算本局總花費時間
                print(f"\n 恭喜 {name} 猜對了！共猜 {count} 次，總花費 {elapsed_time:.2f} 秒。")
                print("正在傳送戰報並獲取排行榜，請稍候...")
                
                # ─────────────────────────────────────
                # 可靠 UDP 傳輸：不斷發送直到收到 ACK
                # 由於 UDP 不保證送達，採用「送出 → 等待 ACK → 超時重傳」機制
                # 格式：WIN_REPORT,暱稱,系統時間,猜測次數,花費秒數
                # ─────────────────────────────────────
                while True:
                    report = f"WIN_REPORT,{name},{time.strftime('%Y-%m-%d %H:%M:%S')},{count},{elapsed_time:.2f}"
                    client_socket.sendto(report.encode('utf-8'), server_address)
                    
                    client_socket.settimeout(2.0) # 等待 2 秒
                    try:
                        ack_data, _ = client_socket.recvfrom(BUFFER_SIZE)
                        if ack_data.decode('utf-8') == "ACK_OK":
                            break # 收到伺服器確認，跳出重傳迴圈
                    except socket.timeout:
                        print("網路超時，重新傳送戰報中...")
                
                # 恢復正常死等模式（不設超時），等待伺服器傳來完整排行榜
                client_socket.settimeout(None) # 恢復正常死等模式
                board_bytes, _ = client_socket.recvfrom(4096) 
                print(board_bytes.decode('utf-8'))
                
                # 詢問玩家是否要再挑戰一次，並將選擇回傳給伺服器
                again = input("\n要不要再挑戰一次? (Y or N): ")
                client_socket.sendto(f"REPLAY,{again.upper()}".encode('utf-8'), server_address)
                
                if again.upper() == "Y":
                    # 重置所有本局狀態，回到第一階段重新敲門
                    visit = False
                    start = False
                    count = 0
                    print("\n" + "="*30)
                else:
                    print("遊戲結束！")
                    break

    except Exception as e:
        print(f"發生錯誤: {e}")
        break

# 關閉 Socket，釋放系統資源
client_socket.close()
