#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include <SPIFFS.h>
#include <WiFi.h>

#include "guest_website.hpp"
#include "private_wifi_credentials.hpp"

AsyncWebServer server(80);

void setup()
{
    Serial.begin(115200);
    delay(10);
    Serial.println();

    // Initialize SPIFFS
    if (!SPIFFS.begin(true)) {
        Serial.println("An error has occurred while mounting SPIFFS");
        return;
    }
    Serial.println("SPIFFS mounted successfully");

    // Connect to WiFi
    Serial.print("Connecting to WiFi...");
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("Connected to WiFi!");
    Serial.print("IP Address: http://");
    Serial.println(WiFi.localIP());

    // Setup the server
    setupServer(server);
}

void loop()
{
    // Nothing to do here
}
