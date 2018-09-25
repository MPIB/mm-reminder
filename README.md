# Mattermost integration base template
This python application includes a server which is able to communicate with a mattermost server in order to provide custom slash command and integrations.  
It also include a template for creating custom slash commands on the fly.

## Usage
### Starting the server

Open ```config.py``` and edit the variables acording to your needs
- ```server_port``` is the port this server should listen on
- ```mattermost_port``` is the port the mattermost server listen on
- ```default_integration``` API key which can be used as a generic hook for all type of messages

The simply launch the server

```
python server.py
```

### Adding new commands
Add a new command on the mattermost interface like it is described here https://docs.mattermost.com/developer/slash-commands.html#custom-slash-command  
You will receive a token you will need later.

Optionally you can additionally create an incoming webhook like it is described here: https://docs.mattermost.com/developer/webhooks-incoming.html  
This is needed if you want to post to different channels then the in-channel or sending replies with a delay.
It is a good idea to create a generic incoming webhook which can be used for all type of messages and save the API key in the ```default_integration``` variable in ```config.py```.

Create a new file in commands directory from the following template
```
import sys
sys.path.insert(0, '../')
from slashcommand.utils import Slashcommand

class MyCommand(Slashcommand):
	def __init__(self, route, host, port, token, api_key):
		Slashcommand.__init__(self, route, host, port, token, api_key)
	
	def run(self, param):
		# Do stuff here
```

Override the ```run``` method with your content.

Go to ```server.py``` and import your class

```
from commands import MyCommand.MyCommand
```

and register the command
```
MatterMostRequestHandler.registerCommand ( MyCommand('route configured in mattermost', mattermots_url, mattermost_port, 'token you got from mattermost', default_integration) )
```
You can use the variables of ```config.py``` or use direct values.

After adding a new command you have to restart the server.

### Usage of Slashcommand class
All the processing stuff of your command can be placed in the ```run``` method.

You will receive a dictionary of parameters you can find in ```param``` argument.
The most important are:
- ```text```: The whole message without the command keyword
- ```user_name```: Initiator of the command
- ```channel```: The channel the command came form

For a complete reference see https://developers.mattermost.com/integrate/slash-commands/#basic-usage

#### sending messages
You have two options for sending messages:
- ```self.sendResponse (json)```  
reply to the slash command in the same channel the request came from. You can send up to 5 responses with a maximum delay of 30min.
After this period expired you have to use
- ```self.sendIntegrationMsg (json)```  

The argument ```json``` is a dictionary containing all needed parameters.  
The most important are
- ```text```: The message should be displayed
- ```username``` (needs to be enabled in the config.json): The name which is displayed for the bot
- ```response_type```: Can be ```ephemeral``` for a private response (only initiator of the slash command can see it, this is default) or ```in_channel``` (everyone can see it)
- ```channel```(only usable in IntegrationMsg): The channel the bot post the message in. Use an @ before to channel to adress the message to a single person

For a full reference see https://developers.mattermost.com/integrate/slash-commands/#parameters

You can use the variable ```default_json``` of your slashcommand class to set some default parameters. 

### interactive buttons
An interavtive button can be added to your message by extending your json payload: https://docs.mattermost.com/developer/interactive-message-buttons.html  
You have to add the url and port to the integration part and name as well as the token of your command to the context. Any additional information can be also added to context.

```
self.sendIntegrationMsg ({
	'text': 'Hello World,
	'channel': 'Town-Square',
	'attachments': [ {
		'actions': [ {
			'name': 'my_button',
			'integration': {
				'url': server_url + ':' + str(server_port),
				'context': {
					'command' : self.route,
					'token': self.tokens[0],
					'custom_information': 'very important'
				}
			}
		} ]
	} ]
})
```

To react to a pressed button override ```processButton``` method. The content of the context part will be available as a dictionary via the param attribute.
Use ```buttonResponse``` method to send your reply.

```
def processButton (self, param):
	self.buttonResponse ({
			"update": {
				"message": "You pressed a button. The custom_information was: " + param['custom_information']  
			}
```

Buttons can only be used in non-ephemeral messages.

### logging
Instead of use the print command to write to std out you can use
```
self.log ('hello world')
```
This will print the route of the command in front of the message which helps you to identify the inititor of the output.

### Examples
```
### Send a simple response just visible for the initiator of the command
self.sendResponse ({'text': 'Hello World', 'username': 'Moon'})
```

```
### Send a simple response visible for the whole channel
self.sendResponse ({'text': 'Hello World', 'username': 'Moon', 'response_type': 'in_channel'})
```

```
### Send a private message
self.sendIntegrationMsg ({'text': 'Hi Tim, what's up?', 'channel': '@tim')
```

```
### sending multiple messages with the same parameters
self.default_json = {'username': 'Mr Pepper', 'response_type': 'in_channel'}

self.sendResponse ({'text': 'Knock knock'})
self.sendIntegrationMsg ({'text': 'who\'s there?'})
self.sendIntegrationMsg ({'text': 'it\'s me'})
```

```
### Accessing the parameters
self.sendResponse ({'text': 'Hi ' + param['user_name'] + '! You posted a message from channel ' + param['channel'] + '.'})
```

Take a look in the commands folder for full code examples.
