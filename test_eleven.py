import requests
url = "https://api.elevenlabs.io/v1/user"
headers = {"xi-api-key": "sk_71c2bf44e0ecc0eded727549de4e5033bd569798b190e2d4"}
resp = requests.get(url, headers=headers)
print(resp.status_code, resp.text)
