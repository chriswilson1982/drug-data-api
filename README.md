# DM+D Data API

The Dictionary of Medicines and Devices (DM+D) is a dataset of all the medicines and devices used in the UK National Health Service (NHS). It is maintained by the [NHS Business Services Authority](https://www.nhsbsa.nhs.uk) and [NHS Digital](https://digital.nhs.uk). DM+D data is provided in XML format under an [Open Government Licence](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

This repository includes a Python script for parsing and cross-referencing two DM+D XML files in order to link Actual Medicinal Product Pack (AMPP) product data with Global Trade Identification Numbers (GTIN) in JSON format. This allows drug data to be found with a GTIN, which is available on a product barcode.

The other part of this repository is a Python web app (using the Bottle framework) that provides an API interface to a MongoDB database containing the JSON data.

## The API is live on Heroku

This API is running on a Heroku dyno at [Ampoule Drug Data API](https://ampoule.herokuapp.com). The data in the MongoDB database is updated periodically as DM+D updates are released.

## What is Ampoule?

[Ampoule](https://apps.apple.com/gb/app/ampoule/id1259841485) is an iOS app that helps healthcare professionals to track an inventory of medical drugs. I developed this way of adapting DM+D data and incorporating it into an API to enable barcode scanning in the app, which will allow more rapid data entry by users.

## A note on barcodes

In the UK, all medical product packs will have an EAN13 or EAN14 barcode, which provides the GTIN. Many packs will also have a 2D data matrix code, which usually encodes the GTIN as well as batch number and expiry date.

## Contact

You can give feedback, suggestions or report bugs here on GitHub or email info@ampoule.io.
