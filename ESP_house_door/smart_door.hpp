#pragma once


class SmartDoor {
public:
  SmartDoor(String subscribed_topic, int pin);
  String topic();
  void save_to_mailbox(String message, unsigned long rx_time);
  void process_new_mail();
  void close_door_if_needed(unsigned long now_ms);
  
private:
  int _pin; // @TODO: what type is a pin?
  bool _new_mail_available;
  String _subscribed_topic;
  unsigned long _rx_time;
  String _message;
  unsigned long _closing_date;

  void _open_door_for_n_seconds(int seconds);
  void _open_door();
  void _set_closing_date(unsigned long closing_date);
  void _close_door();
};
