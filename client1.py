# udp_client.py
import socket
import sys
import time
#IPv4 位址 . . . . . . . . . . . . : 192.168.0.10
# 伺服器端監聽的端口號
SERVER_PORT = 5555

# 定義接收數據的緩衝區大小 (與伺服器一致或更大)
BUFFER_SIZE = 1024

# 創建 UDP socket (IPv4, UDP)
try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("客戶端 Socket 創建成功")
except socket.error as msg:
    print(f'無法創建 Socket. 錯誤碼：{str(msg[0])} 錯誤訊息 {msg[1]}')
    sys.exit()
# 提示用戶輸入目標伺服器的 IP 地址
name=input("請輸入名字:")
while True:
    server_ip = input("請輸入目標伺服器的 IP 地址 (例如: 127.0.0.1): ")
    # 簡單檢查 IP 地址格式
    parts = server_ip.split('.')
    if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
        break # 格式正確
    else:
        print("IP 地址格式不正確，請重新輸入。")

# 定義伺服器的完整地址 (IP 地址和端口號)
server_address = (server_ip, SERVER_PORT)

print(f"客戶端將向 {server_ip}:{SERVER_PORT} 發送訊息。")
print("輸入 'quit' 或 'exit' 來結束程式。")
visit = False
start = False
count = 0
# 進入無限循環，持續發送訊息並接收回傳
while True:
    try:
        if not visit:
            
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
            print(f"訊息 '{message}' 已發送。")
            visit = True
                    # *** 加入接收回傳功能 ***
            print("等待接收數字的位數")
            # 接收來自伺服器的數據和地址 (Blocking Call)
            received_data_bytes, server_reply_address = client_socket.recvfrom(BUFFER_SIZE)

            # 將接收到的字節數據解碼為字符串
            received_message = received_data_bytes.decode('utf-8').strip()

            # 打印接收到的回傳訊息
            print(f"要猜的數字是{received_message}位數")
            N = int(received_message)
            #print(f"收到來自伺服器 {server_reply_address[0]}:{server_reply_address[1]} 的回傳訊息: {received_message}")
        else:
            message = input("請輸入你猜的數字(輸入exit 結束程式) ：")
            count+=1
            if not start:
                start_time = time.perf_counter()
                start = True
            if (message.lower() in ['quit', 'exit']) or message=='0':
                 # 將訊息編碼為字節
                message_bytes = message.encode('utf-8')
                # 發送數據到指定的伺服器地址
                client_socket.sendto(message_bytes, server_address)
                print("客戶端正在關閉...")
                break
            
            # 將訊息編碼為字節
            message_bytes = message.encode('utf-8')
            # 發送數據到指定的伺服器地址
            client_socket.sendto(message_bytes, server_address)
            print(f"訊息 {message} 已發送。等待比對結果...")
            # 接收來自伺服器的數據和地址 (Blocking Call)
            received_data_bytes, server_reply_address = client_socket.recvfrom(BUFFER_SIZE)

            # 將接收到的字節數據解碼為字符串
            received_message = received_data_bytes.decode('utf-8').strip()

            # 打印接收到的回傳訊息
            print(f"比對結果:{received_message}")
            if(received_message==(str(N)+'A'+'0B')):
                end_time = time.perf_counter()
                elapsed_time = end_time - start_time
                print(f"{name}你猜對了，共猜了{count}次，花費{elapsed_time:.2f}秒")
                # === 新增：發送勝利報告給 Server ===
                # 1. 取得當下的系統時間 (格式: 年-月-日 時:分:秒)
                current_system_time = time.strftime("%Y-%m-%d %H:%M:%S")
                report_message = f"WIN_REPORT,{name},{current_system_time},{count},{elapsed_time:.2f}"
                client_socket.sendto(report_message.encode('utf-8'), server_address)
                # 2. 將三個數值打包成一個字串，前面加上 "WIN_REPORT" 作為標識
                # 格式會變成類似這樣： "WIN_REPORT,2026-05-10 22:08:26,5,12.34"
                print("正在向伺服器獲取排行榜，請稍候...")
                # 為了接收排行榜，緩衝區稍微加大到 4096
                board_bytes, _ = client_socket.recvfrom(4096) 
                print(board_bytes.decode('utf-8'))
            
            
                again = input("要不要再玩一次? (Y orN):")
                if again =="Y":
                    
                    visit = False
                    start = False
                    count = 0
                    client_socket.sendto("Y".encode('utf-8'), server_address)
                else:
                    client_socket.sendto("exit".encode('utf-8'), server_address)
                    break
            
            #*****************計時
        '''
        # 獲取用戶輸入的訊息
        message = input("請輸入要發送的訊息：")

        # 檢查退出指令
        if message.lower() in ['quit', 'exit']:
            print("客戶端正在關閉...")
            break

        # 將訊息編碼為字節
        message_bytes = message.encode('utf-8')

        # 發送數據到指定的伺服器地址
        client_socket.sendto(message_bytes, server_address)
        print(f"訊息 {message} 已發送。")
        '''

    except socket.error as msg:
        print(f'發生 Socket 錯誤: {str(msg[0])} 錯誤訊息 {msg[1]}')
        pass # 忽略錯誤，繼續

    except Exception as e:
        print(f'發生意外錯誤: {e}')
        break

# 關閉 socket
client_socket.close()
print("客戶端已關閉。")
