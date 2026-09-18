```python
#!/usr/bin/env python3
"""
recipes.json-dan imageResource sahəsi boş olan reseptləri tapır,
Replicate (FLUX Schnell) ilə şəkil yaradır,
images/ qovluğuna yazır və recipes.json-u yeniləyir.
"""

import json
import os
import re
import sys
import time
import unicodedata
import urllib.request

try:
    import replicate
except ImportError:
    print(
        "XETA: 'replicate' paketi qurulmayıb -> pip install -U replicate",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import httpx
except ImportError:
    httpx = None


RECIPES_JSON_PATH = os.environ.get("RECIPES_JSON_PATH", "recipes.json")
IMAGES_DIR = os.environ.get("IMAGES_DIR", "images")
IMAGE_BASE_URL = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")

API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")

MODEL = os.environ.get(
    "REPLICATE_MODEL",
    "black-forest-labs/flux-schnell"
)

# GitHub Actions-da bunu false etməliyik
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

MAX_IMAGES_PER_RUN = int(
    os.environ.get("MAX_IMAGES_PER_RUN", "20")
)

MAX_ATTEMPTS = 5


AZ_MAP = {
    "ə": "e",
    "Ə": "E",
    "ı": "i",
    "İ": "I",
    "ö": "o",
    "Ö": "O",
    "ü": "u",
    "Ü": "U",
    "ç": "c",
    "Ç": "C",
    "ş": "sh",
    "Ş": "Sh",
    "ğ": "g",
    "Ğ": "G",
}


def slugify(name: str) -> str:
    for src, dst in AZ_MAP.items():
        name = name.replace(src, dst)

    name = (
        unicodedata
        .normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode()
    )

    name = re.sub(
        r"[^a-zA-Z0-9]+",
        "-",
        name
    ).strip("-").lower()

    return name or "recipe"


def build_prompt(recipe: dict) -> str:
    name = (
        recipe.get("name")
        or recipe.get("title")
        or "yemek"
    )

    description = recipe.get("description", "")

    ingredients = recipe.get("ingredients", [])

    if isinstance(ingredients, list):
        parts = []

        for item in ingredients[:8]:
            if isinstance(item, dict):
                ing_name = item.get("name", "")
                quantity = item.get("quantity", "")
                unit = item.get("unit", "")

                parts.append(
                    f"{ing_name} {quantity} {unit}".strip()
                )
            else:
                parts.append(str(item))

        ing_text = ", ".join(parts)

    else:
        ing_text = str(ingredients)

    return (
        f"Professional food photography of {name}. "
        f"{description}. "
        f"Key ingredients: {ing_text}. "
        "Top-down angle, clean plate, natural lighting, "
        "shallow depth of field, appetizing, realistic, "
        "high resolution, no text, no watermark."
    ).strip()


def make_client():
    if httpx is not None:

        timeout = httpx.Timeout(
            connect=60.0,
            read=300.0,
            write=60.0,
            pool=60.0,
        )

        return replicate.Client(
            api_token=API_TOKEN,
            timeout=timeout,
        )

    return replicate.Client(
        api_token=API_TOKEN
    )


def download_image(image_url: str) -> bytes:
    """
    Replicate-in qaytardığı şəkli yükləyir.
    Timeout 5 dəqiqədir.
    """

    request = urllib.request.Request(
        image_url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=300
    ) as response:

        return response.read()


def generate_image(client, prompt: str) -> bytes:

    last_err = None

    for attempt in range(1, MAX_ATTEMPTS + 1):

        try:

            print(
                f"    API sorğusu göndərilir "
                f"({attempt}/{MAX_ATTEMPTS})..."
            )

            output = client.run(
                MODEL,
                input={
                    "prompt": prompt,
                    "aspect_ratio": "1:1",
                    "output_format": "png",
                },
            )

            if not output:
                raise RuntimeError(
                    "Replicate boş nəticə qaytardı."
                )

            result = (
                output[0]
                if isinstance(output, list)
                else output
            )

            # URL kimi gəlibsə
            if isinstance(result, str):

                image_url = result

                if not image_url.startswith("http"):
                    raise RuntimeError(
                        f"Naməlum nəticə: {image_url}"
                    )

                print(
                    "    Şəkil yaradıldı, "
                    "fayl yüklənir..."
                )

                return download_image(image_url)

            # FileOutput / obyekt kimi gəlibsə
            if hasattr(result, "read"):

                print(
                    "    Şəkil yaradıldı, "
                    "fayl oxunur..."
                )

                return result.read()

            # bytes kimi gəlibsə
            if isinstance(result, bytes):
                return result

            raise RuntimeError(
                f"Naməlum Replicate nəticəsi: {type(result)}"
            )

        except Exception as e:

            last_err = e

            print(
                f"    Cəhd {attempt}/{MAX_ATTEMPTS} "
                f"uğursuz oldu: {e}"
            )

            if attempt < MAX_ATTEMPTS:

                wait_time = attempt * 5

                print(
                    f"    {wait_time} saniyə gözlənilir..."
                )

                time.sleep(wait_time)

    raise RuntimeError(
        f"Şəkil yaradıla bilmədi: {last_err}"
    )


def main():

    if not os.path.exists(RECIPES_JSON_PATH):

        print(
            f"XETA: {RECIPES_JSON_PATH} tapılmadı.",
            file=sys.stderr
        )

        sys.exit(1)

    with open(
        RECIPES_JSON_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        recipes = json.load(f)

    recipe_list = (
        recipes["recipes"]
        if isinstance(recipes, dict)
        and "recipes" in recipes
        else recipes
    )

    missing = [
        r
        for r in recipe_list
        if not r.get("imageResource")
    ]

    print(
        f"Cəmi resept: {len(recipe_list)}, "
        f"şəkli olmayan: {len(missing)}"
    )

    if not missing:

        print(
            "Hamısının şəkli var, görüləcək iş yoxdur."
        )

        return

    todo = missing[:MAX_IMAGES_PER_RUN]

    print(
        f"Bu işə salınmada maksimum "
        f"{len(todo)} şəkil yaradılacaq."
    )

    os.makedirs(
        IMAGES_DIR,
        exist_ok=True
    )

    if DRY_RUN:

        print(
            "\n!!! DRY_RUN=true !!!"
        )

        print(
            "API çağırılmayacaq, "
            "şəkil yaradılmayacaq."
        )

    if not DRY_RUN and not API_TOKEN:

        print(
            "\nXETA: REPLICATE_API_TOKEN tapılmadı.",
            file=sys.stderr
        )

        sys.exit(1)

    client = (
        None
        if DRY_RUN
        else make_client()
    )

    changed = False

    success_count = 0
    error_count = 0

    for i, recipe in enumerate(todo, 1):

        name = (
            recipe.get("name")
            or recipe.get("title")
            or f"recipe-{i}"
        )

        slug = slugify(name)

        prompt = build_prompt(recipe)

        file_path = os.path.join(
            IMAGES_DIR,
            f"{slug}.png"
        )

        print(
            f"\n[{i}/{len(todo)}] {name}"
        )

        print(
            f"  slug   : {slug}"
        )

        print(
            f"  prompt : {prompt}"
        )

        # Fayl artıq varsa, yenidən yaratma
        if os.path.exists(file_path):

            print(
                f"  KEÇİLDİ -> {file_path} artıq mövcuddur."
            )

            if not recipe.get("imageResource"):

                recipe["imageResource"] = (
                    f"{IMAGE_BASE_URL}/{slug}.png"
                    if IMAGE_BASE_URL
                    else f"{IMAGES_DIR}/{slug}.png"
                )

                changed = True

            continue

        if DRY_RUN:

            print(
                "  DRY_RUN=true -> "
                "API çağırılmadı."
            )

            continue

        try:

            image_bytes = generate_image(
                client,
                prompt
            )

            if not image_bytes:

                raise RuntimeError(
                    "Şəkil faylı boş gəldi."
                )

            with open(
                file_path,
                "wb"
            ) as img_f:

                img_f.write(image_bytes)

            recipe["imageResource"] = (
                f"{IMAGE_BASE_URL}/{slug}.png"
                if IMAGE_BASE_URL
                else f"{IMAGES_DIR}/{slug}.png"
            )

            changed = True
            success_count += 1

            print(
                f"  OK -> {file_path}"
            )

        except Exception as e:

            error_count += 1

            print(
                f"  XETA: {e}",
                file=sys.stderr
            )

            # Növbəti reseptə keçir
            continue

    if changed:

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

        print(
            f"\n{RECIPES_JSON_PATH} yeniləndi."
        )

    print("\n==============================")
    print("NƏTİCƏ")
    print("==============================")
    print(f"Uğurlu: {success_count}")
    print(f"Xətalı: {error_count}")
    print(
        f"Qalan şəkilsiz: "
        f"{len(missing) - success_count}"
    )


if __name__ == "__main__":
    main()
```
