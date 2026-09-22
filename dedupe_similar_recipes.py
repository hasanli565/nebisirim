import json
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path

INPUT_FILE = Path("recipes.json")
BACKUP_FILE = Path("recipes.backup.json")
DUPLICATES_FILE = Path("duplicates.json")

# Oxşarlıq hədləri
NAME_THRESHOLD = 0.72
CONTENT_THRESHOLD = 0.78
VERY_SIMILAR_THRESHOLD = 0.88


def normalize_text(text):
    """Mətni müqayisə üçün standartlaşdırır."""
    if not text:
        return ""

    text = str(text).lower()

    # Azərbaycan hərflərini standartlaşdır
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

    # mötərizə və xüsusi işarələri sil
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # artıq boşluqları sil
    text = re.sub(r"\s+", " ", text).strip()

    return text


def words(text):
    return set(normalize_text(text).split())


def text_similarity(a, b):
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio()


def word_similarity(a, b):
    wa = words(a)
    wb = words(b)

    if not wa or not wb:
        return 0.0

    intersection = len(wa & wb)
    union = len(wa | wb)

    return intersection / union if union else 0.0


def ingredients_text(recipe):
    ingredients = recipe.get("ingredients", [])

    result = []

    for item in ingredients:
        name = item.get("name", "")
        quantity = item.get("quantity", "")
        unit = item.get("unit", "")

        result.append(
            f"{name} {quantity} {unit}"
        )

    return " ".join(result)


def recipe_content(recipe):
    return " ".join([
        recipe.get("name", ""),
        recipe.get("description", ""),
        ingredients_text(recipe),
        recipe.get("instructions", "")
    ])


def is_same_recipe(recipe1, recipe2):
    name1 = recipe1.get("name", "")
    name2 = recipe2.get("name", "")

    desc1 = recipe1.get("description", "")
    desc2 = recipe2.get("description", "")

    instr1 = recipe1.get("instructions", "")
    instr2 = recipe2.get("instructions", "")

    ing1 = ingredients_text(recipe1)
    ing2 = ingredients_text(recipe2)

    # Ad oxşarlığı
    name_sim = text_similarity(name1, name2)
    name_word_sim = word_similarity(name1, name2)

    # Tərkib oxşarlığı
    ingredient_sim = max(
        text_similarity(ing1, ing2),
        word_similarity(ing1, ing2)
    )

    # Təlimat oxşarlığı
    instruction_sim = text_similarity(instr1, instr2)

    # Təsvir oxşarlığı
    description_sim = text_similarity(desc1, desc2)

    # Çox güclü uyğunluq
    if name_sim >= VERY_SIMILAR_THRESHOLD:
        if ingredient_sim >= 0.65 or instruction_sim >= 0.70:
            return True

    # Adlar çox oxşardırsa və tərkib də oxşardırsa
    if name_sim >= NAME_THRESHOLD or name_word_sim >= NAME_THRESHOLD:
        if ingredient_sim >= CONTENT_THRESHOLD:
            return True

        if instruction_sim >= CONTENT_THRESHOLD:
            return True

    # Ad bir az fərqli olsa da bütün məzmun demək olar eynidirsə
    content1 = recipe_content(recipe1)
    content2 = recipe_content(recipe2)

    overall_sim = text_similarity(content1, content2)

    if overall_sim >= VERY_SIMILAR_THRESHOLD:
        return True

    # Ad fərqlidir, amma tərkib + hazırlanma qaydası eynidir
    if ingredient_sim >= 0.90 and instruction_sim >= 0.80:
        return True

    return False


def recipe_score(recipe):
    """
    Eyni reseptlərdən hansını saxlamaq üçün keyfiyyət balı.
    Daha dolğun resepti saxlamağa çalışırıq.
    """

    score = 0

    name = recipe.get("name", "")
    description = recipe.get("description", "")
    instructions = recipe.get("instructions", "")
    ingredients = recipe.get("ingredients", [])

    score += min(len(name), 80)
    score += min(len(description), 200)
    score += min(len(instructions), 600)

    score += len(ingredients) * 20

    if recipe.get("imageResource"):
        score += 50

    if recipe.get("videoUrl"):
        score += 20

    return score


def main():

    if not INPUT_FILE.exists():
        print("XETA: recipes.json tapilmadi!")
        return

    print("recipes.json oxunur...")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    if not isinstance(recipes, list):
        print("XETA: JSON siyahı formatında deyil!")
        return

    print(f"Ilkin resept sayi: {len(recipes)}")

    # Backup
    shutil.copy2(INPUT_FILE, BACKUP_FILE)
    print(f"Backup yaradildi: {BACKUP_FILE}")

    kept = []
    duplicates = []

    total = len(recipes)

    for i, recipe in enumerate(recipes):

        is_duplicate = False
        duplicate_of = None

        for j, existing in enumerate(kept):

            if is_same_recipe(recipe, existing):

                is_duplicate = True
                duplicate_of = j
                break

        if is_duplicate:

            # Hansı daha dolğundursa onu saxla
            existing = kept[duplicate_of]

            current_score = recipe_score(recipe)
            existing_score = recipe_score(existing)

            if current_score > existing_score:

                duplicates.append({
                    "removed": existing,
                    "kept": recipe,
                    "reason": "Oxşar resept - daha dolğun versiya saxlanıldı"
                })

                kept[duplicate_of] = recipe

            else:

                duplicates.append({
                    "removed": recipe,
                    "kept": existing,
                    "reason": "Oxşar resept"
                })

        else:
            kept.append(recipe)

        if (i + 1) % 25 == 0 or i + 1 == total:
            print(f"Yoxlanildi: {i + 1}/{total}")

    # Əsas recipes.json
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            kept,
            f,
            ensure_ascii=False,
            indent=2
        )

    # Silinənlər
    with open(DUPLICATES_FILE, "w", encoding="utf-8") as f:
        json.dump(
            duplicates,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 50)
    print("HAZIRDIR")
    print("=" * 50)
    print(f"Ilkin resept sayi : {total}")
    print(f"Saxlanilan        : {len(kept)}")
    print(f"Silinen oxsar     : {len(duplicates)}")
    print(f"Backup             : {BACKUP_FILE}")
    print(f"Silinenler         : {DUPLICATES_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
