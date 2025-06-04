#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
// const char* ssid = "your_ssid";
// const char* password = "your_password";
const char* backend_url = "https://api.xiwuzc.tech/iot/iot/sensing/sensor/data";
WiFiClient client;
HTTPClient http;
String buffer = "";
int last_send_time = 0;
void setup() {
 Serial.begin(115200);
//  WiFi.begin(ssid, password);
//  while (WiFi.status() != WL_CONNECTED) {
//   delay(1000);
//   Serial.println("Connecting to WiFi...");
//  }
 Serial.println("Connected to WiFi");
 Serial2.begin(9600);
}
void loop() {
 if (Serial2.available() >0) {
 char data = Serial2.read();
 buffer += data;
 if (data == '\n') {
 process_data(buffer);
 buffer = "";
 }
 }
 delay(10);
}
void process_data(String buffer) {
 if (buffer.length() >=32 && buffer.startsWith("3c02")) {
 String pairs[16];
 for (int i =0; i<16; i++) {
 pairs[i] = buffer.substring(i*2, (i*2)+2);
 }
 try {
 int co2 = strtol(pairs[2].c_str(), NULL,16);
 int ch2o = strtol(pairs[4].c_str(), NULL,16);
 int tvoc = strtol(pairs[6].c_str(), NULL,16);
 int pm25 = strtol(pairs[8].c_str(), NULL,16);
 int pm10 = strtol(pairs[10].c_str(), NULL,16);
 int temp_high = strtol(pairs[12].c_str(), NULL,16);
 int temp_low = strtol(pairs[13].c_str(), NULL,16);
 int humidity_high = strtol(pairs[14].c_str(), NULL,16);
 int humidity_low = strtol(pairs[15].c_str(), NULL,16);
 float double_humid = (float)humidity_high + (float)humidity_low/100;
 send_data_to_backend(co2, ch2o, tvoc, pm25, pm10, temp_high, temp_low, humidity_high, humidity_low);
 } catch (...) {
 Serial.println("Error processing data");
 }
 }
}
void send_data_to_backend(int co2, int ch2o, int tvoc, int pm25, int pm10, int temp_high, int temp_low, int humidity_high, int humidity_low) {
 if (WiFi.status() == WL_CONNECTED) {
 http.begin(client, backend_url);
 http.addHeader("Content-Type", "application/json");
 String payload = "{\"CO2\": \"" + String(co2) + "\", \"Ch2O\": \"" + String(ch2o) + "\", \"TVOC\": \"" + String(tvoc) + "\", \"PM25\": \"" + String(pm25) + "\", \"PM10\": \"" + String(pm10) + "\", \"Temperature\": \"" + String(temp_high) + "." + String(temp_low) + "\", \"Humidity\": \"" + String(humidity_high) + "." + String(humidity_low) + "\"}";
 int httpResponseCode = http.POST(payload);
 if (httpResponseCode >0) {
 Serial.print("HTTP Response Code: ");
 Serial.println(httpResponseCode);
 } else {
 Serial.print("Error on HTTP request: ");
 Serial.println(httpResponseCode);
 }
 http.end();
 }
 else {
 Serial.println("Disconnected from WiFi");
 }
}
