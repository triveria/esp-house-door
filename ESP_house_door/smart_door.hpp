#pragma once


class SmartDoor {
public:
    SmartDoor(int pin, int time_window);
    void save_to_mailbox(String message, unsigned long rx_time);
    void update(unsigned long now_ms);
  
private:
    int _pin;
    int _time_window;
    bool _new_mail_available;
    unsigned long _rx_time;
    String _message;
    unsigned long _closing_date;
    
    void _process_new_mail();
    void _open_door_for_n_seconds(int seconds);
    void _open_door();
    void _set_closing_date(unsigned long closing_date);
    void _close_door_if_needed(unsigned long now_ms);
    void _close_door();
};
