import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import designs
man = json.load(open(sys.argv[1]))
print(designs.hood_tex(man, colorway=sys.argv[2], out=sys.argv[3]))
