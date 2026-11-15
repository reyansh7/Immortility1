"""Extracts the face-only rigged head from source/ultron.glb.

blender -b --factory-startup --python assets/blender/extract_face.py -- \
    source/ultron.glb out.glb

Keeps the head shell and the eye/mouth glow mesh, drops the body, neck, chest
core, reference duplicate and helper sphere, prunes the armature down to the
facial bones (jaw, lips, mouth corners, eyeballs, eyelids, brows), renames them
to stable ASCII names, recentres the head at the origin with a height of 2
units and rebuilds clean PBR materials (gunmetal albedo, roughness/metal map, normal
map, red emissive lines, solid emissive eyes) from the embedded atlas.
Blender front is -Y, which glTF exports as +Z (towards a default camera).
"""

import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1 :]
SRC, OUT = args[0], args[-1]
HEIGHT = 2.0

RENAME = {
    "head neck upper": "Head",
    "head jaw": "Jaw",
    "head lip lower left": "LipLowerL",
    "head lip lower right": "LipLowerR",
    "head lip upper left": "LipUpperL",
    "head lip upper right": "LipUpperR",
    "head mouth corner left": "MouthCornerL",
    "head mouth corner right": "MouthCornerR",
    "head eyeball left": "EyeL",
    "head eyeball right": "EyeR",
    "head eyelid upper left": "LidUpperL",
    "head eyelid upper right": "LidUpperR",
    "head eyelid lower left": "LidLowerL",
    "head eyelid lower right": "LidLowerR",
    "head eyebrow left 1": "BrowInnerL",
    "head eyebrow left 2": "BrowOuterL",
    "head eyebrow right 1": "BrowInnerR",
    "head eyebrow right 2": "BrowOuterR",
}
KEEP = set(RENAME)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
objects = bpy.data.objects
armature = objects["Armature"]
shell = objects["24_ultron_1_0_0"]
glow = objects["24_eyes_1_0_0"]
for name in ("27_ref_1_0_0", "38_emission_1_0_0", "Icosphere"):
    if name in objects:
        bpy.data.objects.remove(objects[name], do_unlink=True)
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)
if armature.animation_data:
    armature.animation_data_clear()


def keep_face(obj):
    """Deletes every vertex whose strongest weight belongs to a non-face bone."""
    names = {g.index: g.name for g in obj.vertex_groups}
    mesh = obj.data
    drop = set()
    for vertex in mesh.vertices:
        if not vertex.groups:
            drop.add(vertex.index)
            continue
        strongest = max(vertex.groups, key=lambda g: g.weight)
        if names[strongest.group] not in KEEP:
            drop.add(vertex.index)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in drop], context="VERTS")
    # Loose slivers left after the cut make dark specks; remove tiny islands.
    bm.to_mesh(mesh)
    bm.free()
    for group in list(obj.vertex_groups):
        if group.name not in KEEP:
            obj.vertex_groups.remove(group)
    bpy.context.view_layer.objects.active = obj
    for other in bpy.context.selected_objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    for group in obj.vertex_groups:
        group.name = RENAME[group.name]
    print("MESH", obj.name, len(mesh.vertices), "verts", len(mesh.polygons), "faces")


keep_face(shell)
keep_face(glow)
shell.name = shell.data.name = "FaceShell"
glow.name = glow.data.name = "FaceGlow"

bpy.context.view_layer.objects.active = armature
bpy.ops.object.mode_set(mode="EDIT")
bones = armature.data.edit_bones
for bone in list(bones):
    if bone.name not in KEEP:
        bones.remove(bone)
bones["head neck upper"].parent = None
for bone in bones:
    bone.name = RENAME[bone.name]
bpy.ops.object.mode_set(mode="OBJECT")
armature.name = "FaceRig"
armature.data.name = "FaceRig"

# Recentre and normalise: head centre at origin, height HEIGHT.
bpy.context.view_layer.update()
points = [shell.matrix_world @ Vector(c) for c in shell.bound_box]
lo = Vector([min(p[i] for p in points) for i in range(3)])
hi = Vector([max(p[i] for p in points) for i in range(3)])
centre = (lo + hi) / 2
scale = HEIGHT / (hi.z - lo.z)
fix = Matrix.Scale(scale, 4) @ Matrix.Translation(-centre)
armature.matrix_world = fix @ armature.matrix_world
bpy.context.view_layer.update()
for obj in bpy.context.selected_objects:
    obj.select_set(False)
for obj in (armature, shell, glow):
    obj.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.context.view_layer.update()
points = [shell.matrix_world @ Vector(c) for c in shell.bound_box]
print("BBOX", [round(min(p[i] for p in points), 3) for i in range(3)],
      [round(max(p[i] for p in points), 3) for i in range(3)])


import numpy as np  # noqa: E402  (bundled with Blender)


def pixels(img):
    data = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(data)
    return data.reshape(img.size[1], img.size[0], 4)


def new_image(name, rgba, non_color=False):
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=np.float32).ravel())
    img.pack()
    return img


# The embedded atlas is authoritative (the loose PNGs in textures/ are the same
# art stored with the opposite row order). Imported images are matched by name.
images = {img.name.split(".")[0]: img for img in bpy.data.images}
diff_px = pixels(images["Ultron_Prime_Diff"])
spec_px = pixels(images["Image"])
spec = spec_px[..., :3].mean(axis=2, keepdims=True)
red = np.clip((diff_px[..., 0:1] - diff_px[..., 1:2]) * 3.0, 0, 1)
# Dark-crimson look: blackened titanium plates, blood-crimson enamel where the
# source art was red. Kept dark so environment reflections, not the albedo,
# carry the highlights (bright albedo + emissive read as washed-out pink).
titanium = np.array([0.19, 0.2, 0.225], dtype=np.float32)
metal = (0.55 + np.clip(spec * 1.6, 0, 1) * 0.9) * titanium
crimson = np.array([0.2, 0.004, 0.012], dtype=np.float32)
base = metal * (1 - red) + crimson * red
albedo = new_image("FaceAlbedo", np.concatenate([base, np.ones_like(spec)], axis=2))
# Brushed metal: polished where the spec map is bright, satin in the recesses.
rough = np.clip(0.52 - spec * 0.32, 0.2, 0.55)
rough = rough * (1 - red) + 0.32 * red
orm = np.concatenate([np.ones_like(spec), rough, 1 - red * 0.55, np.ones_like(spec)], axis=2)
orm_img = new_image("FaceORM", orm, non_color=True)
norm = images["Ultron_Prime_Norm"]
norm.colorspace_settings.name = "Non-Color"
# Emission: the source map lights whole cheek plates, which reads as red paint
# rather than energy. Keep only thin seams: the red line art (edge-detected) plus
# a faint trace of the original map.
src_emis = pixels(images["Ultron_Prime_Emiss"])[..., :3].max(axis=2, keepdims=True)
if src_emis.shape[0] != red.shape[0]:
    k = red.shape[0] // src_emis.shape[0]
    src_emis = src_emis.repeat(k, axis=0).repeat(k, axis=1)
blur = red.copy()
for axis in (0, 1):
    blur = (np.roll(blur, 2, axis) + np.roll(blur, -2, axis) + blur * 2) / 4
seam = np.clip(red - blur * 0.92, 0, 1) ** 1.1
seam = np.clip(seam * 2.2 + src_emis * 0.06, 0, 1)
energy = np.array([1.0, 0.03, 0.06], dtype=np.float32)
emis = new_image("FaceSeams", np.concatenate([seam * energy, np.ones_like(spec)], axis=2))


def build(name, emission_strength, eye=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    if eye:
        bsdf.inputs["Base Color"].default_value = (0.05, 0.0, 0.004, 1)
        bsdf.inputs["Emission Color"].default_value = (1.0, 0.02, 0.045, 1)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.3
        bsdf.inputs["Emission Strength"].default_value = emission_strength
        return m
    t_base = nodes.new("ShaderNodeTexImage")
    t_base.image = albedo
    links.new(t_base.outputs["Color"], bsdf.inputs["Base Color"])
    t_orm = nodes.new("ShaderNodeTexImage")
    t_orm.image = orm_img
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(t_orm.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    t_norm = nodes.new("ShaderNodeTexImage")
    t_norm.image = norm
    nmap = nodes.new("ShaderNodeNormalMap")
    links.new(t_norm.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    t_emis = nodes.new("ShaderNodeTexImage")
    t_emis.image = emis
    links.new(t_emis.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = emission_strength
    return m


armor = build("Armor", 1.0)
eye = build("EyeGlow", 4.0, eye=True)
shell.data.materials.clear()
shell.data.materials.append(armor)
glow.data.materials.clear()
glow.data.materials.append(eye)
# The source used vertex colours only as a tint mixer; drop them.
for obj in (shell, glow):
    while obj.data.color_attributes:
        obj.data.color_attributes.remove(obj.data.color_attributes[0])

for img in list(bpy.data.images):
    if img.users == 0:
        bpy.data.images.remove(img)
for mat in list(bpy.data.materials):
    if mat.users == 0:
        bpy.data.materials.remove(mat)

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    export_skins=True,
    export_animations=False,
    export_morph=False,
    export_yup=True,
    export_apply=False,
    export_image_format="AUTO",
)
print("EXPORTED", OUT)
