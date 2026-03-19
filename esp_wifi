#include <WiFi.h>
#include <HardwareSerial.h>

// UART1 跨板通訊
HardwareSerial MySerial(1);

// ⚠️ 修改為你的 WiFi 信息
const char* ssid     = "一人有一個wifi";
const char* password = "ruxhu7-wycmuS-ripnad";

// TCP 服務器
WiFiServer server(8888);
WiFiClient client;

// 狀態標誌
bool clientConnected = false;
unsigned long lastActivityTime = 0;
const unsigned long ACTIVITY_TIMEOUT = 30000; // 30秒超時

void setup() {
  Serial.begin(115200);
  // RX=20, TX=21（與 Sensor ESP 交叉連接）
  MySerial.begin(921600, SERIAL_8N1, 20, 21);
  
  delay(1000);
  Serial.println("\n╔════════════════════════════════════╗");
  Serial.println("║   WiFi ESP32-C3 啟動...             ║");
  Serial.println("╚════════════════════════════════════╝\n");
  
  // 連接 WiFi
  connectToWiFi();
  
  // 啟動 TCP 服務器
  server.begin();
  Serial.println("✓ TCP 服務器已啟動 (8888 端口)");
  Serial.println("✓ Python 可以連接此 ESP32\n");
}

void loop() {
  // 檢查 Python 客戶端連線
  handleClientConnection();
  
  // Python → Sensor 指令轉發
  if (clientConnected && client.available()) {
    forwardCommandToSensor();
  }
  
  // Sensor → Python 波形轉發
  if (clientConnected && MySerial.available()) {
    forwardWaveformToPython();
  }
  
  // 活動超時檢查
  if (clientConnected && (millis() - lastActivityTime > ACTIVITY_TIMEOUT)) {
    Serial.println("⚠ 客戶端超時，斷開連接");
    client.stop();
    clientConnected = false;
  }
}

void connectToWiFi() {
  Serial.print("正在連接 WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  int attempts = 0;
  
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("\n✓ WiFi 已連接！\n✓ IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n✗ WiFi 連接失敗！");
  }
}

void handleClientConnection() {
  if (!clientConnected) {
    WiFiClient newClient = server.available();
    if (newClient) {
      client = newClient;
      client.setNoDelay(true);
      clientConnected = true;
      lastActivityTime = millis();
      
      Serial.println("✓ Python 客戶端已連接！");
      client.println("CONNECTED:Welcome to Thumb Gesture Sensor\n");
    }
  }
}

void forwardCommandToSensor() {
  String cmd = client.readStringUntil('\n');
  cmd.trim();
  
  if (cmd.length() > 0) {
    lastActivityTime = millis();
    Serial.printf("📤 Python → Sensor: %s\n", cmd.c_str());
    MySerial.println(cmd);
  }
}

void forwardWaveformToPython() {
  String line = MySerial.readStringUntil('\n');
  line.trim();
  
  if (line.length() == 0) return;
  
  lastActivityTime = millis();
  
  // 波形幀開始
  if (line == "START") {
    Serial.println("🎤 Sensor → Python: 開始傳輸波形");
    client.println("START");
    
    int lineCount = 0;
    int sampleCount = 0;
    
    // 讀取標籤
    while (!MySerial.available()) delay(1);
    String label = MySerial.readStringUntil('\n');
    label.trim();
    client.println(label);
    Serial.printf("   標籤: %s\n", label.c_str());
    
    // 讀取數據行
    while (true) {
      while (!MySerial.available()) delay(1);
      
      line = MySerial.readStringUntil('\n');
      line.trim();
      
      if (line.length() > 0) {
        client.println(line);
        lineCount++;
        
        if (line != "END" && line.toInt() > 0) {
          sampleCount++;
        }
        
        if (lineCount % 100 == 0) {
          Serial.printf("   進度: %d 筆\n", sampleCount);
        }
        
        if (line == "END") {
          client.println("DONE");
          Serial.printf("✓ 波形轉發完成 (%d 筆)\n\n", sampleCount);
          break;
        }
      }
    }
  }
}
