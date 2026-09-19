
import os
import re
import json
import base64
from pathlib import Path

import requests
import replicate
from dotenv import load_dotenv


# ============================================================
# AYARLAR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RECIPES_FILE = BASE_DIR / "recipes.json"
VIDEOS_DIR = BASE_DIR / "videos"
TEMP_DIR = BASE_DIR / "temp_video_reference"

VIDEO_COUNT = int(os.getenv("VIDEO_COUNT", "1"))

load_dotenv(BASE_DIR / ".env")

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image"
REPLICATE_MODEL = "wan-video/wan-2.2-5b-fast"

GITHUB_VIDEO_BASE = (
    "https://raw.githubusercontent.com/"
    "hasanli565/nebisirim/main/videos/"
)


# ============================================================
# ENV
# ============================================================

if not REPLICATE_API_TOKEN:
    raise RuntimeError(
        "REPLICATE_API_TOKEN tapilmadi!"
    )

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY tapilmadi!"
    )

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN


# ============================================================
# QOVLUQLAR
# ============================================================

VIDEOS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

TEMP_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# RECIPES
# ============================================================

if not RECIPES_FILE.exists():
    raise FileNotFoundError(
        "recipes.json tapilmadi!"
    )

with open(
    RECIPES_FILE,
    "r",
    encoding="utf-8"
) as f:
    recipes = json.load(f)

if not isinstance(recipes, list):
    raise ValueError(
        "recipes.json list formatinda olmalidir!"
    )


# ============================================================
# TEXT HELPER
# ============================================================

def text_value(value):

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):

        result = []

        for item in value:

            if isinstance(item, str):
                result.append(item.strip())

            elif isinstance(item, dict):

                parts = []

                for key, val in item.items():
                    parts.append(
                        f"{key}: {val}"
                    )

                result.append(
                    ", ".join(parts)
                )

            else:
                result.append(str(item))

        return "\n".join(
            x for x in result if x
        )

    if isinstance(value, dict):

        parts = []

        for key, val in value.items():
            parts.append(
                f"{key}: {val}"
            )

        return "\n".join(parts)

    return str(value)


# ============================================================
# SAFE FILENAME
# ============================================================

def safe_filename(name):

    name = name.lower().strip()

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
        name = name.replace(old, new)

    name = re.sub(
        r"[^a-z0-9]+",
        "-",
        name
    )

    return name.strip("-")


# ============================================================
# SAVE RECIPES
# ============================================================

def save_recipes():

    with open(
        RECIPES_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            recipes,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# RECIPE DATA
# ============================================================

def build_recipe_data(recipe):

    return f"""
Recipe name:
{text_value(recipe.get("name"))}

Category:
{text_value(recipe.get("category"))}

Description:
{text_value(recipe.get("description"))}

Preparation time:
{text_value(recipe.get("prepTime"))} minutes

Ingredients:
{text_value(recipe.get("ingredients"))}

Cooking instructions:
{text_value(recipe.get("instructions"))}
""".strip()


# ============================================================
# GEMINI PROMPT
# ============================================================

def build_reference_prompt(recipe):

    recipe_data = build_recipe_data(recipe)

    return f"""
Create a completely new, highly photorealistic food photograph
of the exact dish described below.

The attached image is only a visual reference for identifying
the dish.

Do NOT preserve its cartoon, illustration, CGI, 3D-rendered,
digital-art or artificial visual style.

Transform the dish into a real professional food photograph.

The final image must look like a real photograph taken
inside a real kitchen with a professional camera.

Keep the exact identity of the dish.

Keep the correct ingredients.

Use physically realistic food textures.

Use realistic:
oil,
moisture,
sauce,
steam,
cooked surfaces,
shadows,
reflections,
plates,
pans,
utensils
and kitchen environment.

Make the food genuinely edible and photographic.

Photography:

professional food photography,
real camera,
full-frame camera,
natural kitchen lighting,
realistic depth of field,
natural shadows,
realistic reflections,
subtle background blur,
realistic lens behavior,
natural imperfections.

Composition:

vertical 9:16,
dish clearly visible,
dish centered,
realistic kitchen environment.

ABSOLUTELY AVOID:

cartoon,
anime,
illustration,
digital painting,
3D render,
CGI,
plastic food,
fake food,
synthetic food,
fantasy food,
glowing ingredients,
unrealistic colors,
oversaturated colors,
artificial surfaces,
video game graphics,
watermark,
logo,
text,
letters,
captions.

RECIPE:

{recipe_data}
""".strip()


# ============================================================
# GEMINI IMAGE GENERATION
# ============================================================

def create_photorealistic_reference(
    recipe,
    original_image_url,
    output_path
):

    print()
    print(
        "[1/2] Gemini realistik reference yaradir..."
    )

    print(
        f"Original image: {original_image_url}"
    )

    response = requests.get(
        original_image_url,
        timeout=120
    )

    response.raise_for_status()

    image_bytes = response.content

    content_type = response.headers.get(
        "Content-Type",
        "image/png"
    )

    if ";" in content_type:
        content_type = content_type.split(";")[0]

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/interactions"
    )

    prompt = build_reference_prompt(
        recipe
    )

    payload = {
        "model": GEMINI_IMAGE_MODEL,

        "input": [
            {
                "type": "image",
                "data": base64.b64encode(
                    image_bytes
                ).decode("utf-8"),
                "mime_type": content_type
            },
            {
                "type": "text",
                "text": prompt
            }
        ],

        "response_format": {
            "type": "image",
            "aspect_ratio": "9:16",
            "image_size": "1K"
        }
    }

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }

    result = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=600
    )

    if not result.ok:

        raise RuntimeError(
            "Gemini API xetasi:\n"
            + result.text
        )

    data = result.json()

    # --------------------------------------------------------
    # OUTPUT IMAGE
    # --------------------------------------------------------

    output_image = data.get(
        "output_image"
    )

    if output_image:

        image_data = output_image.get(
            "data"
        )

        if image_data:

            with open(
                output_path,
                "wb"
            ) as f:

                f.write(
                    base64.b64decode(
                        image_data
                    )
                )

            return True

    # --------------------------------------------------------
    # FALLBACK STEPS
    # --------------------------------------------------------

    steps = data.get(
        "steps",
        []
    )

    for step in steps:

        content_list = step.get(
            "content",
            []
        )

        for content in content_list:

            if content.get("type") != "image":
                continue

            image_data = content.get(
                "data"
            )

            if not image_data:
                continue

            with open(
                output_path,
                "wb"
            ) as f:

                f.write(
                    base64.b64decode(
                        image_data
                    )
                )

            return True

    raise RuntimeError(
        "Gemini cavab verdi, amma image tapilmadi!"
    )


# ============================================================
# VIDEO PROMPT
# ============================================================

def build_video_prompt(recipe):

    name = text_value(
        recipe.get("name")
    )

    description = text_value(
        recipe.get("description")
    )

    ingredients = text_value(
        recipe.get("ingredients")
    )

    instructions = text_value(
        recipe.get("instructions")
    )

    return f"""
Create a REAL LIVE-ACTION cooking video of "{name}".

The input image is a photorealistic reference image
of the exact finished dish.

The video must look like genuine footage recorded
by a professional food videographer in a real kitchen.

Show realistic cooking actions appropriate for this recipe.

The cooking process must logically follow the recipe.

DESCRIPTION:

{description}

INGREDIENTS:

{ingredients}

COOKING INSTRUCTIONS:

{instructions}

Show only actions that make sense for this recipe.

Use realistic cooking actions such as:

cutting,
adding ingredients,
mixing,
stirring,
frying,
boiling,
simmering,
baking,
grilling,
plating

when appropriate.

Keep the food visually consistent with the reference image.

REAL FOOD.
REAL KITCHEN.
REAL INGREDIENTS.
REAL HUMAN HANDS.
REAL COOKING.
REAL STEAM.
REAL OIL.
REAL FOOD TEXTURES.

Professional food cinematography.

Natural kitchen lighting.
Natural shadows.
Realistic reflections.
Realistic depth of field.
Natural camera movement.
Realistic motion blur.

The result must look like a real cooking video
recorded with a professional camera.

NOT an AI animation.

No cartoon.
No anime.
No illustration.
No CGI.
No 3D render.
No plastic-looking food.
No synthetic textures.
No fantasy ingredients.
No glowing food.
No text.
No subtitles.
No captions.
No logo.
No watermark.
No talking.
No narration.

Vertical 9:16.
Photorealistic live-action cooking video.
""".strip()


# ============================================================
# NEGATIVE PROMPT
# ============================================================

def build_negative_prompt():

    return """
cartoon,
anime,
illustration,
digital painting,
3D render,
CGI,
computer graphics,
video game graphics,
plastic food,
fake food,
synthetic food,
unrealistic food,
fantasy food,
glowing food,
oversaturated food,
artificial surfaces,
deformed food,
melting food,
floating objects,
floating ingredients,
duplicate ingredients,
duplicate utensils,
deformed hands,
extra fingers,
missing fingers,
bad anatomy,
unrealistic cooking,
unrealistic physics,
jerky motion,
morphing,
flickering,
blurry,
low quality,
text,
letters,
subtitles,
captions,
logo,
watermark,
talking person,
face close-up
""".strip()


# ============================================================
# SAVE VIDEO
# ============================================================

def save_video_output(
    output,
    destination
):

    if hasattr(
        output,
        "read"
    ):

        with open(
            destination,
            "wb"
        ) as f:

            f.write(
                output.read()
            )

        return


    if isinstance(
        output,
        str
    ):

        response = requests.get(
            output,
            timeout=600
        )

        response.raise_for_status()

        with open(
            destination,
            "wb"
        ) as f:

            f.write(
                response.content
            )

        return


    if hasattr(
        output,
        "url"
    ):

        url = output.url

        if callable(url):
            url = url()

        response = requests.get(
            url,
            timeout=600
        )

        response.raise_for_status()

        with open(
            destination,
            "wb"
        ) as f:

            f.write(
                response.content
            )

        return


    if isinstance(
        output,
        list
    ):

        if not output:

            raise RuntimeError(
                "Replicate output bosdur!"
            )

        save_video_output(
            output[0],
            destination
        )

        return


    raise RuntimeError(
        f"Taninmayan output tipi: {type(output)}"
    )


# ============================================================
# NÖVBƏTİ RESEPTİ TAP
# ============================================================

def find_next_recipe():

    for index, recipe in enumerate(
        recipes
    ):

        name = text_value(
            recipe.get("name")
        )

        video_url = text_value(
            recipe.get("videoUrl")
        )

        image_url = text_value(
            recipe.get("imageResource")
        )

        if video_url:
            continue

        if not name:
            continue

        if not image_url:
            continue

        return index, recipe

    return None, None


# ============================================================
# START
# ============================================================

print()
print("=" * 65)
print(
    "NƏ BİŞİRİM - VIDEO GENERATOR"
)
print("=" * 65)

print(
    f"Cəmi resept : {len(recipes)}"
)

print(
    f"Bu run limiti : {VIDEO_COUNT}"
)

print(
    "Pipeline: Original → Gemini → Wan → MP4"
)

print("=" * 65)


# ============================================================
# REPLICATE CLIENT
# ============================================================

replicate_client = replicate.Client(
    api_token=REPLICATE_API_TOKEN
)


# ============================================================
# MAIN LOOP
# ============================================================

generated_count = 0


while generated_count < VIDEO_COUNT:

    index, recipe = find_next_recipe()

    if recipe is None:

        print()
        print(
            "Yeni video gozleyen resept yoxdur."
        )

        break

    name = text_value(
        recipe.get("name")
    )

    original_image_url = text_value(
        recipe.get("imageResource")
    )

    slug = safe_filename(
        name
    )

    if not slug:

        print(
            f"[SKIP] Fayl adi yaradıla bilmədi: {name}"
        )

        # Sonsuz dövr olmaması üçün
        # bu resepti müvəqqəti yaddaşda işarələ.
        recipe["_videoSkip"] = True

        continue


    video_filename = (
        f"{slug}.mp4"
    )

    video_path = (
        VIDEOS_DIR /
        video_filename
    )

    reference_path = (
        TEMP_DIR /
        f"{slug}-reference.png"
    )

    video_url = (
        GITHUB_VIDEO_BASE +
        video_filename
    )


    print()
    print("=" * 65)
    print(
        f"VIDEO {generated_count + 1}/{VIDEO_COUNT}"
    )
    print("=" * 65)

    print(
        f"Resept: {name}"
    )


    # ========================================================
    # VIDEO ARTIQ VARSA
    # ========================================================

    if (
        video_path.exists()
        and
        video_path.stat().st_size > 0
    ):

        print(
            "[INFO] Video fayli artiq movcuddur."
        )

        recipe["videoUrl"] = video_url

        save_recipes()

        generated_count += 1

        continue


    # ========================================================
    # GEMINI
    # ========================================================

    try:

        create_photorealistic_reference(
            recipe,
            original_image_url,
            reference_path
        )

    except Exception as error:

        print()
        print(
            "[ERROR] Gemini reference yarada bilmedi!"
        )

        print(
            str(error)
        )

        # videoUrl-a HEÇ NƏ yazmırıq
        # Resept növbəti run-da yenidən yoxlanacaq.

        continue


    if (
        not reference_path.exists()
        or
        reference_path.stat().st_size == 0
    ):

        print(
            "[ERROR] Gemini reference bosdur!"
        )

        continue


    print(
        "[OK] Realistik reference hazirdir."
    )

    print(
        f"Reference size: "
        f"{reference_path.stat().st_size / 1024:.1f} KB"
    )


    # ========================================================
    # WAN
    # ========================================================

    prompt = build_video_prompt(
        recipe
    )

    negative = build_negative_prompt()


    print()
    print(
        "[2/2] Wan video yaradir..."
    )


    try:

        with open(
            reference_path,
            "rb"
        ) as image_file:

            output = replicate_client.run(

                REPLICATE_MODEL,

                input={

                    "image":
                        image_file,

                    "prompt":
                        prompt,

                    "negative_prompt":
                        negative,

                    "num_frames":
                        81,

                    "resolution":
                        "480p",

                    "aspect_ratio":
                        "9:16",

                    "go_fast":
                        True,

                    "sample_shift":
                        12,

                    "frames_per_second":
                        16
                }
            )

    except Exception as error:

        print()
        print(
            "[ERROR] Wan video yarada bilmedi!"
        )

        print(
            str(error)
        )

        continue


    # ========================================================
    # SAVE VIDEO
    # ========================================================

    try:

        save_video_output(
            output,
            video_path
        )

    except Exception as error:

        print()
        print(
            "[ERROR] Video fayla yazilmadi!"
        )

        print(
            str(error)
        )

        if video_path.exists():

            try:
                video_path.unlink()
            except Exception:
                pass

        continue


    # ========================================================
    # VERIFY
    # ========================================================

    if (
        not video_path.exists()
        or
        video_path.stat().st_size == 0
    ):

        print(
            "[ERROR] Video fayli bosdur!"
        )

        continue


    # ========================================================
    # JSON UPDATE
    # ========================================================

    recipe["videoUrl"] = video_url

    save_recipes()

    generated_count += 1


    print()
    print("=" * 65)
    print(
        "[SUCCESS] VIDEO HAZIRDIR"
    )
    print("=" * 65)

    print(
        f"Resept : {name}"
    )

    print(
        f"Video  : videos/{video_filename}"
    )

    print(
        f"URL    : {video_url}"
    )

    print(
        f"Size   : "
        f"{video_path.stat().st_size / 1024 / 1024:.2f} MB"
    )

    print("=" * 65)


    # ========================================================
    # TEMP IMAGE SIL
    # ========================================================

    try:

        if reference_path.exists():
            reference_path.unlink()

    except Exception:
        pass


# ============================================================
# TEMP QOVLUQ TƏMİZLƏ
# ============================================================

for file in TEMP_DIR.glob(
    "*-reference.png"
):

    try:
        file.unlink()

    except Exception:
        pass


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 65)
print(
    "İŞ BİTDİ"
)
print("=" * 65)

print(
    f"Uğurlu yeni video: {generated_count}"
)

print(
    f"Run limiti       : {VIDEO_COUNT}"
)

print("=" * 65)
