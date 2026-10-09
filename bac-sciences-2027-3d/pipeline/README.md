# 3D pipeline (Blender `bpy` 5.2.2, Python 3.13)

Everything in this folder is reproducible. Run scripts with the venv that has `bpy`:

    python3 -m venv ~/venvs/bpyenv && ~/venvs/bpyenv/bin/pip install bpy==5.2.2 numpy pillow
    ~/venvs/bpyenv/bin/python pipeline/avatar.py

## Sources actually used (all fetched through the sandbox proxy)
| Asset | Source | Licence |
|---|---|---|
| Blender (as Python module) | https://pypi.org/project/bpy/ (bpy 5.2.2, cp313) — official Blender-built wheel | GPL-3.0-or-later (tool); our renders/outputs are ours |
| MakeHuman base mesh `base.obj`, `default.mhskel`, `default_weights.mhw` | https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/ | CC0 (MakeHuman team, released Sept 2020, stated in file header) |
| MakeHuman morph targets (`targets.npz`) | https://pypi.org/project/makehuman/1.3.2/ wheel (`makehuman/data/targets.npz`) | CC0 (targets.license inside the archive) |
| Studio HDRI (256x128 EXR) | https://www.npmjs.com/package/@pmndrs/assets 1.7.0 `hdri/studio.exr.js` | CC0-1.0 |
| Three.js, GLTFLoader, OrbitControls | https://www.npmjs.com/package/three | MIT |

Poly Haven, ambientCG, download.blender.org, MPFB2 release zips and the MakeHuman asset servers were **not reachable** from the build sandbox
(network proxy returned no response / 403). PBR cloth materials are therefore generated procedurally in Blender shader nodes.
