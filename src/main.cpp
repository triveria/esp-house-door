#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include <SPIFFS.h>
#include <WiFi.h>

#include "private_wifi_credentials.hpp"

AsyncWebServer server(80);

void handleRootRequest(AsyncWebServerRequest *request)
{
    request->send(SPIFFS, "/index.html", "text/html");
}

void handleFormSubmission(AsyncWebServerRequest *request)
{
    if (request->hasParam("foo", true)) {
        String fooValue = request->getParam("foo", true)->value();
        Serial.println("Value of foo: " + fooValue);
    }
    request->send(200, "text/plain", "Value received");
}

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

    // Connect to WiFi
    Serial.print("Connecting to WiFi...");
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("Connected to WiFi!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    // Serve the HTML file
    server.on("/", HTTP_GET, handleRootRequest);

    // Handle form submission
    server.on("/submit", HTTP_POST, handleFormSubmission);

    server.begin();
}

void loop()
{
    // Nothing to do here
}
