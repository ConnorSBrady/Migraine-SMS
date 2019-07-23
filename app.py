# Migrane and Cluster Headache Text Message Tracker
import praw
import sys
import datetime
from twilio.rest import Client
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from darksky import forecast
from pytz import timezone

app = Flask(__name__)
app.secret_key = "super secret"
# Deployed version
app.config['SQLALCHEMY_DATABASE_URI'] = 'URI_HERE'
# Local testing
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////data.db'
db = SQLAlchemy(app)

class tracking_data(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String())
    startTime = db.Column(db.String())
    endTime = db.Column(db.String())
    duration = db.Column(db.String())
    medication = db.Column(db.String())
    notes = db.Column(db.String())
    pressure = db.Column(db.String())
    temperature = db.Column(db.String())
    ozone = db.Column(db.String())
    windBearing = db.Column(db.String())
    dewPoint = db.Column(db.String())
    cloudCover = db.Column(db.String())
    humidity = db.Column(db.String())

# Python, Flask Web App Deployment
@app.route("/", methods=['GET', 'POST'])
def home():
	return 'hello'

@app.route("/sms", methods=['GET', 'POST'])
def sms_ahoy_reply():
	# More security, confirming that if the program recieves a message that the message is from a specific number.
	if ("+1234567890" not in request.form['From']):
		return ""
	resp = MessagingResponse()
	recievedMessage = request.form['Body'].split(",")
	# During a cluster headache attack, the user wont be able to track time, weather, etc. this is automated here
	# This time is dynamic for each "/sms" route GET request (this code is used for both end and start, most efficient)
	tz = timezone("America/New_York")
	current = datetime.now(tz).strftime('%m-%d-%Y %H:%M:%S')
	temp = current.split(" ")
	date = temp[0]
	time = temp[1]

	# When started, get all weather information at a given location (Lat/Long). Can extract infromation (Pandas Library is great here) from all of this data.
	if (recievedMessage[0] == "Start"):
		newYork = forecast('API_KEY_HERE', 40.705744, -74.008804)
		temperature = newYork['currently']['temperature']
		pressure = newYork['currently']['pressure']
		ozone = newYork['currently']['ozone']
		windBearing = newYork['currently']['windBearing']
		dewPoint = newYork['currently']['dewPoint']
		humidity = newYork['currently']['humidity']
		cloudCover = newYork['currently']['cloudCover']
		# Store all possible automated data in db
		new_cluster = tracking_data(date = date, startTime = time, endTime = "Null", duration = "Null", medication = "Null", notes = "Null", pressure = pressure, temperature = temperature, ozone = ozone, windBearing = windBearing, dewPoint = dewPoint, cloudCover = cloudCover, humidity = humidity)
		print(new_cluster)
		db.session.add(new_cluster)
		db.session.commit()
		# Alert the user that the program has started via sending a message back.
		formattedMessage = "...starting..."
		resp.message(formattedMessage)
		return str(resp)
	# User sends second text when the attack has finished.
	if (recievedMessage[0] == "Finished"):
		# Retrieve previously stored info from this attack, and allow user to add additional notes.
		last_item = tracking_data.query.order_by(tracking_data.id.desc()).first()
		# Commit new endtime to db
		last_item.endTime = time
		db.session.commit()
		# Ask the user for additional notes on this attack
		formattedMessage = ("This cluster started at " + last_item.startTime + " and ended at " + time + "\nPlease enter: +,duration, medication, and additional notes")
		resp.message(formattedMessage)
		return str(resp)
	# "+" is the key word for adding additional information.
	if (recievedMessage[0] == "+"):
		# Retrieve information, update, and commit to db
		last_item = tracking_data.query.order_by(tracking_data.id.desc()).first()
		last_item.duration = recievedMessage[1]
		last_item.medication = recievedMessage[2]
		last_item.notes = recievedMessage[3]
		db.session.commit()
		# Grab the now complete attack information & update to specific google sheet (using gSheet wrapper + JSON credentials)
		last_item = tracking_data.query.order_by(tracking_data.id.desc()).first()
		scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
		credentials = ServiceAccountCredentials.from_json_keyfile_name('clusterTracker-123123123123.json', scope)
		gc = gspread.authorize(credentials)
		wks = gc.open('clusterTracker').sheet1
		# Append
		wks.append_row([last_item.date, last_item.startTime, last_item.endTime, last_item.duration, last_item.medication, last_item.notes, last_item.pressure, last_item.temperature, last_item.ozone, last_item.windBearing, last_item.dewPoint, last_item.cloudCover, last_item.humidity])
		formattedMessage = ("Date: " + last_item.date + "\nStart: " + last_item.startTime + "\nEnd: " + last_item.endTime + "\nDuration:" + last_item.duration + "\nMedication:" + last_item.medication + "\nNotes:" + last_item.notes)
		# Send full notes to user
		resp.message(formattedMessage)
		return str(resp)
	# "Get" allows for the user to inquire about most recent attacks
	if (recievedMessage[0] == "Get"):
		formattedMessage = ""
		last_item = tracking_data.query.order_by(tracking_data.id.desc()).first()
		position = last_item.id
		# Get x number of recent attacks
		numOf = int(recievedMessage[1])
		while (numOf > 0):
			print("hit")
			recent = tracking_data.query.get(position)
			print(recent.id)
			print(position)
			position = position -1
			numOf = numOf -1
			formattedMessage += ("Date: " + last_item.date + "\n Start: " + recent.startTime + "\n End:" + recent.endTime + "\n Duration:" + recent.duration + "\n Medication:" + recent.medication + "\n Notes:" + recent.notes + "\n" + "------" + "\n")
		# Return to user
		resp.message(formattedMessage)
		return str(resp)

if __name__ == "__main__":
	#Change debug to =False for final deployment
	app.run(debug=True)
