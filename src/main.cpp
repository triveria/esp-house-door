#include <Arduino.h>

#include "private_wifi_credentials.hpp"

void setup()
{
    Serial.begin(115200);
    delay(10);
    Serial.println();
}

void loop()
{

    Serial.println("Hello World!");
    delay(10);
}
