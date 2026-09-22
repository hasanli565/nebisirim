from pathlib import Path
from PIL import Image
import shutil

# ==============================
# TƏNZİMLƏMƏLƏR
# ==============================

IMAGES_DIR = Path("images")
BACKUP_DIR = Path("images_backup_600")

MAX_SIZE = 360

# ==============================
# BACKUP
# ==============================

print("Backup yaradılır...")

if not BACKUP_DIR.exists():
    shutil.copytree(IMAGES_DIR, BACKUP_DIR)
    print(f"Backup yaradıldı: {BACKUP_DIR}")
else:
    print(f"Backup artıq mövcuddur: {BACKUP_DIR}")

print()

# ==============================
# EMAL
# ==============================

processed = 0
changed = 0

total_before = 0
total_after = 0

for path in IMAGES_DIR.glob("*.png"):

    try:
        before = path.stat().st_size
        total_before += before

        with Image.open(path) as img:

            original_width, original_height = img.size

            max_dimension = max(original_width, original_height)

            # Yalnız 540-dan böyükdürsə kiçilt
            if max_dimension > MAX_SIZE:

                scale = MAX_SIZE / max_dimension

                new_width = round(original_width * scale)
                new_height = round(original_height * scale)

                resized = img.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS
                )

                resized.save(
                    path,
                    format="PNG",
                    optimize=True,
                    compress_level=9
                )

                resized.close()

                final_width = new_width
                final_height = new_height

            else:
                # Onsuz da kiçikdirsə yenidən sıx
                img.save(
                    path,
                    format="PNG",
                    optimize=True,
                    compress_level=9
                )

                final_width = original_width
                final_height = original_height

        after = path.stat().st_size
        total_after += after

        processed += 1

        if (
            original_width > MAX_SIZE
            or original_height > MAX_SIZE
            or after < before
        ):
            changed += 1

        print(
            f"{path.name}: "
            f"{original_width}x{original_height} -> "
            f"{final_width}x{final_height} | "
            f"{before / 1024:.0f} KB -> "
            f"{after / 1024:.0f} KB"
        )

    except Exception as e:
        print(f"XETA: {path.name} -> {e}")


# ==============================
# NƏTİCƏ
# ==============================

print()
print("=" * 60)
print("BITDI")
print("=" * 60)

print(f"Emal olunan sekil: {processed}")
print(f"Deyisdirilen sekil: {changed}")

print(
    f"Evvelki hecm:      "
    f"{total_before / (1024 * 1024):.2f} MB"
)

print(
    f"Yeni hecm:         "
    f"{total_after / (1024 * 1024):.2f} MB"
)

if total_before > 0:

    saved = total_before - total_after
    percent = (saved / total_before) * 100

    print(
        f"Qenaet:            "
        f"{saved / (1024 * 1024):.2f} MB"
    )

    print(
        f"Azalma:            "
        f"{percent:.1f}%"
    )

print("=" * 60)
