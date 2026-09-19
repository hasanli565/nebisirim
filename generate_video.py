
import os
import re
import json
from pathlib import Path

import replicate
from dotenv import load_dotenv


# ============================================================
# AYARLAR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RECIPES_FILE = BASE_DIR / "recipes.json"
VIDEOS_DIR = BASE_DIR / "videos"
TEMP_DIR = BASE_DIR / "temp_video_reference"

VIDEO_COUNT = int(
    os.getenv("VIDEO_COUNT", "1")
)

# .env yüklə
load_dotenv(
    BASE_DIR / ".env"
)

REPLICATE_API_TOKEN = os.getenv(
    "REPLICATE_API_TOKEN"
)

# Replicate image model
IMAGE_MODEL = (
    "black-forest-labs/flux-kontext-pro"
)

# Replicate video model
VIDEO_MODEL = (
    "wan-video/wan-2.2-5b-fast"
)

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

os.environ[
    "REPLICATE_API_TOKEN"
] = REPLICATE_API_TOKEN


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


if not isinstance(
    recipes,
    list
):

    raise ValueError(
        "recipes.json list formatinda olmalidir!"
    )


# ============================================================
# TEXT HELPER
# ============================================================

def text_value(value):

    if value is None:
        return ""

    if isinstance(
        value,
        str
    ):

        return value.strip()

    if isinstance(
        value,
        list
    ):

        result = []

        for item in value:

            if isinstance(
                item,
                str
            ):

                result.append(
                    item.strip()
                )

            elif isinstance(
                item,
                dict
            ):

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

    if isinstance(
        value,
        dict
    ):

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
# FLUX IMAGE PROMPT
# ============================================================

def build_image_prompt(recipe):

    recipe_data = build_recipe_data(
        recipe
    )

    return f"""
Transform the provided food image into a
HIGHLY PHOTOREALISTIC REAL FOOD PHOTOGRAPH.

The original image is only a reference for identifying
the exact dish.

IMPORTANT:

Preserve the exact identity of the dish.

Preserve the correct ingredients.

Preserve the recognizable appearance of the recipe.

Do NOT preserve the original cartoon, illustration,
3D, CGI or artificial visual style.

Turn it into a real photograph of real food.

The food must look genuinely edible.

Use physically realistic:

food textures,
ingredients,
cooked surfaces,
oil,
sauce,
moisture,
steam,
natural imperfections,
real shadows,
real reflections.

Place the dish in a realistic professional kitchen
or food photography environment.

Professional food photography.

Real camera.
Full-frame camera.
Natural lighting.
Realistic depth of field.
Natural shadows.
Realistic lens behavior.
Subtle background blur.

Vertical 9:16 composition.

The dish should be clearly visible and centered.

No cartoon.
No anime.
No illustration.
No digital painting.
No CGI.
No 3D render.
No plastic food.
No fake food.
No synthetic food.
No fantasy food.
No glowing ingredients.
No unrealistic colors.
No oversaturation.
No text.
No letters.
No captions.
No logo.
No watermark.

RECIPE INFORMATION:

{recipe_data}
""".strip()


# ============================================================
# FLUX PHOTOREALISTIC IMAGE
# ============================================================

def create_realistic_image(
    replicate_client,
    recipe,
    original_image_url,
    output_path
):

    print()
    print(
        "[1/2] Replicate FLUX realistik "
        "reference yaradir..."
    )

    print(
        f"Original image: "
        f"{original_image_url}"
    )

    prompt = build_image_prompt(
        recipe
    )

    output = replicate_client.run(

        IMAGE_MODEL,

        input={

            "prompt":
                prompt,

            "input_image":
                original_image_url,

            "aspect_ratio":
                "9:16",

            "output_format":
                "jpg",

            "safety_tolerance":
                2
        }
    )

    # --------------------------------------------------------
    # FLUX OUTPUT
    # --------------------------------------------------------

    if output is None:

        raise RuntimeError(
            "FLUX bos output qaytardi!"
        )

    # FileOutput obyektidir
    if hasattr(
        output,
        "read"
    ):

        with open(
            output_path,
            "wb"
        ) as f:

            f.write(
                output.read()
            )

        return

    # URL kimi qayidarsa
    if isinstance(
        output,
        str
    ):

        import requests

        response = requests.get(
            output,
            timeout=300
        )

        response.raise_for_status()

        with open(
            output_path,
            "wb"
        ) as f:

            f.write(
                response.content
            )

        return

    # URL property
    if hasattr(
        output,
        "url"
    ):

        url = output.url

        if callable(url):

            url = url()

        import requests

        response = requests.get(
            url,
            timeout=300
        )

        response.raise_for_status()

        with open(
            output_path,
            "wb"
        ) as f:

            f.write(
                response.content
            )

        return

    # Bəzi versiyalarda list ola bilər
    if isinstance(
        output,
        list
    ):

        if not output:

            raise RuntimeError(
                "FLUX output siyahisi bosdur!"
            )

        first = output[0]

        if hasattr(
            first,
            "read"
        ):

            with open(
                output_path,
                "wb"
            ) as f:

                f.write(
                    first.read()
                )

            return

        if isinstance(
            first,
            str
        ):

            import requests

            response = requests.get(
                first,
                timeout=300
            )

            response.raise_for_status()

            with open(
                output_path,
                "wb"
            ) as f:

                f.write(
                    response.content
                )

            return

    raise RuntimeError(
        "FLUX output tipi taninmadi: "
        + str(type(output))
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
Create a REAL LIVE-ACTION COOKING VIDEO
for the recipe "{name}".

The input image is a photorealistic reference
of the exact dish.

The video must look like genuine footage
recorded by a professional food videographer
inside a real kitchen.

Show realistic cooking actions appropriate
for this exact recipe.

Follow the recipe logically.

DESCRIPTION:

{description}

INGREDIENTS:

{ingredients}

COOKING INSTRUCTIONS:

{instructions}

Show realistic actions such as:

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

ONLY when appropriate for this recipe.

Keep the dish visually consistent
with the reference image.

REAL FOOD.
REAL INGREDIENTS.
REAL KITCHEN.
REAL COOKING.
REAL HUMAN HANDS.
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

The result must look like real
professional cooking footage.

NOT an AI animation.

No cartoon.
No anime.
No illustration.
No CGI.
No 3D render.
No plastic food.
No synthetic textures.
No fantasy ingredients.
No glowing food.
No text.
No subtitles.
No captions.
No logo.
No watermark.
No narration.
No talking.

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
# VIDEO SAVE
# ============================================================

def save_video_output(
    output,
    destination
):

    if output is None:

        raise RuntimeError(
            "Wan bos output qaytardi!"
        )

    # FileOutput
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

    # URL
    if isinstance(
        output,
        str
    ):

        import requests

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

    # URL property
    if hasattr(
        output,
        "url"
    ):

        url = output.url

        if callable(url):
            url = url()

        import requests

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

    # List
    if isinstance(
        output,
        list
    ):

        if not output:

            raise RuntimeError(
                "Wan output siyahisi bosdur!"
            )

        save_video_output(
            output[0],
            destination
        )

        return

    raise RuntimeError(
        "Taninmayan Wan output tipi: "
        + str(type(output))
    )


# ============================================================
# NÖVBƏTİ RESEPT
# ============================================================

def find_next_recipe(
    attempted_indexes
):

    for index, recipe in enumerate(
        recipes
    ):

        # Bu run-da artıq sınanıbsa keç
        if index in attempted_indexes:
            continue

        name = text_value(
            recipe.get("name")
        )

        video_url = text_value(
            recipe.get("videoUrl")
        )

        image_url = text_value(
            recipe.get("imageResource")
        )

        # Video artıq varsa keç
        if video_url:
            continue

        # Ad yoxdursa keç
        if not name:
            continue

        # Şəkil yoxdursa keç
        if not image_url:
            continue

        return index, recipe

    return None, None


# ============================================================
# START
# ============================================================

print()
print("=" * 70)
print(
    "NƏ BİŞİRİM - REPLICATE IMAGE → VIDEO"
)
print("=" * 70)

print(
    f"Cəmi resept       : {len(recipes)}"
)

print(
    f"Bu run limiti     : {VIDEO_COUNT}"
)

print(
    "Image model       : "
    + IMAGE_MODEL
)

print(
    "Video model       : "
    + VIDEO_MODEL
)

print(
    "Pipeline           : "
    "Original → FLUX → Wan → MP4"
)

print("=" * 70)


# ============================================================
# REPLICATE CLIENT
# ============================================================

replicate_client = replicate.Client(
    api_token=REPLICATE_API_TOKEN
)


# ============================================================
# MAIN
# ============================================================

generated_count = 0

attempted_indexes = set()


while generated_count < VIDEO_COUNT:

    index, recipe = find_next_recipe(
        attempted_indexes
    )

    if recipe is None:

        print()
        print(
            "Yeni video gozleyen resept qalmadi."
        )

        break

    # Bu resepti bu run-da bir dəfə sınayırıq
    attempted_indexes.add(
        index
    )

    name = text_value(
        recipe.get("name")
    )

    original_image_url = text_value(
        recipe.get("imageResource")
    )

    slug = safe_filename(
        name
    )

    print()
    print("=" * 70)

    print(
        f"VIDEO {generated_count + 1}/{VIDEO_COUNT}"
    )

    print(
        f"Resept: {name}"
    )

    print("=" * 70)


    # ========================================================
    # FILENAME
    # ========================================================

    if not slug:

        print(
            "[SKIP] Fayl adi yaradıla bilmədi."
        )

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
        f"{slug}-realistic.jpg"
    )

    video_url = (
        GITHUB_VIDEO_BASE
        + video_filename
    )


    # ========================================================
    # VIDEO ARTIQ DISKDE VARSA
    # ========================================================

    if (
        video_path.exists()
        and
        video_path.stat().st_size > 0
    ):

        print(
            "[INFO] Video artıq mövcuddur."
        )

        recipe[
            "videoUrl"
        ] = video_url

        save_recipes()

        generated_count += 1

        continue


    # ========================================================
    # 1. FLUX
    # ========================================================

    try:

        create_realistic_image(

            replicate_client,

            recipe,

            original_image_url,

            reference_path
        )

    except Exception as error:

        print()
        print(
            "[ERROR] FLUX realistik şəkil yarada bilmədi!"
        )

        print(
            str(error)
        )

        print(
            "[INFO] Bu resept keçilir."
        )

        continue


    # ========================================================
    # REFERENCE CHECK
    # ========================================================

    if (
        not reference_path.exists()
        or
        reference_path.stat().st_size == 0
    ):

        print(
            "[ERROR] FLUX şəkli boşdur!"
        )

        continue


    print()
    print(
        "[OK] Realistik reference hazırdır."
    )

    print(
        f"Reference size: "
        f"{reference_path.stat().st_size / 1024:.1f} KB"
    )


    # ========================================================
    # 2. WAN
    # ========================================================

    prompt = build_video_prompt(
        recipe
    )

    negative_prompt = (
        build_negative_prompt()
    )


    print()
    print(
        "[2/2] Wan video yaradır..."
    )


    try:

        # Local realistik şəkli Wan-a ver
        with open(
            reference_path,
            "rb"
        ) as image_file:

            output = replicate_client.run(

                VIDEO_MODEL,

                input={

                    "image":
                        image_file,

                    "prompt":
                        prompt,

                    "negative_prompt":
                        negative_prompt,

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
            "[ERROR] Wan video yarada bilmədi!"
        )

        print(
            str(error)
        )

        continue


    # ========================================================
    # VIDEO SAVE
    # ========================================================

    try:

        save_video_output(
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
            "[ERROR] Video faylı boşdur!"
        )

        continue


    # ========================================================
    # JSON UPDATE
    # ========================================================

    recipe[
        "videoUrl"
    ] = video_url

    save_recipes()

    generated_count += 1


    # ========================================================
    # SUCCESS
    # ========================================================

    print()
    print("=" * 70)
    print(
        "[SUCCESS] VIDEO HAZIRDIR"
    )
    print("=" * 70)

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

    print("=" * 70)


    # ========================================================
    # TEMP IMAGE SIL
    # ========================================================

    try:

        if reference_path.exists():

            reference_path.unlink()

    except Exception:
        pass


# ============================================================
# TEMP TƏMİZLƏ
# ============================================================

for file in TEMP_DIR.glob(
    "*-realistic.jpg"
):

    try:

        file.unlink()

    except Exception:
        pass


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 70)
print(
    "İŞ BİTDİ"
)
print("=" * 70)

print(
    f"Uğurlu yeni video : {generated_count}"
)

print(
    f"Run limiti        : {VIDEO_COUNT}"
)

print("=" * 70)
