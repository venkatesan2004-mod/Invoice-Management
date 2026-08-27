# import requests

# url = "https://api.sandbox.co.in/gst/compliance/e-way-bill/tax-payer/hsn"

# headers = {
#     "x-api-version": "1.0.0",
#     "Authorization": "<authorization>",
#     "x-api-key": "<x-api-key>"
# }

# response = requests.get(url, headers=headers)

# print(response.text)


# import requests

# url = "https://api.sandbox.co.in/gst/compliance/e-way-bill/tax-payer/gstin/search"

# payload = { "gstin": "29AAACQ3770E000" }
# headers = {
#     "x-api-version": "1.0.0",
#     "Authorization": "<authorization>",
#     "x-api-key": "<x-api-key>",
#     "Content-Type": "application/json"
# }

# response = requests.post(url, json=payload, headers=headers)

# print(response.text)



import requests

url = "https://api.mastersindia.co/gstin"

headers = {
    "Authorization": "Bearer YOUR_API_KEY"
}

params = {
    "gstin": "29AAACQ3770E1ZV"
}

response = requests.get(url, headers=headers, params=params)
print(response.json())