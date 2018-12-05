
=============================================
Configuring PyAlarm to send Telegram messages
=============================================

First of all, you'll need a telegram account and sign-in to https://web.telegram.org

To send messages to Telegram users we will need a Bot (https://core.telegram.org/bots/api). 

To create a new Bot (see https://www.sohamkamani.com/blog/2016/09/21/making-a-telegram-bot/):

 - Open a chat with @BotFather bot
 - Type /newbot
 - Enter your bot name and bot_address
 - Take note of your bot token (a long number like NNNN:ASDFASDFASDFAASDF )
 
Once you have it, you can test your bot::
 
  https://web.telegram.org/#/im?p=@<bot_address>
  https://api.telegram.org/bot<token>/getMe
   
Then, add a new property TGConfig to PyAlarm with your token::
 
  fandango.tango.put_device_property('your/device/name','TGConfig','NNNNN:YOURBOTTOKEN')
   
To start sending messages you will need now your user_id or chat_id (not your username, but a numeric identifier).
 
To obtain it:
 
 - Open a chat with @userinfobot to get your numeric user_id.
 - Add your previously created Bot to a group and call https://api.telegram.org/bot<token>/getUpdates to see the group chat_id.
  
Once you have the ID, just add a new receiver::
  
  TG:654654654
   
