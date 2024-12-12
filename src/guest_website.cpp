#include "guest_website.hpp"
#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include <SPIFFS.h>
#include <WiFi.h>

void handleRootRequest(AsyncWebServerRequest *request)
{
    Serial.println("Handling root request");
    request->send(SPIFFS, "/index.html", "text/html");
}

void handleFormSubmission(AsyncWebServerRequest *request)
{
    Serial.println("Handling form submission");
    if (request->hasParam("foo", true)) {
        String fooValue = request->getParam("foo", true)->value();
        Serial.println("Value of foo: " + fooValue);
    }
    request->send(200, "text/plain", "Value received");
}

void handleSaveGuestsRequest(AsyncWebServerRequest *request)
{
    // Leave empty; actual handling occurs in the body handler
}

void handleSaveGuestsBody(AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total)
{
    if (index == 0) {
        // First chunk of data
        request->_tempObject = new String();
    }
    String *body = (String *)request->_tempObject;
    body->concat((char *)data, len);

    if ((index + len) == total) {
        // All data received
        Serial.println("Handling save guests request");
        Serial.println("Received body: ");
        Serial.println(*body);

        // Write the body to the file
        File file = SPIFFS.open("/guests.json", FILE_WRITE);
        if (!file) {
            Serial.println("Failed to open file for writing");
            request->send(500, "text/plain", "Failed to open file for writing");
            delete body;
            request->_tempObject = NULL;
            return;
        }

        size_t bytesWritten = file.print(*body);
        file.close();

        Serial.print("Bytes written to file: ");
        Serial.println(bytesWritten);

        if (bytesWritten == 0) {
            Serial.println("Failed to write data to file");
            request->send(500, "text/plain", "Failed to write data to file");
        } else {
            Serial.println("Data written successfully");
            request->send(200, "application/json", "{\"status\":\"success\"}");
        }

        // Clean up
        delete body;
        request->_tempObject = NULL;
    }
}

void setupServer(AsyncWebServer &server)
{
    // Serve the HTML file
    server.on("/", HTTP_GET, handleRootRequest);

    // Handle form submission
    server.on("/submit", HTTP_POST, handleFormSubmission);

    // Serve static files
    server.serveStatic("/", SPIFFS, "/");

    // Handle saving guests
    server.on("/save-guests", HTTP_POST, handleSaveGuestsRequest, NULL, handleSaveGuestsBody);

    server.begin();
    Serial.println("Server started");
}
