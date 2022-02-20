// This example uses an ESP32 Development Board
// to connect to shiftr.io.
//
// You can check on your device after a successful
// connection here: https://www.shiftr.io/try.
//
// by Joël Gähwiler
// https://github.com/256dpi/arduino-mqtt

#include <WiFi.h>
#include <MQTT.h>
#include "smart_door.hpp"

const char ssid[] = "wer_das_liest_ist_doof";
const char pass[] = "asdf";



SmartDoor smart_house_door("house_door");
SmartDoor smart_appartment_door("appartment_door");

WiFiClient net;
MQTTClient client;

unsigned long lastMillis = 0;

void connect() {
  Serial.print("checking wifi...");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(1000);
  }

  Serial.print("\nconnecting...");
  while (!client.connect("arduino", "public", "public")) {
    Serial.print(".");
    delay(1000);
  }

  Serial.println("\nconnected!");

  client.subscribe("/hello");
  // client.unsubscribe("/hello");
}

void messageReceived(String &topic, String &payload) {
  Serial.println("incoming: " + topic + " - " + payload);

  // Note: Do not use the client in the callback to publish, subscribe or
  // unsubscribe as it may cause deadlocks when other things arrive while
  // sending and receiving acknowledgments. Instead, change a global variable,
  // or push to a queue and handle it in the loop after calling `client.loop()`.

  // add mailbox callback here

  SmartDoor *smart_door;
  
  if (topic == smart_house_door.topic()) {
    smart_door = &smart_house_door;
  } else if (topic == smart_appartment_door.topic()) {
    smart_door = &smart_appartment_door;
  }
  smart_door->save_to_mailbox(payload);
  smart_door->new_mail_available = true;
}


void process_mailbox()
{ 
  /*
  if (door_open_requested) {
    open_house_door_for_3s();
    open_appartment_door_for_10s();
  }
  */
}


void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, pass);

  // Note: Local domain names (e.g. "Computer.local" on OSX) are not supported
  // by Arduino. You need to set the IP address directly.
  client.begin("public.cloud.shiftr.io", net);
  client.onMessage(messageReceived);

  connect();
}

void loop() {
  client.loop();
  delay(10);  // <- fixes some issues with WiFi stability

  if (!client.connected()) {
    connect();
  }
/*
  if (mailbox_new_mail_available) {
    process_mailbox();
  }
*/
}
