#!/usr/bin/env python3
"""
recipes.json faylini oxuyur, imageResource sahesi bos olan reseptleri tapir,
her biri ucun prompt qurur ve Replicate (flux-schnell) ile shekil yaradir,
images/ qovluguna yazir ve recipes.json-u avtomatik yenileyir.

Env deyisenleri:
  REPLICATE_API_TOKEN - Replicate API tokeni (GitHub Secrets-den gelir)
  RECIPES_JSON_PATH    - recipes.json-un yolu (defolt: recipes.json)
  IMAGES_DIR            - shekillerin yazilacagi qovluq (defolt: images)
  IMAGE_BASE_URL         - imageResource-a yazilacaq public URL prefiksi
                            meselen: https://raw.githubusercontent.com/<user>/<repo>/main/images
  REPLICATE_MODEL         - istifade olunacaq model (defolt: black-forest-labs/flux-schnell)
  DRY_RUN                  - "true" olsa, API-ye pul xerclemeden yalniz
                              hansi reseptlerin shekli olmadigini ve hansi
                              promptun qurulacagini ekrana yazir.
  MAX_IMAGES_PER_RUN       - bir ishe salinmada max nece shekil yaradilsin (defolt: 20)
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
    print("XETA: 'replicate' paketi qurulmayib -> pip install -U replicate", file=sys.stderr)
    sys.exit(1)

try:
    import httpx
except ImportError:
    httpx = None

RECIPES_JSON_PATH = os.environ.get("RECIPES_JSON_PATH", "recipes.json")
IMAGES_DIR = os.environ.get("IMAGES_DIR", "images")
IMAGE_BASE_URL = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
MODEL = os.environ.get("REPLICATE_MODEL", "black-forest-labs/flux-schnell")
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"
MAX_IMAGES_PER_RUN = int(os.environ.get("MAX_IMAGES_PER_RUN", "20"))

AZ_MAP = {
    "ə": "e", "Ə": "E", "ı": "i", "İ": "I", "ö": "o", "Ö": "O",
    "ü": "u", "Ü": "U", "ç": "c", "Ç": "C", "ş": "sh", "Ş": "Sh",
    "ğ": "g", "Ğ": "G",
}


def slugify(name: str) -> str:
    for src, dst in AZ_MAP.items():
        name = name.replace(src, dst)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return name or "recipe"


def build_prompt(recipe: dict) -> str:
    name = recipe.get("name") or recipe.get("title") or "yemek"
    description = recipe.get("description", "")
    ingredients = recipe.get("ingredients", [])
    if isinstance(ingredients, list):
        ing_text = ", ".join(str(i) for i in ingredients[:8])
    else:
        ing_text = str(ingredients)

    return (
        f"Professional food photography of {name}. "
        f"{description}. Key ingredients: {ing_text}. "
        "Top-down angle, clean plate, natural lighting, shallow depth of field, "
        "appetizing, realistic, high resolution, no text, no watermark."
    ).strip()


def make_client():
    if httpx is not None:
        timeout = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0)
        return replicate.Client(api_token=API_TOKEN, timeout=timeout)
    return replicate.Client(api_token=API_TOKEN)


def generate_image(client, prompt: str) -> bytes:
    last_err = None
    for attempt in range(1, 4):
        try:
            output = client.run(
                MODEL,
                input={
                    "prompt": prompt,
                    "aspect_ratio": "1:1",
                    "output_format": "png",
                },
            )
            result = output[0] if isinstance(output, list) else output
            image_url = str(result)

            if image_url.startswith("http"):
                with urllib.request.urlopen(image_url, timeout=60) as resp:
                    return resp.read()
            else:
                # bezi versiyalarda FileOutput obyekti birbasa bytes verir
                return result.read()
        except Exception as e:
            last_err = e
            print(f"    Cehd {attempt}/3 alinmadi ({e}), yeniden cehd edilir...")
            time.sleep(3)

    raise RuntimeError(f"Shekil yaradila bilmedi: {last_err}")


def main():
    if not os.path.exists(RECIPES_JSON_PATH):
        print(f"XETA: {RECIPES_JSON_PATH} tapilmadi.", file=sys.stderr)
        sys.exit(1)

    with open(RECIPES_JSON_PATH, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    recipe_list = recipes["recipes"] if isinstance(recipes, dict) and "recipes" in recipes else recipes

    missing = [r for r in recipe_list if not r.get("imageResource")]
    print(f"Cemi resept: {len(recipe_list)}, sekli olmayan: {len(missing)}")

    if not missing:
        print("Hamisinin sekli var, gorulecek is yoxdur.")
        return

    todo = missing[:MAX_IMAGES_PER_RUN]
    os.makedirs(IMAGES_DIR, exist_ok=True)

    client = None if DRY_RUN else make_client()
    changed = False

    for i, recipe in enumerate(todo, 1):
        name = recipe.get("name") or recipe.get("title") or f"recipe-{i}"
        slug = slugify(name)
        prompt = build_prompt(recipe)

        print(f"\n[{i}/{len(todo)}] {name}")
        print(f"  slug   : {slug}")
        print(f"  prompt : {prompt}")

        if DRY_RUN:
            print("  DRY_RUN=true -> API cagirilmadi, shekil yaradilmadi.")
            continue

        if not API_TOKEN:
            print("  XETA: REPLICATE_API_TOKEN tapilmadi, bu resept atlanir.", file=sys.stderr)
            continue

        try:
            image_bytes = generate_image(client, prompt)
        except Exception as e:
            print(f"  XETA: {e}", file=sys.stderr)
            continue

        file_path = os.path.join(IMAGES_DIR, f"{slug}.png")
        with open(file_path, "wb") as img_f:
            img_f.write(image_bytes)

        recipe["imageResource"] = (
            f"{IMAGE_BASE_URL}/{slug}.png" if IMAGE_BASE_URL else f"{IMAGES_DIR}/{slug}.png"
        )
        changed = True
        print(f"  OK -> {file_path}")

    if changed:
        with open(RECIPES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)
        print(f"\n{RECIPES_JSON_PATH} yenilendi.")
    else:
        print("\nHec bir dyishiklik edilmedi (DRY_RUN ve ya xetalar sebebinden).")


if __name__ == "__main__":
    main()
