import os
import time
import replicate

token = os.environ.get("REPLICATE_API_TOKEN")

print("Token var:", bool(token))

if not token:
    raise Exception("REPLICATE_API_TOKEN tapilmadi!")

print("Async Replicate sorgusu gonderilir...")

client = replicate.Client(api_token=token)

prediction = client.models.predictions.create(
    model="black-forest-labs/flux-schnell",
    input={
        "prompt": "A realistic photo of Azerbaijani scrambled eggs with tomatoes on a white plate",
        "aspect_ratio": "1:1",
        "output_format": "png"
    }
)

print("Prediction yaradildi:")
print("ID:", prediction.id)
print("Status:", prediction.status)

for i in range(60):
    prediction.reload()

    print(f"[{i + 1}/60] Status: {prediction.status}")

    if prediction.status == "succeeded":
        print("CAVAB ALINDI!")
        print("Output:", prediction.output)
        break

    if prediction.status in ["failed", "canceled"]:
        print("XETA:", prediction.error)
        raise Exception("Replicate prediction ugursuz oldu")

    time.sleep(5)
else:
    raise Exception("Prediction 5 deqiqe erzinde tamamlanmadi")
