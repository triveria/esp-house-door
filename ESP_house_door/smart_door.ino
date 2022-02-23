#include "smart_door.hpp"

SmartDoor::SmartDoor(int pin)
    : _new_mail_available(false)
    , _rx_time(0)
    , _message("")
    , _closing_date(0)
{
    _pin = pin;
    pinMode(_pin, OUTPUT);
}


void SmartDoor::save_to_mailbox(String message, unsigned long rx_time)
{
    _rx_time = rx_time;
    _message = message;
    _new_mail_available = true;
}


void SmartDoor::process_new_mail()
{
    if (_new_mail_available == false) {
        return;
    }
    
    if (_message == "open") {
        Serial.println("We received 'open'");
        int n = 3; // get from message
        _open_door_for_n_seconds(n);
    } else {
        Serial.println("We did not receive 'open'");
    }
    
    _new_mail_available = false;
}


void SmartDoor::_open_door_for_n_seconds(int seconds)
{
    unsigned long open_duration_ms = seconds * 1000;
    unsigned long now_ms = millis();
    _set_closing_date(now_ms + open_duration_ms);
    _open_door();
}


void SmartDoor::_open_door()
{
    Serial.println("Open door");
    digitalWrite(_pin, HIGH);
}


void SmartDoor::_set_closing_date(unsigned long closing_date)
{
    _closing_date = closing_date;
}


void SmartDoor::close_door_if_needed(unsigned long now_ms)
{
    if (now_ms >= _closing_date) {
        _close_door();
    }
}


void SmartDoor::_close_door()
{
    Serial.println("Close door");
    digitalWrite(_pin, LOW);
}
