#pragma once


class SmartDoor {
public:
  SmartDoor(String subscribed_topic);
  String topic();
  void save_to_mailbox(String message);
  bool new_mail_available;
  
private:
  String _subscribed_topic;
  bool new_msg_available;
};
