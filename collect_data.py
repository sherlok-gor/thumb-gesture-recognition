"""
Piezo 傳感器數據採集腳本
連接到 ESP32-C3 WiFi，收集各手指敲擊數據
"""

import socket
import time
import os
import csv
from datetime import datetime

# ⚠️ 修改為你的 ESP32 IP
ESP_IP = "192.168.0.201"
PORT = 8888
SAVE_DIR = "piezo_data"
EXPECTED_SAMPLES = 1200

# 建立數據目錄
os.makedirs(SAVE_DIR, exist_ok=True)

class PiezoDataCollector:
    def __init__(self, esp_ip, port):
        self.esp_ip = esp_ip
        self.port = port
        self.sock = None
        self.connected = False
    
    def connect(self):
        """連接到 ESP32"""
        print("\n🔌 正在連接 ESP32...")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.esp_ip, self.port))
            self.sock.settimeout(5)
            self.connected = True
            
            # 接收歡迎信息
            try:
                welcome = self.sock.recv(256).decode('utf-8', errors='replace')
                if "CONNECTED" in welcome:
                    print("✅ 連線成功！")
                    print(f"   服務器回應: {welcome.strip()}")
                    return True
            except socket.timeout:
                print("✅ 連線成功（未收到歡迎信息，但可正常通訊）")
                return True
        
        except Exception as e:
            print(f"❌ 連線失敗: {e}")
            self.connected = False
            return False
    
    def send_label(self, label):
        """發送標籤給 ESP32"""
        try:
            if not self.connected:
                return False
            
            self.sock.sendall((label + "\n").encode())
            print(f"📤 已發送標籤: {label}")
            return True
        except Exception as e:
            print(f"❌ 發送失敗: {e}")
            self.connected = False
            return False
    
    def receive_waveform(self):
        """接收完整的波形數據"""
        data = []
        label = ""
        
        try:
            # 等待 START 信號
            buffer = ""
            start_found = False
            
            print("⏳ 等待 START 信號...")
            timeout_start = time.time()
            
            while not start_found:
                if time.time() - timeout_start > 10:
                    print("❌ 超時：未收到 START 信號")
                    return "", []
                
                try:
                    chunk = self.sock.recv(1024).decode('utf-8', errors='replace')
                    if not chunk:
                        print("❌ 連線中斷")
                        self.connected = False
                        return "", []
                    
                    buffer += chunk
                    if "START" in buffer:
                        start_found = True
                        buffer = buffer.split("START", 1)[1]  # 移除 START 前的內容
                except socket.timeout:
                    continue
            
            print("🎤 開始接收波形...")
            
            # 讀取標籤行
            lines = buffer.split('\n')
            if len(lines) > 0 and lines[0].strip():
                label = lines[0].strip()
            else:
                # 標籤可能在下一個接收中
                label = self.sock.recv(256).decode('utf-8', errors='replace').strip()
            
            print(f"📋 標籤: {label}")
            
            # 將已有的行重新加入處理
            buffer = '\n'.join(lines[1:])
            
            # 讀取數據
            while True:
                if buffer:
                    lines = buffer.split('\n')
                    buffer = ""
                else:
                    try:
                        chunk = self.sock.recv(4096).decode('utf-8', errors='replace')
                        if not chunk:
                            print("❌ 連線中斷")
                            break
                        buffer = chunk
                        lines = buffer.split('\n')
                        buffer = lines[-1]  # 保留未完成的行
                        lines = lines[:-1]
                    except socket.timeout:
                        continue
                
                for line in lines:
                    line = line.strip()
                    
                    if line == "END":
                        print(f"✅ 接收完成！共 {len(data)} 筆")
                        return label, data
                    
                    elif line == "DONE":
                        # 双重檢查 END
                        if len(data) > 0:
                            return label, data
                    
                    elif line and (line.isdigit() or line.lstrip('-').isdigit()):
                        try:
                            value = int(line)
                            data.append(value)
                            
                            if len(data) % 200 == 0:
                                print(f"   進度: {len(data)}/{EXPECTED_SAMPLES} ▓")
                            
                            if len(data) >= EXPECTED_SAMPLES:
                                print(f"✅ 已接收 {EXPECTED_SAMPLES} 筆，停止接收")
                                return label, data
                        
                        except ValueError:
                            pass
        
        except Exception as e:
            print(f"❌ 接收錯誤: {e}")
        
        return label, data
    
    def save_data(self, label, data, file_index):
        """保存數據到 CSV"""
        if len(data) < 1000:  # 至少 1000 筆
            print(f"⚠️ 數據不完整 ({len(data)} 筆)，未保存\n")
            return False
        
        try:
            filename = os.path.join(SAVE_DIR, f"{file_index:03d}_{label}.csv")
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['value'])
                for v in data:
                    writer.writerow([v])
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"💾 [{timestamp}] 儲存成功: {filename}")
            print(f"   資料量: {len(data)} 筆\n")
            return True
        
        except Exception as e:
            print(f"❌ 儲存失敗: {e}\n")
            return False
    
    def close(self):
        """關閉連線"""
        if self.sock:
            self.sock.close()
            print("👋 連線已關閉")

# 主程序
def main():
    collector = PiezoDataCollector(ESP_IP, PORT)
    
    # 連接
    if not collector.connect():
        return
    
    # 顯示幫助信息
    print("\n" + "="*50)
    print("🎤 Piezo 傳感器數據採集")
    print("="*50)
    print("\n標籤命名規則（3×3=9 類）:")
    print("  - 第一部分：目標手指")
    print("    ti=食指, tm=中指, tr=無名指")
    print("  - 第二部分：敲擊部位")
    print("    fi=指尖, fn=指甲, fd=骨頭")
    print("\n範例: ti_fi（敲擊食指指尖）")
    print("      tm_fn（敲擊中指指甲）")
    print("\n輸入 'quit' 結束程序")
    print("="*50 + "\n")
    
    file_index = 0
    
    # 列出已有的文件以確定起始編號
    if os.listdir(SAVE_DIR):
        existing_files = [f for f in os.listdir(SAVE_DIR) if f.endswith('.csv')]
        if existing_files:
            last_index = max([int(f.split('_')[0]) for f in existing_files])
            file_index = last_index + 1
    
    # 數據採集迴圈
    while True:
        label = input("標籤 (例: ti_fi): ").strip()
        
        if label.lower() == 'quit':
            break
        
        if not label:
            print("⚠️ 標籤不能為空\n")
            continue
        
        # 驗證標籤格式
        parts = label.split('_')
        if len(parts) != 2:
            print("⚠️ 標籤格式錯誤！應為 'fi_fi' 格式\n")
            continue
        
        # 發送標籤
        if not collector.send_label(label):
            # 重新連接
            print("🔌 嘗試重新連接...")
            if not collector.connect():
                continue
            collector.send_label(label)
        
        # 接收波形
        received_label, data = collector.receive_waveform()
        
        if len(data) > 0:
            # 保存數據
            if collector.save_data(received_label, data, file_index):
                file_index += 1
        else:
            print("❌ 未接收到有效數據\n")
        
        print("準備下一次採集...\n")
    
    collector.close()
    print("\n程序已結束")

if __name__ == "__main__":
    main()
