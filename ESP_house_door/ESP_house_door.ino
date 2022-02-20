#include <WiFi.h>
#include <MQTT.h>
#include "smart_door.hpp"

const char ssid[] = "wer_das_liest_ist_doof";
const char pass[] = "asdf";
const char mqtt_broker_ip[] = "192.168.2.3";

SmartDoor smart_house_door("house_door", 7);

WiFiClient wifi_network;
MQTTClient mqtt_client;

void connect() {
    Serial.print("checking wifi...");
    while (WiFi.status() != WL_CONNECTED) {
        Serial.print(".");
        delay(1000);
    }
    
    Serial.print("\nconnecting...");
    while (!mqtt_client.connect("smart_house_door")) {
        Serial.print(".");
        delay(1000);
    }
    
    Serial.println("\nconnected!");
    
    mqtt_client.subscribe("/smart_house_door");
}

void messageReceived(String &topic, String &payload) {
    Serial.println("incoming: " + topic + " - " + payload);
    
    unsigned long t = millis();
    if (topic == smart_house_door.topic()) {
        smart_house_door.save_to_mailbox(payload, t);
    }
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
}
