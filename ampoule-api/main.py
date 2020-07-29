"""Ampoule drug data API: Get DM+D drug data for a Global Trade Identification Number (GTIN).

Submit a GET request to '/gtin/<GTIN>', where <GTIN> is a EAN13 or EAN14 digit GTIN.

This API queries a MongoDB database populated with modified Actual Medicinal Product Pack (AMPP)
and Global Trade Identification Number (GTIN) data from the Dictionary of Medicines and Devices
(DM+D), which is published by NHS Digital and available under an Open Government licence.

The API returns a JSON object including the name, strength, units, type and quanity of the product.

"""

import os
import pymongo
from bottle import install, route, get, template, redirect, static_file, error, run
from bson.json_util import dumps
import json
import dns

MONGODB_URI = "<Enter MongoDB URI>"

# MongoDB connection
mongo = pymongo.MongoClient(MONGODB_URI, maxPoolSize=50, connect=False)
db = pymongo.database.Database(mongo, 'ampoule')
col = pymongo.collection.Collection(db, 'dmd')


# Function to make standard response
def make_response(data, message, status="success", error=False):
    return {
        "data": data,
        "message": message,
        "status": status,
        "error": error
    }


# Convenience function for error response
def make_error(message):
    return make_response(None, message, status="fail", error=True)


# Main route for query
@get('/gtin/<gtin>')
def get_drug_data(gtin):
    # Check valid input
    if not gtin.isnumeric():
        return make_error("Error: Submit a 13 or 14 digit numeric GTIN")
    elif len(gtin) != 13 and len(gtin) != 14:
        return make_error("Error: Submit a 13 or 14 digit numeric GTIN")
    # Make database request
    try:
        query = col.find_one({"gtin": gtin}, {"gtin": 0, "_id": 0})
        result = json.loads(dumps(query))
    except Exception as error:
        return make_error(f"Error: {str(error)}")
    
    # If no result, check equivalant GTIN
    if not result:
        # If 13-digit GTIN, try prefixing "0"
        if len(gtin) == 13:
            new_gtin = "0" + gtin
            try:
                query = col.find_one({"gtin": new_gtin}, {"gtin": 0, "_id": 0})
                result = json.loads(dumps(query))
            except Exception as error:
                return make_error(f"Error: {str(error)}")
        # If 14-digit GTIN, try without first digit
        elif len(gtin) == 14:
            new_gtin = gtin[1:]
            try:
                query = col.find_one({"gtin": new_gtin}, {"gtin": 0, "_id": 0})
                result = json.loads(dumps(query))
            except Exception as error:
                return make_error(f"Error: {str(error)}")
    # Return data
    if result:
        # Get AMPP object
        ampp = result["ampp"]
        return make_response(ampp, "Success")
    else:
        return make_error("Error: No drug data found for that GTIN")


# Handle root url
@route('/')
@route('/gtin')
@route('/gtin/')
def handle_root_url():
    return make_response(None, r"Ampoule drug data API. Submit a GET request to '/gtin/<GTIN>', where <GTIN> is a 13 or 14 digit Global Trade Identification Number. This API uses data from the Dictionary of Medicines and Devices (published by NHS Digital and available under an Open Government licence) to link GTIN to Actual Medicinal Product Pack (AMPP) data. Returns JSON object including name, strength, units, type and quanity of the product, if available.")


# 404 error
@error(404)
def error404(error):
    return make_response(None, f"Error: {str(error)}")


# Heroku environment
if os.environ.get('APP_LOCATION') == 'heroku':
    run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
else:
    run(host='localhost', port=8080, debug=True)
