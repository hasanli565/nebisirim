import os
import json
import re
import time
from pathlib import Path

import requests


# ============================================================
# SETTINGS
# ============================================================

RECIPES_JSON_PATH = os.getenv(
    "RECIPES_JSON_PATH",
    "recipes.json"
)

IMAGES_DIR = Path(
    os.getenv("IMAGES_DIR", "images")
)

IMAGE_BASE_URL = os.getenv(
    "IMAGE_BASE_URL",
    "https://raw.githubusercontent.com/hasanli565/nebisirim/main/images"
)

REPLICATE_API_TOKEN = os.getenv(
    "REPLICATE_API_TOKEN"
)

DRY_RUN = (
    os.getenv("DRY_RUN", "false").lower() == "true"
)

try:
    MAX_IMAGES = int(
        os.getenv("MAX_IMAGES_PER_RUN", "1")
    )
except ValueError:
    MAX_IMAGES = 1


REPLICATE_URL = (
    "https://api.replicate.com/v1/models/"
    "black-forest-labs/flux-schnell/predictions"
)


# ============================================================
# AZERBAIJANI -> ENGLISH FOOD TERMS
# ============================================================

FOOD_TRANSLATIONS = {
    "pomidor": "tomato",
    "pomidorlar": "tomatoes",

    "yumurta": "egg",
    "yumurtalar": "eggs",

    "soğan": "onion",
    "soğanlar": "onions",

    "sarımsaq": "garlic",

    "kərə yağı": "butter",
    "yağ": "oil",
    "bitki yağı": "vegetable oil",
    "zeytun yağı": "olive oil",

    "duz": "salt",
    "istiot": "black pepper",
    "qara istiot": "black pepper",
    "qırmızı istiot": "red pepper",

    "ət": "meat",
    "mal əti": "beef",
    "quzu əti": "lamb",
    "toyuq əti": "chicken",
    "toyuq": "chicken",

    "dana əti": "beef",
    "qiymə": "ground meat",
    "qiymə ət": "ground meat",

    "düyü": "rice",
    "basmati düyüsü": "basmati rice",

    "kartof": "potato",
    "kartoflar": "potatoes",

    "kök": "carrot",
    "yerkökü": "carrot",

    "badımcan": "eggplant",
    "bibər": "bell pepper",
    "yaşıl bibər": "green bell pepper",
    "qırmızı bibər": "red bell pepper",

    "xiyar": "cucumber",
    "kələm": "cabbage",

    "göyərti": "fresh herbs",
    "keşniş": "cilantro",
    "cəfəri": "parsley",
    "şüyüd": "dill",

    "nanə": "mint",

    "lobya": "beans",
    "noxud": "chickpeas",
    "mərcimək": "lentils",

    "un": "flour",
    "şəkər": "sugar",

    "süd": "milk",
    "qaymaq": "cream",
    "qatıq": "yogurt",

    "pendir": "cheese",

    "limon": "lemon",

    "qoz": "walnuts",
    "fındıq": "hazelnuts",
    "badam": "almonds",

    "ərik": "apricot",
    "alma": "apple",
    "armud": "pear",

    "kişmiş": "raisins",
    "zəfəran": "saffron",

    "lavaş": "lavash flatbread",
    "çörək": "bread",

    "vermişel": "vermicelli",

    "sirkə": "vinegar",
    "mayonez": "mayonnaise",

    "sous": "sauce",
}


# ============================================================
# DISH-SPECIFIC KNOWLEDGE
# ============================================================

DISH_KNOWLEDGE = {

    "pomidor yumurta": {
        "english": "Azerbaijani-style tomato and scrambled eggs",
        "description": (
            "eggs gently scrambled with cooked tomatoes and onion "
            "in butter, prepared as a traditional homemade breakfast"
        ),
        "appearance": (
            "soft scrambled eggs mixed with visible pieces of "
            "cooked red tomatoes and onion"
        ),
    },

    "pomidorlu yumurta": {
        "english": "Azerbaijani-style tomato and scrambled eggs",
        "description": (
            "eggs gently scrambled with cooked tomatoes and onion "
            "in butter, prepared as a traditional homemade breakfast"
        ),
        "appearance": (
            "soft scrambled eggs mixed with visible pieces of "
            "cooked red tomatoes and onion"
        ),
    },

    "plov": {
        "english": "traditional Azerbaijani rice pilaf",
        "description": (
            "fluffy long-grain rice prepared in the traditional "
            "Azerbaijani style"
        ),
        "appearance": (
            "separate fluffy grains of white and lightly golden rice"
        ),
    },

    "dolma": {
        "english": "traditional Azerbaijani dolma",
        "description": (
            "grape leaves or vegetables stuffed with seasoned "
            "ground meat and rice"
        ),
        "appearance": (
            "neatly rolled stuffed grape leaves or stuffed vegetables "
            "arranged closely together"
        ),
    },

    "düşbərə": {
        "english": "traditional Azerbaijani dushbara dumplings",
        "description": (
            "small handmade meat-filled dumplings served in a "
            "clear golden broth"
        ),
        "appearance": (
            "many tiny dumplings floating in a clear golden broth"
        ),
    },

    "kükü": {
        "english": "Azerbaijani herb kuku",
        "description": (
            "a thick savory egg dish made with eggs and fresh herbs"
        ),
        "appearance": (
            "thick golden-green herb and egg cake cut into wedges"
        ),
    },

    "qutab": {
        "english": "traditional Azerbaijani qutab",
        "description": (
            "thin Azerbaijani flatbread filled with meat, herbs, "
            "pumpkin or other traditional filling"
        ),
        "appearance": (
            "thin golden half-moon flatbreads with a lightly browned surface"
        ),
    },

    "piti": {
        "english": "traditional Azerbaijani piti stew",
        "description": (
            "slow-cooked lamb and chickpea stew prepared in a traditional "
            "clay pot"
        ),
        "appearance": (
            "rich golden broth with tender lamb and chickpeas in a clay pot"
        ),
    },

    "şorba": {
        "english": "traditional Azerbaijani soup",
        "description": (
            "a hearty homemade soup prepared with the listed ingredients"
        ),
        "appearance": (
            "hot flavorful broth with clearly visible pieces of the ingredients"
        ),
    },
}


# ============================================================
# SLUG
# ============================================================

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


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):
    if not text:
        return ""

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

    return text


# ============================================================
# INGREDIENTS
# ============================================================

def get_ingredients(recipe):
    ingredients = recipe.get("ingredients", [])

    if not ingredients:
        return []

    result = []

    for item in ingredients:

        if isinstance(item, str):
            result.append(item.strip())

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
                    result.append(
                        f"{name} {amount}"
                    )
                else:
                    result.append(name)

    return result


# ============================================================
# TRANSLATE INGREDIENT
# ============================================================

def translate_ingredient(text):

    original = str(text).strip()

    if not original:
        return ""

    normalized = normalize_text(original)

    # Əvvəl uzun ifadələri yoxla
    for az, en in sorted(
        FOOD_TRANSLATIONS.items(),
        key=lambda x: len(x[0]),
        reverse=True
    ):

        az_normalized = normalize_text(az)

        if normalized.startswith(
            az_normalized
        ):

            remainder = normalized[
                len(az_normalized):
            ].strip()

            if remainder:
                return f"{en} {remainder}"

            return en

    # Sadə söz axtarışı
    words = normalized.split()

    translated_words = []

    for word in words:

        translated = None

        for az, en in FOOD_TRANSLATIONS.items():

            if normalize_text(az) == word:
                translated = en
                break

        if translated:
            translated_words.append(
                translated
            )
        else:
            translated_words.append(word)

    return " ".join(translated_words)


def get_translated_ingredients(recipe):

    ingredients = get_ingredients(recipe)

    translated = []

    for ingredient in ingredients:

        value = translate_ingredient(
            ingredient
        )

        if value:
            translated.append(value)

    return translated


# ============================================================
# FIND DISH KNOWLEDGE
# ============================================================

def get_dish_knowledge(name):

    normalized = normalize_text(name)

    for dish_name, info in DISH_KNOWLEDGE.items():

        if normalize_text(dish_name) in normalized:

            return info

    return None


# ============================================================
# CREATE ENGLISH VISUAL PROMPT
# ============================================================

def create_prompt(recipe):

    name = recipe.get(
        "name",
        "Traditional food"
    )

    description = recipe.get(
        "description",
        ""
    )

    translated_ingredients = (
        get_translated_ingredients(recipe)
    )

    dish = get_dish_knowledge(name)

    # --------------------------------------------------------
    # Dish identity
    # --------------------------------------------------------

    if dish:

        dish_name = dish["english"]

        dish_description = (
            dish["description"]
        )

        appearance = (
            dish["appearance"]
        )

    else:

        dish_name = (
            f"traditional Azerbaijani {name}"
        )

        if description:
            dish_description = (
                f"{description}. "
                "Prepare it as an authentic homemade Azerbaijani dish."
            )
        else:
            dish_description = (
                "an authentic homemade Azerbaijani dish "
                "prepared using the listed ingredients"
            )

        appearance = (
            "the food should look naturally prepared, "
            "fresh, authentic and appetizing"
        )

    # --------------------------------------------------------
    # Ingredients
    # --------------------------------------------------------

    if translated_ingredients:

        ingredients_text = ", ".join(
            translated_ingredients
        )

    else:

        ingredients_text = (
            "the traditional ingredients of the dish"
        )

    # --------------------------------------------------------
    # Final prompt
    # --------------------------------------------------------

    prompt = f"""
Create a highly realistic professional food photograph of
{dish_name}.

Dish description:
{dish_description}.

Main ingredients:
{ingredients_text}.

Visual appearance:
{appearance}.

The food must look like a real freshly prepared Azerbaijani
homemade dish, with realistic ingredient proportions and natural
cooking textures.

Show the complete finished dish clearly.
Use an appropriate traditional serving plate or bowl.
Do not show raw ingredients separately.
Do not add ingredients that are not appropriate for the dish.

Professional food photography, appetizing presentation,
natural daylight, realistic colors, realistic food texture,
high detail, subtle shadows, shallow depth of field,
clean background, elegant composition,
slightly elevated three-quarter camera angle,
no people, no hands, no text, no labels, no watermark,
photorealistic, high resolution.
"""

    return " ".join(
        prompt.split()
    )


# ============================================================
# CREATE REPLICATE PREDICTION
# ============================================================

def create_prediction(prompt):

    headers = {
        "Authorization": (
            f"Bearer {REPLICATE_API_TOKEN}"
        ),
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


# ============================================================
# WAIT FOR REPLICATE
# ============================================================

def wait_for_prediction(prediction):

    prediction_url = (
        prediction["urls"]["get"]
    )

    headers = {
        "Authorization": (
            f"Bearer {REPLICATE_API_TOKEN}"
        )
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

        status = result.get(
            "status"
        )

        print(
            f"      [{i + 1}/60] Status: {status}"
        )

        if status == "succeeded":

            return result

        if status in (
            "failed",
            "canceled"
        ):

            raise Exception(
                "Prediction uğursuz oldu: "
                f"{result.get('error')}"
            )

    raise Exception(
        "Prediction 5 dəqiqə ərzində tamamlanmadı"
    )


# ============================================================
# GENERATE IMAGE
# ============================================================

def generate_image(
    prompt,
    output_path
):

    last_error = None

    for attempt in range(1, 6):

        try:

            print(
                f"    API sorğusu göndərilir "
                f"({attempt}/5)..."
            )

            prediction = (
                create_prediction(prompt)
            )

            print(
                "    Prediction yaradıldı: "
                f"{prediction.get('id')}"
            )

            print(
                "    Status: "
                f"{prediction.get('status')}"
            )

            result = (
                wait_for_prediction(
                    prediction
                )
            )

            output = result.get(
                "output"
            )

            if not output:

                raise Exception(
                    "Replicate output boşdur"
                )

            if isinstance(
                output,
                list
            ):

                image_url = output[0]

            else:

                image_url = output

            print(
                "    Şəkil URL-i alındı"
            )

            image_response = requests.get(
                image_url,
                timeout=120,
            )

            image_response.raise_for_status()

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            output_path.write_bytes(
                image_response.content
            )

            print(
                "    Şəkil yadda saxlanıldı: "
                f"{output_path}"
            )

            return True

        except Exception as e:

            last_error = e

            print(
                f"    Cəhd {attempt}/5 "
                f"uğursuz oldu: {e}"
            )

            if attempt < 5:

                wait_seconds = (
                    attempt * 5
                )

                print(
                    f"    {wait_seconds} "
                    "saniyə gözlənilir..."
                )

                time.sleep(
                    wait_seconds
                )

    print(
        "    XETA: Şəkil yaradıla bilmədi: "
        f"{last_error}"
    )

    return False


# ============================================================
# MAIN
# ============================================================

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

    if not isinstance(
        recipes,
        list
    ):

        raise Exception(
            "recipes.json siyahı formatında olmalıdır."
        )

    IMAGES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    missing = []

    for recipe in recipes:

        image_resource = (
            recipe.get(
                "imageResource"
            )
        )

        if not image_resource:

            missing.append(recipe)

    print()

    print(
        f"Cəmi resept: {len(recipes)}, "
        f"şəkli olmayan: {len(missing)}"
    )

    print(
        "Bu işə salınmada maksimum "
        f"{MAX_IMAGES} şəkil yaradılacaq."
    )

    # ========================================================
    # DRY RUN
    # ========================================================

    if DRY_RUN:

        print()
        print(
            "DRY RUN aktivdir."
        )

        print(
            "API çağırılmayacaq."
        )

        for recipe in missing[
            :MAX_IMAGES
        ]:

            name = recipe.get(
                "name",
                "Recipe"
            )

            slug = slugify(name)

            prompt = create_prompt(
                recipe
            )

            print()
            print(
                name
            )

            print(
                "slug:",
                slug
            )

            print(
                "prompt:",
                prompt
            )

        return

    # ========================================================
    # GENERATION
    # ========================================================

    successful = 0
    failed = 0

    total_to_generate = min(
        MAX_IMAGES,
        len(missing)
    )

    for index, recipe in enumerate(
        missing[:MAX_IMAGES],
        start=1
    ):

        name = recipe.get(
            "name",
            "Recipe"
        )

        slug = slugify(name)

        image_path = (
            IMAGES_DIR /
            f"{slug}.png"
        )

        print()
        print(
            f"[{index}/{total_to_generate}] "
            f"{name}"
        )

        print(
            f"  slug   : {slug}"
        )

        prompt = create_prompt(
            recipe
        )

        print(
            f"  prompt : {prompt}"
        )

        # ----------------------------------------------------
        # Existing image
        # ----------------------------------------------------

        if image_path.exists():

            print(
                "  Şəkil artıq mövcuddur, keçilir."
            )

            recipe["imageResource"] = (
                f"{IMAGE_BASE_URL}/"
                f"{slug}.png"
            )

            successful += 1

            continue

        # ----------------------------------------------------
        # Generate
        # ----------------------------------------------------

        ok = generate_image(
            prompt,
            image_path
        )

        if ok:

            recipe["imageResource"] = (
                f"{IMAGE_BASE_URL}/"
                f"{slug}.png"
            )

            successful += 1

            print(
                "  imageResource: "
                f"{recipe['imageResource']}"
            )

        else:

            failed += 1

    # ========================================================
    # SAVE JSON
    # ========================================================

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

    # ========================================================
    # RESULT
    # ========================================================

    remaining = sum(
        1
        for recipe in recipes
        if not recipe.get(
            "imageResource"
        )
    )

    print()
    print(
        "=============================="
    )

    print(
        "NƏTİCƏ"
    )

    print(
        "=============================="
    )

    print(
        f"Uğurlu: {successful}"
    )

    print(
        f"Xətalı: {failed}"
    )

    print(
        f"Qalan şəkilsiz: {remaining}"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
