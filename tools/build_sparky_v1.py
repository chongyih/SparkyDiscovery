"""Build Sparky with Blender 4.5: blender --background --python tools/build_sparky.py"""
import bpy, math, os
from mathutils import Vector
from math import sin, cos, pi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'sparky')
os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def mat(name, color, rough=0.8):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    return m

fur = mat('Warm honey plush', (0.57, .405, .225))
muzzle = mat('Soft cream muzzle', (.73, .565, .345))
inner = mat('Ear inset', (.40, .255, .135))
navy = mat('Midnight navy cotton', (.024, .032, .064))
rib = mat('Hoodie ribbing', (.014, .020, .041))
seam = mat('Raised navy seams', (.050, .063, .100))
black = mat('Embroidered charcoal', (.009, .012, .016), .48)
eye = mat('Glossy button eyes', (.006, .008, .011), .21)
ivory = mat('Ivory lettering and cords', (.78, .76, .65))
parts = []

def finish(o, name, material, bone):
    o.name = name
    o.data.materials.append(material)
    if o.type == 'MESH':
        for p in o.data.polygons: p.use_smooth = True
    parts.append((o, bone))
    return o

def ball(name, loc, scale, material, bone='body'):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=loc)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, material, bone)

def tube(name, points, radius, material, bone='body', cyclic=False):
    c = bpy.data.curves.new(name, 'CURVE'); c.dimensions = '3D'
    c.bevel_depth = radius; c.bevel_resolution = 3
    s = c.splines.new('POLY'); s.points.add(len(points)-1)
    for p, co in zip(s.points, points): p.co = (*co, 1)
    s.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name, c); bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o.select_set(False)
    return finish(o, name, material, bone)

def oval_ring(name, center, rx, rz, radius, material, bone='head'):
    x,y,z = center
    return tube(name, [(x+rx*cos(t*2*pi/96),y,z+rz*sin(t*2*pi/96)) for t in range(96)], radius, material, bone, True)

def limb(name, a, b, width, depth, material, bone):
    v = Vector(b)-Vector(a)
    o = ball(name, (Vector(a)+Vector(b))/2, (width,depth,v.length/2+width*.5), material, bone)
    o.rotation_mode='QUATERNION'; o.rotation_quaternion=v.to_track_quat('Z','Y')
    return o

# The visible hoodie is the torso; no hidden body geometry or cloth simulation.
ball('Hoodie soft torso', (0,0,.86), (.465,.29,.47), navy)
ball('Ribbed waistband', (0,-.006,.493), (.443,.275,.085), rib)
for i in range(39):
    t = pi + i*pi/38
    x=.433*cos(t); y=.271*sin(t)-.008
    tube('Waist knit rib %02d'%i, [(x,y,.46),(x,y-.004,.52)], .004, seam)

for side,s in [('L',1),('R',-1)]:
    bone='leg.'+side
    limb('Plush leg '+side,(s*.225,.015,.42),(s*.25,-.035,.16),.205,.22,fur,bone)
    ball('Rounded foot '+side,(s*.25,-.09,.135),(.208,.252,.135),fur,bone)
    bone='arm.'+side
    limb('Hoodie sleeve '+side,(s*.385,0,1.17),(s*.78,-.005,.98),.175,.20,navy,bone)
    limb('Sleeve cuff '+side,(s*.77,-.003,.986),(s*.84,-.003,.953),.166,.19,rib,bone)
    ball('Mitten paw '+side,(s*.895,-.006,.935),(.14,.163,.145),fur,bone)

# Hood volume behind a projecting face, with a rounded opening and two exposed ears.
ball('Hood back', (0,.085,1.68), (.635,.405,.585), navy,'head')
for side,s in [('L',1),('R',-1)]:
    ball('Round ear '+side,(s*.475,.013,2.09),(.205,.139,.208),fur,'head')
    ball('Ear inset '+side,(s*.482,-.107,2.09),(.128,.035,.133),inner,'head')
ball('Bear head',(0,-.13,1.72),(.542,.351,.465),fur,'head')
oval_ring('Thick hood opening',(0,-.267,1.716),.562,.497,.054,navy)
oval_ring('Hood opening stitched edge',(0,-.302,1.716),.562,.497,.008,seam)
ball('Muzzle',(0,-.425,1.638),(.237,.090,.178),muzzle,'head')
for side,s in [('L',1),('R',-1)]:
    ball('Button eye '+side,(s*.213,-.443,1.824),(.051,.035,.063),eye,'head')
ball('Velvet nose',(0,-.522,1.716),(.063,.034,.045),black,'head')
tube('Embroidered mouth stem',[(0,-.52,1.69),(0,-.524,1.639)],.009,black,'head')
for s in [-1,1]:
    tube('Embroidered smile',[(0,-.524,1.639),(s*.026,-.52,1.613),(s*.059,-.51,1.59)],.009,black,'head')

# Shallow pocket and piping, fitted to the front of the sweatshirt.
ball('Kangaroo pocket',(0,-.268,.702),(.283,.055,.117),navy)
tube('Pocket top seam',[(-.24,-.303,.747),(-.17,-.318,.792),(0,-.324,.805),(.17,-.318,.792),(.24,-.303,.747)],.009,seam)
for s in [-1,1]:
    tube('Pocket hand opening',[(s*.22,-.31,.769),(s*.266,-.31,.7),(s*.22,-.31,.641)],.012,rib)
    tube('Cotton drawstring',[(s*.225,-.259,1.28),(s*.169,-.306,1.25),(s*.146,-.323,1.196)],.014,ivory)
    ball('Drawstring knot',(s*.147,-.323,1.203),(.024,.02,.021),ivory)
    limb('Drawstring tip',(s*.146,-.323,1.192),(s*.144,-.324,1.164),.018,.018,ivory,'body')

bpy.ops.object.text_add(location=(0,-.302,.914), rotation=(pi/2,0,0))
o=bpy.context.object; o.data.body='DSTA'; o.data.align_x='CENTER'; o.data.size=.225
o.data.extrude=.001; o.data.bevel_depth=.0005
bpy.ops.object.convert(target='MESH')
finish(o,'DSTA chest lettering',ivory,'body')

# A deliberately simple toy rig: each plush component follows one bone.
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.armature_add()
rig=bpy.context.object; rig.name='Sparky_Rig'; rig.show_in_front=True
bpy.ops.object.mode_set(mode='EDIT'); eb=rig.data.edit_bones
eb.remove(eb[0])
spec=[('root',(0,0,0),(0,0,.2),None),('body',(0,0,.49),(0,0,1.25),'root'),('head',(0,0,1.25),(0,0,1.95),'body')]
for side,s in [('L',1),('R',-1)]:
    spec += [('arm.'+side,(s*.385,0,1.17),(s*.87,0,.95),'body'),('leg.'+side,(s*.225,0,.45),(s*.25,0,.12),'root')]
for name,head,tail,parent in spec:
    b=eb.new(name); b.head=head; b.tail=tail
    if parent: b.parent=eb[parent]
bpy.ops.object.mode_set(mode='OBJECT')
for o,bone in parts:
    vg=o.vertex_groups.new(name=bone); vg.add(list(range(len(o.data.vertices))),1,'REPLACE')
    mod=o.modifiers.new('Plush skeleton','ARMATURE'); mod.object=rig
    o.parent=rig

rig.animation_data_create()
for name,duration in [('Idle',72),('Walk',24),('Wave',60)]:
    action=bpy.data.actions.new(name); rig.animation_data.action=action
    for frame in range(1,duration+2,3):
        phase=(frame-1)/duration*2*pi
        for pb in rig.pose.bones:
            pb.rotation_mode='XYZ'; pb.rotation_euler=(0,0,0); pb.location=(0,0,0)
        if name=='Idle':
            rig.pose.bones['body'].location.y=.012*sin(phase)
            rig.pose.bones['head'].rotation_euler[1]=.035*sin(phase)
        elif name=='Walk':
            rig.pose.bones['root'].location.y=.023*(1-cos(phase*2))
            for side,s in [('L',1),('R',-1)]:
                rig.pose.bones['leg.'+side].rotation_euler[0]=s*.30*sin(phase)
                rig.pose.bones['arm.'+side].rotation_euler[0]=-s*.23*sin(phase)
            rig.pose.bones['body'].rotation_euler[2]=.04*sin(phase)
        else:
            lift=sin(pi*min((frame-1)/duration*3,1)/2)*sin(pi*min((duration-frame+1)/duration*3,1)/2)
            rig.pose.bones['arm.L'].rotation_euler[2]=-.95*lift
            rig.pose.bones['arm.L'].rotation_euler[0]=.22*sin(phase*3)*lift
            rig.pose.bones['head'].rotation_euler[1]=-.09*lift
        for pb in rig.pose.bones:
            pb.keyframe_insert(data_path='rotation_euler',frame=frame,group=pb.name)
            pb.keyframe_insert(data_path='location',frame=frame,group=pb.name)
    track=rig.animation_data.nla_tracks.new(); track.name=name
    track.strips.new(name,1,action)
    track.mute=True
rig.animation_data.action=None
for pb in rig.pose.bones: pb.rotation_euler=(0,0,0); pb.location=(0,0,0)

scene=bpy.context.scene; scene.render.fps=24
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
for o,_ in parts: o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'sparky.glb'),use_selection=True,export_format='GLB',export_animations=True,export_animation_mode='ACTIONS',export_skins=True,export_yup=True)

# Render studio is kept separate from the exported game asset.
ground=mat('Studio sand',(.16,.205,.23))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015))
floor=bpy.context.object; floor.name='STUDIO floor'; floor.data.materials.append(ground)
world=scene.world; world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.19,.24,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.45
def aim(o,point): o.rotation_euler=(Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size in [('Key',(-3,-4,6),650,4),('Fill',(4,-2,3),400,3),('Rim',(1,3,5),850,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc); o=bpy.context.object; o.name='STUDIO '+name
    o.data.energy=power; o.data.shape='DISK'; o.data.size=size; aim(o,(0,0,1))
bpy.ops.object.camera_add(location=(3,-7,3.05)); camera=bpy.context.object
camera.name='STUDIO camera'; camera.data.type='ORTHO'; camera.data.ortho_scale=3.08; aim(camera,(0,0,1.13)); scene.camera=camera
scene.render.engine='CYCLES'; scene.cycles.samples=32
scene.render.resolution_x=1000; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.cycles.use_denoising=True
rig.animation_data.action=bpy.data.actions['Idle']
scene.frame_end=73
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True); bpy.context.view_layer.objects.active=rig
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.color_type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'sparky.blend'))
for name,loc in [('preview',(3,-7,3.05)),('front',(0,-7,2.0)),('back',(3,7,2.7))]:
    camera.location=loc; aim(camera,(0,0,1.13))
    scene.render.filepath=os.path.join(OUT,'sparky-'+name+'.png')
    bpy.ops.render.render(write_still=True)
print('SPARKY_BUILD_COMPLETE',len(parts),'mesh components')
