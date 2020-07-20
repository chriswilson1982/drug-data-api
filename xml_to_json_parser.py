"""Simplify DM+D XML data, link GTIN to AMPP and export as JSON

This script will process Dictionary of Medicines and Devices (DM+D) Actual 
Medicinal Product Pack (AMPP) and Global Trade Indentification Number (GTIN)
data (XML format) and export it to a JSON array.

It links the GTIN (available on product barcodes) to the relevant product
data (parsing the string into separate fields for 'name', 'strength',
'units', 'type' and 'quantity').

The DM+D is released by the NHS Business Services Authority (NHSBSA)
and NHS Digital under an Open Government Licence.

Information: https://isd.digital.nhs.uk
Licence: http://www.nationalarchives.gov.uk/doc/open-government-licence

Created by Dr Chris Wilson in July 2020
Contact: c.m.wilson@me.com

------------------------------------------------------------

* Example XML structure of DM+D AMPP data file (input)

<AMPP>
  <APPID>1328111000001105</APPID>
  <NM>Verapamil 160mg tablets (Actavis UK Ltd) 56 tablet 4 x 14 tablets</NM>
  <VPPID>982511000001103</VPPID>
  <APID>390711000001102</APID>
  <LEGAL_CATCD>0003</LEGAL_CATCD>
  <SUBP>4 x 14 tablets</SUBP>
</AMPP>

* Example XML structure of DM+D AMPP/GTIN mapping file (input)

<AMPP>
  <AMPPID>1328111000001105</AMPPID>
  <GTINDATA>
    <GTIN>5012617009784</GTIN>
    <STARTDT>2010-02-04</STARTDT>
  </GTINDATA>
  <GTINDATA>
    <GTIN>05012617009784</GTIN>
    <STARTDT>2019-03-18</STARTDT>
  </GTINDATA>
</AMPP>

* Example JSON output (top level is array of objects with this format)

[
    {
        "gtin": "5012617009784",
        "ampp": {
            "name": "Verapamil",
            "strength": "160",
            "units": "mg",
            "type": "tablet",
            "quantity": "56"
        }
    }
]

------------------------------------------------------------

"""

import xml.dom.minidom as minidom
import json

# Filename constants (modify as needed)
AMPP_INPUT = "ampp.xml"
GTIN_INPUT = "gtin.xml"

# Output file
JSON_OUTPUT = "drugs.json"

# Dictionary to store mapping of GTIN -> list of AMPPID
gtin_ampp_dict = {}

# Dictionary to store mapping of AMPPID -> drug data
ampp_drug_dict = {}


# Parse XML data to link GTINs with an AMPPID
with open(GTIN_INPUT) as gtin_file:
    print("Parsing GTIN XML data...")
    doc = minidom.parse(gtin_file)
    item_list = doc.getElementsByTagName("AMPP")
    
    for item in item_list:

        # Get AMPPID
        amppid = item.getElementsByTagName("AMPPID")[0].firstChild.data
        
        # Get GTIN and remove duplicate GTINs for this item
        all_gtins = [gtin_element.firstChild.data for gtin_element in item.getElementsByTagName("GTIN")]
        gtins = []
        for item in all_gtins:
            if item not in gtins:
                gtins.append(item)
                
        # Save this relationship to dict (key: AMPPID, value: List of GTINs)
        for gtin in gtins:
            gtin_ampp_dict[gtin] = amppid
            """
            # Previously added AMPPID as list to allow duplicates
            # but they are always equivalent
            if gtin in gtin_ampp_dict:
                gtin_ampp_dict[gtin] += [amppid]
            else:
                gtin_ampp_dict[gtin] = [amppid]
            """
            

# Parse XML data to get drug details for AMPPID
with open(AMPP_INPUT) as ampp_file:
    print("Parsing AMPP XML data...")
    doc = minidom.parse(ampp_file)
    item_list = doc.getElementsByTagName("AMPP")

    for item in item_list:

        # Get AMPPID
        amppid = item.getElementsByTagName("APPID")[0].firstChild.data

        # Get drug details
        nm = item.getElementsByTagName("NM")[0].firstChild.data

        # Find first 'word' with numbers and letters (strength and units)
        word_list = nm.split()
        start_strength_index = 0
        strength_string = ""
        for index, word in enumerate(word_list):
            digit = False
            alpha = False
            for char in word:
                if char.isdigit():
                    digit = True
                elif char.isalpha():
                    alpha = True
            if digit and alpha:
                strength_string = word
                start_strength_index = nm.index(word)
                break
            
        # First letter or "%" in strength_string is start of units
        unit_start_index = 0
        for index, char in enumerate(strength_string):
            if char.isalpha() or char == "%":
                unit_start_index = index
                break
            
        # Set name
        name = nm[:start_strength_index].strip()
        if name == "":
            for index, char in enumerate(nm):
                if char == "(":
                    name = nm[:index].strip()
                    break
            
        # Set strength
        try:
            strength = strength_string[:unit_start_index].strip("()")
        except Exception as e:
            strength = ""

        # Set units
        try:
            units = strength_string[unit_start_index:].strip("()")
        except Exception as e:
            units = ""
            
        # Split at last closing parenthesis - after this is quantity and type
        last_section = nm.split(')')[-1]

        # Set quantity and type
        try:
            quantity = last_section.split()[0]
            if not quantity.isnumeric():
                raise TypeError
        except Exception as e:
            quantity = ""
        try:
            type = last_section.split()[1]
            if type in ["g", "gram", "ml"] or not type.isalpha():
                raise TypeError
        except Exception as e:
            type = ""
            
        output = { 'name' : name, 'strength' : strength, 'units' : units, 'type' : type, 'quantity' : quantity }
        ampp_drug_dict[amppid] = output


# Merge data
print("Organising data for output...")
output_data = []
for gtin, amppid in gtin_ampp_dict.items():
    #output_data.append({ "gtin" : gtin, "ampp" : [ampp_drug_dict[amppid] for amppid in amppids] })
    output_data.append({ "gtin" : gtin, "ampp" : ampp_drug_dict[amppid] })


# Write output file
with open(JSON_OUTPUT, 'w', encoding='utf-8') as outfile:
    json.dump(output_data, outfile, ensure_ascii=False, indent=4)


# Completed
print(f"Completed!\nJSON saved to {JSON_OUTPUT}\n")
