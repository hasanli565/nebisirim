import os
import json
import re
import time
from pathlib import Path

import requests


RECIPES_JSON_PATH = os.getenv("RECIPES_JSON_PATH", "recipes.json")
IMAGES_DIR = Path(os.getenv("IMAGES_DIR", "images"))
IMAGE_BASE_URL = os.getenv(
    "IMAGE_BASE_URL",
    "https://raw.githubusercontent.com/hasanli565/nebisirim/main/images"
)

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

try:
    MAX_IMAGES = int(os.getenv("MAX_IMAGES_PER_RUN", "1"))
except ValueError:
    MAX_IMAGES = 1


REPLICATE_URL = (
    "https://api.replicate.com/v1/models/"
    "black-forest-labs/flux-schnell/predictions"
)


def slugify(text):
    text = str(text).strip().lower()

    replacements = {
        "ə": "e",
        "ı": "i",
        "ö": "o",
        "ü": "u",
        "ş": "s",
        "ç": "c",
        "ğ": "g",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)

    return text.strip("-")


def get_ingredient_text(recipe):
    ingredients = recipe.get("ingredients", [])

    if not ingredients:
        return ""

    result = []

    for item in ingredients:
        if isinstance(item, str):
            result.append(item)

        elif isinstance(item, dict):
            name = (
                item.get("name")
                or item.get("ingredient")
                or item.get("title")
                or ""
            )

            amount = (
                item.get("amount")
                or item.get("quantity")
                or item.get("measure")
                or ""
            )

            if name:
                if amount:
                    result.append(f"{name} {amount}")
                else:
                    result.append(name)

    return ", ".join(result)


def create_prompt(recipe):
    name = recipe.get("name", "Food")
    description = recipe.get("description", "")

    ingredient_text = get_ingredient_text(recipe)

    prompt = (
        f"Professional food photography of {name}. "
        f"{description}. "
        f"Key ingredients: {ingredient_text}. "
        "Top-down angle, clean plate, natural lighting, "
        "shallow depth of field, appetizing, realistic, "
        "high resolution, no text, no watermark."
    )

    return prompt


def create_prediction(prompt):
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "output_format": "png",
        }
    }

    response = requests.post(
        REPLICATE_URL,
        headers=headers,
        json=data,
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


def wait_for_prediction(prediction):
    prediction_url = prediction["urls"]["get"]

    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}"
    }

    for i in range(60):
        time.sleep(5)

        response = requests.get(
            prediction_url,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        result = response.json()

        status = result.get("status")

        print(f"      [{i + 1}/60] Status: {status}")

        if status == "succeeded":
            return result

        if status in ("failed", "canceled"):
            raise Exception(
                f"Prediction uğursuz oldu: {result.get('error')}"
            )

    raise Exception("Prediction 5 dəqiqə ərzində tamamlanmadı")


def generate_image(prompt, output_path):
    last_error = None

    for attempt in range(1, 6):
        try:
            print(f"    API sorğusu göndərilir ({attempt}/5)...")

            prediction = create_prediction(prompt)

            print(
                f"    Prediction yaradıldı: "
                f"{prediction.get('id')}"
            )

            print(
                f"    Status: "
                f"{prediction.get('status')}"
            )

            result = wait_for_prediction(prediction)

            output = result.get("output")

            if not output:
                raise Exception("Replicate output boşdur")

            if isinstance(output, list):
                image_url = output[0]
            else:
                image_url = output

            print(f"    Şəkil URL-i alındı")

            image_response = requests.get(
                image_url,
                timeout=120,
            )

            image_response.raise_for_status()

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            output_path.write_bytes(image_response.content)

            print(
                f"    Şəkil yadda saxlanıldı: "
                f"{output_path}"
            )

            return True

        except Exception as e:
            last_error = e

            print(
                f"    Cəhd {attempt}/5 uğursuz oldu: {e}"
            )

            if attempt < 5:
                wait_seconds = attempt * 5

                print(
                    f"    {wait_seconds} saniyə gözlənilir..."
                )

                time.sleep(wait_seconds)

    print(
        f"    XETA: Şəkil yaradıla bilmədi: "
        f"{last_error}"
    )

    return False


def main():
    if not REPLICATE_API_TOKEN:
        raise Exception(
            "REPLICATE_API_TOKEN tapılmadı!"
        )

    with open(
        RECIPES_JSON_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        recipes = json.load(f)

    if not isinstance(recipes, list):
        raise Exception(
            "recipes.json siyahı formatında olmalıdır."
        )

    IMAGES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    missing = []

    for recipe in recipes:
        image_resource = recipe.get("imageResource")

        if not image_resource:
            missing.append(recipe)

    print()
    print(
        f"Cəmi resept: {len(recipes)}, "
        f"şəkli olmayan: {len(missing)}"
    )

    print(
        f"Bu işə salınmada maksimum "
        f"{MAX_IMAGES} şəkil yaradılacaq."
    )

    if DRY_RUN:
        print()
        print("DRY RUN aktivdir.")
        print("API çağırılmayacaq.")

        for recipe in missing[:MAX_IMAGES]:
            slug = slugify(recipe.get("name", "recipe"))
            prompt = create_prompt(recipe)

            print()
            print(recipe.get("name"))
            print("slug:", slug)
            print("prompt:", prompt)

        return

    successful = 0
    failed = 0

    for index, recipe in enumerate(
        missing[:MAX_IMAGES],
        start=1
    ):
        name = recipe.get("name", "Recipe")
        slug = slugify(name)

        image_path = IMAGES_DIR / f"{slug}.png"

        print()
        print(
            f"[{index}/{min(MAX_IMAGES, len(missing))}] "
            f"{name}"
        )

        print(
            f"  slug   : {slug}"
        )

        prompt = create_prompt(recipe)

        print(
            f"  prompt : {prompt}"
        )

        if image_path.exists():
            print(
                "  Şəkil artıq mövcuddur, keçilir."
            )

            recipe["imageResource"] = (
                f"{IMAGE_BASE_URL}/{slug}.png"
            )

            successful += 1
            continue

        ok = generate_image(
            prompt,
            image_path
        )

        if ok:
            recipe["imageResource"] = (
                f"{IMAGE_BASE_URL}/{slug}.png"
            )

            successful += 1

            print(
                f"  imageResource: "
                f"{recipe['imageResource']}"
            )

        else:
            failed += 1

    if not DRY_RUN:
        with open(
            RECIPES_JSON_PATH,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                recipes,
                f,
                ensure_ascii=False,
                indent=2
            )

    remaining = sum(
        1
        for recipe in recipes
        if not recipe.get("imageResource")
    )

    print()
    print("==============================")
    print("NƏTİCƏ")
    print("==============================")
    print(f"Uğurlu: {successful}")
    print(f"Xətalı: {failed}")
    print(f"Qalan şəkilsiz: {remaining}")


if __name__ == "__main__":
    main()
