# Mattermost slashcommand for sending reminders

## Requirements

- python3
- python-sqlite
- python-mattermostdriver

## Configuration

- Add a slashcommand in Mattermost and note down the token you get. Use ```remind``` as command.
-- https://docs.mattermost.com/developer/slash-commands.html#custom-slash-command
- Create an incoming webhook
-- https://docs.mattermost.com/developer/webhooks-incoming.html

Open ```config.py``` and adjust the variables
- server_port: The port the integration should listen on
- server_url: The host name of the machine which runs the slash command. Most probably that is ```localhost```
- mattermost_url: The URL of your Mattermost server
- mattermost_port: The port the mattermost server is listing on
- tokens: Tokens for your slashcommand, multiple tokens are possible
- default_integration: An incoming webhook used for message posting. Use only the keypart, not the whole URL
- bot_username: The username for a Mattermost account. This is needed for username check
- bot_password: The password of the Mattermost account
 
## Getting started

Start the server

    python server.py

Login into your Mattermost account and type

    /remind

Somewhere to get a help for the slash command

## Usage
### Reminder Slash command
This slash command can be used to send a message to a channel or a member in the future.

## Usage
Enter ```/remind @who -- when -- what``` in the input text field.  
- ***@who***: can be a username or @all if you want to remind the whole channel you are currently into. If you want to remind yourself use @me. 
- ***when***: can be a delay in seconds, hours or days if you enter the prefix "in". Otherwise the the command will interprete your input as date.
- ***what***: What do you want to remind someone. Can be anything.

After your reminder was recognized correctly you will receive a confirmation from the reminder bot including a delete button which allow you to remove an unsended reminder.

To retrieve a list of all your open reminders use ```/remind get``` 
## Examples
- ```/remind @all -- at 15:50 -- don\'t forget the tea time```
- ```/remind @peter -- in 2 hours -- please check your emails```
- ```/remind @me -- at 22 Dec 2018 12:00 -- buy a christmas present for peter```
