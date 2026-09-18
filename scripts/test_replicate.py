import os
import time
import requests

token = os.environ.get("REPLICATE_API_TOKEN")

print("Token var:", bool(token))

if not token:
    raise Exception("REPLICATE_API_TOKEN tapilmadi!")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

data = {
    "input": {
        "prompt": "A realistic photo of Azerbaijani scrambled eggs with tomatoes on a white plate",
        "aspect_ratio": "1:1",
        "output_format": "png"
    }
}

print("Replicate API sorgusu gonderilir...")

response = requests.post(
    "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
    headers=headers,
    json=data,
    timeout=60
)

print("HTTP status:", response.status_code)
print("Cavab:", response.text)

response.raise_for_status()

prediction = response.json()

prediction_url = prediction["urls"]["get"]

print("Prediction ID:", prediction["id"])
print("Status:", prediction["status"])

for i in range(60):
    time.sleep(5)

    check = requests.get(
        prediction_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30
    )

    check.raise_for_status()

    result = check.json()

    print(f"[{i + 1}/60] Status: {result['status']}")

    if result["status"] == "succeeded":
        print("CAVAB ALINDI!")
        print("Output:", result["output"])
        break

    if result["status"] in ["failed", "canceled"]:
        print("XETA:", result.get("error"))
        raise Exception("Prediction ugursuz oldu")
else:
    raise Exception("Prediction 5 deqiqe erzinde tamamlanmadi")
