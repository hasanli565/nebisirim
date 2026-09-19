
import os
import re
import json
from pathlib import Path

import requests
import replicate
from dotenv import load_dotenv


# ============================================================
# SETTINGS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RECIPES_FILE = BASE_DIR / "recipes.json"
VIDEOS_DIR = BASE_DIR / "videos"

VIDEO_COUNT = int(os.getenv("VIDEO_COUNT", "1"))

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

MODEL = "wan-video/wan-2.2-5b-fast"

GITHUB_VIDEO_BASE = (
    "https://raw.githubusercontent.com/"
    "hasanli565/nebisirim/main/videos/"
)


# ============================================================
# LOAD .ENV
# ============================================================

load_dotenv(BASE_DIR / ".env")

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

if not REPLICATE_API_TOKEN:
    raise RuntimeError(
        "REPLICATE_API_TOKEN tapilmadi!"
    )

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN


# ============================================================
# CREATE VIDEOS DIRECTORY
# ============================================================

VIDEOS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD RECIPES
# ============================================================

if not RECIPES_FILE.exists():
    raise FileNotFoundError(
        f"recipes.json tapilmadi: {RECIPES_FILE}"
    )

with open(
    RECIPES_FILE,
    "r",
    encoding="utf-8"
) as f:

    recipes = json.load(f)


if not isinstance(recipes, list):
    raise ValueError(
        "recipes.json list formatinda olmalidir."
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def text_value(value):
    """
    Müxtəlif JSON strukturlarını prompt üçün mətnə çevirir.
    """

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
    """
    Azərbaycan hərflərini sadələşdirib
    təhlükəsiz fayl adı yaradır.
    """

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

    name = name.strip("-")

    return name


def save_recipes():
    """
    recipes.json-u saxlayır.
    """

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


def build_prompt(recipe):
    """
    Konkret resept üçün video promptu yaradır.
    """

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

    prompt = f"""
Create a realistic vertical cooking video specifically for this recipe.

RECIPE NAME:
{name}

CATEGORY:
{category}

DESCRIPTION:
{description}

PREPARATION TIME:
{prep_time} minutes

INGREDIENTS:
{ingredients}

COOKING INSTRUCTIONS:
{instructions}

IMPORTANT:

Use the provided recipe image as the visual reference for the dish.

The final dish must closely resemble the reference image.

The video must show the actual cooking process of this exact recipe,
following the ingredients and cooking instructions above.

Show the ingredients being prepared and added in a logical sequence.

Show realistic cooking actions such as cutting, mixing, stirring,
frying, boiling, baking or simmering only when appropriate for this recipe.

The cooking process must match the recipe.

Do not invent completely different ingredients or a different dish.

Maintain visual consistency throughout the entire video.

Show realistic food textures, realistic ingredients and natural cooking
movements.

Use a clean modern kitchen environment.

Use close-up food photography and natural camera movement.

Make the food look fresh, realistic and appetizing.

Vertical 9:16 format.

Short social-media style cooking video.

No talking people.
No narration.
No subtitles.
No captions.
No text.
No logo.
No watermark.

Photorealistic food.
Realistic hands.
Realistic utensils.
Realistic cooking.
Natural lighting.
Professional food video.
""".strip()

    return prompt


def negative_prompt():
    return """
cartoon,
anime,
illustration,
CGI,
unrealistic food,
wrong food,
wrong ingredients,
different dish,
deformed food,
melted food,
unrealistic cooking,
floating ingredients,
floating utensils,
duplicate objects,
deformed hands,
extra fingers,
missing fingers,
bad anatomy,
blurry,
low resolution,
distorted,
text,
subtitles,
captions,
logo,
watermark,
talking person,
face close-up
""".strip()


def save_output(output, destination):
    """
    Replicate output-unu MP4 faylı kimi saxlayır.
    """

    # FileOutput / file-like object
    if hasattr(output, "read"):

        data = output.read()

        with open(
            destination,
            "wb"
        ) as f:

            f.write(data)

        return


    # String URL
    if isinstance(output, str):

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


    # Object with URL
    if hasattr(output, "url"):

        url = output.url

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


    # List output
    if isinstance(output, list):

        if not output:
            raise RuntimeError(
                "Replicate boş output qaytardı."
            )

        save_output(
            output[0],
            destination
        )

        return


    raise RuntimeError(
        f"Tanınmayan Replicate output tipi: {type(output)}"
    )


# ============================================================
# FIND RECIPES WITHOUT VIDEO
# ============================================================

pending = []

for index, recipe in enumerate(recipes):

    video_url = text_value(
        recipe.get("videoUrl")
    )

    image_url = text_value(
        recipe.get("imageResource")
    )

    name = text_value(
        recipe.get("name")
    )

    # Video artıq varsa keç
    if video_url:
        continue

    # Ad yoxdursa keç
    if not name:
        print(
            "[SKIP] Resept adı yoxdur."
        )
        continue

    # Şəkil yoxdursa video yaratmaq mümkün deyil
    if not image_url:
        print(
            f"[SKIP] Reference image yoxdur: {name}"
        )
        continue

    pending.append(
        (index, recipe)
    )


# ============================================================
# INFO
# ============================================================

print()
print("=" * 60)
print("NƏ BİŞİRİM - RECIPE VIDEO GENERATOR")
print("=" * 60)

print(
    f"Cəmi resept: {len(recipes)}"
)

print(
    f"Video gözləyən: {len(pending)}"
)

print(
    f"Bu run üçün limit: {VIDEO_COUNT}"
)

print("=" * 60)


if not pending:

    print(
        "Yeni video yaradılacaq resept yoxdur."
    )

    raise SystemExit(0)


# ============================================================
# REPLICATE CLIENT
# ============================================================

client = replicate.Client(
    api_token=REPLICATE_API_TOKEN
)


# ============================================================
# GENERATE VIDEOS
# ============================================================

generated_count = 0


for index, recipe in pending:

    if generated_count >= VIDEO_COUNT:
        break


    # --------------------------------------------------------
    # RECIPE DATA
    # --------------------------------------------------------

    name = text_value(
        recipe.get("name")
    )

    image_url = text_value(
        recipe.get("imageResource")
    )

    slug = safe_filename(name)

    if not slug:

        print(
            f"[SKIP] Fayl adı yaradıla bilmədi: {name}"
        )

        continue


    filename = (
        f"{slug}.mp4"
    )

    video_path = (
        VIDEOS_DIR / filename
    )

    video_url = (
        GITHUB_VIDEO_BASE +
        filename
    )


    print()
    print("=" * 60)
    print(
        f"VIDEO {generated_count + 1}/{VIDEO_COUNT}"
    )
    print("=" * 60)

    print(
        f"Resept: {name}"
    )

    print(
        f"Reference image: {image_url}"
    )

    print(
        f"Output: videos/{filename}"
    )


    # --------------------------------------------------------
    # EXISTING LOCAL VIDEO
    # --------------------------------------------------------

    if (
        video_path.exists()
        and
        video_path.stat().st_size > 0
    ):

        print(
            "[INFO] Video artıq mövcuddur."
        )

        recipe["videoUrl"] = video_url

        save_recipes()

        print(
            "[OK] videoUrl əlavə edildi."
        )

        generated_count += 1

        continue


    # --------------------------------------------------------
    # BUILD RECIPE-SPECIFIC PROMPT
    # --------------------------------------------------------

    prompt = build_prompt(
        recipe
    )

    negative = negative_prompt()


    print(
        "[INFO] Resept prompta daxil edildi."
    )

    print(
        "[INFO] Reference image Replicate-ə göndərilir."
    )

    print(
        "[INFO] Video yaradılır..."
    )


    # --------------------------------------------------------
    # GENERATE
    # --------------------------------------------------------

    try:

        output = client.run(

            MODEL,

            input={

                # Mövcud yemək şəklini reference
                "image": image_url,

                # Konkret reseptə uyğun prompt
                "prompt": prompt,

                # Mənfi prompt
                "negative_prompt": negative,

                # 81 frame
                "num_frames": 81,

                # 480p
                "resolution": "480p",

                # Telefon üçün
                "aspect_ratio": "9:16",

                # Sürətli rejim
                "go_fast": True,

                # Model parametri
                "sample_shift": 12,

                # FPS
                "frames_per_second": 16,
            }
        )


    except Exception as error:

        print()
        print(
            "[ERROR] Replicate video yaratmadı!"
        )

        print(
            str(error)
        )

        print(
            "[INFO] Bu resept keçilir."
        )

        continue


    # --------------------------------------------------------
    # SAVE VIDEO
    # --------------------------------------------------------

    try:

        save_output(
            output,
            video_path
        )

    except Exception as error:

        print()
        print(
            "[ERROR] Video saxlanmadı!"
        )

        print(
            str(error)
        )

        # Yarımçıq fayl varsa sil
        if video_path.exists():

            try:
                video_path.unlink()
            except Exception:
                pass

        continue


    # --------------------------------------------------------
    # VERIFY FILE
    # --------------------------------------------------------

    if (
        not video_path.exists()
        or
        video_path.stat().st_size == 0
    ):

        print(
            "[ERROR] Video faylı boşdur."
        )

        continue


    # --------------------------------------------------------
    # UPDATE JSON
    # --------------------------------------------------------

    recipe["videoUrl"] = video_url

    save_recipes()


    generated_count += 1


    print()
    print(
        "[SUCCESS] Video hazırdır!"
    )

    print(
        f"Fayl: {video_path}"
    )

    print(
        f"URL: {video_url}"
    )

    print(
        f"Ölçü: {video_path.stat().st_size / 1024 / 1024:.2f} MB"
    )


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 60)
print("İŞ BİTDİ")
print("=" * 60)

print(
    f"Yeni yaradılan video: {generated_count}"
)

print(
    f"Limit: {VIDEO_COUNT}"
)

print("=" * 60)

