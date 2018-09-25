#!/usr/bin/python3
 
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib
from urllib.parse import urlparse
import re
import requests
import json as json_util


class MatterMostRequestHandler (BaseHTTPRequestHandler):
	
	routeTable = {}
	
	def parsePath (self):
		request = urlparse (self.path)
		path = request.path[1:] # remove /
		query = urllib.parse.parse_qs (request.query)
		return path, query
		
	def do_GET(self):
		pass #self.processRequest()
		
		
	def do_POST(self):
		self.processRequest()
	
	def processRequest(self):
		post_data = {}
		if 'Content-Length' in self.headers: # we got post data
			instr = self.rfile.read ( int(self.headers['Content-Length']) ).decode('utf-8')
			
			if self.headers['Content-Type'] == 'application/json':
				post_data = json_util.loads (instr)
			else:
				post_data = urllib.parse.parse_qs(instr)
		path, get_data = self.parsePath()
		
		# merge post & get data
		data = {**post_data, **get_data}
		for i in data:
			if type(data[i]) is list:
				data[i] = data[i][0]
		
		if path != '':
			if path in MatterMostRequestHandler.routeTable:
				if data['token'] in MatterMostRequestHandler.routeTable[path].tokens:
					self.send_response_only(200)
					self.end_headers()
					
					MatterMostRequestHandler.routeTable[path].responseUrl = data['response_url']
					MatterMostRequestHandler.routeTable[path].run (data)
				else:
					print ('Wrong token')
					self.send_response(500)
			else:
				print (path + " is not registered")
		else: # maybe an interactive button was pressed
			if 'context' in data and 'command' in data['context'] and data['context']['command'] in MatterMostRequestHandler.routeTable:
				if data['context']['token'] in MatterMostRequestHandler.routeTable[data['context']['command']].tokens:
					self.send_response_only(200)
					self.end_headers()
					cmd = MatterMostRequestHandler.routeTable[data['context']['command']]
					cmd.buttonResponseWriter = self.wfile
					cmd.processButton (data['context'])
					cmd.buttonResponseWriter = None
				else:
					print ('request with empty path and no context or command data key, ignoring')
					
			
	
	def registerCommand (cmd):
		MatterMostRequestHandler.routeTable[cmd.route] = cmd

class Slashcommand():
	def __init__(self, route, host, port, tokens, api_key=None, default_json=None):
		self.route = route
		self.tokens = tokens
		self.url = host + ':' + str(port)
		self.responseUrl = None
		self.integrationUrl = None
		self.default_json = default_json
		self.buttonResponseWriter = None
		if api_key != None:
			self.integrationUrl = self.url + '/hooks/' + api_key;
	
	def sendResponse (self, json, alternative_json=None):
		self.sendJSON (self.responseUrl, json, alternative_json)
	
	def sendIntegrationMsg (self, json, alternative_json=None):
		self.sendJSON (self.integrationUrl, json, alternative_json)
	
	def sendJSON (self, url, json, alternative_json=None):
		if url != None:
			payload = json
			if self.default_json != None:
				payload = {**self.default_json, **json} # merge default params with given params
			self.log (payload)
			
			try:
				r = requests.post (url, json=payload)
				if r.status_code != 200:
					self.log ('Error: Got status code ' + str(r.status_code) )
					self.log (r.headers)
					self.log (r.text)
					self.log (r.content)
				
					if alternative_json != None:
						self.sendJSON (url, alternative_json)
			except Exception as e:
				print (e)
				
					  
					 
		else:
			print ("Error, no response hook specified")
			
	def run (self, param):
		pass
	
	def processButton (self, param):
		pass
	
	def buttonResponse (self, json):
		if self.buttonResponseWriter != None:
			self.buttonResponseWriter.write ( json_util.dumps (json).encode ('utf-8') )
		else:
			print ("Error, button was pressed")
	
	def log (self, s):
		print (self.route + ": " + str(s))
