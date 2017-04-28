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

class MainPage(webapp2.RequestHandler):
	def get(self):
		self.response.write("hello")

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

	def handleClientError(self, code=400, msg="Error"):
		self.response.set_status(code)
		self.response.write(msg)

class BoatHandler(BaseHandler):
	 
	def post(self):
		'''handle POST requests (add new items)'''
		# parent_key = ndb.Key(Fish, "parent_fish")
		boat_data = json.loads(self.request.body)
		new_boat = Boat(name=boat_data['name'], btype=boat_data['btype'], blength=boat_data['blength'], at_sea=False)
		new_boat.put()
		new_boat.bid = str(new_boat.key.id())
		new_boat.put()
		boat_dict = new_boat.to_dict()
		boat_dict['self'] = '/boat/' + new_boat.key.urlsafe()
		self.response.write(json.dumps(boat_dict))

	def get(self, id=None):
		'''handle GET requests (get information about an item)'''
		if id:
			b = ndb.Key(urlsafe=id).get()
			b_d = b.to_dict()
			b_d['self'] = "/boat/" + id
			self.response.write(json.dumps(b_d))
		else:
			self.handleClientError(400, 'Please provide a valid id')

	def get(self):
		'''handle GET requests (get information about ALL items)'''
		boats = []
		boats_qry = Boat.query()
		all_boats = boats_qry.fetch()
		for boat in all_boats:
			b = boat.to_dict()
			b['self'] = '/boat/' + boat.key.urlsafe() # get key for url
			boats.append(b)
			
		self.response.write(json.dumps(boats))
		
	def patch(self, id=None):
		'''handle patch requests (modify info about an item)'''
		if id:
			b = ndb.Key(urlsafe=id).get()
			if(b):
				b_d = b.to_dict()
				patch_data = json.loads(self.request.body)
			else:
				self.handleClientError(204, 'No such boat')
				return

			# succeeded, parse patch_data
			for key in patch_data:
				if(key in b_d):
					if(str(key) == 'at_sea'):
						self.handleClientError(403, 'Please use slip API to manage at_sea')
						return
					if(str(key) == 'bid'):
						self.handleClientError(403, 'Attribute cannot be set')
						return

					setattr(b, str(key), patch_data[key]) #works!
					##! FIXME - don't allow at_sea to be set here
				else:
					self.handleClientError(400, 'Key \''+str(key)+'\' not valid')
					return # we're done here :(
			# success! write to the db
			b.put()
			b_d = b.to_dict()
			b_d['self'] = "/boat/" + id
			self.response.write(json.dumps(b_d))
		else:
			self.handleClientError(400, 'Please provide a valid id')

	def put(self, id=None):
		'''handle put requests (replace an item)'''
		if id:
			b = ndb.Key(urlsafe=id).get()
			if(b):
				b_d = b.to_dict()
				required = [u"name", u"btype", u"blength"]
				put_data = json.loads(self.request.body)
			else:
				self.handleClientError(204, 'No such boat')
				return

			if( set(required) == set(put_data.keys()) ): #all required data is present
				# process the data
				for key in put_data:
					setattr(b, str(key), put_data[key])
			else:
				# sent an error
				self.handleClientError(400, 'Please supply all required keys')
				return
			# success! write to the db
			b.put()
			b_d = b.to_dict()
			b_d['self'] = "/boat/" + id
			self.response.write(json.dumps(b_d))

		else:
			self.handleClientError(400, 'Please provide a valid id')

allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH', ))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods

app = webapp2.WSGIApplication([
	('/', MainPage),
	('/boat', BoatHandler),
	('/boats', BoatHandler),
	('/boat/(.*)', BoatHandler),
	], debug=True)
