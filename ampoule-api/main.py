"""Ampoule drug data API: Get drug data for a submitted Global Trade Identification Number.

Submit a GET request to '/gtin/<GTIN>', where <GTIN> is a 13 or 14 digit Global Trade Identification Number. This API queries a MongoDB database and uses modified data from the Dictionary of Medicines and Devices (published by NHS Digital and available under an Open Government licence) to link GTIN to Actual Medicinal Product Pack (AMPP) data. The API returns a JSON object including the name, strength, units, type and quanity of the product, if available.

"""

import os
import pymongo
from bottle import Bottle, install, route, request, get, post, template, redirect, static_file, error, run
from bson.json_util import dumps
import json
import dns

MONGODB_URI = "mongodb+srv://..."

# MongoDB connection
mongo = pymongo.MongoClient(
    MONGODB_URI, maxPoolSize=50, connect=False)
db = pymongo.database.Database(mongo, 'ampoule')
dmd_collection = pymongo.collection.Collection(db, 'dmd')

# Create Bottle app instance
app = Bottle()


def make_response(data, message, status="success", error=False):
    """Return a standardised response object."""
    return {
        "data": data,
        "message": message,
        "status": status,
        "error": error
    }


def make_error(message):
    """Return error response."""
    return make_response(None, message, status="fail", error=True)


@app.get('/gtin/<gtin>')
def get_drug_data(gtin):
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


@app.get('/')
@app.get('/gtin')
@app.get('/gtin/')
def handle_root_url():
    """Return information response for root URL."""
    return make_response(None, r"Ampoule drug data API. Submit a GET request to '/gtin/<GTIN>', where <GTIN> is a 13 or 14 digit Global Trade Identification Number. This API uses data from the Dictionary of Medicines and Devices (published by NHS Digital and available under an Open Government licence) to link GTIN to Actual Medicinal Product Pack (AMPP) data. Returns JSON object including name, strength, units, type and quanity of the product, if available.")


@error(404)
def error404(error):
    """404 response."""
    return make_response(None, f"Error: {str(error)}")


# Heroku environment
if os.environ.get('APP_LOCATION') == 'heroku':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
else:
    app.run(host='localhost', port=8080, debug=True)
