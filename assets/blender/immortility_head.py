"""Builds the original Immortility head and exports it as GLB.

blender -b --factory-startup --python assets/blender/immortility_head.py -- out.glb

Every surface is generated here: a sculpted skull field, a solid armor shell cut
into plates by boolean panel lines, raised titanium plates, recessed eyes, a
hinged jaw, a glowing inner core and neck rings. Blender front is -Y.
"""

import math
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = sys.argv[sys.argv.index("--") + 1]
SEAM = 0.014

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, color, metal, rough, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    return m


ARMOR = material("Armor", (0.018, 0.021, 0.029), 1.0, 0.34)
TITANIUM = material("Titanium", (0.27, 0.29, 0.34), 1.0, 0.24)
INNER = material("Inner", (0.006, 0.006, 0.008), 0.6, 0.55)
CORE = material("Core", (0.05, 0.002, 0.006), 0.2, 0.6, (0.64, 0.013, 0.036), 0.6)
EYE = material("Eye", (1.0, 0.03, 0.07), 0.0, 0.3, (1.0, 0.03, 0.07), 8.0)
GLOW = material("Glow", (0.64, 0.013, 0.036), 0.0, 0.4, (1.0, 0.03, 0.07), 4.0)


def shape(x, y, z):
    front = max(0.0, -y)
    ax = abs(x)
    X, Y, Z = x * 0.78, y * 0.92, z * (0.96 if z > 0 else 1.1)
    if z > 0:
        X *= 1 + 0.06 * z
    if z < 0:
        t = min(1.0, -z)
        X *= 1 - 0.5 * t**1.15
        if y > 0:
            Y *= 1 - 0.45 * t
    if y < 0:
        # A central ridge gives the face a V-shaped plan instead of a round one.
        Y *= 0.78 + 0.3 * max(0.0, 1 - ax / 0.72) ** 1.4
    if y > 0:
        blend = min(1.0, max(0.0, (z + 0.55) / 0.45))
        Y *= 1 + 0.2 * blend * blend * (3 - 2 * blend)
    if z > 0:
        Z += 0.03 * math.exp(-((x / 0.18) ** 2))
    brow = 0.2 + 0.24 * ax
    Y -= 0.08 * math.exp(-(((z - brow) / 0.06) ** 2)) * front * (1 - 0.4 * ax)
    Y += 0.09 * math.exp(-(((z - brow + 0.13) / 0.075) ** 2) - ((ax - 0.27) / 0.14) ** 2) * front
    Y -= 0.06 * math.exp(-((x / 0.06) ** 2) - ((z + 0.02) / 0.22) ** 2) * front
    Y += 0.07 * math.exp(-(((z + 0.38) / 0.12) ** 2) - ((ax - 0.36) / 0.12) ** 2) * front
    Y -= 0.06 * math.exp(-(((z + 0.86) / 0.12) ** 2) - (x / 0.18) ** 2) * front
    X += math.copysign(0.07, x) * math.exp(-(((z + 0.06) / 0.13) ** 2)) * min(1.0, front * 1.6)
    return Vector((X, Y, Z))


def skull(name, scale=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=112, ring_count=72, radius=1)
    o = bpy.context.active_object
    o.name = name
    bm = bmesh.new()
    bm.from_mesh(o.data)
    for v in bm.verts:
        v.co = shape(*v.co) * scale
    bm.to_mesh(o.data)
    bm.free()
    return o


def link(o, coll=None):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    (coll or scene.collection).objects.link(o)
    return o


def apply_modifier(o, kind, **props):
    m = o.modifiers.new(kind.lower(), kind)
    for key, value in props.items():
        setattr(m, key, value)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)


def solid(o, thickness):
    apply_modifier(o, "SOLIDIFY", thickness=thickness, offset=-1.0, use_even_offset=True)


def boolean(target, operand, operation="DIFFERENCE"):
    m = target.modifiers.new("bool", "BOOLEAN")
    m.operation = operation
    m.solver = "EXACT"
    m.use_self = True
    m.use_hole_tolerant = True
    if isinstance(operand, bpy.types.Collection):
        m.operand_type = "COLLECTION"
        m.collection = operand
    else:
        m.object = operand
    bpy.context.view_layer.objects.active = target
    before = len(target.data.vertices)
    bpy.ops.object.modifier_apply(modifier=m.name)
    print("BOOLEAN", target.name, operation, before, len(target.data.vertices))


def box(loc, dims, rot=(0, 0, 0), coll=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return link(o, coll)


def prism(name, points, axis, low, high, coll=None):
    bm = bmesh.new()

    def place(a, b, depth):
        if axis == "y":
            return (a, depth, b)
        return (depth, a, b)

    bottom = [bm.verts.new(place(a, b, low)) for a, b in points]
    top = [bm.verts.new(place(a, b, high)) for a, b in points]
    bm.faces.new(bottom)
    bm.faces.new(top[::-1])
    for i in range(len(points)):
        j = (i + 1) % len(points)
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    return link(o, coll)


def mirror(points):
    return [(-a, b) for a, b in reversed(points)]


def duplicate(o, name):
    copy = o.copy()
    copy.data = o.data.copy()
    copy.name = name
    return link(copy)


def assign(o, mat):
    o.data.materials.clear()
    o.data.materials.append(mat)


def join(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    objects[0].name = name
    return objects[0]


def finish(o, width=0.007):
    apply_modifier(o, "BEVEL", width=width, segments=2, limit_method="ANGLE",
                   angle_limit=math.radians(35))
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(32))
    except (AttributeError, RuntimeError):
        bpy.ops.object.shade_smooth()
    apply_modifier(o, "WEIGHTED_NORMAL", keep_sharp=True)


def unwrap(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")


def new_collection(name):
    coll = bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    return coll


base = skull("Base")
depsgraph = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(base, depsgraph)


def front(x, z):
    hit = bvh.ray_cast(Vector((x, -3, z)), Vector((0, 1, 0)))[0]
    return hit.y if hit else -0.6


# Armor shell cut into plates by panel lines.
armor = duplicate(base, "Armor")
solid(armor, 0.05)
seams = new_collection("Seams")
for s in (-1, 1):
    box((s * 0.085, 0.1, 1.0), (SEAM, 2.6, 0.9), coll=seams)
    box((s * 0.07, -0.8, 0.43), (SEAM, 0.6, 0.42), (0, s * 0.075, 0), seams)
    box((s * 0.042, -0.8, -0.06), (SEAM, 0.6, 0.38), coll=seams)
    box((s * 0.34, -0.6, 0.27), (0.62, 1.1, SEAM), (0, -s * 0.25, 0), seams)
    box((s * 0.36, -0.6, -0.03), (0.56, 1.1, SEAM), (0, s * 0.13, 0), seams)
    box((s * 0.33, -0.6, -0.21), (SEAM, 1.1, 0.38), (0, s * 0.2, 0), seams)
    box((s * 0.42, 0.45, 0.72), (0.5, SEAM, 0.5), (0.45, 0, 0), seams)
box((0, 0.02, 0.1), (2.0, SEAM, 0.9), coll=seams)
box((0, 0.38, 0.95), (0.16, SEAM, 0.6), coll=seams)
box((0, 0.7, 0.75), (0.16, SEAM, 0.6), (0.6, 0, 0), seams)
box((0, 0.65, 0.22), (2.0, 1.0, SEAM), coll=seams)
boolean(armor, seams)

eye_right = [(0.1, 0.085), (0.4, 0.175), (0.42, 0.135), (0.14, 0.045)]
sockets = new_collection("Sockets")
for outline in (eye_right, mirror(eye_right)):
    prism("socket", outline, "y", -1.4, -0.4, sockets)
boolean(armor, sockets)

mouth_line = [(-1.4, -0.4), (0.02, -0.29), (0.3, -0.56), (0.3, -1.6), (-1.4, -1.6)]
jaw_region = prism("jaw_region", mouth_line, "x", -1.2, 1.2)
gap_line = [(y, z + 0.016) for y, z in mouth_line[:2]] + mouth_line[2:]
gap_region = prism("gap_region", [(y + (0.016 if i == 2 else 0), z) for i, (y, z) in
                                  enumerate(gap_line)], "x", -1.2, 1.2)
jaw = duplicate(armor, "Jaw")
boolean(jaw, jaw_region, "INTERSECT")
boolean(armor, gap_region)
grille = new_collection("Grille")
for i in range(-3, 4):
    box((i * 0.048, front(i * 0.048, -0.5), -0.52), (0.017, 0.3, 0.12), coll=grille)
boolean(jaw, grille)

# Raised titanium plates follow the skull at a slightly larger scale.
layer = skull("Layer", 1.014)
solid(layer, 0.024)
ridge = skull("Ridge", 1.06)
solid(ridge, 0.065)
plates = []


def plate(outline, axis="y", low=-2.0, high=0.0, source=None):
    p = duplicate(source or layer, "plate")
    boolean(p, prism("cut", outline, axis, low, high), "INTERSECT")
    plates.append(p)
    return p


brow = [(0.075, 0.215), (0.6, 0.345), (0.65, 0.44), (0.1, 0.31)]
cheek = [(0.11, -0.03), (0.6, 0.09), (0.63, -0.03), (0.2, -0.2)]
temple = [(-0.42, 0.12), (-0.02, 0.22), (0.08, 0.58), (-0.36, 0.5)]
for outline in (brow, mirror(brow), cheek, mirror(cheek)):
    plate(outline)
crest = plate([(-0.062, 0.25), (0.062, 0.25), (0.08, 1.2), (-0.08, 1.2)], low=-2, high=2)
slot = prism("slot", [(-0.016, 0.3), (0.016, 0.3), (0.016, 0.9), (-0.016, 0.9)], "y", -2, 0)
boolean(crest, slot)
plate(temple, "x", 0.3, 1.2)
plate(temple, "x", -1.2, -0.3)
fin = [(-0.2, 0.08), (0.7, 0.52), (0.78, 0.4), (-0.12, -0.04)]
plate(fin, "x", 0.3, 1.2, ridge)
plate(fin, "x", -1.2, -0.3, ridge)
plate([(0.1, 0.62), (0.75, 0.9), (0.8, 0.82), (0.16, 0.54)], "x", 0.2, 1.2, ridge)
plate([(0.1, 0.62), (0.75, 0.9), (0.8, 0.82), (0.16, 0.54)], "x", -1.2, -0.2, ridge)
chin = duplicate(layer, "Chin")
jaw_plates = [chin]
boolean(chin, prism("cut", [(-0.12, -0.66), (0.12, -0.66), (0.07, -0.9), (-0.07, -0.9)],
                    "y", -2, 0), "INTERSECT")
lower = [(0.17, -0.44), (0.45, -0.36), (0.4, -0.5), (0.18, -0.66)]
for outline in (lower, mirror(lower)):
    piece = duplicate(layer, "Lower")
    boolean(piece, prism("cut", outline, "y", -2, 0), "INTERSECT")
    jaw_plates.append(piece)
bpy.data.objects.remove(layer)
bpy.data.objects.remove(ridge)
titanium = join(plates, "Plates")
chin = join(jaw_plates, "Chin")

# Emissive parts sit behind the armor openings.
eyes = []
for name, outline in (("EyeR", eye_right), ("EyeL", mirror(eye_right))):
    inset = [(a * 0.97 + (0.004 if a > 0 else -0.004), b) for a, b in outline]
    depth = front(sum(a for a, _ in outline) / 4, 0.12)
    eye = prism(name, inset, "y", depth + 0.02, depth + 0.07)
    assign(eye, EYE)
    eyes.append(eye)
glow = skull("CrestGlow", 1.012)
solid(glow, 0.008)
boolean(glow, prism("cut", [(-0.014, 0.31), (0.014, 0.31), (0.014, 0.89), (-0.014, 0.89)],
                    "y", -2, 0), "INTERSECT")
assign(glow, GLOW)
core = skull("Core", 0.93)
assign(core, CORE)
mouth = prism("MouthGlow", [(-0.15, -0.44), (0.15, -0.44), (0.13, -0.58), (-0.13, -0.58)],
              "y", front(0, -0.5) + 0.09, front(0, -0.5) + 0.13)
assign(mouth, GLOW)

# Neck rings stay still while the head turns.
neck_parts = []
for i, (z, r) in enumerate(((-0.92, 0.34), (-1.04, 0.325), (-1.16, 0.31), (-1.28, 0.295))):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=r, depth=0.085,
                                        location=(0, 0.26, z), rotation=(0.12, 0, 0))
    ring = bpy.context.active_object
    finish(ring, 0.01)
    assign(ring, ARMOR if i % 2 == 0 else TITANIUM)
    neck_parts.append(ring)
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.26, depth=0.62,
                                    location=(0, 0.26, -1.1), rotation=(0.12, 0, 0))
neck_core = bpy.context.active_object
assign(neck_core, INNER)
neck_parts.append(neck_core)
for s in (-1, 1):
    start, end = Vector((s * 0.3, 0.02, -0.55)), Vector((s * 0.24, 0.2, -1.3))
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.022, depth=(end - start).length,
                                        location=(start + end) / 2)
    piston = bpy.context.active_object
    piston.rotation_mode = "QUATERNION"
    piston.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(end - start)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    assign(piston, TITANIUM)
    neck_parts.append(piston)
neck = join(neck_parts, "Neck")

for o in (armor, jaw, titanium, chin):
    finish(o)
assign(armor, ARMOR)
assign(jaw, ARMOR)
assign(titanium, TITANIUM)
assign(chin, TITANIUM)
jaw = join([jaw, chin], "Jaw")
for o in (armor, jaw, titanium, neck):
    unwrap(o)

for coll in list(bpy.data.collections):
    for o in list(coll.objects):
        bpy.data.objects.remove(o)
    bpy.data.collections.remove(coll)
for o in list(scene.objects):
    if o.name.startswith(("cut", "slot", "socket", "jaw_region", "gap_region", "Base")):
        bpy.data.objects.remove(o)


def empty(name, location, parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = location
    link(e)
    if parent:
        e.parent = parent
        e.matrix_parent_inverse = parent.matrix_world.inverted()
    return e


head = empty("Head", (0, 0.22, -0.78))
hinge = empty("JawPivot", (0, 0.04, -0.3), head)
bpy.context.view_layer.update()
for o in (armor, titanium, core, glow, mouth, *eyes):
    o.parent = head
    o.matrix_parent_inverse = head.matrix_world.inverted()
jaw.parent = hinge
jaw.matrix_parent_inverse = hinge.matrix_world.inverted()

for o in scene.objects:
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        print("MESH", o.name, len(o.data.vertices), len(o.data.loop_triangles))

options = dict(filepath=OUT, export_format="GLB", export_apply=True, export_yup=True,
               export_texcoords=True, export_normals=True, export_cameras=False,
               export_lights=False, export_animations=False)
try:
    bpy.ops.export_scene.gltf(**options)
except TypeError:
    bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB")
print("EXPORTED", OUT)
