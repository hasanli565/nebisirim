
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

# GitHub Actions-dan gəlir
VIDEO_COUNT = int(os.getenv("VIDEO_COUNT", "1"))

# .env yüklə
load_dotenv(BASE_DIR / ".env")

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini
GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image"

# Wan
REPLICATE_MODEL = "wan-video/wan-2.2-5b-fast"

GITHUB_VIDEO_BASE = (
    "https://raw.githubusercontent.com/"
    "hasanli565/nebisirim/main/videos/"
)


# ============================================================
# ENV YOXLA
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
# RECIPES.JSON
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
# HELPER
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

                result.append(
                    item.strip()
                )

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

                result.append(
                    str(item)
                )

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

        name = name.replace(
            old,
            new
        )

    name = re.sub(
        r"[^a-z0-9]+",
        "-",
        name
    )

    return name.strip("-")


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
# RESEPT MƏLUMATLARI
# ============================================================

def build_recipe_data(recipe):

    name = text_value(
        recipe.get("name")
    )

    description = text_value(
        recipe.get("description")
    )

    category = text_value(
        recipe.get("category")
    )

    ingredients = text_value(
        recipe.get("ingredients")
    )

    instructions = text_value(
        recipe.get("instructions")
    )

    prep_time = text_value(
        recipe.get("prepTime")
    )

    return f"""
Recipe name:
{name}

Category:
{category}

Description:
{description}

Preparation time:
{prep_time} minutes

Ingredients:
{ingredients}

Cooking instructions:
{instructions}
""".strip()


# ============================================================
# GEMINI PHOTO-REALISTIC IMAGE PROMPT
# ============================================================

def build_reference_prompt(recipe):

    recipe_data = build_recipe_data(
        recipe
    )

    return f"""
Create a completely new, highly photorealistic food photograph
of the exact dish described in the recipe below.

The attached image is ONLY a visual reference for identifying
the dish.

IMPORTANT:
Do NOT copy the cartoon, illustration, CGI, 3D-rendered,
digital-art or artificial style of the reference image.

Transform the dish into a REALISTIC PROFESSIONAL FOOD PHOTOGRAPH.

The final image must look like a real photograph taken
inside a real kitchen with a professional camera.

Keep the identity of the dish accurate.

The food must contain the correct ingredients from the recipe.

Use physically realistic food textures.

Use realistic:
- oil
- moisture
- sauce
- steam
- cooked surfaces
- shadows
- reflections
- utensils
- plates
- pans
- kitchen environment

Make the food look genuinely edible.

Photography style:

professional food photography,
real camera,
full-frame camera,
natural kitchen lighting,
realistic depth of field,
natural shadows,
realistic reflections,
subtle background blur,
realistic lens behavior,
natural imperfections,
high photographic realism.

Composition:

vertical 9:16,
dish clearly visible,
dish centered,
real kitchen environment,
clean but realistic composition.

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
perfect artificial surfaces,
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

    # --------------------------------------------------------
    # ORIGINAL IMAGE DOWNLOAD
    # --------------------------------------------------------

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

        content_type = (
            content_type.split(";")[0]
        )

    # --------------------------------------------------------
    # GEMINI INTERACTIONS API
    # --------------------------------------------------------

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

        "x-goog-api-key":
            GEMINI_API_KEY,

        "Content-Type":
            "application/json"
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

            return


    # --------------------------------------------------------
    # FALLBACK: STEPS
    # --------------------------------------------------------

   or step in data.get(
        "steps",
        []
    ):

        if step.get("type") != "model_output":
            continue

        for content in step.get(
            "content",
            []
        ):

            if content.get("type") != "image":
                continue

            image_data = content.get(
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

                return

    raise RuntimeError(
        "Gemini cavab verdi, amma image tapilmadi!"
    )
