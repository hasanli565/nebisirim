#!/usr/bin/env python3
"""
recipes.json faylini oxuyur, imageResource sahesi bos olan reseptleri tapir,
her biri ucun prompt qurur ve OpenAI Image API ile shekil yaradir.

Env deyisenleri:
  OPENAI_API_KEY   - OpenAI API acari (GitHub Secrets-den gelir)
  RECIPES_JSON_PATH - recipes.json-un yolu (defolt: recipes.json)
  IMAGES_DIR        - shekillerin yazilacagi qovluq (defolt: images)
  IMAGE_BASE_URL    - imageResource-a yazilacaq public URL-in prefiksi
                       meselen: https://raw.githubusercontent.com/<user>/<repo>/main/images
  OPENAI_IMAGE_MODEL - istifade olunacaq model (defolt: gpt-image-1-mini)
  OPENAI_IMAGE_QUALITY - low | medium | high (defolt: medium)
  DRY_RUN            - "true" olsa, API-ye pul xerclemeden yalniz
                        hansi reseptlerin shekli olmadigini ve hansi
                        promptun qurulacagini ekrana yazir.
  MAX_IMAGES_PER_RUN - bir ishe salinmada max nece shekil yaradilsin (defolt: 20)
"""

import base64
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
import urllib.error

RECIPES_JSON_PATH = os.environ.get("RECIPES_JSON_PATH", "recipes.json")
IMAGES_DIR = os.environ.get("IMAGES_DIR", "images")
IMAGE_BASE_URL = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1-mini")
OPENAI_IMAGE_QUALITY = os.environ.get("OPENAI_IMAGE_QUALITY", "medium")
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

    prompt = (
        f"Professional food photography of {name}. "
        f"{description}. "
        f"Key ingredients: {ing_text}. "
        "Top-down or 45-degree angle shot, on a clean plate, natural lighting, "
        "shallow depth of field, appetizing, realistic, high resolution, no text, no watermark."
    )
    return prompt.strip()


def call_openai_image_api(prompt: str) -> bytes:
    url = "https://api.openai.com/v1/images/generations"
    payload = {
        "model": OPENAI_IMAGE_MODEL,
        "prompt": prompt,
        "size": "1024x1024",
        "quality": OPENAI_IMAGE_QUALITY,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI API xetasi ({e.code}): {err_body}") from e

    b64 = body["data"][0]["b64_json"]
    return base64.b64decode(b64)


def main():
    if not os.path.exists(RECIPES_JSON_PATH):
        print(f"XETA: {RECIPES_JSON_PATH} tapilmadi.", file=sys.stderr)
        sys.exit(1)

    with open(RECIPES_JSON_PATH, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    if isinstance(recipes, dict) and "recipes" in recipes:
        recipe_list = recipes["recipes"]
    else:
        recipe_list = recipes

    missing = [r for r in recipe_list if not r.get("imageResource")]
    print(f"Cemi resept: {len(recipe_list)}, sekli olmayan: {len(missing)}")

    if not missing:
        print("Hamisinin sekli var, gorulecek is yoxdur.")
        return

    todo = missing[:MAX_IMAGES_PER_RUN]
    os.makedirs(IMAGES_DIR, exist_ok=True)

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

        if not OPENAI_API_KEY:
            print("  XETA: OPENAI_API_KEY tapilmadi, bu resept atlanir.", file=sys.stderr)
            continue

        try:
            image_bytes = call_openai_image_api(prompt)
        except Exception as e:
            print(f"  XETA: {e}", file=sys.stderr)
            continue

        file_path = os.path.join(IMAGES_DIR, f"{slug}.png")
        with open(file_path, "wb") as img_f:
            img_f.write(image_bytes)

        if IMAGE_BASE_URL:
            recipe["imageResource"] = f"{IMAGE_BASE_URL}/{slug}.png"
        else:
            recipe["imageResource"] = f"{IMAGES_DIR}/{slug}.png"

        changed = True
        print(f"  OK -> {file_path}")
        time.sleep(1)  # sade rate-limit qorumasi

    if changed:
        with open(RECIPES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)
        print(f"\n{RECIPES_JSON_PATH} yenilendi.")
    else:
        print("\nHec bir dyishiklik edilmedi (DRY_RUN ve ya xetalar sebebinden).")


if __name__ == "__main__":
    main()
