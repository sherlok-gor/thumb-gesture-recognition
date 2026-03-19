#include <HardwareSerial.h>

// UART1 跨板通訊
HardwareSerial MySerial(1);

#define PIEZO_PIN    4
#define SAMPLE_RATE  2000   // Hz
#define TOTAL_SAMPLES 1600  // 0.8秒
#define SKIP_SAMPLES 400    // 前0.2秒（預熱）
#define SEND_SAMPLES 1200   // 後0.6秒

String currentLabel = "";
bool collecting = false;

void setup() {
  Serial.begin(115200);
  // RX=20, TX=21（與 WiFi ESP 交叉連接）
  MySerial.begin(921600, SERIAL_8N1, 20, 21);
  
  analogReadResolution(12);  // 0-4095
  pinMode(PIEZO_PIN, INPUT);
  
  delay(1000);
  Serial.println("\n╔════════════════════════════════════╗");
  Serial.println("║   Sensor ESP32-C3 啟動完成！       ║");
  Serial.println("║   頻率: 2000Hz | 通道: UART1      ║");
  Serial.println("╚════════════════════════════════════╝\n");
}

void loop() {
  // 監聽來自 WiFi ESP 的指令
  if (MySerial.available()) {
    String cmd = MySerial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd.length() > 0 && !collecting) {
      currentLabel = cmd;
      Serial.printf("[收到] 標籤: %s\n", currentLabel.c_str());
      collectAndSend();
    }
  }
}

void collectAndSend() {
  collecting = true;
  
  // 計數倒數
  MySerial.println("COUNT:3");
  delay(1000);
  MySerial.println("COUNT:2");
  delay(1000);
  MySerial.println("COUNT:1");
  delay(200);
  MySerial.println("COUNT:START");
  
  // 採樣
  uint16_t fullWave[TOTAL_SAMPLES];
  
  Serial.println("[採樣] 開始 2000Hz 採樣...");
  unsigned long startTime = micros();
  
  for (int i = 0; i < TOTAL_SAMPLES; i++) {
    fullWave[i] = analogRead(PIEZO_PIN);
    
    // 精確計時：每次迭代應耗時 500µs (1/2000Hz)
    unsigned long targetTime = startTime + (unsigned long)(i + 1) * 500UL;
    while (micros() < targetTime) {
      // 忙等，確保精確性
    }
  }
  
  unsigned long elapsed = micros() - startTime;
  Serial.printf("[採樣完成] 耗時: %.2f ms (應為 800ms)\n", elapsed / 1000.0);
  
  // 發送數據幀
  Serial.println("[發送] 開始傳輸波形...");
  MySerial.println("START");
  MySerial.println(currentLabel);
  
  for (int i = SKIP_SAMPLES; i < TOTAL_SAMPLES; i++) {
    MySerial.println(fullWave[i]);
  }
  
  MySerial.println("END");
  Serial.printf("[完成] 已發送 %d 筆採樣\n\n", SEND_SAMPLES);
  
  collecting = false;
}
