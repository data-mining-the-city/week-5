from flask import Flask
from flask import render_template
from flask import request
from flask import Response

import json
import time
import sys
import random
import math

import pyorient

from Queue import Queue

app = Flask(__name__)

q = Queue()

def event_stream():
    while True:
        result = q.get()
        yield 'data: %s\n\n' % str(result)

@app.route('/eventSource/')
def sse_source():
    return Response(
            event_stream(),
            mimetype='text/event-stream')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/getData/")
def getData():

	q.put("starting data query...")

	lat1 = str(request.args.get('lat1'))
	lng1 = str(request.args.get('lng1'))
	lat2 = str(request.args.get('lat2'))
	lng2 = str(request.args.get('lng2'))

	w = float(request.args.get('w'))
	h = float(request.args.get('h'))
	cell_size = float(request.args.get('cell_size'))

	print "received coordinates: [" + lat1 + ", " + lat2 + "], [" + lng1 + ", " + lng2 + "]"
	
	client = pyorient.OrientDB("localhost", 2424)
	session_id = client.connect("root", "password")
	db_name = "soufun"
	db_username = "admin"
	db_password = "admin"

	if client.db_exists( db_name, pyorient.STORAGE_TYPE_MEMORY ):
		client.db_open( db_name, db_username, db_password )
		print db_name + " opened successfully"
	else:
		print "database [" + db_name + "] does not exist! session ending..."
		sys.exit()

	query = 'SELECT FROM Listing WHERE latitude BETWEEN {} AND {} AND longitude BETWEEN {} AND {}'

	records = client.command(query.format(lat1, lat2, lng1, lng2))

	random.shuffle(records)
	records = records[:100]

	numListings = len(records)
	print 'received ' + str(numListings) + ' records'

	client.db_close()

	output = {"type":"FeatureCollection","features":[]}

	for record in records:
		feature = {"type":"Feature","properties":{},"geometry":{"type":"Point"}}
		feature["id"] = record._rid
		feature["properties"]["name"] = record.title
		feature["properties"]["price"] = record.price
		feature["geometry"]["coordinates"] = [record.latitude, record.longitude]

		output["features"].append(feature)

	q.put('idle')

	output["analysis"] = []

	numW = int(math.floor(w/cell_size))
	numH = int(math.floor(h/cell_size))

	offsetLeft = (w - numW * cell_size) / 2.0 ;
	offsetTop = (h - numH * cell_size) / 2.0 ;

	for j in range(numH):
		for i in range(numW):
			newItem = {}

			newItem['x'] = offsetLeft + i*cell_size
			newItem['y'] = offsetTop + j*cell_size
			newItem['width'] = cell_size-1
			newItem['height'] = cell_size-1
			newItem['value'] = .5

			output["analysis"].append(newItem)

	return json.dumps(output)

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000,debug=True,threaded=True)