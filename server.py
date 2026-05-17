import socket
import sys
import os
import time

# =====================================================
# 常數設定
# SERVER_PORT : 伺服器監聽的 UDP 埠號
# BUFFER_SIZE : 每次接收資料的緩衝區大小（位元組）
# =====================================================
SERVER_PORT = 5555
BUFFER_SIZE = 1024

# =====================================================
# 全域狀態變數
# player_sessions      : 字典，以玩家位址 (ip, port) 為 key，
#                        儲存每位玩家的獨立遊戲狀態
# total_bytes_received : 累計收到的 UDP payload 總位元組數
# packet_count         : 累計收到的封包總數
# start_monitor_time   : 伺服器啟動時間，用於計算平均流量速率
# =====================================================
player_sessions = {}  
total_bytes_received = 0
packet_count = 0
start_monitor_time = time.time()

def ab(message, answer):
    """
    計算猜測結果，回傳 ?A?B 格式字串。

    A：位置與字元都正確的數量（完全命中）
    B：字元存在但位置不對的數量（存在但錯位）

    參數：
        message (str) : 玩家猜測的字串
        answer  (str) : 本局謎底字串

    回傳：
        str : 例如 "1A2B"
    """
    n = len(answer)
    a, b = 0, 0
    # 只比對到 min(猜測長度, 謎底長度) 的範圍，避免 index 越界
    check_len = min(len(message), n)
    for i in range(check_len):
        if message[i] == answer[i]:
            # 位置與字元完全相同 → A+1
            a += 1
        else:
            # 字元存在於謎底其他位置 → B+1
            for j in range(n):
                if message[i] == answer[j]: b += 1
    return f"{a}A{b}B"

# =====================================================
# 確保 records.txt 存在
# 若檔案不存在則建立空白檔案，避免後續讀取時發生錯誤
# =====================================================
if not os.path.exists("records.txt"):
    with open("records.txt", "w", encoding="utf-8") as f: pass

# =====================================================
# 建立並綁定 UDP Socket
# bind('', PORT) 表示監聽本機所有網路介面
# settimeout(1.0) 讓 recvfrom 每秒超時一次，
#   使主迴圈可以定期檢查 KeyboardInterrupt 等中斷訊號
# =====================================================
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    server_socket.bind(('', SERVER_PORT))
    server_socket.settimeout(1.0)
except socket.error as msg:
    print(f"無法綁定 Socket。錯誤訊息：{msg}")
    sys.exit()

# =====================================================
#  遊戲初始化：手動輸入第一局的題目
# =====================================================
print("=== 1A2B 伺服器啟動設定 ===")
n=int(input("輸入字元數"))
global_answer = input("請輸入第一局的正確數字/文字：").upper()
print(f"\nUDP 伺服器啟動，監聽窗口 {SERVER_PORT} 中...\n等待玩家連線...")

# =====================================================
# 主事件迴圈
# 持續等待並處理來自各玩家的 UDP 封包
# 每個封包依訊息內容分流至對應的處理邏輯
# =====================================================
while True:
    try:
        # 等待接收任意玩家的封包
        # data_bytes : 原始位元組資料
        # address    : 來源位址 tuple (ip, port)
        data_bytes, address = server_socket.recvfrom(BUFFER_SIZE)
        message = data_bytes.decode('utf-8').strip()
        
        # ─────────────────────────────────────────────
        # 流量監控區塊
        # 每收到一個封包就更新統計數據並印出監控日誌
        # ─────────────────────────────────────────────
        # --- 流量日誌 ---
        # --- 流量日誌 ---
        packet_count += 1

        # 應用層資料大小，也就是 UDP payload
        payload_size = len(data_bytes)

        # 累計 payload 總大小
        total_bytes_received += payload_size

        # 計算平均封包大小
        avg_packet_size = total_bytes_received / packet_count

        # 計算目前已運行時間
        elapsed_monitor_time = time.time() - start_monitor_time

        # 計算平均接收速率 Bytes/sec
        if elapsed_monitor_time > 0:
            bytes_per_second = total_bytes_received / elapsed_monitor_time
        else:
            bytes_per_second = 0

        # 估算實際網路層封包大小：
        # IPv4 header 約 20 bytes，UDP header 8 bytes
        estimated_network_packet_size = payload_size + 20 + 8
        estimated_total_network_bytes = total_bytes_received + packet_count * 28

        print(
            f"[流量監控] {time.strftime('%H:%M:%S')} | "
            f"來源: {address} | "
            f"Payload: {payload_size:3} Bytes | "
            f"估算實際封包: {estimated_network_packet_size:3} Bytes | "
            f"累計封包: {packet_count:2} 個 | "
            f"累計Payload: {total_bytes_received} Bytes | "
            f"估算總流量: {estimated_total_network_bytes} Bytes | "
            f"平均封包: {avg_packet_size:.2f} Bytes | "
            f"速率: {bytes_per_second:.2f} Bytes/s"
        )

        # ─────────────────────────────────────────────
        # 新玩家初始化
        # 若此位址尚未在 player_sessions 中，代表是新玩家
        # 為其建立獨立的遊戲狀態：
        #   answer : 本局謎底（使用全域設定的 global_answer）
        #   visit  : 是否已完成敲門握手
        #   count  : 本局猜測次數
        # ─────────────────────────────────────────────
        # --- 處理新玩家加入 ---
        if address not in player_sessions:
            player_sessions[address] = {"answer": global_answer, "visit": False, "count": 0}
            print(f"\n[系統] 新玩家 {address} 加入了！")
            print(f"[系統] 他的謎底為我們剛才設定的：【{global_answer}】")

        # 取出該玩家的狀態物件，後續操作皆透過此參考
        user = player_sessions[address]

        # =====================================================
        # 攔截 1：處理玩家離開
        # 收到 QUIT / EXIT / 0 時，清除該玩家的 session 並結束
        # =====================================================
        if message.upper() in ['QUIT', 'EXIT', '0']:
            print(f"\n[系統] 玩家 {address} 已中斷連線。")
            del player_sessions[address] # 清除該玩家紀錄
            break

        # =====================================================
        # 攔截 2：處理勝利報告與排行榜 (WIN_REPORT)
        # 格式：WIN_REPORT,暱稱,系統時間,猜測次數,花費秒數
        # 流程：
        #   1. 立即回傳 ACK_OK，確認伺服器已收到戰報
        #   2. 解析戰報內容並寫入 records.txt
        #   3. 讀取所有紀錄，依花費時間排序
        #   4. 組合排行榜字串（當前玩家以黃色粗體標示）
        #   5. 將排行榜傳回給玩家
        # =====================================================
        if message.startswith("WIN_REPORT"):
            # 1. 回傳 ACK 讓 Client 知道伺服器收到了
            server_socket.sendto("ACK_OK".encode('utf-8'), address)
            
            parts = message.split(',')
            if len(parts) == 5:
                r_name, r_sys_time, r_count, r_time_spent = parts[1], parts[2], parts[3], parts[4]
                print(f"\n🎉 [戰報] {r_name} ({address}) 猜對了！共猜 {r_count} 次，花費 {r_time_spent} 秒。")
                
                # 將本局戰績追加寫入歷史紀錄檔
                with open("records.txt", "a", encoding="utf-8") as f:
                    f.write(f"{r_name},{r_sys_time},{r_count},{r_time_spent}\n")
                
                # 讀取所有歷史紀錄並解析為 tuple 清單
                # 格式：(暱稱, 系統時間, 猜測次數(int), 花費秒數(float))
                all_records = []
                with open("records.txt", "r", encoding="utf-8") as file:
                    for line in file:
                        if line.strip(): 
                            data = line.strip().split(',')
                            if len(data) == 4:
                                all_records.append((data[0], data[1], int(data[2]), float(data[3])))
                # 依花費時間（第 4 欄）由小到大排序
                all_records.sort(key=lambda x: x[3])
                
                # 組合完整的排行榜字串，含表頭與分隔線
                board_str = "\n🏆 --- 英雄榜 (按花費時間排序) --- 🏆\n"
                board_str += "名次 | 暱稱       | 系統時間             | 次數 | 花費時間\n"
                board_str += "-" * 55 + "\n"
                rank = 1
                for rec in all_records:
                    rec_name, rec_time, rec_count, rec_spent = rec
                    # 判斷是否為本次勝利的玩家，若是則以黃色粗體 ANSI 碼標示
                    is_current = (rec_name == r_name and rec_time == r_sys_time and rec_count == int(r_count) and rec_spent == float(r_time_spent))
                    row_info = f"第{rank:2}名 | {rec_name:^8} | {rec_time} | {rec_count:2}次 | {rec_spent:.2f} 秒\n"
                    if is_current:
                        board_str += f"\033[1m\033[93m => {row_info} \033[0m" 
                    else:
                        board_str += f"    {row_info}"
                    rank += 1
                
                # 將完整排行榜字串傳回給該玩家
                server_socket.sendto(board_str.encode('utf-8'), address)
                print(f"[系統] 已將排行榜發送給 {address}，等待他決定是否重玩...")
            continue

        # =====================================================
        # 攔截 3：處理重玩指令 (REPLAY)
        # 格式：REPLAY,Y 或 REPLAY,N
        # 若選擇 Y：管理員手動輸入下一局新謎底，重置玩家狀態
        # 若選擇 N：清除玩家 session，結束該玩家的遊戲
        # =====================================================
        if message.startswith("REPLAY"):
            choice = message.split(',')[1]
            if choice == "Y":
                print(f"\n[系統] 玩家 {address} 選擇再玩一次！")
                
                # 🚨 拔除自動產生，改為讓伺服器管理員手動輸入下一局新答案
                new_answer = input(f" 請為該玩家輸入下一局的新謎底 (輸入 0 結束伺服器)：").upper()
                if new_answer == '0':
                    print("伺服器關閉中...")
                    break
                
                # 更新該玩家的謎底並重置遊戲狀態
                user["answer"] = new_answer
                user["visit"] = False
                user["count"] = 0
                print(f"[系統] 已設定新謎底：【{user['answer']}】，等待玩家猜測...")
            else:
                # 玩家選擇不再玩，清除其 session
                print(f"\n[系統] 玩家 {address} 結束遊戲並離開了。")
                del player_sessions[address]
                break
            continue

        # =====================================================
        # 正常遊戲邏輯
        # visit=False：玩家尚未完成握手，回傳謎底位數 N
        # visit=True ：玩家送來猜測字串，計算 ?A?B 並回傳
        # =====================================================
        if not user["visit"]:
            # 玩家第一次傳來的敲門封包，回傳位數 N
            server_socket.sendto(str(len(user["answer"])).encode('utf-8'), address)
            user["visit"] = True
        else:
            # 玩家傳來猜測的數字，呼叫 ab() 計算結果後回傳
            user["count"] += 1
            status = ab(message, user["answer"])
            print(f"[遊戲] {address} 猜了: {message} ➜ 結果: {status}")
            server_socket.sendto(status.encode('utf-8'), address)

    except socket.timeout:
        # recvfrom 超時（每秒觸發一次），繼續等待下一個封包
        continue
    except KeyboardInterrupt:
        # 管理員按下 Ctrl+C，優雅地關閉伺服器
        print("\n伺服器正在關閉...")
        break

# 關閉 Socket，釋放系統資源
server_socket.close()
