#include <WiFi.h>
#include <MQTT.h>
#include "smart_door.hpp"
#include "private_settings.hpp"


SmartDoor smart_house_door(32);

WiFiClient wifi_network;
MQTTClient mqtt_client;

void connect() {
    Serial.print("checking wifi...");
    while (WiFi.status() != WL_CONNECTED) {
        Serial.print(".");
        delay(1000);
    }
    
    Serial.print("\nconnecting...");
    while (!mqtt_client.connect("house_door_ESP")) {
        Serial.print(".");
        delay(1000);
    }
    
    Serial.println("\nconnected!");
    
    mqtt_client.subscribe("smart_house_door"); // test on server: $ mosquitto_pub -t smart_house_door -m 'open'
}

void messageReceived(String &topic, String &payload) {
    Serial.println("incoming: " + topic + " - " + payload);
    
    unsigned long t = millis();
    smart_house_door.save_to_mailbox(payload, t);
}


void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, pass);

    mqtt_client.begin(mqtt_broker_ip, wifi_network);
    mqtt_client.onMessage(messageReceived);

    connect();
}

void loop() {
    mqtt_client.loop();
    delay(10);  // <- fixes some issues with WiFi stability
    
    if (!mqtt_client.connected()) {
        connect();
    }
    
    unsigned long now_ms = millis();
    smart_house_door.process_new_mail();
    smart_house_door.close_door_if_needed(now_ms);
    delay(1000);
}
