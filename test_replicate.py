import os
import replicate

token = os.environ.get("REPLICATE_API_TOKEN")

print("Token var:", bool(token))
print("Sorğu göndərilir...")

client = replicate.Client(
    api_token=token
)

output = client.run(
    "black-forest-labs/flux-schnell",
    input={
        "prompt": "A realistic photo of Azerbaijani scrambled eggs with tomatoes on a white plate",
        "aspect_ratio": "1:1",
        "output_format": "png"
    }
)

print("CAVAB ALINDI:")
print(output)
