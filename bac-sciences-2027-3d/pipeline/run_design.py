import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import designs
man = json.load(open(sys.argv[1]))
name, colorway, out = sys.argv[2], sys.argv[3], sys.argv[4]
if len(sys.argv) > 5 and sys.argv[5] == "--flip":
    for k, v in man["pieces"].items():
        if any(k.endswith(f) for f in ("Back", "Sleeve_R")):
            v["flipx"] = True
t = time.time()
res = getattr(designs, name)(man, colorway=colorway, out=out)
print(res, round(time.time() - t, 1), "s")
