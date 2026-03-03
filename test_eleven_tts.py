import requests
url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
headers = {
  "xi-api-key": "sk_72090e178228a123fa8f75dab1a25085c13970229acd6323",
  "Content-Type": "application/json"
}
data = {
  "text": "Hello world"
}
resp = requests.post(url, json=data, headers=headers)
print(resp.status_code, resp.text[:200])
