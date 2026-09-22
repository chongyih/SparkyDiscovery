"""Build Sparky with Blender 4.5: blender --background --python tools/build_sparky.py"""
import bpy, math, os, random
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

def surface_texture(material, name, strength, cloth=False):
    """Packed tangent normal image; survives GLB export instead of Blender-only noise."""
    import numpy as np
    rng=np.random.default_rng(218 if cloth else 44)
    size=512
    noise=rng.random((size,size))
    # Short directional tufts / a fine woven weave.
    height=sum(np.roll(noise,k,axis=0)*w for k,w in [(-2,.12),(-1,.22),(0,.32),(1,.22),(2,.12)])
    if cloth:
        y,x=np.mgrid[:size,:size]
        height=.15*noise+.15*np.sin(x*pi/2)+.15*np.sin(y*pi/2)
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*strength
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*strength
    rgb=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1)
    rgb/=np.linalg.norm(rgb,axis=-1)[...,None]
    pixels=np.ones((size,size,4),dtype=np.float32); pixels[:,:,:3]=rgb*.5+.5
    im=bpy.data.images.new(name,width=size,height=size)
    im.colorspace_settings.name='Non-Color'; im.pixels.foreach_set(pixels.ravel()); im.pack()
    nodes=material.node_tree.nodes; links=material.node_tree.links
    tex=nodes.new('ShaderNodeTexImage'); tex.image=im
    normal=nodes.new('ShaderNodeNormalMap'); normal.inputs['Strength'].default_value=.18 if cloth else .40
    links.new(tex.outputs['Color'],normal.inputs['Color'])
    links.new(normal.outputs['Normal'],nodes.get('Principled BSDF').inputs['Normal'])
    p=nodes.get('Principled BSDF')
    p.inputs['Roughness'].default_value=.95
    p.inputs['Sheen Weight'].default_value=.25 if cloth else .4

for m in [fur,muzzle,inner]: surface_texture(m,'Packed plush pile '+m.name,1.8)
for m in [navy,rib,seam]: surface_texture(m,'Packed cotton weave '+m.name,1.5,True)

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

def pillow(name,loc,scale,material,bone='body',power=.8):
    """A softly squared sewn cushion with gentle stuffing irregularities."""
    o=ball(name,loc,scale,material,bone)
    for v in o.data.vertices:
        q=[v.co[i]/scale[i] for i in range(3)]
        for i in range(3):
            q[i]=math.copysign(abs(q[i])**power,q[i])
        ripple=1+.013*sin(q[2]*9+q[0]*5)*sin(q[1]*8+1)
        v.co=Vector([q[i]*scale[i]*ripple for i in range(3)])
    return o

def loft(name,rings,material,bone='body'):
    # Rings: center xyz, horizontal radius, front/back radius.
    vertices=[]; faces=[]; count=48
    for j,(cx,cy,z,rx,ry) in enumerate(rings):
        for i in range(count):
            t=i*2*pi/count
            folds=1+.024*sin(t*9+j*.8)+.012*sin(t*15-j*.6)
            vertices.append((cx+rx*cos(t)*folds,cy+ry*sin(t)*folds,z))
    for j in range(len(rings)-1):
        for i in range(count):
            a=j*count+i; b=j*count+(i+1)%count
            faces.append((a,b,b+count,a+count))
    faces += [tuple(reversed(range(count))),tuple((len(rings)-1)*count+i for i in range(count))]
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(vertices,[],faces); mesh.update()
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Soft sewn folds','SUBSURF'); mod.levels=2
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.02); bpy.ops.object.mode_set(mode='OBJECT')
    return finish(o,name,material,bone)

# The visible hoodie is the torso; no hidden body geometry or cloth simulation.
torso=loft('Hoodie soft torso',[(0,0,.44,.40,.255),(0,0,.49,.47,.29),(0,0,.59,.48,.30),(0,0,.76,.46,.285),(0,0,.99,.425,.267),(0,0,1.15,.405,.24),(0,0,1.26,.32,.21),(0,0,1.3,.22,.18)],navy)
loft('Soft knitted hem',[(0,0,.433,.423,.271),(0,0,.445,.443,.285),(0,0,.49,.45,.288),(0,0,.515,.454,.283)],rib)

for side,s in [('L',1),('R',-1)]:
    bone='leg.'+side
    o=pillow('Continuous stuffed leg '+side,(s*.244,-.016,.247),(.208,.235,.24),fur,bone,.73)
    for v in o.data.vertices:
        v.co.y-=.045*(1-v.co.z/.24)/2
        v.co.x+=s*.025*(-v.co.z/.24)
    bone='arm.'+side
    o=loft('Soft sleeve '+side,[(0,0,-.30,.132,.14),(0,0,-.25,.155,.162),(0,0,-.13,.177,.18),(0,0,.06,.19,.185),(0,0,.22,.155,.165),(0,0,.28,.10,.13)],navy,bone)
    o.location=(s*.625,0,1.065); o.rotation_euler[1]=-s*1.23
    o=loft('Fabric cuff '+side,[(0,0,-.032,.14,.152),(0,0,-.025,.15,.161),(0,0,.027,.152,.164),(0,0,.034,.146,.158)],rib,bone)
    o.location=(s*.87,0,.98); o.rotation_euler[1]=-s*1.23
    pillow('Mitten paw '+side,(s*.93,-.006,.955),(.12,.147,.126),fur,bone,.8)

# Hood volume behind a projecting face, with a rounded opening and two exposed ears.
# A single open-front shell runs from the face opening to the rear of the hood.
# Separate ellipsoids leave a visible band of exposed head in side view.
verts=[]; faces=[]; count=128
hood_rings=[(-.247,.538,.466),(-.230,.550,.478),(-.18,.573,.505),(-.06,.601,.535),(.10,.59,.535),(.26,.51,.465),(.38,.365,.335),(.45,.18,.17),(.47,.012,.012)]
for j,(y,rx,rz) in enumerate(hood_rings):
    for i in range(count):
        t=2*pi*i/count
        ripple=1+.009*sin(t*7+j*.5)*sin(pi*j/(len(hood_rings)-1))
        verts.append((rx*cos(t)*(1+.025*sin(3*t))*ripple,y+.015*sin(4*t)*(1-j/(len(hood_rings)-1)),1.697+rz*sin(t)*ripple))
for j in range(len(hood_rings)-1):
    for i in range(count):
        a=j*count+i; b=j*count+(i+1)%count
        faces.append((a,a+count,b+count,b))
faces.append(tuple(reversed([(len(hood_rings)-1)*count+i for i in range(count)])))
mesh=bpy.data.meshes.new('Continuous hood shell'); mesh.from_pydata(verts,[],faces); mesh.update()
hood=bpy.data.objects.new('Continuous fabric hood',mesh); bpy.context.collection.objects.link(hood)
bpy.ops.object.select_all(action='DESELECT'); hood.select_set(True); bpy.context.view_layer.objects.active=hood
sub=hood.modifiers.new('Soft fabric curvature','SUBSURF'); sub.levels=2; bpy.ops.object.modifier_apply(modifier=sub.name)
solid=hood.modifiers.new('Fabric thickness','SOLIDIFY'); solid.thickness=.012; bpy.ops.object.modifier_apply(modifier=solid.name)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.015); bpy.ops.object.mode_set(mode='OBJECT')
finish(hood,'Continuous fabric hood',navy,'head')
for side,s in [('L',1),('R',-1)]:
    pillow('Soft ear '+side,(s*.453,.013,2.053),(.174,.103,.19),fur,'head',.88)
    ball('Ear inset '+side,(s*.459,-.079,2.05),(.104,.027,.12),muzzle,'head')
head=pillow('Bear head',(0,-.13,1.695),(.505,.325,.435),fur,'head',.85)
# Union an oval stuffed muzzle into the face. Unlike a point displacement,
# this gives the nose AND mouth a broad rounded cushion in side profile.
puff=ball('Rounded muzzle volume',(0,-.414,1.675),(.228,.194,.194),fur,'head')
parts.remove((puff,'head'))
bpy.ops.object.select_all(action='DESELECT')
head.select_set(True); puff.select_set(True); bpy.context.view_layer.objects.active=head
bpy.ops.object.join()
remesh=head.modifiers.new('Continuous stuffed muzzle','REMESH'); remesh.mode='VOXEL'; remesh.voxel_size=.008
remesh.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=remesh.name)
smooth=head.modifiers.new('Blend muzzle into cheeks','SMOOTH'); smooth.factor=1; smooth.iterations=8
bpy.ops.object.modifier_apply(modifier=smooth.name)
decimate=head.modifiers.new('Simplify plush surface','DECIMATE'); decimate.ratio=.6
bpy.ops.object.modifier_apply(modifier=decimate.name)
for poly in head.data.polygons: poly.use_smooth=True
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.015); bpy.ops.object.mode_set(mode='OBJECT')
head.data.update()
bpy.context.view_layer.update()
def face_y(x,z):
    origin=head.matrix_world.inverted() @ Vector((x,-2,z))
    hit,point,normal,index=head.ray_cast(origin,Vector((0,1,0)))
    assert hit, (x,z)
    return (head.matrix_world @ point).y
rim_points=[]
for i in range(128):
    t=i*2*pi/128; x=.538*cos(t); z=1.697+.466*sin(t)
    x*=1+.025*sin(3*t); y=-.247+.015*sin(4*t)
    rim_points.append((x,y,z))
tube('Soft folded hood edge',rim_points,.029,navy,'head',True)
tube('Fine hood stitching',[(x,y-.025,z) for x,y,z in rim_points],.0038,seam,'head',True)
for side,s in [('L',1),('R',-1)]:
    ball('Button eye '+side,(s*.204,face_y(s*.204,1.811)-.012,1.811),(.046,.025,.055),eye,'head')
ball('Velvet nose',(0,face_y(0,1.714)-.017,1.714),(.062,.028,.043),black,'head')
tube('Embroidered mouth stem',[(0,face_y(0,z)-.006,z) for z in [1.69,1.675,1.655,1.639]],.007,black,'head')
for s in [-1,1]:
    tube('Embroidered smile',[(x,face_y(x,z)-.006,z) for x,z in [(0,1.639),(s*.026,1.613),(s*.059,1.59)]],.007,black,'head')

# Shallow pocket and piping, fitted to the front of the sweatshirt.
pillow('Flat sewn kangaroo pocket',(0,-.271,.685),(.276,.034,.111),navy,power=.65)
tube('Pocket top seam',[(-.24,-.301,.747),(-.17,-.307,.782),(0,-.309,.787),(.17,-.307,.782),(.24,-.301,.747)],.004,seam)
for s in [-1,1]:
    tube('Pocket hand opening',[(s*.22,-.306,.769),(s*.266,-.306,.7),(s*.22,-.306,.641)],.005,rib)
    tube('Cotton drawstring',[(s*.225,-.259,1.28),(s*.169,-.306,1.25),(s*.146,-.323,1.196)],.014,ivory)
    ball('Drawstring knot',(s*.147,-.323,1.203),(.024,.02,.021),ivory)
    limb('Drawstring tip',(s*.146,-.323,1.192),(s*.144,-.324,1.164),.018,.018,ivory,'body')

bpy.ops.object.text_add(location=(0,-.302,.914), rotation=(pi/2,0,0))
o=bpy.context.object; o.data.body='DSTA'; o.data.align_x='CENTER'; o.data.size=.215
o.data.extrude=0; o.data.bevel_depth=0
bpy.ops.object.convert(target='MESH')
# Fit the printed letters to the actual chest instead of floating on a plane.
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.subdivide(number_cuts=3); bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()
inverse=o.matrix_world.inverted()
for v in o.data.vertices:
    world=o.matrix_world @ v.co
    origin=torso.matrix_world.inverted() @ Vector((world.x,-2,world.z))
    hit,point,normal,index=torso.ray_cast(origin,Vector((0,1,0)))
    if hit:
        surface=torso.matrix_world @ point
        world.y=surface.y-.002
        v.co=inverse @ world
finish(o,'DSTA chest lettering',ivory,'body')

# Short tapered ribbons give actual plush fuzz in both Blender and the GLB.
# They are mesh geometry, not a render-only hair system.
bpy.context.view_layer.update()
random.seed(20260922)
pile_materials=[mat('Plush fibre '+str(i),c) for i,c in enumerate([(.57,.405,.225),(.585,.418,.235),(.555,.395,.22)])]
for m in pile_materials:
    m.use_backface_culling=False
    m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=1
    m.node_tree.nodes.get('Principled BSDF').inputs['Sheen Weight'].default_value=.45
for source,bone in list(parts):
    if source.data.materials[0] not in [fur,muzzle]: continue
    source.data.calc_loop_triangles()
    mw=source.matrix_world; normal_matrix=mw.to_3x3().inverted().transposed()
    tris=list(source.data.loop_triangles)
    weights=[t.area for t in tris]
    area=sum(weights)
    count=int(area*12000)
    verts=[]; faces=[]
    for tri in random.choices(tris,weights=weights,k=count):
        a,b,c=[source.data.vertices[i] for i in tri.vertices]
        u=random.random(); v=random.random()
        if u+v>1:u=1-u;v=1-v
        p=mw @ (a.co*(1-u-v)+b.co*u+c.co*v)
        n=(normal_matrix @ (a.normal*(1-u-v)+b.normal*u+c.normal*v)).normalized()
        if p.z<.025: continue
        # Keep embroidery and eyes clear of the pile.
        if source.name=='Bear head' and p.y<-.40:
            if any(((p.x-s*.204)/.059)**2+((p.z-1.811)/.067)**2<1 for s in [-1,1]):continue
            if abs(p.x)<.083 and 1.565<p.z<1.767:continue
        tangent=n.cross(Vector((.31,.71,.47))).normalized()
        second=n.cross(tangent).normalized()
        angle=random.random()*2*pi
        side=(tangent*cos(angle)+second*sin(angle)).normalized()
        lean=second*random.uniform(-.45,.45)+tangent*random.uniform(-.45,.45)
        length=random.uniform(.005,.010)
        width=random.uniform(.00045,.00075)
        base=p-n*.001; middle=p+n*length*.55+lean*length*.2; tip=p+n*length+lean*length*.65
        k=len(verts)
        verts.extend([base-side*width,base+side*width,middle-side*width*.60,middle+side*width*.60,tip])
        faces.extend([(k,k+1,k+3,k+2),(k+2,k+3,k+4)])
    mesh=bpy.data.meshes.new('Short pile '+source.name); mesh.from_pydata(verts,[],faces); mesh.update()
    o=bpy.data.objects.new('Short pile '+source.name,mesh); bpy.context.collection.objects.link(o)
    for m in pile_materials: mesh.materials.append(m)
    for face in mesh.polygons:
        face.material_index=random.choices([0,1,2],[.65,.22,.13])[0]
        face.use_smooth=True
    parts.append((o,bone))

# Blended shoulder and hip weights soften the bends under the clothing.
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
    vg=o.vertex_groups.new(name=bone)
    blend=o.name.startswith('Soft sleeve') or o.name.startswith('Continuous stuffed leg') or o.name.startswith('Short pile Continuous stuffed leg')
    if blend:
        parent='body' if bone.startswith('arm') else 'root'
        pv=o.vertex_groups.new(name=parent)
        for v in o.data.vertices:
            co=o.matrix_world @ v.co
            t=max(0,min(1,(abs(co.x)-.33)/.27)) if bone.startswith('arm') else max(0,min(1,(.49-co.z)/.21))
            t=t*t*(3-2*t)
            vg.add([v.index],t,'REPLACE'); pv.add([v.index],1-t,'REPLACE')
    else: vg.add(list(range(len(o.data.vertices))),1,'REPLACE')
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
            for side,s in [('L',1),('R',-1)]:
                rig.pose.bones['arm.'+side].rotation_euler[2]=s*.035*sin(phase+.4)
        elif name=='Walk':
            rig.pose.bones['root'].location.y=.015*(1-cos(phase*2))
            for side,s in [('L',1),('R',-1)]:
                rig.pose.bones['leg.'+side].rotation_euler[0]=s*.23*sin(phase)
                rig.pose.bones['arm.'+side].rotation_euler[0]=-s*.18*sin(phase+.3)
            rig.pose.bones['body'].rotation_euler[2]=.04*sin(phase)
            rig.pose.bones['head'].rotation_euler[2]=-.035*sin(phase+.3)
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
for name,loc in [('preview',(3,-7,3.05)),('front',(0,-7,2.0)),('back',(3,7,2.7)),('side',(7,-.5,2.0))]:
    camera.location=loc; aim(camera,(0,0,1.13))
    scene.render.filepath=os.path.join(OUT,'sparky-'+name+'.png')
    bpy.ops.render.render(write_still=True)
print('SPARKY_BUILD_COMPLETE',len(parts),'mesh components')
