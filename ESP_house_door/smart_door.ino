#include "smart_door.hpp"

SmartDoor::SmartDoor(int pin, int time_window)
    : _new_mail_available(false)
    , _rx_time(0)
    , _message("")
    , _closing_date(0)
{
    _pin = pin;
    _time_window = time_window;
    pinMode(_pin, OUTPUT);
}


void SmartDoor::save_to_mailbox(String message, unsigned long rx_time)
{
    _rx_time = rx_time;
    _message = message;
    _new_mail_available = true;
}


void SmartDoor::update(unsigned long now_ms)
{
    _process_new_mail();
    _close_door_if_needed(now_ms);
}


void SmartDoor::_process_new_mail()
{
    if (_new_mail_available == false) {
        return;
    }
    
    if (_message == "open") {
        Serial.println("We received 'open'");
        _open_door_for_n_seconds(_time_window);
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


void SmartDoor::_close_door_if_needed(unsigned long now_ms)
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
