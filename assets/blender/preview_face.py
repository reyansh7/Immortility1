"""Renders review images of the extracted face (Cycles CPU, headless-safe).

blender -b --factory-startup --python assets/blender/preview_face.py -- face.glb out_dir [samples] [portrait.png]
"""

import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1 :]
glb, out = args[:2]
samples = int(args[2]) if len(args) > 2 else 48
portrait = args[3] if len(args) > 3 else None
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 720
scene.render.film_transparent = False
# Khronos PBR Neutral keeps saturated reds red (AgX/Filmic push hot red toward
# pink-white, which is what made earlier previews look washed out). It matches
# three.js NeutralToneMapping used in the app.
for _view in ("Khronos PBR Neutral", "Filmic", "Standard"):
    try:
        scene.view_settings.view_transform = _view
        break
    except TypeError:
        continue
print("VIEW", scene.view_settings.view_transform)
scene.view_settings.exposure = -0.35
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.0035, 0.0022, 0.0028, 1)  # obsidian #09070A
bg.inputs["Strength"].default_value = 1.0


def light(name, kind, loc, energy, color, size=1.0):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == "AREA":
        data.size = size
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    direction = Vector((0, 0, 0)) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(obj)


# Same lighting language as the app: dim neutral key from above, crimson rims.
light("Key", "AREA", (1.6, -3.8, 3.2), 2400, (0.93, 0.94, 0.97), 5.0)
light("Top", "AREA", (0, -0.6, 4.2), 380, (0.9, 0.92, 0.96), 2.5)
light("Fill", "AREA", (-3.6, -3.0, -0.2), 140, (0.82, 0.85, 0.92), 3)
light("RimL", "AREA", (-2.8, 2.4, 1.0), 200, (1.0, 0.05, 0.09), 1.2)
light("RimR", "AREA", (2.8, 2.4, 0.4), 130, (1.0, 0.07, 0.11), 1.2)

for mat in bpy.data.materials:
    if mat.name.startswith("EyeGlow") and mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                node.inputs["Emission Strength"].default_value = 2.2

cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 70
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
for label, angle in (("front", 0), ("three-quarter", 35), ("side", 80)):
    a = math.radians(angle)
    cam.location = (7.2 * math.sin(a), -7.2 * math.cos(a), 0.15)
    direction = Vector((0, 0, 0)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = f"{out}/face-{label}.png"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", scene.render.filepath)

if portrait:
    # Transparent square portrait used by the 2D fallback and the brand mark.
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 512
    cam.location = (1.2, -7.0, 0.3)
    direction = Vector((0, 0, 0)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = 62
    scene.render.filepath = portrait
    bpy.ops.render.render(write_still=True)
    print("RENDERED", portrait)
