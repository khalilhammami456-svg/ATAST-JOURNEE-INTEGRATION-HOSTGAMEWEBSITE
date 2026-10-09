# Clothing Design - a pattern-based garment workflow for Blender.
#
#   2D pattern pieces  ->  arranged on the measured body  ->  sewn by cloth
#   sewing springs  ->  draped against the body  ->  welded, thickened, rigged.
bl_info = {
    "name": "Clothing Design",
    "author": "Marcello Morettoni",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Clothing  |  Workspace: Clothing Design",
    "description": "Draw 2D patterns, sew them into a garment and simulate it onto your character",
    "category": "Physics",
}

import importlib
import bpy

from . import props, avatar, patterns, library, build, sim, workspace, ops, ui

_MODULES = (props, avatar, patterns, library, build, sim, workspace, ops, ui)

if "_LOADED" in locals():
    for m in _MODULES:
        importlib.reload(m)
_LOADED = True


def register():
    props.register()
    ops.register()
    ui.register()
    workspace.register()


def unregister():
    workspace.unregister()
    ui.unregister()
    ops.unregister()
    props.unregister()
