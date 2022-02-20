#include "smart_door.hpp"

SmartDoor::SmartDoor(String subscribed_topic) : new_mail_available(false)
{
  _subscribed_topic = subscribed_topic;
}


String SmartDoor::topic()
{
  return _subscribed_topic;
}

void SmartDoor::save_to_mailbox(String message)
{
  
}
