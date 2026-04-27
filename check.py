import os, hashlib
from PIL import Image
from collections import defaultdict
from pathlib import Path

# ⬇ SIRF YE PATH APNA DAALO
root = Path(r"C:\Users\yasha\OneDrive\Desktop\yoga recognition")

IMG_EXTS = {".jpg", ".jpeg", ".png"}
CLASSES  = {"downdog", "goddess", "plank", "tree", "warrior"}

image_files = [f for f in root.rglob("*") if f.suffix.lower() in IMG_EXTS]
print(f"Total images: {len(image_files)}")

# Class counts
counts = defaultdict(lambda: defaultdict(int))
for fp in image_files:
    parts = [p.lower() for p in fp.parts]
    split = next((p for p in parts if p in {"train","test"}), "?")
    cls   = next((p for p in parts if p in CLASSES), "?")
    counts[split][cls] += 1

for split in counts:
    print(f"\n[{split.upper()}]")
    for cls, n in sorted(counts[split].items()):
        print(f"  {cls:<12} {n}")

# Imbalance
for split in counts:
    vals = list(counts[split].values())
    print(f"\n[{split}] Imbalance ratio: {max(vals)/min(vals):.2f}x")

# Duplicates
print("\nDuplicates check...")
hashes = defaultdict(list)
for fp in image_files:
    h = hashlib.md5(open(fp,"rb").read()).hexdigest()
    hashes[h].append(str(fp))
dups = {h:v for h,v in hashes.items() if len(v)>1}
print(f"Duplicate groups: {len(dups)}")

# Corrupt + zero size
corrupt, zero = [], []
for fp in image_files:
    if fp.stat().st_size == 0:
        zero.append(fp)
    else:
        try:
            Image.open(fp).verify()
        except:
            corrupt.append(fp)
print(f"Zero-size : {len(zero)}")
print(f"Corrupt   : {len(corrupt)}")