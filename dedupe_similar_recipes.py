import json
import re
import shutil
from pathlib import Path
from difflib import SequenceMatcher

INPUT_FILE = Path("recipes.json")
BACKUP_FILE = Path("recipes.backup.json")
DUPLICATES_FILE = Path("duplicates.json")
GROUPS_FILE = Path("similar_groups.json")


# ============================================================
# AYARLAR
# ============================================================

# Ərzaqların neçə faizi eyni olmalıdır
INGREDIENT_SIMILARITY = 0.65

# Adların minimum oxşarlığı
NAME_SIMILARITY = 0.55

# Çox güclü ad uyğunluğu
STRONG_NAME_SIMILARITY = 0.75

# 1-2 əlavə ərzağa icazə
MAX_EXTRA_INGREDIENTS = 2


# ============================================================
# NORMALİZASİYA
# ============================================================

def normalize(text):
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

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# SÖZLƏR
# ============================================================

STOP_WORDS = {
    "ve",
    "ile",
    "uchun",
    "ucun",
    "azerbaycan",
    "azerbaycan",
    "usulu",
    "usulda",
    "qaydasinda",
    "qaydasında",
    "ev",
    "evde",
    "evsayaqi",
    "klassik",
    "milli",
    "dadli",
    "lezzetli",
    "asan",
}


def word_set(text):
    text = normalize(text)

    result = set()

    for word in text.split():

        if len(word) <= 1:
            continue

        if word in STOP_WORDS:
            continue

        result.add(word)

    return result


# ============================================================
# ADDAKI AÇAR SÖZLƏR
# ============================================================

DISH_WORDS = {
    "levengi",
    "dolma",
    "plov",
    "kabab",
    "qutab",
    "dushbere",
    "dusbere",
    "sorba",
    "salat",
    "kotlet",
    "piti",
    "buglama",
    "qovurma",
    "kuku",
    "omlet",
    "piroq",
    "sirniyyat",
    "keks",
    "tort",
    "kurabiye",
    "pechenye",
    "shor",
    "ichki",
}


def dish_words(name):
    words = word_set(name)
    return words & DISH_WORDS


# ============================================================
# AD OXŞARLIĞI
# ============================================================

def name_similarity(name1, name2):

    a = normalize(name1)
    b = normalize(name2)

    if not a or not b:
        return 0

    direct = SequenceMatcher(None, a, b).ratio()

    wa = word_set(name1)
    wb = word_set(name2)

    if not wa or not wb:
        return direct

    common = len(wa & wb)
    union = len(wa | wb)

    jaccard = common / union if union else 0

    return max(direct, jaccard)


# ============================================================
# ƏRZAQLAR
# ============================================================

def ingredient_names(recipe):

    result = set()

    ingredients = recipe.get("ingredients", [])

    for item in ingredients:

        name = item.get("name", "")

        name = normalize(name)

        if not name:
            continue

        # Məsələn:
        # "2 ədəd soğan" kimi gələn halları təmizləmək
        name = re.sub(r"\d+", " ", name)
        name = re.sub(r"\s+", " ", name).strip()

        result.add(name)

    return result


# ============================================================
# ƏRZAQ OXŞARLIĞI
# ============================================================

def ingredient_similarity(recipe1, recipe2):

    a = ingredient_names(recipe1)
    b = ingredient_names(recipe2)

    if not a or not b:
        return 0, 0, 0

    common = a & b

    # kiçik dəstin neçə faizi böyük dəstdə var
    smaller = min(len(a), len(b))

    coverage = len(common) / smaller if smaller else 0

    # Jaccard
    union = a | b

    jaccard = len(common) / len(union) if union else 0

    extra = len(union) - len(common)

    return coverage, jaccard, extra


# ============================================================
# ƏRZAQ ADLARINI YAXIN SAYMA
# ============================================================

def ingredients_semantically_similar(a, b):

    if a == b:
        return True

    similarity = SequenceMatcher(None, a, b).ratio()

    if similarity >= 0.82:
        return True

    # bəzi sözlər bir-birinin variantıdır
    aliases = {
        ("lavaşana", "alca tursusu"),
        ("alca tursusu", "lavaşana"),
        ("duz", "qaya duzu"),
        ("yag", "kərə yagi"),
        ("bitki yagi", "yag"),
    }

    if (a, b) in aliases:
        return True

    return False


def smart_ingredient_similarity(recipe1, recipe2):

    a = ingredient_names(recipe1)
    b = ingredient_names(recipe2)

    if not a or not b:
        return 0, 0

    matched = 0

    for ingredient_a in a:

        found = False

        for ingredient_b in b:

            if ingredients_semantically_similar(
                ingredient_a,
                ingredient_b
            ):
                found = True
                break

        if found:
            matched += 1

    smaller = min(len(a), len(b))

    coverage = matched / smaller if smaller else 0

    return coverage, matched


# ============================================================
# RESEPTİN EYNİ OLUB-OLMAMASI
# ============================================================

def is_same_recipe(recipe1, recipe2):

    name1 = recipe1.get("name", "")
    name2 = recipe2.get("name", "")

    name_sim = name_similarity(name1, name2)

    ing_sim, matched = smart_ingredient_similarity(
        recipe1,
        recipe2
    )

    a = ingredient_names(recipe1)
    b = ingredient_names(recipe2)

    if not a or not b:
        return False

    total_difference = len(a | b) - matched

    # --------------------------------------------------------
    # 1. Ad çox oxşardır + ərzaqların böyük hissəsi eynidir
    # --------------------------------------------------------

    if name_sim >= NAME_SIMILARITY:

        if ing_sim >= INGREDIENT_SIMILARITY:

            if total_difference <= MAX_EXTRA_INGREDIENTS:
                return True

    # --------------------------------------------------------
    # 2. Ad çox güclü oxşardır
    # --------------------------------------------------------

    if name_sim >= STRONG_NAME_SIMILARITY:

        if ing_sim >= 0.60:

            if total_difference <= 3:
                return True

    # --------------------------------------------------------
    # 3. Eyni əsas yemək sözü
    # --------------------------------------------------------

    dishes1 = dish_words(name1)
    dishes2 = dish_words(name2)

    if dishes1 and dishes2 and dishes1 & dishes2:

        if ing_sim >= 0.75:

            if total_difference <= 3:
                return True

    return False


# ============================================================
# SAXLANACAQ RESEPTİ SEÇ
# ============================================================

def recipe_score(recipe):

    score = 0

    name = recipe.get("name", "")
    description = recipe.get("description", "")
    instructions = recipe.get("instructions", "")
    ingredients = recipe.get("ingredients", [])

    # Daha dolğun resept üstün olsun
    score += len(name)

    score += min(len(description), 300)

    score += min(len(instructions), 800)

    score += len(ingredients) * 25

    # Şəkilli resepti üstün tut
    if recipe.get("imageResource"):
        score += 100

    # Videolu resepti üstün tut
    if recipe.get("videoUrl"):
        score += 30

    return score


# ============================================================
# ƏSAS
# ============================================================

def main():

    if not INPUT_FILE.exists():

        print("XETA: recipes.json tapilmadi!")

        return

    print()
    print("=" * 60)
    print("RESEPT OXSARLIQ TEMIZLEME")
    print("=" * 60)
    print()

    # JSON oxu
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        recipes = json.load(f)

    if not isinstance(recipes, list):

        print("XETA: recipes.json siyahi formatinda deyil!")

        return

    total = len(recipes)

    print(f"Ilkin resept sayi: {total}")

    # Backup
    shutil.copy2(
        INPUT_FILE,
        BACKUP_FILE
    )

    print(f"Backup yaradildi: {BACKUP_FILE}")

    kept = []

    duplicates = []

    similar_groups = []

    processed = 0

    # ========================================================
    # RESEPTLƏRİ QRUPLA
    # ========================================================

    for recipe in recipes:

        processed += 1

        matched_index = None

        # Artıq saxlanılan reseptlərlə müqayisə
        for index, existing in enumerate(kept):

            if is_same_recipe(
                recipe,
                existing
            ):

                matched_index = index

                break

        # ====================================================
        # OXSAR TAPILDI
        # ====================================================

        if matched_index is not None:

            existing = kept[matched_index]

            score_new = recipe_score(recipe)
            score_old = recipe_score(existing)

            # Yeni resept daha dolğundursa onu saxla
            if score_new > score_old:

                duplicates.append({
                    "removed": existing,
                    "kept": recipe,
                    "reason": "Eyni esas resept, daha dolgun variant saxlanildi"
                })

                kept[matched_index] = recipe

            else:

                duplicates.append({
                    "removed": recipe,
                    "kept": existing,
                    "reason": "Eyni esas resept"
                })

        else:

            kept.append(recipe)

        if processed % 25 == 0 or processed == total:

            print(
                f"Yoxlanildi: {processed}/{total} | "
                f"Saxlanilib: {len(kept)} | "
                f"Oxsar: {len(duplicates)}"
            )

    # ========================================================
    # OXSAR QRUPLARI GÖSTƏR
    # ========================================================

    groups = {}

    for item in duplicates:

        kept_name = item["kept"].get(
            "name",
            ""
        )

        if kept_name not in groups:

            groups[kept_name] = []

        groups[kept_name].append(
            item["removed"]
        )

    for kept_name, removed_list in groups.items():

        group = {
            "kept": kept_name,
            "removed": [
                item.get("name", "")
                for item in removed_list
            ]
        }

        similar_groups.append(group)

    # ========================================================
    # recipes.json YAZ
    # ========================================================

    with open(
        INPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            kept,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # duplicates.json
    # ========================================================

    with open(
        DUPLICATES_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            duplicates,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # similar_groups.json
    # ========================================================

    with open(
        GROUPS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            similar_groups,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # NƏTİCƏ
    # ========================================================

    print()
    print("=" * 60)
    print("HAZIRDIR")
    print("=" * 60)

    print(f"Ilkin resept sayi : {total}")
    print(f"Saxlanilan        : {len(kept)}")
    print(f"Silinen oxsar     : {len(duplicates)}")
    print()

    print(f"Backup            : {BACKUP_FILE}")
    print(f"Silinenler        : {DUPLICATES_FILE}")
    print(f"Oxsar qruplar     : {GROUPS_FILE}")

    print("=" * 60)


if __name__ == "__main__":
    main()
