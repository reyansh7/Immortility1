"""Renders review images of the exported head.

blender -b --factory-startup --python assets/blender/preview_head.py -- head.glb out_dir
"""

import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1 :]
glb, out = args[:2]
portrait = args[2] if len(args) > 2 else None
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {
    e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
} else "BLENDER_EEVEE"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
world = bpy.data.worlds.new("World")
scene.world = world
world.color = (0.004, 0.004, 0.006)
try:
    world.use_nodes = True
except AttributeError:
    pass
background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
background.inputs["Color"].default_value = (0.004, 0.004, 0.006, 1)
background.inputs["Strength"].default_value = 1.0


def light(name, kind, location, energy, color=(1, 1, 1), size=1.0):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == "AREA":
        data.size = size
    o = bpy.data.objects.new(name, data)
    o.location = location
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(o)


light("Key", "AREA", (2.2, -3.0, 2.4), 420, (0.9, 0.93, 1.0), 2.5)
light("Rim", "AREA", (-2.6, 1.8, 1.2), 260, (1.0, 0.12, 0.16), 2.0)
light("Fill", "AREA", (-1.8, -2.6, -0.6), 60, (0.7, 0.75, 0.85), 3.0)
light("Top", "AREA", (0, 0.5, 3.2), 140, (0.85, 0.9, 1.0), 2.0)

cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 70
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
for name, angle, height in (("front", 0, 0.0), ("three-quarter", 32, 0.25), ("side", 80, 0.1)):
    radians = math.radians(angle)
    cam.location = (math.sin(radians) * 5.6, -math.cos(radians) * 5.6, height)
    cam.rotation_euler = (Vector((0, 0, -0.15)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = f"{out}/head-{name}.png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", scene.render.filepath)
if portrait:
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.image_settings.color_mode = "RGBA"
    cam.location = (0, -5.2, -0.05)
    cam.rotation_euler = (Vector((0, 0, -0.12)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = portrait
    bpy.ops.render.render(write_still=True)
    print("RENDERED", portrait)
