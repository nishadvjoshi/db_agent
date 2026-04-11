import requests
import json
prompt = "Hello"
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyAegoA_J5VcYLhqnJqUBOptq3CrZyQ09IQ"
payload = {"contents": [{"parts": [{"text": prompt}]}]}
r = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=120)
print(r.status_code)
print(r.text)
