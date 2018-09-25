import sys
sys.path.insert(0, '../')
from slashcommand.utils import Slashcommand
import dateutil.parser
import time
import datetime
import re
import _thread
import sqlite3
import subprocess
from mattermostdriver import Driver
from config import *

class Reminder(Slashcommand):
	def __init__(self, route, host, port, token, api_key):
		Slashcommand.__init__(self, route, host, port, token, api_key)
		
		self.check_for_user = True # check if recipient exists on system
		
		self.default_json = {'username': 'Reminder', 'icon_url': 'https://vignette.wikia.nocookie.net/harrypotter/images/6/6b/Tumblr_n1wf8hUVYf1qg4gkko4_250.gif/revision/latest?cb=20140502010946'}
		
		# set up database
		self.sql = sqlite3.connect ('reminder.db', check_same_thread=False)
		self.cursor = self.sql.cursor()
		
		self.cursor.execute ('PRAGMA foreign_keys = ON')
		self.sql.commit()
		
		self.cursor.execute ('CREATE TABLE IF NOT EXISTS reminder (id INTEGER PRIMARY KEY, sender TEXT, message TEXT, date TEXT)')
		self.sql.commit()
		# Reminder n : n Recipient -> extra table required
		self.cursor.execute ('CREATE TABLE IF NOT EXISTS reminder_recipient ( name TEXT, reminder_id, PRIMARY KEY (name, reminder_id), FOREIGN KEY(reminder_id) REFERENCES reminder(id) ON DELETE CASCADE )')
		self.sql.commit()
		
		self.driver = None
		self.loggedIn = False
		if self.check_for_user and bot_username != None and bot_password != None:
			try:
				self.driver = Driver ({'url': 'localhost', 'port': mattermost_port, 'login_id': bot_username, 'password': bot_password})
				self.driver.login()
				self.loggedIn = True
			except:
				self.log ('Could not log in into account ' + bot_username + '. Username check will not be available.');
		
		# launch all open reminder events unless they lie in the past
		for row in self.cursor.execute ('SELECT id, sender, message, date FROM reminder'):
			delay = self.time2delay ( dateutil.parser.parse (row[3]) )
			if delay < 0:
				self.log ("The following reminder event lies in the past and will be omitted:")
				self.log (row)
			else:
				recipients = [i[0] for i in self.cursor.execute ('SELECT rr.name FROM reminder_recipient as rr, reminder as r WHERE r.id = (?) AND rr.reminder_id = r.id', [row[0]]).fetchall()]
				self.sendlater ( row[0], delay, recipients, row[1], row[2] )
	
	# process reminder command
	def run(self, param):
		sender = param['user_name']
		
		# show help
		if not 'text' in param:
			self.sendResponse ({'text': '### Reminder Slash command\nThis slash command can be used to send a message to a channel or a member in the future.\n\n## Usage\nEnter ```/remind @who -- when -- what``` in the input text field.  \n- ***@who***: can be a username or @all if you want to remind the whole channel you are currently into. If you want to remind yourself use @me. \n- ***when***: can be a delay in seconds, hours or days if you enter the prefix "in". Otherwise the the command will interprete your input as date.\n- ***what***: What do you want to remind someone. Can be anything.\n\nAfter your reminder was recognized correctly you will receive a confirmation from the reminder bot including a delete button which allow you to remove an unsended reminder.\n\nTo retrieve a list of all your open reminders use ```/remind get``` \n## Examples\n- ```/remind @all -- at 15:50 -- don\'t forget the tea time```\n- ```/remind @peter -- in 2 hours -- please check your emails```\n- ```/remind @me -- at 22 Dec 2018 12:00 -- buy a christmas present for peter```', 'response_type': 'ephemeral'})
			return
		
		if param['text'].strip().lower() == 'get':
			# send all open reminders as pm
			rows = self.cursor.execute ('SELECT id, sender, message, date FROM reminder WHERE sender=?', [sender])
			if self.cursor.rowcount == 0 or self.cursor.rowcount == -1:
				self.sendIntegrationMsg ({'text': 'You have no open reminders', 'channel': '@' + sender})
				
			for row in rows:
				if self.time2delay ( dateutil.parser.parse (row[4]) ) >= 0:
					recipients = self.cursor.execute ('SELECT r.name FROM recipient AS r, reminder_recipient AS rr WHERE r.id = ? AND rr.name = r.id', [self.cursor.lastrowid]) 
					self.sendReminderDetails ('', recipients, row[4], row[3], sender, row[0])
			
			return
		
		message = param['text'] 
		
		split = param['text'].split ('--')
		if len(split) >= 3:
			
			### recognize recipient
			who = split[0].strip().lower()
			recipient = ['@all']
			regex_recipient = r"@*[a-zA-Z0-9]+"
			m = re.findall (regex_recipient, who)
			if len(m) > 0:
				recipients = []
				
				for r in m:
					if r == '@me' or r == 'me':
						recipients.append ('@' + sender)
					elif r == '@all' or r == 'all':
						if self.check_for_user and self.loggedIn:
							try:
								c = self.driver.channels.get_channel (param['channel_id'])
								# direct message or group message?
								if c['type'] == 'G' or c['type'] == 'D':
									t = self.driver.channels.get_channel_members (param['channel_id'])
									recipients = ['@' + self.driver.users.get_user (u['user_id'])['username'] for u in t]
								else:
									recipients.append (param['channel_name'])
							except:
								self.log ('Bot account does not have permissions')
								self.sendResponse ({'text': 'You can not assign @all in direct or group messages. Ask your SysAdmin to give permissions to the bot account to enable this feature.', 'response_type': 'ephemeral'})
								return
						else:
							self.log ('No bot account available, cannot check for channel members')
					else:
						if self.check_for_user:
							if self.loggedIn:
								u = self.driver.users.search_users ({'term': r.replace ('@', '')})
								if len(u) == 0:
									self.sendResponse ({'text': 'user ***' + r + '*** was not found', 'response_type': 'ephemeral'})
									return
								else:
									recipients.append (r)
							else:
								self.log ('No valid credentials for user provided, could not perform check if user exists. Disable user check.')
								self.check_for_user = False
							
			else: # no recipient was specified with @
				self.sendResponse ({'text': 'I did not understand your request. No recipient was specified. Please use the following format: ```/remind <@who> -- <when> -- <what>```', 'response_type': 'ephemeral'})
				return
				
			### regognize delay
			when = split[1].strip()
			regex_when = r"in (\d+) *(\w+)"
			match = re.search (regex_when, when)
			delay = None
			if match:
				n = int(match.group(1)) # number
				u = match.group(2) # unit
				
				if n != None and u != None:
					if u in ['s', 'sec', 'secs', 'second', 'seconds', 'sekunde', 'sekunden']:
						 delay = n
					elif u in ['m', 'min', 'mins', 'minutes', 'minuten']:
						 delay = n * 60
					elif u in ['h', 'hour', 'hours', 'stunden']:
						 delay = n * 3600
					elif u in ['d', 'day', 'days', 'tage', 'tagen']:
						 delay = n * 3600*24
				else:
					self.sendResponse ({'text': 'Sorry, I did not unterstand your request. No delay or date was recognized. Please use the following format: ```/remind <@who> -- <when> -- <what>```', 'response_type': 'ephemeral'})
					return
			### no delay recognized, try to recognize a date
			else:
				try:
					# parsed[0] contain recognized date
					# parsed[1] contains parts of the message which were not used for date recognition
					parsed = dateutil.parser.parse (when, fuzzy_with_tokens=True)
					when = parsed[0]
					delay = self.time2delay (when)
				except ValueError:
					self.sendResponse ({'text': 'Sorry, I did not unterstand your request. No delay or date was recognized. Please use the following format: ```/remind <@who> -- <when> -- <what>```', 'response_type': 'ephemeral'})
					return
			
			if delay == None:
				self.sendResponse ({'text': 'Sorry, I did not unterstand your request. No delay or date was recognized. Please use the following format: ```/remind <@who> -- <when> -- <what>```', 'response_type': 'ephemeral'})
				return
			
			### recognize remind message
			what = split[2].strip()
			
			
			### all parameter recognized, continue processing
			
			if delay >= 0:
				# save reminder in database
				self.cursor.execute ('INSERT INTO reminder (sender, message, date) VALUES (?, ?, ?)', [sender, what, self.delay2time (delay)])
				self.sql.commit()
				reminder_id = self.cursor.lastrowid
				
				for r in recipients:
					self.cursor.execute ('INSERT INTO reminder_recipient (name, reminder_id) VALUES (?, ?)', [r, reminder_id])
					self.sql.commit()
				
				
				# send confirmation as private message including delete button
				self.sendReminderDetails ('New reminder created: ', recipients, self.delay2time (delay), what, sender, self.cursor.lastrowid)
				
				self.sendlater (reminder_id, delay, recipients, sender, what)
			else:
				self.sendResponse ({'text': 'Cannot proceed reminder, your specified date lies in the past.', 'response_type': 'ephemeral'})
			
		# malformed request
		else:
			self.sendResponse ({'text': 'I did not understand your request. Please use the following format: ```/remind <@who> -- <when> -- <what>```', 'response_type': 'ephemeral'})
	
	# delete reminder when delte button was pressed
	def processButton (self, param):
		self.cursor.execute ('DELETE FROM reminder WHERE id=?', [param['reminder_id']])
		self.sql.commit()
		
		if self.cursor.rowcount > 0:
			self.buttonResponse ({
				"update": {
					"message": "Reminder deleted"
				}
			})
		else:
			self.buttonResponse ({
				"update": {
					"message": "Cannot delete, reminder already sended"
				}
			})
	
	# send reminder
	def sendlater (self, remind_id, delay, recipients, sender, message):
		def sub_sendlater (remind_id, delay, recipients, sender, message):
			time.sleep (delay)
			reminder_id = self.cursor.execute ('SELECT id FROM reminder WHERE id=?', [remind_id])
			
			if len ( self.cursor.fetchall() ) == 1: # still there?
				for r in recipients:
					self.sendIntegrationMsg ({'text': sender + ' wants to remind you: ' + message, 'channel': r}, {'text': 'Your reminder could not be sended, maybe you entered a wrong recipient?\n reminder: ' + message + '\n recipient: ' + r, 'channel': '@' + sender})
					#self.sendIntegrationMsg ({'text': 'Hi', 'channel': 'h1akgn7bufbb9mrpt8itkwfk9o__iaj7x5886b8t8ddi1exqinkuur'})
				
				self.cursor.execute ('DELETE FROM reminder WHERE id=?', [remind_id])
				self.sql.commit()
				
		# use thread to not block the server
		try:
			_thread.start_new_thread ( sub_sendlater, (remind_id, delay, recipients, sender, message) )
		except Exception as e:
			self.log (e)
	
	def sendReminderDetails (self, text, recipients, date, what, sender, reminder_id):
		#display_recipient = 'you' if recipient == ('@' + sender) else (recipient if recipient[0] == '@' else '~' + recipient)
		self.sendIntegrationMsg ({
					'text' : text,
					'channel': '@' + sender,
					'attachments': [ {
						'text': '- **recipients**: ' + str(recipients).replace ('[', '').replace (']', '').replace ('\'', '') + '\n- **date**: ' + date + '\n- **message**: ' + what,
						'actions': [ {
							'name': 'Delete',
							'integration': {
								'url': server_url + ':' + str(server_port),
								'context': {
									'command' : self.route,
									'action': 'delete',
									'reminder_id': reminder_id,
									'token': self.tokens[0]
								}
							}
						} ]
					} ]
				})
	
	def time2delay (self, when):
		return time.mktime (when.timetuple() ) - time.time()
		
	def delay2time (self, delay):
		return '{0:%Y-%m-%d %H:%M:%S}'.format ( datetime.datetime.now() + datetime.timedelta (0, delay) )
