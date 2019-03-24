#*********************************************************************
#** Author: Collin James
#** Date: 04/30/2017
#** Description: An api for managing boats and slips
#*********************************************************************/

from google.appengine.ext import ndb
import webapp2
import json
import logging

class Boat(ndb.Model):
	bid = ndb.StringProperty() #use a key?
	name = ndb.StringProperty(required=True)
	btype = ndb.StringProperty(required=True)
	blength = ndb.IntegerProperty(required=True)
	at_sea = ndb.BooleanProperty()

class Slip(ndb.Model):
	sid = ndb.StringProperty() #use a key?
	number = ndb.IntegerProperty(required=True)
	current_boat = ndb.StringProperty()
	arrival_date = ndb.StringProperty()
	# departure_history = ndb.IntegerProperty() # extra credit

class MainPage(webapp2.RequestHandler):
	def get(self):
		self.response.write("Welcome to the assignment 3 boat and slip API. Visit /boats to get started.")

class BaseHandler(webapp2.RequestHandler):
	'''from http://webapp2.readthedocs.io/en/latest/guide/exceptions.html'''
	def handle_exception(self, exception, debug):
		# Log the error.
		logging.exception(exception)

		# Set a custom message.
		self.response.write('An error occurred.'+str(vars(exception)))

		# If the exception is an HTTPException, use its error code.
		# Otherwise use a generic 500 error code.
		if isinstance(exception, webapp2.HTTPException):
		    self.response.set_status(exception.code)
		else:
		    self.response.set_status(500)

	def setStatusCode(self, code=400, msg="Error"):
		self.response.set_status(code)
		self.response.write(msg)

class BoatHandler(BaseHandler):
	 
	def post(self):
		'''handle POST requests (add new items)'''
		boat_data = json.loads(self.request.body)
		if not "name" in boat_data:
			# error
			self.setStatusCode(400, 'Please provide a name')
			return
		if not "btype" in boat_data:
			# error
			self.setStatusCode(400, 'Please provide a boat type')
			return
		if not "blength" in boat_data:
			# error
			self.setStatusCode(400, 'Please provide a boat length')
			return

		new_boat = Boat(name=boat_data['name'], btype=boat_data['btype'], blength=boat_data['blength'], at_sea=True)
		new_boat.put()
		# new_boat.bid = str(new_boat.key.id())
		new_boat.bid = str(new_boat.key.urlsafe())
		new_boat.put()
		boat_dict = new_boat.to_dict()
		boat_dict['self'] = '/boat/' + new_boat.key.urlsafe()
		self.setStatusCode(201, '')
		self.response.write(json.dumps(boat_dict))

	def returnAllBoats(self, response):
		boats = []
		boats_qry = Boat.query()
		all_boats = boats_qry.fetch()
		for boat in all_boats:
			b = boat.to_dict()
			b['self'] = '/boat/' + boat.key.urlsafe() # get key for url
			boats.append(b)
		if len(boats) == 0:
			self.setStatusCode(204, '')
		response.write(json.dumps(boats))

	def get(self, id=None):
		'''handle GET requests (get information about an item or all items)'''
		# handle all items
		path = self.request.path
		if "/boats" in path:
			self.returnAllBoats(self.response)

		# handle one item
		else:
			if id:
				b = ndb.Key(urlsafe=id).get()
				b_d = b.to_dict()
				b_d['self'] = "/boat/" + id
				self.response.write(json.dumps(b_d))
			else:
				self.setStatusCode(400, 'Please provide an id')
		
	def patch(self, id=None):
		'''handle patch requests (modify info about an item)'''
		if id:
			b = ndb.Key(urlsafe=id).get()
			if(b):
				b_d = b.to_dict()
				patch_data = json.loads(self.request.body)
			else:
				self.setStatusCode(204, 'No such boat')
				return

			# succeeded, parse patch_data
			for key in patch_data:
				if(key in b_d):
					if(str(key) == 'at_sea'):
						self.setStatusCode(403, 'Please use slip API to manage at_sea')
						return
					if(str(key) == 'bid'):
						self.setStatusCode(403, 'Attribute cannot be set')
						return

					setattr(b, str(key), patch_data[key]) #works!
					##! FIXME - don't allow at_sea to be set here
				else:
					self.setStatusCode(400, 'Key \''+str(key)+'\' not valid')
					return # we're done here :(
			# success! write to the db
			b.put()
			b_d = b.to_dict()
			b_d['self'] = "/boat/" + id
			self.response.write(json.dumps(b_d))
		else:
			self.setStatusCode(400, 'Please provide a valid id')

	def put(self, id=None):
		'''handle put requests (replace an item)'''
		if id:
			b = ndb.Key(urlsafe=id).get()
			if(b):
				b_d = b.to_dict()
				required = [u"name", u"btype", u"blength"]
				put_data = json.loads(self.request.body)
			else:
				self.setStatusCode(204, 'No such boat')
				return

			if( set(required) == set(put_data.keys()) ): #all required data is present
				# process the data
				for key in put_data:
					setattr(b, str(key), put_data[key])
			else:
				# sent an error
				self.setStatusCode(400, 'Please supply all required keys')
				return
			# success! write to the db
			b.put()
			b_d = b.to_dict()
			b_d['self'] = "/boat/" + id
			self.response.write(json.dumps(b_d))

		else:
			self.setStatusCode(400, 'Please provide a valid id')

	def delete(self, id=None):
		'''hand delete requests (delete a boat)'''
		if id:
			b = ndb.Key(urlsafe=id).get()
			if(b != None):
				# remove the boat from the slip
				if b.at_sea == False:
					# search for the slip
					# slip_qry = ndb.gql(("SELECT * from Slip WHERE current_boat = \' "+"/boat/"+id+"\'"))
					slip_qry = ndb.gql("SELECT * from Slip WHERE current_boat = :1", str("/boat/"+id))
					slip = slip_qry.fetch()[0]
					print slip
					slip.current_boat = None
					slip.put()
				# delete the entity
				k = b.key
				k.delete() # delete is called on a key
				self.setStatusCode(204, '') # not actually an error, but we have this nice function :)
			else:
				self.setStatusCode(404, 'No such boat')
				return
		else:
			self.setStatusCode(400, 'Please provide a valid id')

class SlipHandler(BaseHandler):

	def findNumber(self, number):
		# # look for slips with the supplied number and ask for a different one
		slips_qry = Slip.query(Slip.number == number)
		all_slips = slips_qry.fetch()
		if len(all_slips):
			slips = []
			slips_qry = ndb.gql("SELECT number FROM Slip")
			all_slips = slips_qry.fetch()
		
			for slip in all_slips:
				s = slip.to_dict()
				slips.append(s)
			self.setStatusCode(403, '')
			self.response.write(json.dumps(slips))
			return 1

		return 0

	def post(self, id=None):
		'''handle POST requests (add new item)'''
		# parent_key = ndb.Key(Fish, "parent_fish")
		slip_data = json.loads(self.request.body)
		if not "number" in slip_data:
			# error
			self.setStatusCode(400, 'Please provide a slip number')
			return

		# # look for slips with the supplied number and ask for a different one
		end = self.findNumber(slip_data["number"])
		if end:
			return

		# valid request
		new_slip = Slip(number=slip_data["number"])
		new_slip.put()
		# new_slip.sid = str(new_slip.key.id())
		new_slip.sid = str(new_slip.key.urlsafe())
		new_slip.put()
		slip_dict = new_slip.to_dict()
		slip_dict['self'] = '/slip/' + new_slip.key.urlsafe()
		self.setStatusCode(201, '')
		self.response.write(json.dumps(slip_dict))

	def get(self, id=None): #[DONE]
		'''handle GET requests (get information about an item or all items)'''
		path = self.request.path
		# handle boat docking [DONE]
		if "/boat" in path:
			parts = id.split('/boat/')
			id = parts[0]
			if id:
				s = ndb.Key(urlsafe=id).get()
				if s != None:
					s_d = s.to_dict()
					print s_d
					if testNotNull(s_d["current_boat"]):
						# return boat information
						BoatHandler(response=self.response, request=self.request).get(s_d["current_boat"].split('/boat/')[1])
						return
					else:
						self.setStatusCode(204, 'No boat')
						return
				else:
					self.setStatusCode(403, 'No such slip')
					return

		# handle all items [DONE]
		elif "/slips" in path:
			slips = []
			slips_qry = Slip.query()
			all_slips = slips_qry.fetch()
			for slip in all_slips:
				s = slip.to_dict()
				s['self'] = '/slip/' + slip.key.urlsafe() # get key for url
				slips.append(s)
			if len(slips) == 0:
				self.setStatusCode(204, '')
			self.response.write(json.dumps(slips))
		# handle one item [DONE]
		else:
			if id:
				s = ndb.Key(urlsafe=id).get()
				if s != None:
					s_d = s.to_dict()
					s_d['self'] = "/slip/" + id
					self.response.write(json.dumps(s_d))
				else:
					self.setStatusCode(204, 'No such slip')
					return
			else:
				self.setStatusCode(400, 'Please provide a valid id')

	def patch(self, id=None): #[FINISH ME]
		'''handle patch requests (modify info about an item)'''
		if id:
			s = ndb.Key(urlsafe=id).get()
			if(s != None):
				s_d = s.to_dict()
				patch_data = json.loads(self.request.body)
			else:
				self.setStatusCode(204, 'No such slip')
				return

			# succeeded, parse patch_data
			for key in patch_data:
				if(key in s_d):
					if(str(key) == 'current_boat'):
						self.setStatusCode(403, 'Please use PUT /slip/id/boat')
						return
					if(str(key) == 'sid'):
						self.setStatusCode(403, 'Attribute cannot be set')
						return
					if(str(key) == 'number'):
						if str(key) != s_d["number"]:
							end = self.findNumber(patch_data[key])
							if end:
								return
					if(str(key) == 'arrival_date' and not testNotNull(s_d["current_boat"])):
						self.setStatusCode(403, 'No boat set')
						return

					setattr(s, str(key), patch_data[key]) #works!
				else:
					self.setStatusCode(400, 'Key \''+str(key)+'\' not valid')
					return # we're done here :(
			# success! write to the db
			s.put()
			s_d = s.to_dict()
			s_d['self'] = "/slip/" + id
			self.response.write(json.dumps(s_d))
		else:
			self.setStatusCode(400, 'Please provide a valid id')

	def put(self, url=None):
		'''handle put requests (replace an item, add a boat)'''
		# handle boat docking [DONE]
		if "/boat/" in url:
			# split up path to bet bid
			parts = url.split('/boat/')
			id = parts[0]
			put_data = json.loads(self.request.body)
			if not "arrival_date" in put_data:
				self.setStatusCode(400, 'Please provide an arrival date')
				return
			if "bid" in put_data: # got a boat id
				bid = put_data["bid"]
				b = ndb.Key(urlsafe=bid).get()
				if id:
					s = ndb.Key(urlsafe=id).get()
					s_d = s.to_dict()
					if testNotNull(s_d["current_boat"]):
						self.setStatusCode(403, 'A boat already exists')
						# self.response.write(json.dumps(s_d["current_boat"]))
						return
					else:
						# add boat to slip
						s.current_boat = "/boat/" + bid
						s.arrival_date = put_data["arrival_date"]
						s.put()
						# update boat to be not at sea
						b.at_sea = False
						b.put()
					s_d = s.to_dict()
					s_d['self'] = "/slip/" + id
					self.response.write(json.dumps(s_d))
				else:
					self.setStatusCode(400, 'Please provide a slip id')
					return
			else:
				self.setStatusCode(400, 'Please provide a boat id')
				return
		# handle replace data (don't allow setting a boat) [FINISH ME]
		else:
			id = url
			if id:
				s = ndb.Key(urlsafe=id).get()
				if(s):
					s_d = s.to_dict()
					required = [u"number"]
					put_data = json.loads(self.request.body)
				else:
					self.setStatusCode(204, 'No such slip')
					return

				# if( set(required) & set(put_data.keys()) ): #all required data is present
				if "number" in put_data: #all required data is present
					if put_data["number"] != s.number:
						# look for slips with the supplied number and ask for a different one
						end = self.findNumber(put_data["number"])
						if end:
							return
					# process the data
					if "bid" in put_data:
						b = None
						# check for boat in current slip and set it to at sea
						if not "arrival_date" in put_data:
							self.setStatusCode(400, 'Currently need arrival date for replace')
							return

						if testNotNull(s.current_boat):
							# update boat to be at sea
							b = ndb.Key(urlsafe=s_d["current_boat"].split('/boat/')[1]).get()
							if b:
								b.at_sea = True
							else:
								self.setStatusCode(204, 'No such boat')
								return
							# b.put()
						else:
							self.setStatusCode(400, 'Dock a boat first')
							return
						# add boat
						s.current_boat = "/boat/" + put_data["bid"]
						s.arrival_date = put_data["arrival_date"]
						b2 = ndb.Key(urlsafe=put_data["bid"]).get()
						b2.at_sea = False
						b.put()
						b2.put()

					elif "arrival_date" in put_data:
						s.arrival_date = put_data["arrival_date"]

					# set new number
					s.number = put_data["number"]
					# write all data
					s.put()
					s_d = s.to_dict()
					s_d['self'] = "/slip/" + id
					self.response.write(json.dumps(s_d))
				else:
					# send an error
					self.setStatusCode(400, 'Please supply only required keys')
					return
			else:
				self.setStatusCode(400, 'Please provide a valid id')

	def delete(self, id=None):
		'''hand delete requests (delete a slip, delete a boat from a slip)'''
		# handle boat deletion
		if "/boat" in id:
			# print "HEEEYYYYY"
			s = ndb.Key(urlsafe=(id.split('/boat')[0])).get()
			s_d = s.to_dict()

			if testNotNull(s_d["current_boat"]):
				b = ndb.Key(urlsafe=s_d["current_boat"].split('/boat/')[1]).get()
				b.at_sea = True
				b.put()
			else:
				self.setStatusCode(404, 'No boat docked')
				return
			s.current_boat = None
			s.arrival_date = None
			s.put()
			s_d = s.to_dict()
			s_d['self'] = "/slip/" + id
			self.response.write(json.dumps(s_d))
			return	
		# handle slip deletion
		else:
			if id:
				s = ndb.Key(urlsafe=id).get()
				s_d = s.to_dict()
				if(s):
					# remove the boat from the slip
					print "HEYYYYYYYY"
					print  s_d["current_boat"]
					if testNotNull(s_d["current_boat"]):
						b = ndb.Key(urlsafe=s_d["current_boat"].split('/boat/')[1]).get()
						b.at_sea = True
						b.put()
					# delete the entity
					k = s.key
					k.delete() # delete is called on a key
					
					self.setStatusCode(204, '') # not actually an error, but we have this nice function :)
					return				
				else:
					self.setStatusCode(404, 'No such slip')
					return
			else:
				self.setStatusCode(400, 'Please provide a valid id')

def testNotNull(term):
	return (term != "null" and term != None)

allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH', ))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods

app = webapp2.WSGIApplication([
	('/', MainPage),
	('/boat', BoatHandler), # "post" (create) a new boat
	('/boats', BoatHandler), # return all boats
	('/boat/(.*)', BoatHandler), # get, put, patch, or delete a specific boat (/boat/id) 
	('/slip', SlipHandler), # "post" (create) a new slip
	('/slips', SlipHandler), # return all slips
	('/slip/(.*)', SlipHandler), # get, put, patch, or delete a specific slip (/slip/id)
	('/slip/(.*)/boat', SlipHandler), # "get", "delete" or "put" a boat at slip (/slip/id/boat)
	], debug=True)
