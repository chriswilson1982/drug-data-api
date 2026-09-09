"""Ampoule drug data API: Get drug data for a submitted Global Trade Identification Number.

UK: Submit a GET request to '/api/dmd/gtin/<GTIN>', where <GTIN> is a 13 or 14 digit Global Trade Identification Number (GTIN).

USA: Submit a GET request to '/api/fda/ndc/<NDC>', where <NDC> is a dehyphenated National Drug Code (NDC).

This API queries a MongoDB database that uses modified data from the Dictionary of Medicines and Devices
(published by NHS Digital and available under an Open Government licence) and the Food and Drug Administration (FDA)
to serve drug data on submission of a valid GTIN or NDC.

The API returns a JSON object including the name, strength, units, type and quanity of the product, if available.

"""


import os
import logging
import pymongo
from bottle import Bottle, static_file
from bson.json_util import dumps
import json


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


MONGODB_URI = os.environ.get("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI environment variable must be set")


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


def find_with_fallback(collection, field, candidates, projection):
    """Try each candidate value in turn and return the first match found, or None."""
    for candidate in candidates:
        query = collection.find_one({field: candidate}, projection)
        if query:
            return json.loads(dumps(query))
    return None


def insert_zero(value, pos):
    """Insert a '0' immediately before the 1-indexed position `pos`."""
    return value[:pos - 1] + "0" + value[pos - 1:]


def gtin_candidates(gtin):
    """Build the list of GTIN values to try, most likely match first.

    Barcode data sometimes has an extra or missing leading zero
    depending on encoding, so also try the 13/14-digit equivalent.
    """
    candidates = [gtin]
    if len(gtin) == 13:
        candidates.append("0" + gtin)
    elif len(gtin) == 14:
        candidates.append(gtin[1:])
    return candidates


def ndc_candidates(ndc):
    """Build the list of NDC values to try, most likely match first.

    A 10-digit NDC is missing the leading zero from one of its three
    segments, so try inserting it in the first or sixth position; an
    11-digit NDC starting with "0" may just need that zero stripped.
    """
    candidates = [ndc]
    if len(ndc) == 10:
        candidates.append(insert_zero(ndc, 1))
        candidates.append(insert_zero(ndc, 6))
    elif len(ndc) == 11 and ndc[0] == "0":
        candidates.append(ndc[1:])
    return candidates


# Static javascript
@app.get('/js/<filename>')
def js(filename):
    return static_file(filename, root='./static/js/', mimetype='text/javascript')


# New API endpoint - DM+D (UK)
@app.get('/api/dmd/gtin/<gtin>')
def dmd_api(gtin):
    """Accept GTIN and return corresponding drug data."""
    # Check valid input
    if not gtin.isnumeric() or len(gtin) not in (13, 14):
        return make_error("Error: Submit a 13 or 14 digit numeric GTIN")

    # Make database request
    candidates = gtin_candidates(gtin)
    try:
        result = find_with_fallback(
            dmd_collection, "gtin", candidates, {"gtin": 0, "_id": 0})
    except Exception:
        logger.exception("Database error looking up GTIN %s", gtin)
        return make_error("Error: Unable to process request at this time")

    # Return data
    if result:
        return make_response(result["ampp"], "Success")
    return make_error("Error: No drug data found for that GTIN")


# New API endpoint - FDA (USA)
@app.get('/api/fda/ndc/<ndc>')
def fda_api(ndc):
    """Accept NDC and return corresponding drug data."""
    # Check valid input
    if not ndc.isnumeric() or len(ndc) not in (10, 11):
        return make_error("Error: Submit a 10 or 11 digit numeric NDC")

    # Make database request
    candidates = ndc_candidates(ndc)
    try:
        result = find_with_fallback(
            fda_collection, "package_ndc", candidates,
            {"base_ndc": 0, "package_ndc": 0, "_id": 0})
    except Exception:
        logger.exception("Database error looking up NDC %s", ndc)
        return make_error("Error: Unable to process request at this time")

    # Return data
    if result:
        return make_response(result, "Success")
    return make_error("Error: No drug data found for that NDC")


@app.get('/test')
def api_test():
    return make_response(None, "API Status OK")

@app.get('/')
def handle_root_url():
    """Return information response for root URL."""
    return make_response(None, r"Ampoule drug data API. Submit a GET request to '/api/dmd/gtin/GTIN or '/api/fda/ndc/NDC', where GTIN is a Global Trade Identification Number and NDC is a National Drug Code. This API uses adapted data from the Dictionary of Medicines and Devices (published by NHS Digital and available under an Open Government licence) and data from the Food and Drug Administration (FDA).  Returns a JSON object including the name, strength, units, type and quantity of the drug, if available.")


@app.error(404)
def error404(error):
    """404 response."""
    return make_response(None, f"Error: {str(error)}")


if __name__ == '__main__':
    # Heroku environment
    if os.environ.get('APP_LOCATION') == 'heroku':
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    else:
        app.run(host='localhost', port=8080, debug=True)
