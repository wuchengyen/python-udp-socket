import socket
import sys
import os
#192.168.0.11
#伺服器端監聽的端口號
#myIP(for client):61.31.233.1
SERVER_PORT = 5555
#預設閘道 . . . . . . . . . . . . .: 192.168.0.1
#定義接收數據的緩衝區大小
BUFFER_SIZE = 1024

def ab(message,answer):
#12345
#52341
    n = len(answer)
    a=0
    b=0
    for i in range(n):
        if message[i]==answer[i]:
            a+=1
        else:
            for j in range(n):
                if message[i]==answer[j]:
                    b+=1
    return str(a)+'A'+str(b)+'B'

# =======================================================
# 系統啟動時：檢查並自動建立 records.txt
# =======================================================
if not os.path.exists("records.txt"):
    with open("records.txt", "w", encoding="utf-8") as file:
        pass 
    print("系統提示：找不到歷史紀錄，已自動建立全新的 records.txt 檔案。")
print(f"UDP伺服器正在啟動，監聽窗口{SERVER_PORT}...")

#創建UDP socket(IPv4,UDP)
try:
    server_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    print("Socket創建成功")
except socket.error as msg:
    print(f'無法創建 Socket.錯誤碼:{str(msg[0])} 錯誤訊息 {msg[1]}')
    sys.exit()
    
#將 socket綁定到指定的地址和端口
#''表示綁定到所有可用的網路接口
try:
    server_socket.bind(('', SERVER_PORT))
    print(f"Socket 綁定到端口 {SERVER_PORT} 成功，伺服器已準備好接收訊息。")
except socket.error as msg:
    print(f"無法綁定 Socket。錯誤碼：{str(msg[0])} 錯誤訊息 {msg[1]}")
    server_socket.close()
    sys.exit()

    # 伺服器進入無限循環，持續等待接收訊息
N=int(input("請輸入位數N："))
answer=input("N位數的正確字串:")
#N=len(answer)
visit = False
# === 在進入 while 迴圈前，加入這行設定超時 ===
# 設定 1 秒的超時，讓 recvfrom 不會永遠卡死
server_socket.settimeout(1.0)
if answer !='0':
    print("等待client...")
    while True:
        try:
            
            # 接收來自客戶端的數據和地址 (Blocking Call)
            # 返回 (數據, 發送方地址) 元組
            
            data_bytes, address = server_socket.recvfrom(BUFFER_SIZE)

            # 將接收到的字節數據轉換為字符串
            message = data_bytes.decode('utf-8').strip()
            if message.lower() in ['quit', 'exit']:
                print("客戶端已關閉...")
                break

            # 變更發送方的 IP 地址和端口號
            client_ip, client_port = address

            # 打印收到的訊息以及發送方的地址信息
            #print(f"收到來自 {client_ip}:{client_port} 的訊息: {message}")
            #傳送N
            #server_socket.sendto(N, address)在 Python 3 的 Socket 網路通訊中，傳輸的資料必須是 「字節 (bytes)」 格式。
            #你目前程式碼裡的 N 是一個整數 (Integer)，因為它是透過 len() 計算出來的長度。Socket 不知道怎麼直接把整數丟到網路上，所以會直接當機報錯。
            # 正確的寫法：先轉成字串，再編碼成 utf-8 字節
            # === 新增：攔截並處理勝利報告 ===
                # 檢查字串開頭是不是我們剛剛設定的標籤
            if message.startswith("WIN_REPORT"):
                # 使用逗號將字串切成四個部分
                # split(',') 會把 "WIN_REPORT,時間,次數,秒數" 變成一個串列 (List)
                parts = message.split(',')
                print(f"收到{client_ip}:{client_port}:名字:{parts[1]}、系統時間:{parts[2]}、次數:{parts[3]}、花費時間:{parts[4]}")#收到Client z.z.z.z：你的名字、系統時間、猜出結果的次數與時間。
                # 確保切割出來的資料數量正確再處理，避免發生錯誤
                if len(parts) == 5:
                    r_name = parts[1]
                    r_sys_time = parts[2]
                    r_count = parts[3]
                    r_time_spent = parts[4]
                    
                    # 1. 將這次的紀錄「附加 (append)」寫入 txt 檔案
                    # 使用 encoding='utf-8' 確保中文名字不會亂碼
                    with open("records.txt", "a", encoding="utf-8") as file:
                        file.write(f"{r_name},{r_sys_time},{r_count},{r_time_spent}\n")
                    
                    # 2. 讀取所有紀錄並準備排序
                    all_records = []
                    with open("records.txt", "r", encoding="utf-8") as file:
                        for line in file:
                            if line.strip(): # 略過空行
                                data = line.strip().split(',')
                                if len(data) == 4:
                                    # 將秒數轉為浮點數(float)以便後續排序
                                    all_records.append((data[0], data[1], int(data[2]), float(data[3])))
                    
                    # 3. 依照「花費時間 (索引值 3)」從小到大排序
                    all_records.sort(key=lambda x: x[3])
                    
                    # 4. 建立排行榜字串
                    board_str = "\n🏆 --- 英雄榜 (按花費時間排序) --- 🏆\n"
                    board_str += "名次 | 暱稱       | 系統時間             | 次數 | 花費時間\n"
                    board_str += "-" * 55 + "\n"
                    
                    rank = 1
                    for rec in all_records:
                        rec_name, rec_time, rec_count, rec_spent = rec
                        
                        # 判斷這筆紀錄是不是「本次」的成績
                        # 條件：名字、時間、次數、秒數 都完全吻合
                        is_current = (rec_name == r_name and rec_time == r_sys_time and rec_count == int(r_count) and rec_spent == float(r_time_spent))
                        
                        # 格式化單行內容
                        row_info = f"第{rank:2}名 | {rec_name:^8} | {rec_time} | {rec_count:2}次 | {rec_spent:.2f} 秒\n"
                        
                        if is_current:
                            # 使用 ANSI 碼 \033[1m (粗體) 和 \033[0m (重置) 來強調
                            # 順便加上 => 箭頭讓它更明顯
                            board_str += f"\033[1m\033[93m => {row_info} \033[0m" 
                        else:
                            board_str += f"    {row_info}"
                            
                        rank += 1
                    
                    # 5. 將排版好的排行榜傳回給 Client
                    server_socket.sendto(board_str.encode('utf-8'), address)
                    print(f"已將最新排行榜發送給 {client_ip}:{client_port}")

            
                    # ================================
                    print(f"等待client{client_ip}:{client_port}回復... ")
                    #data_bytes, address = server_socket.recvfrom(BUFFER_SIZE)
                continue # 處理完報告後，直接進入下一個迴圈
            if message == "Y":
                N=int(input("請輸入位數N："))
                answer=input("請輸入正確數字:")
                if answer =='0':
                    break
                #N=len(answer)
                print("等待client...")
                visit=False
            
            
            elif not visit:
                print(f" {client_ip}:{client_port} 來猜數字了!")
                server_socket.sendto(str(N).encode('utf-8'), address)
                print(f"已將位數回傳給 {client_ip}:{client_port}")
                visit = True
            else:
                #print(f"已將訊息回傳給 {client_ip}:{client_port}")
                status = ab(message,answer)
                
                print(f"client{client_ip}:{client_port}猜的數字是:{message},比對結果是{status} ")
                server_socket.sendto(status.encode('utf-8'), address)
                #if(status==(str(N)+'A'+'0B')):
                
            '''
            # *** 加入回傳功能 ***
            # 將收到的原始字節數據發送回發送方地址
            server_socket.sendto(data_bytes, address)
            print(f"已將訊息回傳給 {client_ip}:{client_port}")
            '''
        except socket.timeout:
        # 這是我們預期的超時！
        # 什麼都不用做，直接 continue 讓迴圈繼續。
        # 這個短暫的甦醒，可以讓 Python 捕捉到 KeyboardInterrupt (Ctrl+C)
            continue
        except KeyboardInterrupt:
            # 按下 Ctrl+C 結束
            print("\n伺服器正在關閉...")
            break

        except socket.error as msg:
            print(f"接收訊息時發生錯誤: {str(msg[0])} 錯誤訊息: {msg[1]}")
            # pass # 忽略錯誤繼續
        
#循環結束後關閉
server_socket.close()
print("伺服器關閉")