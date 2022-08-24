"""Converts FDA issued JSON NDC data to simplified schema usable with Ampoule API.

Hyphens/dashes are removed from NDC for simplicity and to reflect what can be
scanned from a barcode without having to guess where the hyphens go
(section lengths are variable)

------------------------------------------------------------

"""

import json
import string


# Filename constants (modify as needed)
FDA_INPUT = "fda.json"

# Output file
JSON_OUTPUT = "fda_output.json"

# Dictionary to store loaded data
fda_dict = {}

# Dictionary to store mapping of AMPPID -> drug data
output_array_of_dict = []

# Item counts
total_items = 0
error_items = 0

# Avoid duplicates
used_ndcs = []

with open(FDA_INPUT) as fda_file:
    print("Parsing FDA data...")
    fda_dict = json.load(fda_file)

    for drug in fda_dict["results"]:
        packs = drug["packaging"]
        item_error = False
        
        for pack in packs:

            # Avoid duplicates
            if pack["package_ndc"] in used_ndcs:
                continue

            try:
                generic_name = drug["generic_name"].title()
            except:
                generic_name = ""
                item_error = True
                
            try:
                brand_name = drug["brand_name"].title()
            except:
                brand_name = ""
                item_error = True
                
            try:
                strength = drug["active_ingredients"][0]["strength"].split(" ")[0]
                if strength[0] == ".":
                    strength = "0" + strength
            except:
                strength = ""
                item_error = True
            
            try:
                units = drug["active_ingredients"][0]["strength"].split(" ")[1].replace("mg/1", "mg")
            except:
                units = ""
                item_error = True

            try:
                type_string = pack["description"].split(" ")[1].replace(",", "").title()
            except:
                type_string = ""
                item_error = True

            try:
                this_pack = {
                    "base_ndc" : drug["product_ndc"].replace("-", ""),
                    "package_ndc" : pack["package_ndc"].replace("-", ""),
                    "generic_name" : generic_name,
                    "brand_name" : brand_name,
                    "strength" : strength,
                    "units" : units,
                    "type" : type_string,
                    "quantity" : pack["description"].split(" ")[0]
                }
                output_array_of_dict.append(this_pack)
                used_ndcs.append(pack["package_ndc"])
                total_items += 1
                if item_error:
                    error_items += 1
            except Exception as e:
                print(e)

# Write output file
with open(JSON_OUTPUT, 'w', encoding='utf-8') as outfile:
    json.dump(output_array_of_dict, outfile, ensure_ascii=False, indent=4)


# Completed
print(f"Completed!\n\n{total_items} total items\n{error_items} items with incompleteness errors\n\nJSON saved to {JSON_OUTPUT}\n")
