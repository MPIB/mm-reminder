import sys
sys.path.insert(0, '../')
from slashcommand.utils import Slashcommand

class EchoBot(Slashcommand):
	def __init__(self, route, host, port, token, api_key):
		Slashcommand.__init__(self, route, host, port, token, api_key)
		self.default_json = {'username': 'harry potter'}
	
	def run(self, param):
		self.sendResponse ({'text': param['text'], 'username' : 'peter', 'response_type': 'ephemeral'})
