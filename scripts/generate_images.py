import os
import json
import re
import time
from pathlib import Path

import requests
from google import genai
from google.genai import types


# ============================================================
# SETTINGS
# ============================================================

RECIPES_JSON_PATH = os.getenv("RECIPES_JSON_PATH", "recipes.json")

IMAGES_DIR = Path(os.getenv("IMAGES_DIR", "images"))

IMAGE_BASE_URL = os.getenv(
    "IMAGE_BASE_URL",
    "https://raw.githubusercontent.com/hasanli565/nebisirim/main/images"
)

VISUAL_CACHE_PATH = Path(
    os.getenv("VISUAL_CACHE_PATH", "visual_cache.json")
)

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

MAX_IMAGES_PER_RUN = int(
    os.getenv("MAX_IMAGES_PER_RUN", "1")
)

REFERENCE_IMAGES_PER_RECIPE = int(
    os.getenv("REFERENCE_IMAGES_PER_RECIPE", "5")
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash-lite"
)

REPLICATE_MODEL_URL = (
    "https://api.replicate.com/v1/models/"
    "black-forest-labs/flux-schnell/predictions"
)

BRAVE_IMAGE_SEARCH_URL = (
    "https://api.search.brave.com/res/v1/images/search"
)


# ============================================================
# TRANSLATIONS
# ============================================================

FOOD_TRANSLATIONS = {

    # Əsas ərzaqlar
    "pomidor": "tomato",
    "pomidorlar": "tomatoes",

    "yumurta": "egg",
    "yumurtalar": "eggs",

    "soğan": "onion",
    "soğanlar": "onions",

    "sarımsaq": "garlic",

    "kartof": "potato",
    "kartoflar": "potatoes",

    "kök": "carrot",
    "yerkökü": "carrot",

    "badımcan": "eggplant",
    "badımcanlar": "eggplants",

    "bibər": "bell pepper",
    "şirin bibər": "sweet bell pepper",
    "acı bibər": "chili pepper",

    "xiyar": "cucumber",

    "kələm": "cabbage",
    "gül kələmi": "cauliflower",
    "brokoli": "broccoli",

    "ispanaq": "spinach",

    "lobya": "beans",
    "noxud": "chickpeas",
    "mərcimək": "lentils",

    "düyü": "rice",
    "bulqur": "bulgur",

    "un": "flour",
    "çörək": "bread",

    "pendir": "cheese",
    "kəsmik": "curd cheese",
    "qatıq": "yogurt",
    "süd": "milk",
    "qaymaq": "cream",

    "kərə yağı": "butter",
    "yağ": "oil",
    "zeytun yağı": "olive oil",

    "toyuq": "chicken",
    "toyuq əti": "chicken",
    "toyuq filesi": "chicken breast",

    "mal əti": "beef",
    "quzu əti": "lamb",
    "qoyun əti": "lamb",

    "qiymə": "ground meat",
    "ət": "meat",

    "balıq": "fish",

    "qoz": "walnuts",
    "fındıq": "hazelnuts",
    "badam": "almonds",

    "kişmiş": "raisins",

    "göyərti": "fresh herbs",
    "keşniş": "cilantro",
    "cəfəri": "parsley",
    "şüyüd": "dill",
    "nanə": "mint",

    "duz": "salt",
    "istiot": "black pepper",
    "qara istiot": "black pepper",

    "şəkər": "sugar",
    "bal": "honey",

    "limon": "lemon",
    "limon suyu": "lemon juice",

    "sirkə": "vinegar",

    "darçın": "cinnamon",

    "şokolad": "chocolate",
    "kakao": "cocoa powder",

    "vanil": "vanilla",
    "vanilin": "vanilla",

    "qabartma tozu": "baking powder",
    "maya": "yeast",

    "su": "water",
}


# ============================================================
# DISH KNOWLEDGE
# ============================================================

DISH_KNOWLEDGE = {

    "pomidor yumurta": {
        "identity": "Azerbaijani-style eggs cooked with tomatoes",
        "appearance": (
            "soft scrambled or fried eggs mixed with visibly cooked "
            "red tomatoes"
        ),
        "serving": "served hot in a shallow pan or plate",
    },

    "pomidorlu yumurta": {
        "identity": "Azerbaijani-style eggs cooked with tomatoes",
        "appearance": (
            "yellow eggs surrounded by soft red tomato pieces "
            "with visible tomato juices"
        ),
        "serving": "served hot in a shallow pan",
    },

    "plov": {
        "identity": "traditional Azerbaijani rice pilaf",
        "appearance": (
            "fluffy separate white or golden rice grains, "
            "often accompanied by meat, dried fruits or chestnuts"
        ),
        "serving": "large traditional serving platter",
    },

    "dolma": {
        "identity": "Azerbaijani dolma",
        "appearance": (
            "small stuffed grape leaves or vegetables containing "
            "a rice and meat filling"
        ),
        "serving": "arranged closely on a serving plate",
    },

    "düşbərə": {
        "identity": "Azerbaijani dumpling soup",
        "appearance": (
            "many tiny meat-filled dumplings in a clear golden broth"
        ),
        "serving": "deep soup bowl",
    },

    "kükü": {
        "identity": "Azerbaijani herb and egg kuku",
        "appearance": (
            "thick round green-flecked egg dish with abundant fresh herbs"
        ),
        "serving": "cut into wedges on a plate",
    },

    "qutab": {
        "identity": "Azerbaijani qutab",
        "appearance": (
            "thin half-moon shaped flatbread filled with herbs, "
            "meat or other filling, lightly browned on the surface"
        ),
        "serving": "stacked or overlapping on a plate",
    },

    "piti": {
        "identity": "traditional Azerbaijani piti stew",
        "appearance": (
            "rich golden broth with chunks of lamb, chickpeas "
            "and vegetables"
        ),
        "serving": "traditional individual clay pot",
    },

    "şorba": {
        "identity": "traditional soup",
        "appearance": (
            "hot soup with clearly visible main ingredients "
            "and natural broth"
        ),
        "serving": "deep soup bowl",
    },

    "ləvəngi": {
        "identity": "Azerbaijani lavangi",
        "appearance": (
            "whole roasted chicken or fish stuffed with a dark "
            "walnut, onion and dried fruit mixture"
        ),
        "serving": "whole roasted centerpiece on a serving platter",
    },

    "lavangi": {
        "identity": "Azerbaijani lavangi",
        "appearance": (
            "whole roasted chicken or fish filled with walnut "
            "and onion stuffing"
        ),
        "serving": "whole roasted dish on a traditional platter",
    },
}


# ============================================================
# HELPERS
# ============================================================

def normalize_text(text):
    if not text:
        return ""

    text = str(text).lower().strip()

    replacements = {
        "ə": "e",
        "ı": "i",
        "ö": "o",
        "ü": "u",
        "ğ": "g",
        "ş": "s",
        "ç": "c",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def slugify(text):
    text = normalize_text(text)

    text = re.sub(
        r"[^a-z0-9]+",
        "-",
        text
    )

    return text.strip("-")


def translate_ingredient(text):
    if not text:
        return ""

    original = str(text).strip()
    normalized = original.lower()

    if normalized in FOOD_TRANSLATIONS:
        return FOOD_TRANSLATIONS[normalized]

    # Miqdarı ayırmağa çalışırıq
    words = normalized.split()

    translated_words = []

    for word in words:

        clean_word = re.sub(
            r"[^a-zəğıöüşç]",
            "",
            word
        )

        if clean_word in FOOD_TRANSLATIONS:
            translated_words.append(
                FOOD_TRANSLATIONS[clean_word]
            )
        else:
            translated_words.append(clean_word)

    result = " ".join(translated_words)

    return result


def get_ingredients(recipe):
    ingredients = recipe.get("ingredients", [])

    result = []

    if isinstance(ingredients, list):

        for item in ingredients:

            if isinstance(item, str):
                result.append(item)

            elif isinstance(item, dict):

                name = (
                    item.get("name")
                    or item.get("ingredient")
                    or item.get("ad")
                )

                if name:
                    result.append(str(name))

    return result


def get_translated_ingredients(recipe):

    ingredients = get_ingredients(recipe)

    translated = []

    for ingredient in ingredients:

        value = translate_ingredient(ingredient)

        if value:
            translated.append(value)

    return translated


def get_dish_knowledge(recipe):

    name = recipe.get("name", "")

    normalized = normalize_text(name)

    for dish_name, knowledge in DISH_KNOWLEDGE.items():

        if normalize_text(dish_name) in normalized:
            return knowledge

    return None


# ============================================================
# VISUAL CACHE
# ============================================================

def load_visual_cache():

    if not VISUAL_CACHE_PATH.exists():
        return {}

    try:

        with open(
            VISUAL_CACHE_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"Visual cache oxunmadi: {e}"
        )

        return {}


def save_visual_cache(cache):

    with open(
        VISUAL_CACHE_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            cache,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# BRAVE IMAGE SEARCH
# ============================================================

def brave_image_search(recipe):

    if not BRAVE_SEARCH_API_KEY:
        raise RuntimeError(
            "BRAVE_SEARCH_API_KEY tapilmadi."
        )

    name = recipe.get("name", "").strip()

    category = recipe.get(
        "category",
        ""
    )

    # Əvvəl Azərbaycan dilində axtarırıq.
    query = (
        f'"{name}" resepti yemek'
    )

    print(
        f"🔎 Brave Image Search: {query}"
    )

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token":
            BRAVE_SEARCH_API_KEY
    }

    params = {
        "q": query,
        "count": 20,
        "search_lang": "az",
        "country": "AZ",
        "safesearch": "strict",
    }

    response = requests.get(
        BRAVE_IMAGE_SEARCH_URL,
        headers=headers,
        params=params,
        timeout=30
    )

    if response.status_code != 200:

        print(
            "Brave AZ search failed:",
            response.status_code,
            response.text[:500]
        )

        # İngilis dilində ikinci cəhd
        query = (
            f'"{name}" Azerbaijani recipe food'
        )

        print(
            f"🔎 İkinci axtarış: {query}"
        )

        params = {
            "q": query,
            "count": 20,
            "search_lang": "en",
            "country": "ALL",
            "safesearch": "strict",
        }

        response = requests.get(
            BRAVE_IMAGE_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=30
        )

    response.raise_for_status()

    data = response.json()

    results = data.get(
        "results",
        []
    )

    references = []

    for item in results:

        title = item.get(
            "title",
            ""
        )

        thumbnail = item.get(
            "thumbnail",
            {}).get(
                "src"
            )

        properties = item.get(
            "properties",
            {}
        )

        original_url = properties.get(
            "url"
        )

        source_url = item.get(
            "url",
            ""
        )

        if not thumbnail:
            continue

        references.append({
            "title": title,
            "thumbnail": thumbnail,
            "image_url": original_url or thumbnail,
            "source_url": source_url,
        })

        if len(references) >= REFERENCE_IMAGES_PER_RECIPE:
            break

    return references


# ============================================================
# DOWNLOAD REFERENCE IMAGE
# ============================================================

def download_reference_image(
    url,
    index,
    recipe_slug
):

    try:

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent":
                    "Mozilla/5.0"
            }
        )

        if response.status_code != 200:
            return None

        content_type = response.headers.get(
            "Content-Type",
            ""
        )

        if (
            "image" not in content_type
            and not url.lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp")
            )
        ):
            return None

        data = response.content

        if len(data) < 5000:
            return None

        path = Path(
            f"/tmp/{recipe_slug}_ref_{index}.jpg"
        )

        with open(
            path,
            "wb"
        ) as f:

            f.write(data)

        return path

    except Exception as e:

        print(
            f"Şəkil yüklənmədi: {e}"
        )

        return None


# ============================================================
# GEMINI VISUAL ANALYSIS
# ============================================================

def analyze_reference_images(
    recipe,
    references
):

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY tapilmadi."
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    recipe_name = recipe.get(
        "name",
        ""
    )

    description = recipe.get(
        "description",
        ""
    )

    ingredients = get_ingredients(
        recipe
    )

    knowledge = get_dish_knowledge(
        recipe
    )

    prompt = f"""
You are an expert food photographer and food recognition AI.

We are generating a NEW original food photograph for an Azerbaijani
recipe.

Recipe name:
{recipe_name}

Description:
{description}

Ingredients:
{json.dumps(ingredients, ensure_ascii=False)}

Your task is NOT to copy any reference photograph.

Analyze the reference photographs and determine what the REAL finished
dish should visually look like.

Important:
- Ingredients such as salt, water and oil should NOT automatically appear
  as visible objects.
- Only ingredients that materially affect the final appearance should be
  emphasized.
- Identify the actual dish shape.
- Identify the dominant colors.
- Identify texture.
- Identify cooking method visible from the result.
- Identify serving style.
- Identify whether the dish should be whole, sliced, folded, stuffed,
  liquid, layered, etc.
- Pay special attention to traditional Azerbaijani appearance.
- Do not invent ingredients that are not present.
- The final image must look like a realistic professional food photograph.

If the reference images disagree, use the majority visual pattern and
the recipe information.

Return ONLY a concise visual description in English with these sections:

DISH IDENTITY:
APPEARANCE:
VISIBLE INGREDIENTS:
TEXTURE:
COLOR:
SHAPE:
SERVING:
CAMERA:
LIGHTING:
IMPORTANT DETAILS:

Do not mention the reference photographs in the final description.
"""

    if knowledge:

        prompt += f"""

Additional known information about this traditional dish:

Identity:
{knowledge["identity"]}

Expected appearance:
{knowledge["appearance"]}

Expected serving:
{knowledge["serving"]}
"""

    contents = [prompt]

    recipe_slug = slugify(
        recipe_name
    )

    temp_files = []

    for index, reference in enumerate(
        references
    ):

        image_url = (
            reference.get("thumbnail")
            or reference.get("image_url")
        )

        if not image_url:
            continue

        path = download_reference_image(
            image_url,
            index,
            recipe_slug
        )

        if not path:
            continue

        temp_files.append(path)

        try:

            with open(
                path,
                "rb"
            ) as f:

                image_bytes = f.read()

            contents.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg"
                )
            )

        except Exception as e:

            print(
                f"Gemini image əlavə edilə bilmədi: {e}"
            )

    if len(contents) == 1:

        print(
            "⚠️ Analiz üçün şəkil tapılmadı."
        )

        return None

    try:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents
        )

        text = response.text

        if not text:
            return None

        return text.strip()

    except Exception as e:

        print(
            f"Gemini visual analysis xətası: {e}"
        )

        return None


# ============================================================
# FLUX PROMPT
# ============================================================

def create_flux_prompt(
    recipe,
    visual_analysis
):

    name = recipe.get(
        "name",
        ""
    )

    description = recipe.get(
        "description",
        ""
    )

    ingredients = get_translated_ingredients(
        recipe
    )

    ingredient_text = ", ".join(
        ingredients[:15]
    )

    if visual_analysis:

        visual_part = visual_analysis

    else:

        knowledge = get_dish_knowledge(
            recipe
        )

        if knowledge:

            visual_part = f"""
DISH IDENTITY:
{knowledge["identity"]}

APPEARANCE:
{knowledge["appearance"]}

SERVING:
{knowledge["serving"]}
"""

        else:

            visual_part = f"""
The dish should visually correspond to the recipe:
{name}

Description:
{description}

Main ingredients:
{ingredient_text}
"""

    prompt = f"""
Create a completely NEW, photorealistic professional food photograph.

Dish:
{name}

Recipe description:
{description}

Main ingredients:
{ingredient_text}

VISUAL RECIPE ANALYSIS:
{visual_part}

STRICT VISUAL RULES:

- The food must be the exact finished dish described above.
- Do not turn the dish into a generic Western food.
- Preserve the traditional Azerbaijani appearance when applicable.
- Do not randomly add ingredients.
- Do not show raw ingredients unless they naturally belong in the finished dish.
- Salt, water and cooking oil should not appear as separate visible objects.
- The food must look cooked and ready to eat.
- Correct natural food proportions.
- Realistic textures.
- Realistic colors.
- No artificial plastic appearance.
- No illustration.
- No cartoon.
- No CGI look.
- No text.
- No labels.
- No watermark.
- No utensils covering the food.

PHOTOGRAPHY:

Professional restaurant-quality food photography,
natural realistic food texture,
soft natural window lighting,
subtle shadows,
realistic highlights,
45-degree camera angle unless the dish is better photographed from above,
shallow depth of field,
sharp focus on the food,
natural background,
realistic ceramic serving dish,
high detail,
photorealistic,
editorial food photography.

The image should look like a real photograph taken by a professional
food photographer, not an AI-generated illustration.
"""

    return prompt.strip()


# ============================================================
# REPLICATE
# ============================================================

def create_prediction(prompt):

    if not REPLICATE_API_TOKEN:

        raise RuntimeError(
            "REPLICATE_API_TOKEN tapilmadi."
        )

    headers = {
        "Authorization":
            f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type":
            "application/json",
    }

    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "output_format": "png",
            "output_quality": 95,
        }
    }

    response = requests.post(
        REPLICATE_MODEL_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    return response.json()


def wait_for_prediction(
    prediction_id,
    max_wait=180
):

    headers = {
        "Authorization":
            f"Bearer {REPLICATE_API_TOKEN}"
    }

    url = (
        f"https://api.replicate.com/v1/predictions/"
        f"{prediction_id}"
    )

    start = time.time()

    while time.time() - start < max_wait:

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        status = data.get(
            "status"
        )

        print(
            f"   FLUX status: {status}"
        )

        if status == "succeeded":
            return data

        if status in (
            "failed",
            "canceled"
        ):

            print(
                "FLUX error:",
                data.get("error")
            )

            return None

        time.sleep(3)

    print(
        "⚠️ FLUX timeout."
    )

    return None


def generate_image(
    prompt,
    retries=3
):

    for attempt in range(
        1,
        retries + 1
    ):

        try:

            print(
                f"🖼️ FLUX cəhd {attempt}/{retries}"
            )

            prediction = create_prediction(
                prompt
            )

            result = wait_for_prediction(
                prediction["id"]
            )

            if result:

                output = result.get(
                    "output"
                )

                if isinstance(
                    output,
                    list
                ):

                    return output[0]

                if isinstance(
                    output,
                    str
                ):

                    return output

        except Exception as e:

            print(
                f"FLUX xətası: {e}"
            )

            if attempt < retries:
                time.sleep(5)

    return None


# ============================================================
# SAVE GENERATED IMAGE
# ============================================================

def save_generated_image(
    image_url,
    image_path
):

    response = requests.get(
        image_url,
        timeout=60
    )

    response.raise_for_status()

    with open(
        image_path,
        "wb"
    ) as f:

        f.write(
            response.content
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("NƏ BİŞİRİM? — SMART RECIPE IMAGE GENERATOR")
    print("=" * 60)
    print()

    IMAGES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # LOAD RECIPES
    # --------------------------------------------------------

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

        raise RuntimeError(
            "recipes.json list formatında deyil."
        )

    print(
        f"📚 Cəmi resept: {len(recipes)}"
    )

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    visual_cache = load_visual_cache()

    print(
        f"🧠 Visual cache: {len(visual_cache)} resept"
    )

    # --------------------------------------------------------
    # FIND MISSING IMAGES
    # --------------------------------------------------------

    missing = []

    for recipe in recipes:

        name = recipe.get(
            "name",
            ""
        ).strip()

        if not name:
            continue

        image_resource = recipe.get(
            "imageResource"
        )

        if image_resource:
            continue

        missing.append(
            recipe
        )

    print(
        f"🖼️ Şəkilsiz resept: {len(missing)}"
    )

    if not missing:

        print(
            "✅ Bütün reseptlərin şəkli var."
        )

        return

    # --------------------------------------------------------
    # PROCESS
    # --------------------------------------------------------

    processed = 0

    for recipe in missing:

        if processed >= MAX_IMAGES_PER_RUN:
            break

        name = recipe.get(
            "name",
            ""
        ).strip()

        slug = slugify(
            name
        )

        image_filename = (
            f"{slug}.png"
        )

        image_path = (
            IMAGES_DIR /
            image_filename
        )

        image_url = (
            f"{IMAGE_BASE_URL}/"
            f"{image_filename}"
        )

        print()
        print("-" * 60)
        print(
            f"🍽️ RESEPT: {name}"
        )
        print("-" * 60)

        # ----------------------------------------------------
        # EXISTING LOCAL IMAGE
        # ----------------------------------------------------

        if image_path.exists():

            print(
                "📁 Lokal şəkil artıq var."
            )

            recipe[
                "imageResource"
            ] = image_url

            processed += 1

            continue

        # ----------------------------------------------------
        # CACHE KEY
        # ----------------------------------------------------

        cache_key = slug

        visual_analysis = visual_cache.get(
            cache_key
        )

        references = []

        # ----------------------------------------------------
        # WEB SEARCH
        # ----------------------------------------------------

        if visual_analysis:

            print(
                "🧠 Visual analysis cache-dən götürüldü."
            )

        else:

            if DRY_RUN:

                print(
                    "DRY RUN → Brave/Gemini işlədilmir."
                )

                visual_analysis = (
                    "Visual analysis would be generated here."
                )

            else:

                try:

                    references = brave_image_search(
                        recipe
                    )

                    print(
                        f"🔎 Tapılan reference şəkillər: "
                        f"{len(references)}"
                    )

                except Exception as e:

                    print(
                        f"⚠️ Brave Search xətası: {e}"
                    )

                    references = []

                # ------------------------------------------------
                # GEMINI
                # ------------------------------------------------

                if references:

                    visual_analysis = (
                        analyze_reference_images(
                            recipe,
                            references
                        )
                    )

                    if visual_analysis:

                        print()
                        print(
                            "🧠 Gemini visual analysis:"
                        )
                        print(
                            visual_analysis
                        )

                        visual_cache[
                            cache_key
                        ] = visual_analysis

                        save_visual_cache(
                            visual_cache
                        )

                    else:

                        print(
                            "⚠️ Gemini analiz vermədi."
                        )

        # ----------------------------------------------------
        # CREATE FLUX PROMPT
        # ----------------------------------------------------

        prompt = create_flux_prompt(
            recipe,
            visual_analysis
        )

        print()
        print(
            "🎨 FLUX PROMPT:"
        )
        print(prompt)

        # ----------------------------------------------------
        # DRY RUN
        # ----------------------------------------------------

        if DRY_RUN:

            print()
            print(
                "✅ DRY RUN tamamlandı."
            )

            processed += 1
            continue

        # ----------------------------------------------------
        # GENERATE
        # ----------------------------------------------------

        generated_url = generate_image(
            prompt
        )

        if not generated_url:

            print(
                "❌ Şəkil yaradılmadı."
            )

            continue

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        try:

            save_generated_image(
                generated_url,
                image_path
            )

        except Exception as e:

            print(
                f"❌ Şəkil yadda saxlanmadı: {e}"
            )

            continue

        # ----------------------------------------------------
        # UPDATE JSON
        # ----------------------------------------------------

        recipe[
            "imageResource"
        ] = image_url

        print()
        print(
            f"✅ Şəkil hazırdır: {image_filename}"
        )

        print(
            f"🔗 {image_url}"
        )

        processed += 1

        # API-lərə çox sürətli yüklənməmək üçün
        time.sleep(2)

    # --------------------------------------------------------
    # SAVE RECIPES
    # --------------------------------------------------------

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

    print()
    print("=" * 60)
    print(
        f"✅ Bu run-da hazırlanan şəkil: {processed}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
