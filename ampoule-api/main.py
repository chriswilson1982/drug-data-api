"""Ampoule drug data API: Get drug data for a submitted Global Trade Identification Number.

UK: Submit a GET request to '/api/dmd/gtin/<GTIN>', where <GTIN> is a 13 or 14 digit Global Trade Identification Number (GTIN). 

USA: Submit a GET request to '/api/fda/ndc/<NDC>', where <NDC> is a dehyphenated National Drug Code (NDC). 

This API queries a MongoDB database that uses modified data from the Dictionary of Medicines and Devices
(published by NHS Digital and available under an Open Government licence) and the Food and Drug Administration (FDA)
to serve drug data on submission of a valid GTIN or NDC.

The API returns a JSON object including the name, strength, units, type and quanity of the product, if available.

"""


import os
import pymongo
from bottle import Bottle, install, route, request, get, post, template, redirect, response, static_file, error, run
from bson.json_util import dumps
import json
import dns
from datetime import datetime
import hashlib
import markdown


MONGODB_URI = "mongodb+srv://..."


# MongoDB connection
mongo = pymongo.MongoClient(
    MONGODB_URI, maxPoolSize=50, connect=False)
db = pymongo.database.Database(mongo, 'ampoule')


# Collections
dmd_collection = pymongo.collection.Collection(db, 'dmd')
fda_collection = pymongo.collection.Collection(db, 'fda')


# Create Bottle app instance
app = Bottle()


# Convenience function for successful response
def make_response(data, message, status="success", error=False):
    """Return a standardised response object."""
    return {
        "data": data,
        "message": message,
        "status": status,
        "error": error
    }


# Convenience function for error response
def make_error(message):
    """Return error response."""
    return make_response(None, message, status="fail", error=True)


# Static javascript
@app.get('/js/<filename>')
def js(filename):
    return static_file(filename, root='./static/js/', mimetype='text/javascript')


# New API endpoint - DM+D (UK)
@app.get('/api/dmd/gtin/<gtin>')
def dmd_api(gtin):
    """Accept GTIN and return corresponding drug data."""
    # Check valid input
    if not gtin.isnumeric():
        return make_error("Error: Submit a 13 or 14 digit numeric GTIN")
    elif len(gtin) != 13 and len(gtin) != 14:
        return make_error("Error: Submit a 13 or 14 digit numeric GTIN")
    # Make database request
    try:
        query = dmd_collection.find_one({"gtin": gtin}, {"gtin": 0, "_id": 0})
        result = json.loads(dumps(query))
    except Exception as error:
        return make_error(f"Error: {str(error)}")
    # If no result, check equivalant GTIN
    if not result:
        # If 13-digit GTIN, try prefixing "0"
        if len(gtin) == 13:
            new_gtin = "0" + gtin
            try:
                query = dmd_collection.find_one(
                    {"gtin": new_gtin}, {"gtin": 0, "_id": 0})
                result = json.loads(dumps(query))
            except Exception as error:
                return make_error(f"Error: {str(error)}")
        # If 14-digit GTIN, try without first digit
        elif len(gtin) == 14:
            new_gtin = gtin[1:]
            try:
                query = dmd_collection.find_one(
                    {"gtin": new_gtin}, {"gtin": 0, "_id": 0})
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



# New API endpoint - FDA (USA)
@app.get('/api/fda/ndc/<ndc>')
def fda_api(ndc):
    def insertZero(str, pos):
        return str[:pos-1] + "0" + str[pos-1:]
    # 10-digit NDC - if unsuccessful try inserting zero in first or sixth position
    # Check valid input
    if not ndc.isnumeric():
        return make_error("Error: Submit a 10 or 11 digit numeric NDC")
    elif len(ndc) != 10 and len(ndc) != 11:
        return make_error("Error: Submit a 10 or 11 digit numeric NDC")
    # Make database request
    try:
        query = fda_collection.find_one({"package_ndc": ndc}, {"base_ndc": 0,"package_ndc": 0, "_id": 0})
        result = json.loads(dumps(query))
    except Exception as error:
        return make_error(f"Error: {str(error)}")
    # If no result, check equivalant GTIN
    if not result:
        # If 13-digit GTIN, try prefixing "0"
        if len(ndc) == 10:
            new_ndc = insertZero(ndc, 0)
            try:
                query = fda_collection.find_one({"package_ndc": new_ndc}, {"base_ndc": 0,"package_ndc": 0, "_id": 0})
                result = json.loads(dumps(query))
            except Exception as error:
                return make_error(f"Error: {str(error)}")
            if not result:
                try:
                    new_ndc = insertZero(ndc, 6)
                    query = fda_collection.find_one({"package_ndc": new_ndc}, {"base_ndc": 0,"package_ndc": 0, "_id": 0})
                    result = json.loads(dumps(query))
                except Exception as error:
                    return make_error(f"Error: {str(error)}")
        # If 14-digit GTIN, try without first digit
    elif len(ndc) == 11 and ndc[0] == "0":
            new_ndc = ndc[1:]
            try:
                query = fda_collection.find_one({"package_ndc": new_ndc}, {"base_ndc": 0,"package_ndc": 0, "_id": 0})
                result = json.loads(dumps(query))
            except Exception as error:
                return make_error(f"Error: {str(error)}")
    # Return data
    if result:
        return make_response(result, "Success")
    else:
        return make_error("Error: No drug data found for that GTIN")


@app.get('/test')
def api_test():
    return make_response(None, "API Status OK")

@app.get('/')
def handle_root_url():
    """Return information response for root URL."""
    return make_response(None, r"Ampoule drug data API. Submit a GET request to '/api/dmd/gtin/<GTIN> or '/api/fda/ndc/<NDC>', where <GTIN> is a Global Trade Identification Number and NDC is a National Drug Code. This API uses adapted data from the Dictionary of Medicines and Devices (published by NHS Digital and available under an Open Government licence) and data from the Food and Drug Administration (FDA).  Returns a JSON object including the name, strength, units, type and quanity of the drug, if available.")


@error(404)
def error404(error):
    """404 response."""
    return make_response(None, f"Error: {str(error)}")


# Heroku environment
if os.environ.get('APP_LOCATION') == 'heroku':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
else:
    app.run(host='localhost', port=8080, debug=True)