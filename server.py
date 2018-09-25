#!/usr/bin/python3
 
from http.server import HTTPServer
from slashcommand.utils import MatterMostRequestHandler, Slashcommand
from config import *

### IMPORT your custom commands
from commands.Reminder import Reminder


### REGISTER your custom commands
MatterMostRequestHandler.registerCommand ( Reminder('remind', mattermost_url, mattermost_port, tokens, default_integration) )

server_address = (server_url, server_port)
httpd = HTTPServer(server_address, MatterMostRequestHandler)
httpd.serve_forever()
