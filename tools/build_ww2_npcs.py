"""
Sparky Discovery - Chapter 1 (Singapore, Feb 1942) NPC builder.

Reproducible, fully procedural: every character is described by a CONFIG dict
(body proportions, age/posture/energy, palette, outfit, hair, face, props).
Making the 1965/1967 versions later = add a new entry to CHARACTERS (copy one,
change height / head_frac / palette / outfit), nothing else.

Run:
  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python tools/build_ww2_npcs.py -- [--only siti,rajan] [--tier desktop|mobile|both]

Outputs  public/assets/models/npc-<id>.glb         (desktop: <=8k tris, 512^2 palette, sheen)
         public/assets/models/npc-<id>-mobile.glb  (mobile:  <=4k tris, 256^2 palette)
Both tiers share identical bone names/hierarchy and identical clip names.

Conventions: metres, Z-up in Blender, character faces Blender -Y (three.js +Z),
feet at z=0, origin at the feet. Character's LEFT is +X (bones *.L).
"""
import bpy, bmesh, math, os, sys, json, copy
import numpy as np
from math import sin, cos, pi, radians, degrees, atan2, sqrt, acos
from mathutils import Vector, Matrix, Euler, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, 'public', 'assets', 'models')
FPS = 30

TIERS = {
    'desktop': dict(q=1.0, tex=512, sheen=True, suffix='', tri_budget=8000),
    'mobile':  dict(q=0.56, tex=256, sheen=False, suffix='-mobile', tri_budget=4000),
}

# --------------------------------------------------------------------------------------
# Shared colours
# --------------------------------------------------------------------------------------
COMMON_SWATCHES = {
    'eye':    '#1f1612',
    'eye_hi': '#ffffff',
    'mouth':  '#6c2f2a',
}

# --------------------------------------------------------------------------------------
# CHARACTER CONFIGS  (all sizes relative to height unless noted)
# --------------------------------------------------------------------------------------
BASE_BODY = dict(
    height=1.60,
    head_frac=0.26,          # skull height / total height (toy: 0.25-0.33)
    head_aspect=(0.96, 0.92),# width/height, depth/height
    leg_frac=0.50,           # hip-joint height / (height - head)
    torso_w=0.20,            # chest full width / height
    torso_depth=0.78,        # depth / width
    hip_ratio=0.98,          # hip width / chest width
    belly=0.0,               # extra belly bulge (fraction)
    neck_r=0.030,            # neck radius / height
    arm_r=0.026,             # upper-arm radius / height
    leg_r=0.034,             # thigh radius / height
    hand_r=0.034,            # hand size / height
    foot_len=0.13,           # foot length / height
    arm_len=1.12,            # arm length relative to shoulder->hip distance
    arm_spread=9.0,          # rest A-pose angle (deg)
)

def body(**kw):
    b = dict(BASE_BODY); b.update(kw); return b

CHARACTERS = {
    # ---------------------------------------------------------------- Siti, 12
    'siti': dict(
        name='Siti', file='npc-siti', age=12,
        body=body(height=1.35, head_frac=0.325, head_aspect=(0.98, 0.93), leg_frac=0.43,
                  torso_w=0.235, torso_depth=0.80, hip_ratio=0.97, neck_r=0.042,
                  arm_r=0.037, leg_r=0.045, hand_r=0.046, foot_len=0.145, arm_len=1.02, arm_spread=12),
        energy=1.1, walk_period=0.9, run_period=0.62, posture=dict(spine=0, chest=-1, head=0),
        idle_arms='relaxed',
        palette={
            'skin': '#b7825f', 'skin_shade': '#a26c4d',
            'face': dict(kind='face', skin='#b7825f', blush='#c56f62'),
            'hair': dict(kind='strands', base='#221813'),
            'baju': dict(kind='twill', base='#6f9f80', amt=0.035),
            'trim': '#ead8a2',
            'batik': dict(kind='batik', base='#7a4a2d', motif='#e5c68e', dark='#3d281c', border='#b8662f'),
            'ribbon': '#c2433b',
            'sandal': '#6b4a33',
            'bag': dict(kind='twill', base='#cbb993', amt=0.05), 'strap': '#a8956b',
            'news': dict(kind='news', base='#efe8d6', ink='#6d6a63'),
        },
        hair=dict(style='plaits', sw='hair', scale=(1.055, 1.065, 1.045), ribbon='ribbon',
                  line=[(0, 40), (8, 33), (25, 30), (50, 16), (72, -4), (95, -22), (135, -42), (180, -52)]),
        face=dict(eye=1.0, eye_az=21, eye_el=-5, brow=dict(inner=1.5, outer=-0.5, arch=1.5, r=1.0),
                  mouth=dict(w=8.5, smile=4.0, el=-27), nose=0.9, blush=0.55, lashes=True),
        outfit=dict(
            top=dict(sw='baju', hem=('knee', 0.01), ease=0.016, flare=1.38,
                     sleeve=1.0, sleeve_ease=0.006, sleeve_flare=1.12, collar='round_trim', trim='trim'),
            lower=dict(type='skirt', sw='batik', hem=('ankle', 0.035), top='waist', ease=0.008, flare=1.14),
            feet=dict(type='sandals', sw='sandal'),
        ),
        props=[dict(type='news_bag', side='R', sw='bag', strap='strap', papers='news')],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Mr Rajan, adult
    'rajan': dict(
        name='Rajan', file='npc-rajan', age=40,
        body=body(height=1.70, head_frac=0.285, head_aspect=(0.95, 0.91), leg_frac=0.45,
                  torso_w=0.262, torso_depth=0.80, hip_ratio=0.93, belly=0.03, neck_r=0.042,
                  arm_r=0.037, leg_r=0.046, hand_r=0.044, foot_len=0.15, arm_len=1.02, arm_spread=11),
        energy=1.0, walk_period=1.0, run_period=0.66, posture=dict(spine=-1, chest=-2, head=1),
        idle_arms='relaxed',
        palette={
            'skin': '#7d5136', 'skin_shade': '#6c442c',
            'face': dict(kind='face', skin='#7d5136', blush='#8c4c3c'),
            'hair': dict(kind='strands', base='#17110e'),
            'khaki': dict(kind='twill', base='#b69b69', amt=0.05),
            'khaki_dk': dict(kind='twill', base='#a0875a', amt=0.05),
            'helmet': '#2b2d2a', 'letter': '#f1eee4',
            'armband': '#24334f',
            'belt': '#5a3b24', 'brass': '#c9a04a', 'metal': '#c9ccd1',
            'shoe': '#43291b', 'lanyard': '#ece9df', 'button': '#8c7449',
            'bag': dict(kind='twill', base='#8f7f55', amt=0.06),
        },
        hair=dict(style='short', sw='hair', scale=(1.035, 1.045, 1.03),
                  line=[(0, 44), (40, 34), (70, 8), (86, -16), (100, -12), (140, -30), (180, -38)]),
        face=dict(eye=0.95, eye_az=20, eye_el=-4, brow=dict(inner=0.0, outer=0.5, arch=1.0, r=1.4),
                  mouth=dict(w=7.5, smile=3.0, el=-30), nose=1.1, blush=0.25, moustache='thick'),
        outfit=dict(
            top=dict(sw='khaki', hem='waist', ease=0.010, flare=1.0, sleeve=0.42, sleeve_ease=0.009,
                     sleeve_flare=1.18, collar='shirt', buttons='button', pockets=True),
            lower=dict(type='trousers', sw='khaki_dk', hem=('ankle', 0.012), top='waist', ease=0.006,
                       leg_ease=0.006, leg_flare=1.08),
            feet=dict(type='shoes', sw='shoe'),
        ),
        props=[dict(type='belt', sw='belt', buckle='brass'),
               dict(type='armband', side='L', sw='armband', text='ARP', letter='letter'),
               dict(type='whistle', side='L', cord='lanyard', metal='metal'),
               dict(type='gas_bag', side='L', sw='bag', strap='khaki_dk')],
        headwear=dict(type='helmet', sw='helmet', letter='letter', text='W'),
    ),
    # ---------------------------------------------------------------- Ah Ma, elderly
    'ahma': dict(
        name='AhMa', file='npc-ahma', age=68,
        body=body(height=1.55, head_frac=0.29, head_aspect=(0.98, 0.94), leg_frac=0.41,
                  torso_w=0.262, torso_depth=0.84, hip_ratio=1.07, belly=0.06, neck_r=0.042,
                  arm_r=0.036, leg_r=0.046, hand_r=0.043, foot_len=0.135, arm_len=1.0, arm_spread=12),
        energy=0.7, walk_period=1.15, run_period=0.78, posture=dict(spine=9, chest=9, head=-13),
        idle_arms='clasp',
        palette={
            'skin': '#e2bb96', 'skin_shade': '#cf9f7c',
            'face': dict(kind='face', skin='#e2bb96', blush='#e39683'),
            'hair': dict(kind='strands', base='#b8b3ab'), 'hair_dk': '#8f8a83',
            'samfu': dict(kind='twill', base='#a9c5d7', amt=0.03),
            'frog': '#3e5d79',
            'trousers': '#262628',
            'apron': dict(kind='twill', base='#eee8d8', amt=0.03),
            'shoe': '#1d1d1f', 'pin': '#7a5634', 'jade': '#6fae8a',
        },
        hair=dict(style='bun', sw='hair', scale=(1.04, 1.05, 1.04), pin='pin',
                  line=[(0, 42), (25, 36), (55, 20), (80, 10), (100, 0), (140, -30), (180, -42)]),
        face=dict(eye=0.82, eye_az=21, eye_el=-5, brow=dict(inner=2.0, outer=-2.0, arch=1.0, r=0.9, sw='hair_dk'),
                  mouth=dict(w=8.0, smile=4.5, el=-28), nose=1.0, blush=0.6, smile_lines=True),
        outfit=dict(
            top=dict(sw='samfu', hem=('hip', -0.035), ease=0.016, flare=1.10, sleeve=0.82, sleeve_ease=0.010,
                     sleeve_flare=1.42, collar='mandarin', placket='frog'),
            lower=dict(type='trousers', sw='trousers', hem=('ankle', 0.010), top='waist', ease=0.006,
                       leg_ease=0.012, leg_flare=1.30),
            feet=dict(type='slippers', sw='shoe'),
        ),
        props=[dict(type='apron', sw='apron'), dict(type='bangle', side='L', sw='jade')],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Ah Boon, 7
    'boon': dict(
        name='Boon', file='npc-boon', age=7,
        body=body(height=1.10, head_frac=0.345, head_aspect=(1.0, 0.95), leg_frac=0.41,
                  torso_w=0.262, torso_depth=0.86, hip_ratio=1.0, belly=0.08, neck_r=0.045,
                  arm_r=0.042, leg_r=0.052, hand_r=0.052, foot_len=0.155, arm_len=1.0, arm_spread=15),
        energy=1.3, walk_period=0.8, run_period=0.56, posture=dict(spine=0, chest=-2, head=0),
        idle_arms='relaxed',
        palette={
            'skin': '#ecc7a3', 'skin_shade': '#dcae8a',
            'face': dict(kind='face', skin='#ecc7a3', blush='#ef9a86'),
            'hair': dict(kind='strands', base='#1b1613'),
            'singlet': dict(kind='rib', base='#f1eee6', amt=0.03),
            'shorts': dict(kind='twill', base='#2f4563', amt=0.05),
        },
        hair=dict(style='crop', sw='hair', scale=(1.04, 1.05, 1.04),
                  line=[(0, 30), (10, 26), (22, 32), (45, 26), (75, 12), (95, 6), (130, -14), (180, -28)]),
        face=dict(eye=1.15, eye_az=22, eye_el=-6, brow=dict(inner=2.5, outer=0.5, arch=2.0, r=0.95),
                  mouth=dict(w=10.5, smile=6.0, el=-27, open=True), nose=0.85, blush=0.75),
        outfit=dict(
            top=dict(sw='singlet', hem=('hip', -0.01), ease=0.007, flare=1.02, sleeve=0.0,
                     collar='singlet', top_z='armpit'),
            lower=dict(type='shorts', sw='shorts', hem='thigh_mid', top='waist', ease=0.009,
                       leg_ease=0.012, leg_flare=1.18),
            feet=dict(type='bare', sw='skin'),
        ),
        props=[],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Pak Hassan, adult
    # Satay hawker (NOT a rickshaw puller: 1942 pullers were almost all Chinese - see
    # docs/research/ww2-costume.md). Collarless Teluk Belanga-style work baju with rolled
    # sleeves, checked kain pelikat, black songkok, cloth sash. Twisted ankle -> Limp clip.
    'hassan': dict(
        name='Hassan', file='npc-hassan', age=45,
        body=body(height=1.65, head_frac=0.285, head_aspect=(0.93, 0.91), leg_frac=0.46,
                  torso_w=0.245, torso_depth=0.78, hip_ratio=0.93, belly=0.0, neck_r=0.040,
                  arm_r=0.034, leg_r=0.043, hand_r=0.042, foot_len=0.15, arm_len=1.03, arm_spread=11),
        energy=0.9, walk_period=1.05, run_period=0.70, posture=dict(spine=3, chest=2, head=-3),
        idle_arms='relaxed',
        palette={
            'skin': '#9a6947', 'skin_shade': '#875a3b',
            'face': dict(kind='face', skin='#9a6947', blush='#a55c4a'),
            'hair': dict(kind='strands', base='#1f1813'),
            'shirt': dict(kind='twill', base='#46607f', amt=0.06),
            'cuff': dict(kind='twill', base='#6f87a3', amt=0.05),
            'trim': '#9fb2c6',
            'sarong': dict(kind='check', base='#4d6a4a', stripe='#6a4a2f', line='#dccb9f', nu=4, nv=5),
            'sash': dict(kind='twill', base='#8e3b32', amt=0.05),
            'songkok': '#1c1a1c',
            'sole': '#4a382b', 'sstrap': '#6a5443',
        },
        hair=dict(style='short', sw='hair', scale=(1.035, 1.045, 1.03),
                  line=[(0, 44), (40, 34), (70, 8), (86, -14), (100, -12), (140, -30), (180, -38)]),
        face=dict(eye=0.9, eye_az=20, eye_el=-4, brow=dict(inner=0.8, outer=-0.5, arch=1.0, r=1.1),
                  mouth=dict(w=7.5, smile=3.5, el=-30), nose=1.05, blush=0.3, moustache='thin'),
        outfit=dict(
            top=dict(sw='shirt', hem=('hip', -0.03), ease=0.011, flare=1.05, sleeve=0.50, sleeve_ease=0.008,
                     sleeve_flare=1.08, cuff=dict(sw='cuff', roll=True), collar='round_trim', trim='trim'),
            lower=dict(type='sarong', sw='sarong', hem=('shin_mid', 0.0), top='waist', ease=0.008, flare=1.16),
            feet=dict(type='sandals', sw='sole', strap='sstrap'),
        ),
        props=[dict(type='sash', sw='sash')],
        headwear=dict(type='songkok', sw='songkok'),
    ),
    # ---------------------------------------------------------------- Mr Boon, 91 (present day, 2026)
    # Same face DNA as young Boon (round head, eye spacing, brow and grin shape), aged:
    # thinning white hair, smile lines, round glasses, gentle stoop. Void-deck uncle outfit:
    # pinstriped short-sleeve shirt, grey slacks + belt, rubber slippers, wooden cane (node 'Cane').
    'oldboon': dict(
        name='MrBoon', file='npc-oldboon', age=91,
        body=body(height=1.55, head_frac=0.30, head_aspect=(1.0, 0.95), leg_frac=0.42,
                  torso_w=0.25, torso_depth=0.84, hip_ratio=1.0, belly=0.07, neck_r=0.040,
                  arm_r=0.034, leg_r=0.042, hand_r=0.043, foot_len=0.14, arm_len=1.02, arm_spread=11),
        energy=0.6, walk_period=1.25, run_period=0.85, posture=dict(spine=11, chest=9, head=-15),
        idle_arms='cane', cane_side='L',
        palette={
            'skin': '#e8c3a0', 'skin_shade': '#d2a27f',
            'face': dict(kind='face', skin='#e8c3a0', blush='#e59a86'),
            'hair': dict(kind='strands', base='#ece9e2'), 'brow': '#cfcac1',
            'shirt': dict(kind='pinstripe', base='#eef0ec', line='#9fb4c8', n=24),
            'slacks': dict(kind='twill', base='#7c7f83', amt=0.04),
            'belt': '#2b2624', 'metal': '#c9ccd1', 'button': '#e3e2dc',
            'slipper': '#3f6fa8', 'sstrap': '#2f4f7a',
            'frame': '#3a2b24', 'wood': dict(kind='twill', base='#7a5230', amt=0.08), 'rubber': '#232323',
        },
        hair=dict(style='short', sw='hair', scale=(1.03, 1.04, 1.03), top_el=58,
                  line=[(0, 50), (30, 40), (60, 12), (85, -4), (100, -8), (140, -24), (180, -30)],
                  wisps=[(-30, 25, 56, 70), (-22, 30, 50, 66), (-38, 12, 60, 76)]),
        face=dict(eye=0.92, eye_az=22, eye_el=-6, brow=dict(inner=2.5, outer=-0.5, arch=2.0, r=1.05, sw='brow'),
                  mouth=dict(w=10.0, smile=5.5, el=-28), nose=1.05, blush=0.55, smile_lines=True,
                  glasses=dict(sw='frame')),
        outfit=dict(
            top=dict(sw='shirt', hem=('hip', -0.02), ease=0.012, flare=1.04, sleeve=0.45, sleeve_ease=0.010,
                     sleeve_flare=1.2, collar='shirt', buttons='button', pockets='L'),
            lower=dict(type='trousers', sw='slacks', hem=('ankle', 0.012), top='waist', ease=0.006,
                       leg_ease=0.010, leg_flare=1.1),
            feet=dict(type='flipflops', sw='slipper', strap='sstrap'),
        ),
        props=[],
        extras=[dict(type='cane', name='Cane', side='L', sw='wood', tip_sw='rubber')],
        headwear=None,
    ),
    # ================================================================ 1942 townsfolk (generic crowd)
    'shopkeeper-cn': dict(
        name='ShopkeeperCN', file='npc-shopkeeper-cn', age=50,
        body=body(height=1.62, head_frac=0.285, head_aspect=(1.0, 0.94), leg_frac=0.43,
                  torso_w=0.27, torso_depth=0.88, hip_ratio=1.02, belly=0.10, neck_r=0.044,
                  arm_r=0.037, leg_r=0.046, hand_r=0.044, foot_len=0.145, arm_len=1.0, arm_spread=12),
        energy=0.85, walk_period=1.08, run_period=0.72, posture=dict(spine=1, chest=-2, head=0),
        idle_arms='relaxed',
        palette={
            'skin': '#e0b48c', 'skin_shade': '#c99a73',
            'face': dict(kind='face', skin='#e0b48c', blush='#df8f7a'),
            'hair': dict(kind='strands', base='#2a2522'),
            'singlet': dict(kind='rib', base='#f0ece2', amt=0.03),
            'trousers': dict(kind='twill', base='#2d3440', amt=0.05),
            'towel': dict(kind='check', base='#f1ece0', stripe='#c8554f', line='#f6f2ea', nu=2, nv=6),
            'shoe': '#1f1e1e',
        },
        hair=dict(style='short', sw='hair', scale=(1.035, 1.045, 1.03), top_el=76,
                  line=[(0, 54), (30, 46), (60, 16), (86, 2), (100, -4), (140, -24), (180, -30)]),
        face=dict(eye=0.88, eye_az=21, eye_el=-5, brow=dict(inner=0.5, outer=-1.0, arch=1.2, r=1.4),
                  mouth=dict(w=9.5, smile=5.0, el=-28), nose=1.1, blush=0.45, smile_lines=True),
        outfit=dict(
            top=dict(sw='singlet', hem=('hip', -0.02), ease=0.008, flare=1.03, sleeve=0.0,
                     collar='singlet', top_z='armpit'),
            lower=dict(type='trousers', sw='trousers', hem=('ankle', 0.02), top='waist', ease=0.007,
                       leg_ease=0.014, leg_flare=1.22),
            feet=dict(type='slippers', sw='shoe'),
        ),
        props=[dict(type='towel', side='L', sw='towel')],
        headwear=None,
    ),
    'woman-cn': dict(
        name='WomanCN', file='npc-woman-cn', age=32,
        body=body(height=1.56, head_frac=0.29, head_aspect=(0.96, 0.93), leg_frac=0.44,
                  torso_w=0.232, torso_depth=0.80, hip_ratio=1.02, belly=0.0, neck_r=0.038,
                  arm_r=0.032, leg_r=0.041, hand_r=0.040, foot_len=0.13, arm_len=1.0, arm_spread=11),
        energy=1.0, walk_period=0.95, run_period=0.66, posture=dict(spine=0, chest=-1, head=0),
        idle_arms='relaxed',
        palette={
            'skin': '#ecc8a6', 'skin_shade': '#d8ae8b',
            'face': dict(kind='face', skin='#ecc8a6', blush='#ec9887'),
            'hair': dict(kind='strands', base='#171311'),
            'samfu': dict(kind='floral', base='#d8a7ad', flower='#f5ece6', centre='#b76e7c', n=7),
            'frog': '#8a4a5a',
            'trousers': '#232326',
            'shoe': '#2a2324',
        },
        hair=dict(style='bun', sw='hair', scale=(1.045, 1.055, 1.04), pin='frog',
                  line=[(0, 26), (18, 24), (32, 30), (55, 10), (80, -8), (100, -14), (140, -34), (180, -42)]),
        face=dict(eye=1.0, eye_az=21, eye_el=-5, brow=dict(inner=1.0, outer=-0.5, arch=1.8, r=0.9),
                  mouth=dict(w=7.5, smile=3.8, el=-28), nose=0.9, blush=0.6, lashes=True),
        outfit=dict(
            top=dict(sw='samfu', hem=('hip', -0.04), ease=0.012, flare=1.10, sleeve=0.62, sleeve_ease=0.008,
                     sleeve_flare=1.25, collar='mandarin', placket='frog'),
            lower=dict(type='trousers', sw='trousers', hem=('ankle', 0.03), top='waist', ease=0.006,
                       leg_ease=0.011, leg_flare=1.22),
            feet=dict(type='slippers', sw='shoe'),
        ),
        props=[],
        headwear=None,
    ),
    'man-in': dict(
        name='ManIN', file='npc-man-in', age=45,
        body=body(height=1.72, head_frac=0.28, head_aspect=(0.93, 0.91), leg_frac=0.47,
                  torso_w=0.24, torso_depth=0.78, hip_ratio=0.92, belly=0.03, neck_r=0.040,
                  arm_r=0.033, leg_r=0.041, hand_r=0.041, foot_len=0.15, arm_len=1.03, arm_spread=10),
        energy=0.9, walk_period=1.05, run_period=0.70, posture=dict(spine=0, chest=-2, head=1),
        idle_arms='clasp',
        palette={
            'skin': '#6e452e', 'skin_shade': '#5d3a26',
            'face': dict(kind='face', skin='#6e452e', blush='#7b4535'),
            'hair': dict(kind='strands', base='#141110'),
            'shirt': dict(kind='twill', base='#f3f1ea', amt=0.03),
            'veshti': dict(kind='border', base='#efe9da', band='#8a2f2f', line='#c9a44a'),
            'button': '#d9d6cc', 'sandal': '#5b3e2a',
        },
        hair=dict(style='short', sw='hair', scale=(1.04, 1.05, 1.035),
                  line=[(0, 40), (30, 34), (60, 14), (86, -12), (100, -12), (140, -30), (180, -38)]),
        face=dict(eye=0.92, eye_az=20, eye_el=-4, brow=dict(inner=0.5, outer=0.0, arch=1.4, r=1.35),
                  mouth=dict(w=7.5, smile=3.5, el=-30), nose=1.15, blush=0.2, moustache='thick'),
        outfit=dict(
            top=dict(sw='shirt', hem=('hip', -0.03), ease=0.011, flare=1.05, sleeve=0.78, sleeve_ease=0.008,
                     sleeve_flare=1.06, cuff=dict(sw='shirt', roll=True), collar='shirt', buttons='button', pockets='L'),
            lower=dict(type='skirt', sw='veshti', hem=('ankle', 0.03), top='waist', ease=0.008, flare=1.12),
            feet=dict(type='sandals', sw='sandal'),
        ),
        props=[],
        headwear=None,
    ),
    'woman-my': dict(
        name='WomanMY', file='npc-woman-my', age=34,
        body=body(height=1.54, head_frac=0.29, head_aspect=(0.97, 0.93), leg_frac=0.44,
                  torso_w=0.236, torso_depth=0.80, hip_ratio=1.04, belly=0.02, neck_r=0.038,
                  arm_r=0.032, leg_r=0.041, hand_r=0.040, foot_len=0.13, arm_len=1.0, arm_spread=12),
        energy=0.95, walk_period=1.0, run_period=0.68, posture=dict(spine=0, chest=-1, head=0),
        idle_arms='clasp',
        palette={
            'skin': '#a8734f', 'skin_shade': '#94623f',
            'face': dict(kind='face', skin='#a8734f', blush='#b0604d'),
            'hair': dict(kind='strands', base='#1a1411'),
            'baju': dict(kind='twill', base='#9c4b55', amt=0.035),
            'trim': '#e3c27a',
            'batik': dict(kind='batik', base='#2f4668', motif='#e8d9b0', dark='#1b2a40', border='#8a6a3a'),
            'selendang': dict(kind='border', base='#f1e6cf', band='#d2a95c'),
            'sandal': '#5e4232', 'pin': '#c9a04a',
        },
        hair=dict(style='bun', sw='hair', scale=(1.045, 1.055, 1.04), pin='pin',
                  line=[(0, 40), (8, 33), (25, 30), (50, 16), (72, -4), (95, -16), (135, -36), (180, -44)]),
        face=dict(eye=0.98, eye_az=21, eye_el=-5, brow=dict(inner=1.2, outer=-0.8, arch=1.6, r=0.95),
                  mouth=dict(w=8.0, smile=4.2, el=-28), nose=0.95, blush=0.5, lashes=True),
        outfit=dict(
            top=dict(sw='baju', hem=('knee', 0.03), ease=0.016, flare=1.34,
                     sleeve=1.0, sleeve_ease=0.006, sleeve_flare=1.12, collar='round_trim', trim='trim'),
            lower=dict(type='skirt', sw='batik', hem=('ankle', 0.03), top='waist', ease=0.008, flare=1.12),
            feet=dict(type='sandals', sw='sandal'),
        ),
        props=[dict(type='shawl', sw='selendang')],
        headwear=None,
    ),
    'man-cn-young': dict(
        name='ManCNYoung', file='npc-man-cn-young', age=24,
        body=body(height=1.66, head_frac=0.28, head_aspect=(0.95, 0.92), leg_frac=0.47,
                  torso_w=0.25, torso_depth=0.76, hip_ratio=0.86, belly=0.0, neck_r=0.041,
                  arm_r=0.036, leg_r=0.043, hand_r=0.043, foot_len=0.15, arm_len=1.04, arm_spread=12),
        energy=1.15, walk_period=0.92, run_period=0.60, posture=dict(spine=0, chest=-3, head=0),
        idle_arms='relaxed',
        palette={
            'skin': '#cf9a70', 'skin_shade': '#b98660',
            'face': dict(kind='face', skin='#cf9a70', blush='#cf7f66'),
            'hair': dict(kind='strands', base='#171312'),
            'singlet': dict(kind='rib', base='#aebfc9', amt=0.035),
            'shorts': dict(kind='twill', base='#7e6b4c', amt=0.06, grime=0.06),
            'straw': dict(kind='twill', base='#d2b77a', amt=0.10), 'sole': '#3a2f28', 'sstrap': '#4c3d31',
        },
        hair=dict(style='crop', sw='hair', scale=(1.035, 1.045, 1.035),
                  line=[(0, 34), (15, 32), (35, 30), (60, 18), (85, 8), (120, -12), (180, -28)]),
        face=dict(eye=0.95, eye_az=20, eye_el=-5, brow=dict(inner=-0.5, outer=0.5, arch=0.8, r=1.3),
                  mouth=dict(w=9.0, smile=4.5, el=-28), nose=1.0, blush=0.35),
        outfit=dict(
            top=dict(sw='singlet', hem=('hip', -0.01), ease=0.006, flare=1.02, sleeve=0.0,
                     collar='singlet', top_z='armpit'),
            lower=dict(type='shorts', sw='shorts', hem=('knee', 0.05), top='waist', ease=0.007,
                       leg_ease=0.014, leg_flare=1.25),
            feet=dict(type='sandals', sw='sole', strap='sstrap'),
        ),
        props=[],
        headwear=dict(type='straw_hat', sw='straw'),
    ),
    # ---------------------------------------------------------------- Soldier, 22
    # A tired Malay Regiment private who lost his unit after Pasir Panjang / Bukit Chandu
    # (13-14 Feb 1942). KD shirt + shorts, hose tops + puttees, boots, 1937-pattern webbing,
    # plain Brodie helmet (NO warden "W"). No weapon.
    'soldier': dict(
        name='Soldier', file='npc-soldier', age=22,
        body=body(height=1.70, head_frac=0.285, head_aspect=(0.94, 0.91), leg_frac=0.46,
                  torso_w=0.25, torso_depth=0.78, hip_ratio=0.92, belly=0.0, neck_r=0.041,
                  arm_r=0.035, leg_r=0.044, hand_r=0.043, foot_len=0.155, arm_len=1.02, arm_spread=10),
        energy=0.75, walk_period=1.12, run_period=0.70, posture=dict(spine=4, chest=5, head=5),
        idle_arms='relaxed',
        palette={
            'skin': '#a8764f', 'skin_shade': '#93623f',
            'face': dict(kind='face', skin='#a8764f', blush='#aa604b'),
            'hair': dict(kind='strands', base='#1a1512'),
            'kd': dict(kind='twill', base='#b09a69', amt=0.05, grime=0.09),
            'kd_dk': dict(kind='twill', base='#9f8a5c', amt=0.05, grime=0.10),
            'hose': dict(kind='twill', base='#8c7e57', amt=0.04),
            'puttee': dict(kind='puttee', base='#7e7250', line='#5c5438'),
            'boot': '#2a1f18', 'brass': '#b8954a', 'button': '#8a7a52',
            'webbing': dict(kind='twill', base='#9a9674', amt=0.06, grime=0.06),
            'helmet': '#56563f', 'strap': '#6b6247', 'bottle': dict(kind='twill', base='#7c7a5b', amt=0.05),
        },
        hair=dict(style='short', sw='hair', scale=(1.035, 1.045, 1.03),
                  line=[(0, 44), (40, 34), (70, 8), (86, -14), (100, -12), (140, -30), (180, -38)]),
        face=dict(eye=0.92, eye_az=20, eye_el=-5, brow=dict(inner=3.2, outer=-2.8, arch=0.6, r=1.25),
                  mouth=dict(w=6.5, smile=1.2, el=-29), nose=1.05, blush=0.2, lids=True),
        outfit=dict(
            top=dict(sw='kd', hem='waist', ease=0.010, flare=1.0, sleeve=0.5, sleeve_ease=0.009,
                     sleeve_flare=1.08, cuff=dict(sw='kd', roll=True), collar='shirt', buttons='button', pockets=True),
            lower=dict(type='shorts', sw='kd_dk', hem=('knee', 0.035), top='waist', ease=0.006,
                       leg_ease=0.014, leg_flare=1.28),
            legwear=[dict(sw='hose', z0=('ankle', 0.0), z1=('knee', -0.03), ease=0.006, prio=1),
                     dict(sw='puttee', z0=('ankle', -0.01), z1=('ankle', 0.075), ease=0.011, prio=2)],
            feet=dict(type='boots', sw='boot'),
        ),
        props=[dict(type='webbing', sw='webbing', buckle='brass'), dict(type='bottle', side='R', sw='bottle', strap='webbing')],
        headwear=dict(type='helmet', sw='helmet', text=None, strap='strap'),
    ),
}

BONES = ['root', 'hips', 'spine', 'chest', 'head',
         'upperarm.L', 'forearm.L', 'hand.L', 'upperarm.R', 'forearm.R', 'hand.R',
         'thigh.L', 'shin.L', 'foot.L', 'thigh.R', 'shin.R', 'foot.R']
PARENT = {'hips': 'root', 'spine': 'hips', 'chest': 'spine', 'head': 'chest',
          'upperarm.L': 'chest', 'forearm.L': 'upperarm.L', 'hand.L': 'forearm.L',
          'upperarm.R': 'chest', 'forearm.R': 'upperarm.R', 'hand.R': 'forearm.R',
          'thigh.L': 'hips', 'shin.L': 'thigh.L', 'foot.L': 'shin.L',
          'thigh.R': 'hips', 'shin.R': 'thigh.R', 'foot.R': 'shin.R'}

# --------------------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------------------
def lerp(a, b, t): return a + (b - a) * t
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def smooth(a, b, x):
    t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t)
def hexrgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
def qs(n, q, mn=3):
    return max(mn, int(round(n * q)))
def qs_even(n, q, mn=4):
    v = max(mn, int(round(n * q))); return v + (v % 2)
def sgn(side): return 1.0 if side == 'L' else -1.0

class NS(dict):
    __getattr__ = dict.__getitem__
    def __setattr__(self, k, v): self[k] = v

def frame_z(origin, zdir, xhint=None):
    z = Vector(zdir).normalized()
    if xhint is None: xhint = Vector((1, 0, 0))
    xhint = Vector(xhint)
    if abs(xhint.normalized().dot(z)) > 0.98:
        xhint = Vector((0, 1, 0)) if abs(z.y) < 0.9 else Vector((1, 0, 0))
    x = (xhint - z * xhint.dot(z)).normalized()
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = Vector(origin)
    return M

def catmull(table, f):
    """smooth interpolation through (x, y) knots"""
    xs = [k[0] for k in table]; ys = [k[1] for k in table]
    if f <= xs[0]: return ys[0]
    if f >= xs[-1]: return ys[-1]
    i = max(0, min(len(xs) - 2, int(np.searchsorted(xs, f)) - 1))
    t = (f - xs[i]) / (xs[i + 1] - xs[i])
    p0 = ys[max(i - 1, 0)]; p1 = ys[i]; p2 = ys[i + 1]; p3 = ys[min(i + 2, len(ys) - 1)]
    t2 = t * t; t3 = t2 * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)

# --------------------------------------------------------------------------------------
# Mesh builder
# --------------------------------------------------------------------------------------
class MB:
    def __init__(self):
        self.co = []; self.w = []; self.faces = []
    def v(self, co, wt):
        co = Vector(co)
        self.co.append(co)
        self.w.append(wt(co) if callable(wt) else (wt if isinstance(wt, dict) else {wt: 1.0}))
        return len(self.co) - 1
    def f(self, idx, uvs, sw, mat):
        self.faces.append((tuple(idx), tuple(uvs), sw, mat))

GLOSS = 1  # material index for glossy bits

def mu(j, segs):
    """mirrored ('ping-pong') u around a lathe: 0 at the back seam, 1 at the front -> no UV seam split."""
    return 1.0 - abs(2.0 * ((j % segs) / segs) - 1.0) if j != segs else 0.0

def lathe(mb, rings, segs, frame, sw, wt, mat=0, theta0=pi / 2, iv=None, closed_hint=None):
    """rings: [(t, rx, ry)] ascending t along frame local Z. rx==ry==0 -> pole.
       iv: optional per-interval [(sw, v0, v1)]."""
    n = len(rings)
    ts = [r[0] for r in rings]
    t0, t1 = ts[0], ts[-1]
    gv = [(t - t0) / (t1 - t0 + 1e-12) for t in ts]
    rows = []
    for (t, rx, ry) in rings:
        if rx < 1e-7 and ry < 1e-7:
            rows.append([mb.v(frame @ Vector((0, 0, t)), wt)])
        else:
            row = []
            for j in range(segs):
                th = theta0 + 2 * pi * j / segs
                row.append(mb.v(frame @ Vector((rx * cos(th), ry * sin(th), t)), wt))
            rows.append(row)
    for i in range(n - 1):
        a, b = rows[i], rows[i + 1]
        if len(a) == 1 and len(b) == 1: continue
        if iv is not None: s, va, vb = iv[i]
        else: s, va, vb = sw, gv[i], gv[i + 1]
        for j in range(segs):
            j2 = (j + 1) % segs; ua = mu(j, segs); ub = mu(j + 1, segs)
            if len(a) == 1:
                mb.f((a[0], b[j2], b[j]), ((0.5, va), (ub, vb), (ua, vb)), s, mat)
            elif len(b) == 1:
                mb.f((a[j], a[j2], b[0]), ((ua, va), (ub, va), (0.5, vb)), s, mat)
            else:
                mb.f((a[j], a[j2], b[j2], b[j]), ((ua, va), (ub, va), (ub, vb), (ua, vb)), s, mat)
    return rows

def ellipsoid(mb, frame, radii, segs, rings, sw, wt, mat=0, theta0=pi / 2, el_range=(-90, 90)):
    rs = []; iv = []
    e0, e1 = el_range
    for i in range(rings + 1):
        el = radians(e0 + (e1 - e0) * i / rings)
        ce = cos(el) if abs(cos(el)) > 1e-6 else 0.0
        rs.append((radii[2] * sin(el), radii[0] * ce, radii[1] * ce))
    for i in range(rings):
        iv.append((sw, i / rings, (i + 1) / rings))
    return lathe(mb, rs, segs, frame, sw, wt, mat, theta0, iv)

def ell(mb, center, radii, segs, rings, sw, wt, mat=0, rot=None):
    F = Matrix.Translation(Vector(center))
    if rot is not None: F = F @ rot.to_4x4()
    return ellipsoid(mb, F, radii, segs, rings, sw, wt, mat)

def tube(mb, pts, rad, sides, sw, wt, mat=0, cap=True, closed=False):
    pts = [Vector(p) for p in pts]; n = len(pts)
    rads = list(rad) if isinstance(rad, (list, tuple)) else [rad] * n
    T = []
    for i in range(n):
        if closed:
            d = pts[(i + 1) % n] - pts[(i - 1) % n]
        else:
            d = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        T.append(d.normalized())
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = (up - T[0] * up.dot(T[0])).normalized()
    rows = []
    for i in range(n):
        N = (N - T[i] * N.dot(T[i])).normalized()
        B = T[i].cross(N)
        row = []
        for j in range(sides):
            th = 2 * pi * j / sides
            row.append(mb.v(pts[i] + (N * cos(th) + B * sin(th)) * rads[i], wt))
        rows.append(row)
    nseg = n if closed else n - 1
    for i in range(nseg):
        a = rows[i]; b = rows[(i + 1) % n]
        for j in range(sides):
            j2 = (j + 1) % sides
            va = (i % n) / max(1, n - 1) if not closed else mu(i, n)
            vb = ((i + 1) % n) / max(1, n - 1) if not closed else mu(i + 1, n)
            if not closed: va, vb = i / max(1, n - 1), (i + 1) / max(1, n - 1)
            mb.f((a[j], a[j2], b[j2], b[j]), ((mu(j, sides), va), (mu(j + 1, sides), va),
                                              (mu(j + 1, sides), vb), (mu(j, sides), vb)), sw, mat)
    if cap and not closed:
        c0 = mb.v(pts[0] - T[0] * rads[0] * 0.6, wt)
        c1 = mb.v(pts[-1] + T[-1] * rads[-1] * 0.6, wt)
        for j in range(sides):
            j2 = (j + 1) % sides
            mb.f((c0, rows[0][j2], rows[0][j]), ((0.5, 0.0), (mu(j + 1, sides), 0.0), (mu(j, sides), 0.0)), sw, mat)
            mb.f((rows[-1][j], rows[-1][j2], c1), ((mu(j, sides), 1.0), (mu(j + 1, sides), 1.0), (0.5, 1.0)), sw, mat)

def ribbon(mb, pts, nrms, width, thick, sw, wt, mat=0):
    """flat strap/cloth band along pts; nrms = surface normals (the band lies on the surface)."""
    pts = [Vector(p) for p in pts]; n = len(pts)
    rows = []
    for i in range(n):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        N = Vector(nrms[i]); N = (N - T * N.dot(T)).normalized()
        Sd = T.cross(N)
        w = width[i] if isinstance(width, (list, tuple)) else width
        c = pts[i]
        corners = [c + Sd * w / 2 + N * thick / 2, c - Sd * w / 2 + N * thick / 2,
                   c - Sd * w / 2 - N * thick / 2, c + Sd * w / 2 - N * thick / 2]
        rows.append([mb.v(q_, wt) for q_ in corners])
    uvs = (0.0, 0.5, 1.0, 0.5)
    for i in range(n - 1):
        a, b = rows[i], rows[i + 1]
        for j in range(4):
            j2 = (j + 1) % 4
            mb.f((a[j], a[j2], b[j2], b[j]), ((uvs[j], i / (n - 1)), (uvs[j2], i / (n - 1)),
                                              (uvs[j2], (i + 1) / (n - 1)), (uvs[j], (i + 1) / (n - 1))), sw, mat)
    for row, rev in ((rows[0], True), (rows[-1], False)):
        idx = list(reversed(row)) if rev else row
        mb.f(tuple(idx), ((0, 0), (0.5, 0), (1, 0), (0.5, 0)), sw, mat)

def drape(S, waypoints, n, out):
    """points + normals on the torso surface through (z, az) waypoints"""
    pts = []; nrm = []
    seg = len(waypoints) - 1
    for k in range(n + 1):
        t = k / n * seg; i = min(int(t), seg - 1); f = t - i
        z = lerp(waypoints[i][0], waypoints[i + 1][0], f); az = lerp(waypoints[i][1], waypoints[i + 1][1], f)
        o = lerp(waypoints[i][2] if len(waypoints[i]) > 2 else out, waypoints[i + 1][2] if len(waypoints[i + 1]) > 2 else out, f)
        p_, n_ = surf(S, z, az, o)
        pts.append(p_); nrm.append(n_ if z < S.z_nb - 0.01 * S.H else (n_ + Vector((0, 0, 1))).normalized())
    return pts, nrm

def rbox(mb, frame, size, r, sw, wt, mat=0, n=3, bend=0.0):
    """rounded box centred at frame origin, size along local x,y,z. bend curves local z by -bend*x^2."""
    h = Vector(size) * 0.5
    r = min(r, h.x * 0.99, h.y * 0.99, h.z * 0.99)
    inner = Vector((h.x - r, h.y - r, h.z - r))
    faces = [((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((-1, 0, 0), (0, -1, 0), (0, 0, 1)),
             ((0, 1, 0), (0, 0, 1), (1, 0, 0)), ((0, -1, 0), (0, 0, -1), (1, 0, 0)),
             ((0, 0, 1), (1, 0, 0), (0, 1, 0)), ((0, 0, -1), (-1, 0, 0), (0, 1, 0))]
    cache = {}
    def vert(p):
        key = (round(p.x, 5), round(p.y, 5), round(p.z, 5))
        if key in cache: return cache[key]
        qv = Vector((p.x * h.x, p.y * h.y, p.z * h.z))
        cl = Vector((clamp(qv.x, -inner.x, inner.x), clamp(qv.y, -inner.y, inner.y), clamp(qv.z, -inner.z, inner.z)))
        d = qv - cl
        fin = cl + d.normalized() * r if d.length > 1e-9 else qv
        fin.z -= bend * fin.x * fin.x
        idx = mb.v(frame @ fin, wt); cache[key] = idx; return idx
    for nrm, ua, va in faces:
        nrm = Vector(nrm); ua = Vector(ua); va = Vector(va)
        pos = [[nrm + ua * (-1 + 2 * i / n) + va * (-1 + 2 * j / n) for j in range(n + 1)] for i in range(n + 1)]
        grid = [[vert(pp) for pp in row] for row in pos]
        U = lambda pp: (0.5 + 0.5 * pp.x, 0.5 + 0.5 * pp.y)
        for i in range(n):
            for j in range(n):
                mb.f((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]),
                     (U(pos[i][j]), U(pos[i + 1][j]), U(pos[i + 1][j + 1]), U(pos[i][j + 1])), sw, mat)

# --------------------------------------------------------------------------------------
# Skeleton / proportions
# --------------------------------------------------------------------------------------
TORSO_TABLE = [(0.0, 0.0), (0.02, 0.46), (0.06, 0.70), (0.14, 0.88), (0.26, 0.97), (0.42, 0.97),
               (0.60, 1.0), (0.74, 1.0), (0.85, 0.92), (0.92, 0.76), (0.97, 0.55), (1.0, 0.40)]

def derive(C):
    b = C['body']; H = b['height']
    S = NS(H=H)
    hh = b['head_frac'] * H
    S.hh = hh
    S.head_r = Vector((hh * b['head_aspect'][0] / 2, hh * b['head_aspect'][1] / 2, hh / 2))
    S.head_c = Vector((0, 0, H - hh / 2))
    body_h = H - hh
    S.hip_z = b['leg_frac'] * body_h
    S.hw = b['torso_w'] * H / 2
    S.hd = S.hw * b['torso_depth']
    S.leg_r = b['leg_r'] * H
    S.arm_r = b['arm_r'] * H
    S.neck_r = b['neck_r'] * H
    S.crotch = S.hip_z - S.leg_r * 1.0
    S.z_nb = H - hh + 0.02 * H              # shoulder line meets neck
    S.z_top = H - hh + 0.10 * hh            # neck top (inside head)
    S.spine_z = S.hip_z + 0.30 * (S.z_nb - S.hip_z)
    S.chest_z = S.hip_z + 0.62 * (S.z_nb - S.hip_z)
    S.neck_z = S.z_nb - 0.01 * H
    S.belly = b['belly']; S.hip_ratio = b['hip_ratio']
    # shoulders
    S.z_sh = S.crotch + 0.83 * (S.z_nb - S.crotch)
    rx_sh, _ = body_r(S, S.z_sh)
    S.sh_x = rx_sh * 0.86
    # legs
    rxh, _ = body_r(S, S.crotch + 0.26 * (S.z_nb - S.crotch))
    S.leg_x = max(S.leg_r * 0.95, rxh - S.leg_r * 1.02)
    S.foot_h = 0.042 * H
    S.ankle_z = S.foot_h * 1.35
    S.knee_z = S.ankle_z + (S.hip_z - S.ankle_z) * 0.5
    S.l1 = S.hip_z - S.knee_z; S.l2 = S.knee_z - S.ankle_z
    S.leg_len = S.l1 + S.l2
    S.foot_len = b['foot_len'] * H
    S.foot_w = S.leg_r * 1.08
    # arms
    L = b['arm_len'] * (S.z_sh - S.hip_z)
    S.arm_total = L
    a = radians(b['arm_spread'])
    S.arm_spread = b['arm_spread']
    S.hand_r = b['hand_r'] * H
    S.up_len = 0.46 * (L - S.hand_r)
    S.fore_len = 0.54 * (L - S.hand_r) - S.hand_r * 0.4
    S.joints = {}
    for side in 'LR':
        s = sgn(side)
        sh = Vector((s * S.sh_x, 0, S.z_sh))
        d = Vector((s * sin(a), 0, -cos(a)))
        el = sh + d * S.up_len
        wr = el + d * S.fore_len
        tip = wr + d * (S.hand_r * 2.1)
        S.joints[side] = dict(sh=sh, el=el, wr=wr, tip=tip, dir=d)
    # anchors for hems
    S.anchors = dict(crotch=S.crotch, hip=S.hip_z, waist=S.hip_z + 0.22 * (S.z_nb - S.hip_z),
                     chest=S.chest_z, armpit=S.z_sh - 0.03 * H, neck=S.z_nb,
                     knee=S.knee_z, ankle=S.ankle_z, shin_mid=0.5 * (S.knee_z + S.ankle_z),
                     thigh_mid=0.5 * (S.hip_z + S.knee_z))
    return S

def anchor(S, spec):
    if isinstance(spec, (list, tuple)): return S.anchors[spec[0]] + spec[1] * S.H
    return S.anchors[spec]

def body_mult(S, f):
    m = catmull(TORSO_TABLE, clamp(f))
    m += S.belly * smooth(0.25, 0.45, f) * (1 - smooth(0.5, 0.72, f))
    return max(0.0, m)

def body_r(S, z):
    """bare torso radii (rx, ry) at height z; neck above z_nb."""
    if z >= S.z_nb:
        return S.neck_r, S.neck_r * 0.95
    f = (z - S.crotch) / (S.z_nb - S.crotch)
    m = body_mult(S, f)
    mx = m * lerp(S.hip_ratio, 1.0, smooth(0.25, 0.6, f))
    rx = S.hw * mx; ry = S.hd * m
    if f > 0.9:  # blend into neck radius
        k = smooth(0.9, 1.0, f)
        rx = lerp(rx, max(rx, S.neck_r), k); ry = lerp(ry, max(ry, S.neck_r * 0.95), k)
    return rx, ry

# --------------------------------------------------------------------------------------
# Weight functions
# --------------------------------------------------------------------------------------
def chain_w(z, S):
    """torso chain hips/spine/chest/head by height."""
    H = S.H; b = 0.05 * H
    def mix(a, bn, t):
        t = clamp(t)
        return {a: 1 - t, bn: t} if 0 < t < 1 else ({a: 1.0} if t <= 0 else {bn: 1.0})
    if z < S.spine_z - b: return {'hips': 1.0}
    if z < S.spine_z + b: return mix('hips', 'spine', (z - (S.spine_z - b)) / (2 * b))
    if z < S.chest_z - b: return {'spine': 1.0}
    if z < S.chest_z + b: return mix('spine', 'chest', (z - (S.chest_z - b)) / (2 * b))
    if z < S.neck_z: return {'chest': 1.0}
    return mix('chest', 'head', (z - S.neck_z) / (0.03 * H))

def body_w_fn(S):
    def f(co):
        z = co.z
        if z >= S.hip_z: return chain_w(z, S)
        a = clamp((S.hip_z - z) / (S.hip_z - S.knee_z)) ** 0.9
        bk = clamp((S.knee_z - z) / (S.knee_z - S.ankle_z))
        sL = smooth(-1.0, 1.0, co.x / (S.leg_x * 1.4))
        sR = 1 - sL
        w = {'hips': 1 - a}
        for side, sv in (('L', sL), ('R', sR)):
            w['thigh.' + side] = a * (1 - bk) * sv
            w['shin.' + side] = a * bk * sv
        return w
    return f

def arm_w_fn(S, side):
    J = S.joints[side]
    L = (J['sh'] - J['wr']).length
    se = (J['el'] - J['wr']).length / L
    def f(co):
        s = (co - J['wr']).dot(-J['dir']) / L   # 0 wrist .. 1 shoulder
        bl = 0.07
        if s > se + bl:
            w = {'upperarm.' + side: 1.0}
            k = smooth(0.9, 1.08, s) * 0.35
            if k > 0: w = {'upperarm.' + side: 1 - k, 'chest': k}
            return w
        if s < se - bl: return {'forearm.' + side: 1.0}
        t = (s - (se - bl)) / (2 * bl)
        return {'forearm.' + side: 1 - t, 'upperarm.' + side: t}
    return f

def leg_w_fn(S, side):
    def f(co):
        z = co.z; bl = 0.03 * S.H
        if z > S.knee_z + bl:
            k = smooth(S.hip_z - 0.02 * S.H, S.hip_z + 0.05 * S.H, z) * 0.5
            return {'thigh.' + side: 1 - k, 'hips': k} if k > 0 else {'thigh.' + side: 1.0}
        if z < S.knee_z - bl: return {'shin.' + side: 1.0}
        t = (z - (S.knee_z - bl)) / (2 * bl)
        return {'shin.' + side: 1 - t, 'thigh.' + side: t}
    return f

# --------------------------------------------------------------------------------------
# Body parts
# --------------------------------------------------------------------------------------
def build_torso(mb, S, C, q):
    H = S.H; o = C['outfit']; top = o['top']; low = o.get('lower')
    segs = qs_even(22, q, 12)
    top_hem = anchor(S, top['hem'])
    top_hi = anchor(S, top['top_z']) if top.get('top_z') else S.z_nb
    skirtish = low is not None and low['type'] in ('skirt', 'sarong')
    low_hem = anchor(S, low['hem']) if (low and skirtish) else S.crotch
    low_top = anchor(S, low['top']) if low else S.crotch

    def garment_r(z, ease, flare, hem):
        e = ease * H
        if z >= S.hip_z:
            rx, ry = body_r(S, z); return rx + e, ry + e
        rx, ry = body_r(S, S.hip_z)
        if hem < S.hip_z - 1e-6:
            k = clamp((S.hip_z - z) / (S.hip_z - hem)) ** 1.25
        else:
            k = 0.0
        m = lerp(1.0, flare, k)
        return rx * m + e, ry * m + e

    def layer_at(z):
        if top_hem <= z <= top_hi: return 'top'
        if low and low_hem <= z <= low_top: return 'low'
        return 'skin'

    def radius(key, z):
        if key == 'top': return garment_r(z, top['ease'], top.get('flare', 1.0), top_hem)
        if key == 'low':
            if skirtish: return garment_r(z, low['ease'], low.get('flare', 1.0), low_hem)
            rx, ry = body_r(S, z); e = low['ease'] * H; return rx + e, ry + e
        return body_r(S, z)

    def sw_of(key):
        return top['sw'] if key == 'top' else (low['sw'] if key == 'low' else 'skin')

    z_bottom = min(top_hem, low_hem, S.crotch)
    brk = sorted(set([z_bottom, top_hem, top_hi, S.z_nb, S.z_top] +
                     ([low_top, low_hem] if low else [])))
    brk = [z for z in brk if z_bottom - 1e-9 <= z <= S.z_top + 1e-9]
    bands = []
    for z0, z1 in zip(brk[:-1], brk[1:]):
        if z1 - z0 < 1e-5: continue
        key = layer_at(0.5 * (z0 + z1))
        if bands and bands[-1][2] == key: bands[-1] = (bands[-1][0], z1, key)
        else: bands.append((z0, z1, key))
    # candidate sample heights
    dz = 0.042 * H / max(q, 0.35)
    cands = list(np.arange(z_bottom, S.z_top, dz))
    span = S.z_nb - S.crotch
    for f in (0.006, 0.03, 0.09, 0.17, 0.88, 0.95):
        cands.append(S.crotch + f * span)
    cands = sorted(cands)
    rings = []; iv = []
    prev_key = None
    for bi, (z0, z1, key) in enumerate(bands):
        zs = [z0] + [z for z in cands if z0 + 0.004 * H < z < z1 - 0.004 * H] + [z1]
        band_rings = []
        for z in zs:
            rx, ry = radius(key, z)
            band_rings.append((z, rx, ry))
        append_from = 0
        if rings:
            # lip between previous band's last ring and this band's first
            pz, prx, pry = rings[-1]
            if abs(prx - band_rings[0][1]) > 1e-5:
                outer = prev_key if prx > band_rings[0][1] else key
                zz = band_rings[0][0] + 0.0004 * H
                band_rings[0] = (zz, band_rings[0][1], band_rings[0][2])
                iv.append((sw_of(outer), 0.0, 0.02))
            else:
                band_rings[0] = rings[-1]; append_from = 1
        rings.extend(band_rings[append_from:])
        for k in range(len(band_rings) - 1):
            za = band_rings[k][0]; zb = band_rings[k + 1][0]
            iv.append((sw_of(key), clamp((za - z0) / (z1 - z0)), clamp((zb - z0) / (z1 - z0))))
        prev_key = key
    rings2 = rings
    # sanity: number of intervals should equal len(rings)-1
    assert len(iv) == len(rings2) - 1, (len(iv), len(rings2))
    # bottom closure
    if rings2[0][1] > 1e-6:
        rings2.insert(0, (rings2[0][0] - 0.002 * H, 0.0, 0.0))
        iv.insert(0, (iv[0][0], 0.0, 0.02))
    rings2.append((S.z_top + 0.004 * H, 0.0, 0.0))
    iv.append(('skin', 0.98, 1.0))
    lathe(mb, rings2, segs, Matrix.Identity(4), None, body_w_fn(S), 0, pi / 2, iv)
    # store for surface queries (max radius per z)
    prof = {}
    for z, rx, ry in rings2:
        k = round(z, 5)
        if k not in prof or prof[k][0] < rx: prof[k] = (rx, ry)
    zs = sorted(prof.keys())
    S.tz = np.array(zs); S.trx = np.array([prof[z][0] for z in zs]); S.try_ = np.array([prof[z][1] for z in zs])
    S.top_hem = top_hem; S.low_hem = low_hem

def torso_r(S, z):
    return float(np.interp(z, S.tz, S.trx)), float(np.interp(z, S.tz, S.try_))

def surf(S, z, az, out=0.0):
    rx, ry = torso_r(S, z)
    a = radians(az)
    p = Vector((rx * sin(a), -ry * cos(a), z))
    n = Vector((sin(a) / max(rx, 1e-4), -cos(a) / max(ry, 1e-4), 0)).normalized()
    return p + n * out, n

def build_arm(mb, S, C, q, side):
    H = S.H; top = C['outfit']['top']; J = S.joints[side]
    segs = qs_even(12, q, 8)
    L = (J['sh'] - J['wr']).length
    F = frame_z(J['wr'], -J['dir'], Vector((0, 1, 0)))
    r = S.arm_r
    sleeve = top.get('sleeve', 0.0)
    t_cuff = L * (1 - sleeve)
    se = top.get('sleeve_ease', 0.008) * H
    sfl = top.get('sleeve_flare', 1.0)
    cuff = top.get('cuff')
    def rad(t): return r * lerp(0.80, 1.0, clamp(t / L)) * (1 - 0.06 * math.exp(-((t - (J['el'] - J['wr']).length) / (0.04 * H)) ** 2))
    ts = sorted(set([x for x in np.linspace(0, L, qs(8, q, 5) + 1)] + ([t_cuff] if 0 < sleeve < 1.0 else [])))
    rings = []; iv = []
    def add(t, rx, sw, v0=0.0, v1=1.0):
        rings.append((t, rx, rx * 0.96))
    # wrist cap (inside hand)
    seq = []
    seq.append((-0.35 * r, 0.0, 'skin'))
    seq.append((-0.1 * r, r * 0.62, 'skin'))
    for t in ts:
        in_sleeve = sleeve > 0 and t >= t_cuff - 1e-6
        if in_sleeve:
            k = clamp((t - t_cuff) / max(L - t_cuff, 1e-6))
            rx = rad(t) + se * lerp(1.0, 0.6, k)
            rx *= lerp(sfl, 1.0, k)
            if abs(t - t_cuff) < 1e-6:
                seq.append((t, rad(t), 'skin'))       # skin ring at cuff
                if cuff and cuff.get('roll'):
                    seq.append((t + 0.0003 * H, rad(t) + se * 2.2, cuff['sw']))
                    seq.append((t + 0.03 * H, rad(t) + se * 2.2, cuff['sw']))
                    seq.append((t + 0.0306 * H, rx, cuff['sw']))
                    continue
                seq.append((t + 0.0003 * H, rx, top['sw']))
                continue
            if cuff and cuff.get('roll') and t < t_cuff + 0.031 * H: continue
            seq.append((t, rx, top['sw']))
        else:
            seq.append((t, rad(t), 'skin'))
    # shoulder cap
    topsw = top['sw'] if sleeve > 0 else 'skin'
    rt = seq[-1][1]
    for k in (0.45, 0.8):
        seq.append((L + rt * sin(k * pi / 2) * 0.9, rt * cos(k * pi / 2), topsw))
    seq.append((L + rt * 0.95, 0.0, topsw))
    rings = [(t, rx, rx * 0.96) for (t, rx, _) in seq]
    for i in range(len(seq) - 1):
        sw_i = seq[i + 1][2] if seq[i + 1][2] == seq[i][2] else (seq[i + 1][2] if seq[i + 1][1] > seq[i][1] else seq[i][2])
        iv.append((sw_i, i / (len(seq) - 1), (i + 1) / (len(seq) - 1)))
    lathe(mb, rings, segs, F, None, arm_w_fn(S, side), 0, 0.0, iv)
    S.setdefault('arm_frames', {})[side] = dict(F=F, L=L, rad=rad, se=se)
    # hand: soft mitten + thumb
    hr = S.hand_r
    hc = J['wr'] + J['dir'] * hr * 1.0
    Fh = frame_z(hc, J['dir'], Vector((0, 1, 0)))  # local z along arm, x ~ forward (-Y ... +Y)
    ell(mb, Fh.translation, (hr * 0.80, hr * 0.92, hr * 1.02), qs_even(10, q, 8), qs(7, q, 5), 'skin',
        'hand.' + side, 0, rot=Fh.to_3x3())
    tc = hc + Vector((0, -hr * 0.78, 0)) + J['dir'] * (-hr * 0.30) + Vector((-sgn(side) * hr * 0.10, 0, 0))
    ell(mb, tc, (hr * 0.34, hr * 0.34, hr * 0.46), qs_even(8, q, 6), qs(5, q, 4), 'skin', 'hand.' + side, 0,
        rot=Euler((radians(-30), 0, 0)).to_matrix())

def build_leg(mb, S, C, q, side):
    H = S.H; o = C['outfit']; low = o.get('lower') or {}
    segs = qs_even(12, q, 8)
    s_ = sgn(side); x = s_ * S.leg_x
    z0 = S.ankle_z; z1 = S.hip_z; L = z1 - z0
    r = S.leg_r
    skirt = low.get('type') in ('skirt', 'sarong')
    def rad(z):
        t = clamp((z - z0) / L)
        base = r * lerp(0.70, 1.0 if not skirt else 0.80, t ** 0.8)
        knee = 1 + 0.05 * math.exp(-((z - S.knee_z) / (0.035 * H)) ** 2)
        return base * knee
    layers = []   # (z_lo, z_hi, sw, ease, flare, prio)
    if low.get('type') in ('trousers', 'shorts'):
        layers.append((anchor(S, low['hem']), z1 + 1.0, low['sw'], low.get('leg_ease', 0.006) * H,
                       low.get('leg_flare', 1.0), 3))
    for lw in o.get('legwear', []):
        layers.append((anchor(S, lw['z0']), anchor(S, lw['z1']), lw['sw'], lw.get('ease', 0.006) * H, 1.0, lw.get('prio', 1)))
    def layer_at(z):
        best = None
        for L_ in layers:
            if L_[0] - 1e-6 <= z <= L_[1] + 1e-6 and (best is None or L_[5] > best[5]): best = L_
        return best
    def radius(Ly, z):
        if Ly is None: return rad(z)
        lo, hi, sw, e, fl, _ = Ly
        k = clamp((z - lo) / max(min(hi, z1) - lo, 1e-6))
        return (rad(z) + e) * lerp(fl, 1.0, smooth(0, 0.8, k))
    brk = sorted(set([z0, z1] + [clamp(v, z0, z1) for L_ in layers for v in (L_[0], L_[1])]))
    cand = list(np.linspace(z0, z1, qs(8, q, 5) + 1))
    seq = [(z0 - 0.4 * r, 0.0, 'skin'), (z0 - 0.15 * r, rad(z0) * 0.7, 'skin')]
    first = True
    for za, zb in zip(brk[:-1], brk[1:]):
        if zb - za < 1e-5: continue
        Ly = layer_at(0.5 * (za + zb)); sw = Ly[2] if Ly else 'skin'
        zs = [za] + [z for z in cand if za + 0.004 * H < z < zb - 0.004 * H] + [zb]
        ring = [(z, radius(Ly, z), sw) for z in zs]
        if not first:
            pz, pr_, psw = seq[-1]
            if abs(pr_ - ring[0][1]) > 1e-5:
                ring[0] = (ring[0][0] + 0.0003 * H, ring[0][1], sw if ring[0][1] > pr_ else psw)
                seq.append(ring[0]); ring = ring[1:]
                ring = [(z, rr, sw) for (z, rr, _) in ring]
            else:
                ring = ring[1:]
        seq.extend(ring); first = False
    # the first real ring after the wrist-like cap should carry its layer's swatch
    rt = seq[-1][1]; tsw = seq[-1][2]
    for k in (0.4, 0.75):
        seq.append((z1 + rt * sin(k * pi / 2) * 0.8, rt * cos(k * pi / 2), tsw))
    seq.append((z1 + rt * 0.85, 0.0, tsw))
    rings = [(z, rx, rx * 0.98) for (z, rx, _) in seq]
    iv = []
    for i in range(len(seq) - 1):
        sw_i = seq[i + 1][2]
        iv.append((sw_i, i / (len(seq) - 1), (i + 1) / (len(seq) - 1)))
    F = Matrix.Translation(Vector((x, 0, 0)))
    lathe(mb, rings, segs, F, None, leg_w_fn(S, side), 0, pi / 2, iv)

def build_foot(mb, S, C, q, side):
    H = S.H; ft = C['outfit']['feet']; s = sgn(side); x = s * S.leg_x
    typ = ft['type']
    sole_t = 0.016 * H if typ in ('sandals', 'flipflops') else 0.0
    fl = S.foot_len; fw = S.foot_w; fh = S.foot_h
    if typ == 'shoes': fw *= 1.12; fh *= 1.12; fl *= 1.04
    if typ == 'boots': fw *= 1.16; fh *= 1.22; fl *= 1.05
    if typ == 'slippers': fw *= 1.04; fh *= 0.92
    c = Vector((x + s * fw * 0.08, -fl * 0.2, fh + sole_t))
    sw = ft['sw'] if typ in ('shoes', 'slippers', 'boots') else 'skin'
    ell(mb, c, (fw, fl * 0.5, fh), qs_even(12, q, 8), qs(7, q, 5), sw, 'foot.' + side, 0)
    if typ == 'flipflops':
        ell(mb, Vector((c.x, c.y - fl * 0.02, sole_t * 0.55)), (fw * 1.06, fl * 0.53, sole_t * 0.6),
            qs_even(12, q, 8), qs(4, q, 3), ft['sw'], 'foot.' + side, 0)
        toe = Vector((c.x - s * fw * 0.25, c.y - fl * 0.36, sole_t + fh * 0.5))
        for sd in (1, -1):
            end = Vector((c.x + sd * fw * 0.98, c.y + fl * 0.02, sole_t + fh * 0.35))
            midp = toe.lerp(end, 0.5) + Vector((0, 0, fh * 0.55))
            tube(mb, [toe, midp, end], 0.0065 * H, qs(6, q, 4), ft.get('strap', ft['sw']), 'foot.' + side, 0)
    if typ == 'sandals':
        ell(mb, Vector((c.x, c.y - fl * 0.02, sole_t * 0.55)), (fw * 1.06, fl * 0.53, sole_t * 0.6),
            qs_even(12, q, 8), qs(4, q, 3), ft['sw'], 'foot.' + side, 0)
        stc = ft.get('strap', ft['sw'])
        pts = []
        for k in range(7):
            a = radians(-80 + 160 * k / 6)
            pts.append(Vector((c.x + fw * 1.02 * sin(a), c.y - fl * 0.12, sole_t + fh * (1.0 + 0.95 * cos(a)) * 0.98)))
        tube(mb, pts, 0.006 * H, qs(6, q, 4), stc, 'foot.' + side, 0, cap=True)

def head_pt(S, az, el, out=0.0):
    a = radians(az); e = radians(el)
    d = Vector((sin(a) * cos(e), -cos(a) * cos(e), sin(e)))
    R = S.head_r
    p = S.head_c + Vector((R.x * d.x, R.y * d.y, R.z * d.z))
    n = Vector((d.x / R.x, d.y / R.y, d.z / R.z)).normalized()
    return p + n * out, n

def feature_frame(p, n):
    return frame_z(p, n, Vector((0, 0, 1)).cross(n) if abs(n.z) < 0.95 else Vector((1, 0, 0)))

def build_head(mb, S, C, q):
    H = S.H; hh = S.hh; R = S.head_r; fc = C['face']
    ellipsoid(mb, Matrix.Translation(S.head_c), (R.x, R.y, R.z), qs_even(26, q, 14), qs(16, q, 10), 'face', 'head', 0)
    # ears
    for s in (1, -1):
        p, n = head_pt(S, s * 88, -8, -0.02 * hh)
        F = frame_z(p, n, Vector((0, 0, 1)))
        ell(mb, p, (0.075 * hh, 0.11 * hh, 0.05 * hh), qs_even(10, q, 6), qs(6, q, 4), 'skin', 'head', 0,
            rot=Matrix((F.col[0].xyz, F.col[1].xyz, F.col[2].xyz)).transposed() if False else F.to_3x3() @ Matrix.Rotation(radians(90), 3, 'Z'))
    # nose
    p, n = head_pt(S, 0, -14)
    ns = fc.get('nose', 1.0)
    ell(mb, p - n * 0.01 * hh, (0.045 * hh * ns, 0.035 * hh * ns, 0.04 * hh * ns), qs_even(10, q, 6), qs(6, q, 4),
        'skin_shade', 'head', 0, rot=feature_frame(p, n).to_3x3())
    # eyes
    es = fc.get('eye', 1.0)
    ew, eh, ed = 0.060 * hh * es, 0.077 * hh * es, 0.034 * hh
    for s in (1, -1):
        p, n = head_pt(S, s * fc['eye_az'], fc['eye_el'])
        F = feature_frame(p, n)
        ell(mb, p - n * ed * 0.25, (ew, eh, ed), qs_even(12, q, 8), qs(8, q, 5), 'eye', 'head', GLOSS, rot=F.to_3x3())
        hp = p + F.col[1].xyz * eh * 0.38 + F.col[0].xyz * (s * ew * 0.30) + n * ed * 0.72
        ell(mb, hp, (ew * 0.30, ew * 0.30, ed * 0.3), qs_even(6, q, 4), qs(4, q, 3), 'eye_hi', 'head', GLOSS,
            rot=F.to_3x3())
        # brows
        br = fc['brow']; bsw = br.get('sw', C['hair']['sw'])
        pts = []
        nb = qs(6, q, 4)
        for k in range(nb + 1):
            t = k / nb
            az = s * (fc['eye_az'] - 8 + 17 * t)
            el = fc['eye_el'] + 15.0 * es ** 0.5 + lerp(br['inner'], br['outer'], t) + br['arch'] * sin(pi * t)
            pp, _ = head_pt(S, az, el, 0.004 * hh)
            pts.append(pp)
        tube(mb, pts, [0.0165 * hh * br['r'] * (0.8 + 0.4 * sin(pi * min(1, k / nb + 0.25))) for k in range(nb + 1)],
             qs(6, q, 4), bsw, 'head', 0)
        if fc.get('smile_lines'):
            pts = []
            for k in range(4):
                t = k / 3
                pp, _ = head_pt(S, s * (fc['eye_az'] + 14 + 2 * t), fc['eye_el'] - 1 - 6 * t, 0.002 * hh)
                pts.append(pp)
            tube(mb, pts, 0.005 * hh, 4, 'skin_shade', 'head', 0)
        if fc.get('lids'):
            lp = p + F.col[1].xyz * eh * 0.62 + n * ed * 0.05
            ell(mb, lp, (ew * 1.18, eh * 0.52, ed * 1.35), qs_even(10, q, 6), qs(5, q, 4), 'skin_shade', 'head', 0,
                rot=F.to_3x3() @ Matrix.Rotation(radians(s * -8), 3, 'Z'))
        if fc.get('lashes'):
            pp, nn = head_pt(S, s * (fc['eye_az'] + 5.5 * es), fc['eye_el'] + 4.5 * es, 0.0)
            tube(mb, [pp, pp + nn * 0.012 * hh + Vector((s * 0.018 * hh, 0, 0.012 * hh))], 0.006 * hh, 4, 'eye', 'head', 0)
    # glasses: round wire frames, bridge and temples back to the ears
    gl = fc.get('glasses')
    if gl:
        gsw = gl.get('sw', 'frame'); gr = 0.0065 * hh
        for s in (1, -1):
            p, n = head_pt(S, s * fc['eye_az'], fc['eye_el'] - 0.5)
            F = feature_frame(p, n)
            c = p + n * 0.03 * hh
            ring = []
            nr = qs(16, q, 10)
            for k in range(nr):
                a = 2 * pi * k / nr
                ring.append(c + F.col[0].xyz * (ew * 1.75 * cos(a)) + F.col[1].xyz * (eh * 1.35 * sin(a)))
            tube(mb, ring, gr, 4, gsw, 'head', GLOSS, closed=True)
            outer = c + F.col[0].xyz * (s * ew * 1.75)
            ep, _ = head_pt(S, s * 84, fc['eye_el'] + 2, 0.01 * hh)
            mid, _ = head_pt(S, s * 62, fc['eye_el'] + 2, 0.02 * hh)
            tube(mb, [outer, mid, ep], gr, 4, gsw, 'head', GLOSS)
        pl, nl = head_pt(S, fc['eye_az'], fc['eye_el'] - 0.5)
        pr_, nr_ = head_pt(S, -fc['eye_az'], fc['eye_el'] - 0.5)
        Fl = feature_frame(pl, nl); Fr = feature_frame(pr_, nr_)
        il = pl + nl * 0.03 * hh - Fl.col[0].xyz * ew * 1.75
        ir = pr_ + nr_ * 0.03 * hh + Fr.col[0].xyz * ew * 1.75
        bm_, _ = head_pt(S, 0, fc['eye_el'] + 2, 0.045 * hh)
        tube(mb, [il, bm_, ir], gr, 4, gsw, 'head', GLOSS)
    # mouth
    m = fc['mouth']; nm = qs(8, q, 5)
    pts = []
    for k in range(nm + 1):
        t = -1 + 2 * k / nm
        pp, _ = head_pt(S, m['w'] * t, m['el'] + m['smile'] * t * t, 0.003 * hh)
        pts.append(pp)
    if m.get('open'):
        # small open smile: a dark D-shaped pad + upper lip line
        p, n = head_pt(S, 0, m['el'] + m['smile'] * 0.25)
        F = feature_frame(p, n)
        ell(mb, p - n * 0.006 * hh + F.col[1].xyz * (-0.012 * hh), (m['w'] * 0.0072 * hh, 0.028 * hh, 0.012 * hh),
            qs_even(10, q, 6), qs(5, q, 4), 'mouth', 'head', 0, rot=F.to_3x3())
    tube(mb, pts, 0.0135 * hh, qs(6, q, 4), 'mouth', 'head', 0)
    # moustache
    mo = fc.get('moustache')
    if mo:
        nm = qs(8, q, 6); pts = []; rr = []
        w = 13 if mo == 'thick' else 11
        th = 0.022 * hh if mo == 'thick' else 0.012 * hh
        for k in range(nm + 1):
            t = -1 + 2 * k / nm
            pp, _ = head_pt(S, w * t, -21 - (4.5 if mo == 'thick' else 3.0) * t * t + 1.2 * (1 - abs(t)), th * 0.35)
            pts.append(pp); rr.append(th * (1.0 - 0.55 * t * t))
        tube(mb, pts, rr, qs(6, q, 5), C['hair']['sw'], 'head', 0)

def hair_cap(mb, S, line, scale, segs, rings, sw, wt='head', lip=0.955, top_el=90.0):
    """hair shell over the skull with a designed hairline: line = [(|az| deg, lowest elevation deg)]"""
    R = S.head_r; Cc = S.head_c
    cols = []
    for j in range(segs):
        th = pi / 2 + 2 * pi * j / segs
        az = degrees(atan2(cos(th), -sin(th)))
        cols.append((th, catmull(line, abs(az))))
    def P_(th, el, sc):
        e = radians(el)
        return Cc + Vector((R.x * scale[0] * sc * cos(e) * cos(th), R.y * scale[1] * sc * cos(e) * sin(th),
                            R.z * scale[2] * sc * sin(e)))
    rows = []
    rows.append([mb.v(P_(th, el - 2.0, lip), wt) for th, el in cols])      # tucked lip (inside skull)
    for i in range(rings):
        k = i / rings
        rows.append([mb.v(P_(th, lerp(el, top_el, k ** 1.15), 1.0 if i else 0.985), wt) for th, el in cols])
    if top_el < 89.0:   # open crown (thinning hair): tuck the upper edge into the skull too
        rows.append([mb.v(P_(th, top_el, 0.99), wt) for th, el in cols])
        rows.append([mb.v(P_(th, top_el + 2.0, lip), wt) for th, el in cols])
    top = mb.v(Cc + Vector((0, 0, R.z * scale[2] * (1.0 if top_el >= 89.0 else lip))), wt)
    n = len(rows)
    for i in range(n - 1):
        a, b = rows[i], rows[i + 1]
        for j in range(segs):
            j2 = (j + 1) % segs
            mb.f((a[j], a[j2], b[j2], b[j]), ((mu(j, segs), i / n), (mu(j + 1, segs), i / n), (mu(j + 1, segs), (i + 1) / n),
                                              (mu(j, segs), (i + 1) / n)), sw, 0)
    for j in range(segs):
        j2 = (j + 1) % segs
        mb.f((rows[-1][j], rows[-1][j2], top), ((mu(j, segs), (n - 1) / n), (mu(j + 1, segs), (n - 1) / n), (0.5, 1.0)), sw, 0)

def build_hair(mb, S, C, q):
    hs = C['hair']; H = S.H; hh = S.hh; R = S.head_r; st = hs['style']; sw = hs['sw']
    if st != 'none':
        hair_cap(mb, S, hs['line'], hs['scale'], qs_even(26, q, 14), qs(9, q, 6), sw, top_el=hs.get('top_el', 90.0))
    for (az0, az1, el0, el1) in hs.get('wisps', []):
        pts = []
        for k in range(5):
            t = k / 4
            pp, _ = head_pt(S, lerp(az0, az1, t), lerp(el0, el1, t), 0.012 * hh * (1 - 0.4 * t))
            pts.append(pp)
        tube(mb, pts, [0.014 * hh * (1 - 0.6 * k / 4) for k in range(5)], 5, sw, 'head', 0)
    if st == 'bun':
        bc = S.head_c + Vector((0, R.y * 1.04, -R.z * 0.08))
        ell(mb, bc, (R.x * 0.36, R.y * 0.30, R.z * 0.31), qs_even(14, q, 8), qs(9, q, 5), sw, 'head', 0)
        pc = bc + Vector((0, R.y * 0.16, R.z * 0.05))
        tube(mb, [pc + Vector((-R.x * 0.48, 0, -R.z * 0.06)), pc + Vector((R.x * 0.52, 0, R.z * 0.08))],
             0.008 * hh, qs(6, q, 4), hs.get('pin', sw), 'head', 0)
    if st == 'crop':
        # soft fringe: three felt tufts along the front hairline
        for k, az in enumerate((-16, 0, 16)):
            el = catmull(hs['line'], abs(az)) + 4
            p, n = head_pt(S, az, el, 0.012 * hh)
            F = feature_frame(p, n)
            ell(mb, p, (0.07 * hh, 0.045 * hh, 0.03 * hh), qs_even(10, q, 6), qs(5, q, 4), sw, 'head', 0,
                rot=F.to_3x3() @ Matrix.Rotation(radians(-10 * (k - 1)), 3, 'Z'))
    if st == 'plaits':
        for s in (1, -1):
            pts = [S.head_c + Vector((s * R.x * 0.62, R.y * 0.62, -R.z * 0.45)),
                   S.head_c + Vector((s * R.x * 0.66, R.y * 0.74, -R.z * 0.85)),
                   Vector((s * (S.hw * 0.95), S.hd * 1.15, S.z_nb - 0.02 * H)),
                   Vector((s * (S.hw * 0.9), S.hd * 1.2, S.z_sh - 0.06 * H)),
                   Vector((s * (S.hw * 0.86), S.hd * 1.18, S.chest_z - 0.02 * H))]
            # braid: overlapping, alternating-tilt lobes along a smooth path
            nbd = qs(9, q, 6)
            path = []
            for k in range(nbd):
                t = k / (nbd - 1) * (len(pts) - 1)
                i = min(int(t), len(pts) - 2); f = t - i
                path.append(pts[i].lerp(pts[i + 1], f))
            for k, pp in enumerate(path):
                wt = {'head': 1.0} if pp.z > S.H - S.hh * 0.9 else {'chest': 1.0}
                rr = 0.052 * hh * (1 - 0.3 * k / nbd)
                ell(mb, pp, (rr, rr * 0.9, rr * 1.25), qs_even(8, q, 6), qs(5, q, 4), sw, wt, 0,
                    rot=Euler((0, radians(18 if k % 2 else -18), 0)).to_matrix())
            # ribbon bow at the end
            e = path[-1] + Vector((0, 0.005 * H, -0.05 * hh))
            for d in (-1, 1):
                ell(mb, e + Vector((d * 0.03 * hh, 0.004 * H, 0)), (0.035 * hh, 0.014 * hh, 0.025 * hh),
                    qs_even(8, q, 6), qs(5, q, 4), hs.get('ribbon', sw), {'chest': 1.0}, 0,
                    rot=Euler((0, radians(d * 25), 0)).to_matrix())
            tube(mb, [e, e + Vector((0, 0.002, -0.05 * hh))], 0.01 * hh, 4, hs.get('ribbon', sw), {'chest': 1.0}, 0)

def build_headwear(mb, S, C, q):
    hw = C.get('headwear')
    if not hw: return
    H = S.H; hh = S.hh; R = S.head_r
    if hw['type'] == 'helmet':
        # Mk II "Brodie": shallow dome + wide brim, tilted slightly back
        Rd = R.x * 1.07; hd = R.z * 0.84; Rb = R.x * 1.55; th = 0.018 * H
        base = S.head_c + Vector((0, R.y * 0.05, R.z * 0.30))
        rot = Matrix.Rotation(radians(-7), 4, 'X')
        F = Matrix.Translation(base) @ rot
        prof = [(-0.004, 0.0, 0.0), (0.0, Rd * 0.9, Rd * 0.9 * 0.96), (0.0005, Rb * 0.97, Rb * 0.93),
                (th * 0.8, Rb, Rb * 0.96), (th * 1.6, Rb * 0.93, Rb * 0.9), (th * 2.2, Rd * 1.03, Rd * 0.99)]
        nd = qs(7, q, 4)
        for k in range(1, nd + 1):
            a = k / nd * (pi / 2)
            prof.append((th * 2.2 + hd * sin(a), Rd * 1.03 * cos(a) if k < nd else 0.0, Rd * 0.99 * cos(a) if k < nd else 0.0))
        lathe(mb, prof, qs_even(24, q, 14), F, hw['sw'], 'head', 0)
        # "W" letter on the front of the dome
        def dome_pt(az, h):   # h in [0,1] height on dome
            a = pi / 2 * (0.12 + 0.62 * h)
            rr = Rd * 1.03 * cos(a); zz = th * 2.2 + hd * sin(a)
            ang = radians(az)
            p = Vector((rr * sin(ang), -rr * 0.96 * cos(ang), zz))
            nloc = Vector((sin(ang) * cos(a), -cos(ang) * cos(a), sin(a))).normalized()
            return F @ (p + nloc * 0.004 * H)
        if hw.get('text') == 'W':
            Wpts = [(-1, 1), (-0.5, 0), (0, 0.65), (0.5, 0), (1, 1)]
            pts = [dome_pt(16 * x, 0.12 + 0.55 * y) for x, y in Wpts]
            tube(mb, pts, 0.0048 * H, qs(6, q, 4), hw['letter'], 'head', 0)
        # chin strap sides (short, reading as the strap)
        for s in (1, -1):
            p0, _ = head_pt(S, s * 80, 12, 0.004 * hh)
            p1, _ = head_pt(S, s * 72, -30, 0.004 * hh)
            p2, _ = head_pt(S, s * 55, -58, 0.004 * hh)
            tube(mb, [p0, p1, p2], 0.006 * H, 4, hw.get('strap', 'belt'), 'head', 0)
    elif hw['type'] == 'headcloth':
        # semutar: a rolled cloth band around the head, crown covered, knot at the back
        z0 = S.head_c.z + R.z * 0.36
        n = qs_even(20, q, 12)
        pts = []
        for k in range(n):
            a = 2 * pi * k / n
            zz = z0 + R.z * 0.07 * cos(a)   # a little lower at the front? (cos(0)=front? no: a=0 -> +X side)
            dz = zz - S.head_c.z
            k2 = sqrt(max(0.0, 1 - (dz / R.z) ** 2))
            rr = 1.07
            pts.append(Vector((R.x * k2 * rr * cos(a), R.y * k2 * rr * sin(a), z0 + R.z * 0.06 * sin(a))))
        tube(mb, pts, 0.034 * hh, qs(8, q, 6), hw['sw'], 'head', 0, closed=True)
        cc = S.head_c + Vector((0, R.y * 0.04, R.z * 0.18))
        ellipsoid(mb, Matrix.Translation(cc), (R.x * 1.04, R.y * 1.05, R.z * 0.88), qs_even(22, q, 12), qs(12, q, 6),
                  hw['sw'], 'head', 0)
        kc = S.head_c + Vector((R.x * 0.25, R.y * 1.06, R.z * 0.36))
        ell(mb, kc, (0.07 * hh, 0.05 * hh, 0.06 * hh), qs_even(10, q, 6), qs(6, q, 4), hw['sw'], 'head', 0)
        tube(mb, [kc, kc + Vector((0.03 * hh, 0.04 * hh, -0.08 * hh)), kc + Vector((0.05 * hh, 0.05 * hh, -0.16 * hh))],
             [0.03 * hh, 0.026 * hh, 0.018 * hh], qs(6, q, 4), hw['sw'], 'head', 0)
    elif hw['type'] == 'straw_hat':
        # wide conical labourer's straw hat
        cc = S.head_c + Vector((0, R.y * 0.02, R.z * 0.58))
        F = Matrix.Translation(cc) @ Matrix.Rotation(radians(-5), 4, 'X')
        Rb = R.x * 1.95; hpk = R.z * 0.62
        prof = [(-0.01 * H, 0.0, 0.0), (0.0, R.x * 0.9, R.y * 0.9), (0.001, Rb * 0.98, Rb * 0.98),
                (0.012 * H, Rb, Rb), (0.02 * H, Rb * 0.9, Rb * 0.9)]
        nk = qs(5, q, 3)
        for k in range(1, nk + 1):
            t = k / nk
            prof.append((0.02 * H + hpk * t, Rb * 0.9 * (1 - t) if k < nk else 0.0, Rb * 0.9 * (1 - t) if k < nk else 0.0))
        lathe(mb, prof, qs_even(24, q, 12), F, hw['sw'], 'head', 0)
        # band where it sits on the head
        prof2 = [(0.004 * H, R.x * 0.98, R.y * 0.98), (0.014 * H, R.x * 0.98, R.y * 0.98)]
        # (chin tie omitted - keeps the face clear)
    elif hw['type'] == 'songkok':
        cc = S.head_c + Vector((0, R.y * 0.05, R.z * 0.62))
        F = Matrix.Translation(cc) @ Matrix.Rotation(radians(-6), 4, 'X')
        h = R.z * 0.42
        prof = [(-0.01, 0, 0), (0, R.x * 0.93, R.y * 0.90), (h, R.x * 0.95, R.y * 0.92), (h + 0.004, R.x * 0.9, R.y * 0.86),
                (h + 0.012, 0, 0)]
        lathe(mb, prof, qs_even(24, q, 12), F, hw['sw'], 'head', 0)

def build_collar(mb, S, C, q):
    top = C['outfit']['top']; H = S.H; kind = top.get('collar')
    if not kind: return
    wt = body_w_fn(S)
    if kind == 'mandarin':
        z0 = S.z_nb - 0.012 * H; z1 = S.z_nb + 0.03 * H
        r0 = S.neck_r + 0.012 * H
        prof = [(z0 - 0.002, r0 * 0.6, r0 * 0.6 * 0.95), (z0, r0 * 1.05, r0), (z1, r0 * 0.98, r0 * 0.94),
                (z1 + 0.003, r0 * 0.7, r0 * 0.66)]
        lathe(mb, prof, qs_even(18, q, 10), Matrix.Identity(4), top['sw'], chain_w_fn(S), 0)
        # frog trim line along collar top
    elif kind == 'shirt':
        z0 = S.z_nb - 0.01 * H
        r0 = S.neck_r + 0.012 * H
        prof = [(z0 - 0.004, r0 * 0.7, r0 * 0.66), (z0, r0 * 1.06, r0), (z0 + 0.024 * H, r0 * 1.0, r0 * 0.95),
                (z0 + 0.027 * H, r0 * 0.7, r0 * 0.66)]
        lathe(mb, prof, qs_even(18, q, 10), Matrix.Identity(4), top['sw'], chain_w_fn(S), 0)
        for s in (1, -1):
            p, n = surf(S, S.z_nb - 0.035 * H, s * 24, 0.004 * H)
            F = frame_z(p, n, Vector((0, 0, 1)).cross(n)) @ Matrix.Rotation(radians(s * 28), 4, 'Z')
            rbox(mb, F, (0.05 * H, 0.04 * H, 0.008 * H), 0.004 * H, top['sw'], wt, 0, n=qs(3, q, 2), bend=0.0)
    elif kind == 'round_trim':
        pts = []
        n = qs_even(18, q, 10)
        z = S.z_nb - 0.004 * H
        for k in range(n):
            a = 360 * k / n
            p, _ = surf(S, z - 0.012 * H * max(0, cos(radians(a))) ** 4, a, 0.002 * H)
            pts.append(p)
        tube(mb, pts, 0.0055 * H, qs(6, q, 4), top.get('trim', top['sw']), chain_w_fn(S), 0, closed=True)
        # short front slit with tulang belut stitch
        p0, _ = surf(S, z - 0.012 * H, 0, 0.002 * H); p1, _ = surf(S, z - 0.06 * H, 0, 0.002 * H)
        tube(mb, [p0, p1], 0.004 * H, 4, top.get('trim', top['sw']), chain_w_fn(S), 0)
    elif kind == 'singlet':
        # shoulder straps
        for s in (1, -1):
            pts = []
            zA = anchor(S, 'armpit')
            for k in range(7):
                t = k / 6
                az = s * lerp(30, 150, t)
                z = lerp(zA + 0.01 * H, S.z_nb + 0.004 * H, sin(pi * t) ** 0.7)
                p, _ = surf(S, z, az, 0.004 * H)
                pts.append(p)
            tube(mb, pts, 0.011 * H, qs(6, q, 4), top['sw'], chain_w_fn(S), 0)

def chain_w_fn(S):
    return lambda co: chain_w(co.z, S)

def build_top_details(mb, S, C, q):
    top = C['outfit']['top']; H = S.H; wt = body_w_fn(S)
    if top.get('buttons'):
        zs = np.linspace(S.z_nb - 0.05 * H, max(S.top_hem, S.anchors['waist']) + 0.03 * H, 4)
        for z in zs:
            p, n = surf(S, z, 0, 0.001 * H)
            ell(mb, p, (0.009 * H, 0.009 * H, 0.004 * H), qs_even(8, q, 6), qs(4, q, 3), top['buttons'], wt, 0,
                rot=feature_frame(p, n).to_3x3())
        # placket line
        pts = [surf(S, z, 0, 0.0015 * H)[0] for z in np.linspace(S.z_nb - 0.03 * H, S.top_hem + 0.004 * H, 6)]
        tube(mb, pts, 0.0035 * H, 4, top['sw'], wt, 0)
    if top.get('pockets'):
        for s in ((1,) if top['pockets'] == 'L' else (1, -1)):
            z = S.chest_z + 0.035 * H
            p, n = surf(S, z, s * 30, 0.004 * H)
            F = feature_frame(p, n)
            rbox(mb, F, (0.075 * H, 0.078 * H, 0.009 * H), 0.004 * H, top['sw'], wt, 0, n=qs(3, q, 2), bend=2.0)
            pf, nf = surf(S, z + 0.04 * H, s * 30, 0.009 * H)
            Ff = feature_frame(pf, nf)
            rbox(mb, Ff, (0.08 * H, 0.026 * H, 0.008 * H), 0.004 * H, top['sw'], wt, 0, n=qs(3, q, 2), bend=2.0)
            pb = pf + nf * 0.004 * H - Vector((0, 0, 0.005 * H))
            ell(mb, pb, (0.007 * H, 0.007 * H, 0.004 * H), 6, 4, top.get('buttons', top['sw']), wt, 0,
                rot=Ff.to_3x3())
    if top.get('placket'):
        # samfu diagonal side opening (to the wearer's right, -X) with frog-knot buttons
        path = []
        z_c = S.z_nb - 0.015 * H
        for k in range(8):
            t = k / 7
            az = -lerp(0, 72, smooth(0, 1, t))
            z = lerp(z_c, anchor(S, 'armpit') - 0.01 * H, t ** 1.4)
            path.append((z, az))
        for k in range(1, 4):
            t = k / 3
            path.append((lerp(anchor(S, 'armpit') - 0.01 * H, S.top_hem + 0.02 * H, t), -72 - 4 * t))
        pts = [surf(S, z, az, 0.003 * H)[0] for z, az in path]
        tube(mb, pts, 0.0045 * H, 4, top['placket'], wt, 0)
        for (z, az) in [path[1], path[4], path[7], path[9]]:
            p, n = surf(S, z, az, 0.004 * H)
            F = feature_frame(p, n)
            ell(mb, p, (0.017 * H, 0.0075 * H, 0.0055 * H), qs_even(8, q, 6), qs(4, q, 3), top['placket'], wt, 0,
                rot=F.to_3x3())
            ell(mb, p, (0.0065 * H, 0.0065 * H, 0.0075 * H), 6, 4, top['placket'], wt, 0, rot=F.to_3x3())

def strap_path(S, start, end, n, out, via=None):
    """start/end: (z, az). returns points on torso surface."""
    pts = []
    for k in range(n + 1):
        t = k / n
        z = lerp(start[0], end[0], t); az = lerp(start[1], end[1], t)
        if via is not None:
            z = z + via * sin(pi * t)
        pts.append(surf(S, z, az, out)[0])
    return pts

def build_props(mb, S, C, q):
    H = S.H; wt = body_w_fn(S)
    for pr in C.get('props', []):
        typ = pr['type']
        if typ == 'belt':
            z = S.anchors['waist']
            prof = []
            bh = 0.034 * H; th = 0.007 * H
            for dz, grow in ((-bh / 2 - 0.0005, 0.0), (-bh / 2, 1.0), (bh / 2, 1.0), (bh / 2 + 0.0005, 0.0)):
                rx, ry = torso_r(S, z + dz)
                prof.append((z + dz, rx + th * grow - 0.002 * (1 - grow), ry + th * grow - 0.002 * (1 - grow)))
            lathe(mb, prof, qs_even(26, q, 12), Matrix.Identity(4), pr['sw'], wt, 0)
            p, n = surf(S, z, 0, th + 0.003 * H)
            rbox(mb, feature_frame(p, n), (0.05 * H, 0.04 * H, 0.008 * H), 0.004 * H, pr['buckle'], wt, GLOSS, n=2)
        elif typ == 'webbing':
            # 1937-pattern: wide belt, two basic pouches on the chest, braces over the shoulders
            z = S.anchors['waist']
            bh = 0.048 * H; th = 0.008 * H
            prof = []
            for dz, grow in ((-bh / 2 - 0.0005, 0.0), (-bh / 2, 1.0), (bh / 2, 1.0), (bh / 2 + 0.0005, 0.0)):
                rx, ry = torso_r(S, z + dz)
                prof.append((z + dz, rx + th * grow - 0.002 * (1 - grow), ry + th * grow - 0.002 * (1 - grow)))
            lathe(mb, prof, qs_even(26, q, 12), Matrix.Identity(4), pr['sw'], wt, 0)
            p, n = surf(S, z, 0, th + 0.003 * H)
            rbox(mb, feature_frame(p, n), (0.055 * H, 0.042 * H, 0.008 * H), 0.004 * H, pr['buckle'], wt, GLOSS, n=2)
            for sd in (1, -1):
                zp = z + 0.075 * H
                p, n = surf(S, zp, sd * 30, 0.021 * H)
                F = feature_frame(p, n)
                rbox(mb, F, (0.07 * H, 0.085 * H, 0.04 * H), 0.012 * H, pr['sw'], wt, 0, n=qs(3, q, 2), bend=1.5)
                pf = F @ Vector((0, 0.035 * H, 0.021 * H))
                rbox(mb, Matrix.Translation(pf) @ F.to_3x3().to_4x4(), (0.074 * H, 0.028 * H, 0.01 * H), 0.004 * H,
                     pr['sw'], wt, 0, n=2)
                # brace: from pouch top over the shoulder, down the back to the belt
                front = strap_path(S, (zp + 0.045 * H, sd * 32), (S.z_sh + 0.02 * H, sd * 50), qs(5, q, 3), 0.007 * H)
                over = [surf(S, S.z_sh + 0.035 * H, sd * 90, 0.02 * H)[0]]
                back = strap_path(S, (S.z_sh + 0.02 * H, sd * 130), (z + bh / 2, sd * 158), qs(5, q, 3), 0.007 * H)
                tube(mb, front + over + back, 0.009 * H, 4, pr['sw'], wt, 0)
        elif typ == 'bottle':
            side = pr['side']; sd = sgn(side)
            z = S.anchors['waist'] - 0.05 * H
            p, n = surf(S, z, sd * 118, 0.03 * H)
            F = feature_frame(p, n)
            ell(mb, p, (0.045 * H, 0.062 * H, 0.028 * H), qs_even(12, q, 8), qs(7, q, 5), pr['sw'], wt, 0, rot=F.to_3x3())
            ell(mb, p + Vector((0, 0, 0.066 * H)), (0.013 * H, 0.013 * H, 0.012 * H), 8, 5, 'boot', wt, 0)
        elif typ == 'towel':
            # small cotton towel folded over one shoulder, hanging front and back
            sd = sgn(pr['side'])
            wp = [(S.anchors['waist'] + 0.03 * H, sd * 26), (S.chest_z, sd * 34), (S.z_sh, sd * 50),
                  (S.z_sh + 0.04 * H, sd * 82, 0.035 * H), (S.z_sh, sd * 125), (S.chest_z - 0.03 * H, sd * 150)]
            pts, nrm = drape(S, wp, qs(12, q, 7), 0.013 * H)
            ribbon(mb, pts, nrm, 0.105 * H, 0.013 * H, pr['sw'], wt, 0)
        elif typ == 'shawl':
            # selendang: draped around the back of the neck, over both shoulders, ends hanging in front
            wp = [(S.anchors['waist'] + 0.02 * H, 22), (S.chest_z, 40), (S.z_sh + 0.02 * H, 68, 0.022 * H),
                  (S.z_nb + 0.01 * H, 140, 0.03 * H), (S.z_nb + 0.01 * H, 220, 0.03 * H), (S.z_sh + 0.02 * H, 292, 0.022 * H),
                  (S.chest_z - 0.02 * H, 318), (S.anchors['hip'] - 0.01 * H, 336)]
            pts, nrm = drape(S, wp, qs(20, q, 12), 0.013 * H)
            ribbon(mb, pts, nrm, 0.075 * H, 0.009 * H, pr['sw'], wt, 0)
        elif typ == 'sash':
            # soft cloth sash tied over the baju, knot on the wearer's left hip with two tails
            z = S.anchors['waist'] - 0.01 * H
            prof = []
            bh = 0.045 * H; th = 0.009 * H
            for dz, grow in ((-bh / 2 - 0.0005, 0.0), (-bh / 2, 0.8), (0, 1.0), (bh / 2, 0.8), (bh / 2 + 0.0005, 0.0)):
                rx, ry = torso_r(S, z + dz)
                prof.append((z + dz, rx + th * grow - 0.002 * (1 - grow), ry + th * grow - 0.002 * (1 - grow)))
            lathe(mb, prof, qs_even(26, q, 12), Matrix.Identity(4), pr['sw'], wt, 0)
            p, n = surf(S, z + 0.004 * H, 58, th + 0.004 * H)
            rbox(mb, feature_frame(p, n), (0.05 * H, 0.03 * H, 0.012 * H), 0.005 * H, pr['sw'], wt, 0, n=2, bend=4.0)
            # two short, broad soft tails (felt flaps) hanging from the knot
            for daz, ln, tilt in ((-7, 0.06, 8), (8, 0.048, -10)):
                pt, nt = surf(S, z - ln * 0.55 * H, 58 + daz, th + 0.004 * H)
                F = feature_frame(pt, nt) @ Matrix.Rotation(radians(tilt), 4, 'Z')
                rbox(mb, F, (0.034 * H, ln * H, 0.008 * H), 0.0035 * H, pr['sw'], wt, 0, n=2, bend=4.0)
        elif typ == 'armband':
            side = pr['side']; A = S.arm_frames[side]; F = A['F']; L = A['L']
            t0 = L * 0.64; bh = 0.045 * H
            rr = A['rad'](t0) + A['se'] * 1.0 * C['outfit']['top'].get('sleeve_flare', 1.0) + 0.006 * H
            if C['outfit']['top'].get('sleeve', 0) < (1 - 0.64 + 0.05):
                rr = A['rad'](t0) + 0.006 * H
            prof = [(t0 - bh / 2 - 0.001, rr * 0.8, rr * 0.8), (t0 - bh / 2, rr, rr * 0.97), (t0 + bh / 2, rr, rr * 0.97),
                    (t0 + bh / 2 + 0.001, rr * 0.8, rr * 0.8)]
            lathe(mb, prof, qs_even(16, q, 10), F, pr['sw'], arm_w_fn(S, side), 0)
            # letters: geometry strokes on the outer face; reading left->right = front->back on the left arm
            glyphs = {
                'A': [[(0, 0), (0.5, 1), (1, 0)], [(0.22, 0.42), (0.78, 0.42)]],
                'R': [[(0, 0), (0, 1), (0.65, 1), (0.9, 0.84), (0.9, 0.66), (0.65, 0.5), (0, 0.5)], [(0.42, 0.5), (0.95, 0)]],
                'P': [[(0, 0), (0, 1), (0.65, 1), (0.9, 0.84), (0.9, 0.66), (0.65, 0.5), (0, 0.5)]],
                'W': [[(0, 1), (0.25, 0), (0.5, 0.65), (0.75, 0), (1, 1)]],
            }
            text = pr.get('text', 'ARP')
            lh = bh * 0.56; lw = lh * 0.72; gap = lw * 0.4
            total = len(text) * lw + (len(text) - 1) * gap
            outward = sgn(side)
            for li, ch in enumerate(text):
                for stroke in glyphs.get(ch, []):
                    pts = []
                    for gx, gy in stroke:
                        sarc = -total / 2 + li * (lw + gap) + gx * lw
                        th = sarc / rr
                        # local frame of arm lathe: x ~ world X (outward for L), y ~ world Y (back)
                        # outward angle = 0 for L (x+), pi for R
                        base = 0.0 if outward > 0 else pi
                        ang = base + th * outward
                        tt = t0 - lh / 2 + gy * lh
                        loc = Vector(((rr + 0.0018 * H) * cos(ang), (rr * 0.97 + 0.0018 * H) * sin(ang), tt))
                        pts.append(F @ loc)
                    tube(mb, pts, 0.0024 * H, 4, pr['letter'], arm_w_fn(S, side), 0)
        elif typ == 'whistle':
            side = pr['side']; s = sgn(side)
            zp = S.chest_z + 0.035 * H
            # lanyard from shoulder seam to pocket
            pts = strap_path(S, (S.z_sh + 0.02 * H, s * 62), (zp + 0.045 * H, s * 36), qs(6, q, 4), 0.006 * H)
            pts += [surf(S, zp - 0.005 * H, s * 33, 0.016 * H)[0]]
            tube(mb, pts, 0.0032 * H, 4, pr['cord'], wt, 0)
            p, n = surf(S, zp - 0.012 * H, s * 33, 0.02 * H)
            F = frame_z(p, Vector((0, 0, -1)), Vector((1, 0, 0)))
            prof = [(-0.018 * H, 0, 0), (-0.017 * H, 0.008 * H, 0.008 * H), (0.012 * H, 0.009 * H, 0.009 * H),
                    (0.018 * H, 0.0065 * H, 0.0065 * H), (0.02 * H, 0, 0)]
            lathe(mb, prof, qs_even(10, q, 6), F, pr['metal'], wt, GLOSS)
            ell(mb, p + Vector((0, -0.006 * H, -0.012 * H)), (0.011 * H, 0.011 * H, 0.011 * H), 8, 5, pr['metal'], wt, GLOSS)
        elif typ in ('gas_bag', 'news_bag'):
            side = pr['side']; s = sgn(side)
            if typ == 'gas_bag':
                size = (0.15 * H * 0.62, 0.12 * H * 0.62, 0.075 * H * 0.62)  # w(front-back), h, thickness
                zc = S.hip_z + 0.02 * H
            else:
                size = (0.19 * H, 0.15 * H, 0.06 * H)
                zc = S.hip_z + 0.015 * H
            rx, ry = torso_r(S, zc)
            if typ == 'news_bag':
                rx = max(rx, torso_r(S, S.hip_z - 0.03 * H)[0])
            c = Vector((s * (rx + size[2] * 0.55), -0.015 * H, zc))
            F = frame_z(c, Vector((s, 0, 0)), Vector((0, -1, 0)))
            # F local: x ~ forward(-Y), y ~ up?, z = outward
            Fr = F @ Matrix.Rotation(0, 4, 'Z')
            # make local y = world up
            xloc = Vector((0, -1, 0)); zloc = Vector((s, 0, 0)); yloc = zloc.cross(xloc)
            M = Matrix((xloc, yloc, zloc)).transposed().to_4x4(); M.translation = c
            rbox(mb, M, (size[0], size[1], size[2]), size[2] * 0.4, pr['sw'], wt, 0, n=qs(4, q, 3), bend=1.0)
            # flap
            fl = M @ Matrix.Translation(Vector((0, size[1] * 0.28, size[2] * 0.5)))
            if typ == 'gas_bag':
                rbox(mb, fl, (size[0] * 1.02, size[1] * 0.5, size[2] * 0.18), size[2] * 0.08, pr['sw'], wt, 0, n=2)
            if pr.get('papers'):
                for k, (ox, rz, h) in enumerate(((-0.05, -8, 0.10), (0.0, 3, 0.12), (0.05, 11, 0.09))):
                    pc = M @ Vector((ox * H * 0.8, size[1] * 0.5 + h * H * 0.25, -size[2] * 0.05 + (k - 1) * 0.012 * H))
                    Mr = Matrix.Translation(pc) @ (M.to_3x3() @ Matrix.Rotation(radians(rz), 3, 'Z')).to_4x4()
                    rbox(mb, Mr, (0.14 * H * 0.8, h * H, 0.01 * H), 0.004 * H, pr['papers'], wt, 0, n=2)
            # strap over the opposite shoulder
            top_z = zc + size[1] * 0.5
            o = 0.006 * H
            front = strap_path(S, (top_z - 0.01 * H, s * 80), (S.z_sh + 0.01 * H, -s * 58), qs(9, q, 6), o)
            back = strap_path(S, (S.z_sh + 0.01 * H, -s * 58 - s * 360 + (s * 360 if False else 0)), (top_z - 0.01 * H, s * 100), qs(9, q, 6), o)
            # go over the shoulder via the back: interpolate az the long way round
            back = strap_path(S, (S.z_sh + 0.01 * H, -s * 58), (top_z - 0.01 * H, -s * 58 - s * (360 - 58 - 100)), qs(9, q, 6), o)
            over = [surf(S, S.z_sh + 0.03 * H, -s * 80, o + 0.012 * H)[0]]
            sw_strap = pr.get('strap', pr['sw'])
            tube(mb, front + over + back, 0.009 * H, qs(6, q, 4), sw_strap, wt, 0)
        elif typ == 'apron':
            z1 = S.anchors['waist'] + 0.005 * H; z0 = S.knee_z + 0.03 * H
            zc = 0.5 * (z0 + z1)
            rx, ry = torso_r(S, S.top_hem + 0.002 * H)
            ry_max = max(torso_r(S, z)[1] for z in np.linspace(z0, z1, 12) if z >= S.top_hem - 0.001) if True else ry
            y = -(ry_max + 0.009 * H)
            c = Vector((0, y, zc))
            xloc = Vector((1, 0, 0)); zloc = Vector((0, -1, 0)); yloc = zloc.cross(xloc)
            M = Matrix((xloc, yloc, zloc)).transposed().to_4x4(); M.translation = c
            w = rx * 1.55
            rbox(mb, M, (w, z1 - z0, 0.012 * H), 0.005 * H, pr['sw'], wt, 0, n=qs(4, q, 3), bend=0.5 / rx)
            # pocket on the apron
            Mp = M @ Matrix.Translation(Vector((w * 0.18, -(z1 - z0) * 0.12, 0.009 * H - 0.5 / rx * (w * 0.18) ** 2)))
            rbox(mb, Mp, (w * 0.3, (z1 - z0) * 0.22, 0.008 * H), 0.004 * H, pr['sw'], wt, 0, n=2)
            # waist tie
            prof = []
            for dz, g in ((-0.009 * H, 0), (-0.008 * H, 1), (0.008 * H, 1), (0.009 * H, 0)):
                rxx, ryy = torso_r(S, z1 + dz)
                prof.append((z1 + dz, rxx + 0.005 * H * g, ryy + 0.005 * H * g))
            lathe(mb, prof, qs_even(22, q, 12), Matrix.Identity(4), pr['sw'], wt, 0)
        elif typ == 'bangle':
            side = pr['side']; J = S.joints[side]
            c = J['wr'] - J['dir'] * 0.012 * H
            F = frame_z(c, J['dir'])
            n = qs_even(14, q, 8)
            rr = S.arm_r * 0.86 + 0.006 * H
            pts = [F @ Vector((rr * cos(2 * pi * k / n), rr * sin(2 * pi * k / n), 0)) for k in range(n)]
            tube(mb, pts, 0.0055 * H, qs(6, q, 4), pr['sw'], arm_w_fn(S, side), GLOSS, closed=True)

def build_extras(S, C, q):
    out = []
    for ex in C.get('extras', []):
        if ex['type'] == 'cane':
            side = ex.get('side', 'L'); J = S.joints[side]; H = S.H
            mb = MB()
            grip = J['wr'] + J['dir'] * S.hand_r * 1.0          # centre of the mitten
            tip = Vector((grip.x + sgn(side) * 0.01 * H, grip.y - 0.01 * H, 0.004))
            r = 0.011 * H
            n = qs(6, q, 4)
            shaft = [grip.lerp(tip, k / n) for k in range(n + 1)]
            shaft[0] = grip + Vector((0, 0, S.hand_r * 0.6))
            # crook handle curling forward over the hand
            hook = []
            c0 = grip + Vector((0, 0, S.hand_r * 0.6))
            R_ = S.hand_r * 0.9
            for k in range(1, qs(6, q, 4) + 1):
                a = pi * k / qs(6, q, 4)
                hook.append(c0 + Vector((0, -R_ + R_ * cos(a), R_ * sin(a))) + Vector((0, R_, 0)) - Vector((0, R_, 0)))
            pts = list(reversed(hook)) + shaft
            tube(mb, pts, r, qs(8, q, 6), ex['sw'], 'hand.' + side, 0)
            ell(mb, tip + Vector((0, 0, 0.006 * H)), (r * 1.25, r * 1.25, r * 1.1), 8, 4, ex.get('tip_sw', ex['sw']), 'hand.' + side, 0)
            out.append((ex.get('name', 'Cane'), mb, 'hand.' + side))
    return out

# --------------------------------------------------------------------------------------
# Palette texture
# --------------------------------------------------------------------------------------
GRID = 8
MARGIN = 0.07

def value_noise(size, n, rng):
    g = rng.random((n + 2, n + 2))
    x = np.linspace(0, n, size, endpoint=False)
    i = x.astype(int); f = x - i; f = f * f * (3 - 2 * f)
    a = g[np.ix_(i, i)]; b = g[np.ix_(i, i + 1)]; c = g[np.ix_(i + 1, i)]; d = g[np.ix_(i + 1, i + 1)]
    fy = f[:, None]; fx = f[None, :]
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy

def paint_swatch(spec, U, V):
    shp = U.shape + (3,)
    if isinstance(spec, str):
        return np.broadcast_to(hexrgb(spec), shp).copy()
    k = spec['kind']
    base = hexrgb(spec['base']) if 'base' in spec else None
    if k == 'twill':
        img = np.broadcast_to(base, shp).copy()
        tw = (np.sin((U * 40 + V * 40) * pi) > 0.3).astype(float)
        img *= (1 + spec.get('amt', 0.04) * (tw - 0.5))[..., None]
        if spec.get('grime'):
            blot = np.sin(U * 9.1 + 1.3) * np.sin(V * 7.3 + 0.4) + 0.6 * np.sin(U * 17.0 - V * 13.0 + 2.0)
            img *= (1 - spec['grime'] * np.clip(blot, 0, 1.5))[..., None]
        return img
    if k == 'border':
        bd = hexrgb(spec['band']); ln = hexrgb(spec.get('line', spec['band']))
        img = np.broadcast_to(base, shp).copy()
        band = ((V > 0.04) & (V < 0.13)).astype(float)[..., None]
        line = ((V > 0.16) & (V < 0.18)).astype(float)[..., None]
        img = img * (1 - band) + bd * band
        return img * (1 - line) + ln * line
    if k == 'floral':
        fl = hexrgb(spec['flower']); ct = hexrgb(spec.get('centre', spec['flower']))
        img = np.broadcast_to(base, shp).copy()
        n = spec.get('n', 7)
        fu = (U * n) % 1.0 - 0.5; fv = (V * n + 0.5 * (np.floor(U * n) % 2)) % 1.0 - 0.5
        r = np.sqrt(fu ** 2 + fv ** 2); ang = np.arctan2(fv, fu)
        petal = (r < 0.17 + 0.07 * np.cos(5 * ang)).astype(float)[..., None]
        centre = (r < 0.06).astype(float)[..., None]
        img = img * (1 - petal) + fl * petal
        return img * (1 - centre) + ct * centre
    if k == 'pinstripe':
        ln = hexrgb(spec['line'])
        img = np.broadcast_to(base, shp).copy()
        m = ((((U * spec.get('n', 22)) % 1.0) < 0.12)).astype(float)[..., None] * 0.6
        return img * (1 - m) + ln * m
    if k == 'puttee':
        ln = hexrgb(spec['line'])
        img = np.broadcast_to(base, shp).copy()
        band = (((U * 3 + V * 7) % 1.0) < 0.14).astype(float)[..., None]
        return img * (1 - band) + ln * band
    if k == 'rib':
        img = np.broadcast_to(base, shp).copy()
        rb = np.sin(U * 2 * pi * 36)
        img *= (1 + spec.get('amt', 0.03) * rb)[..., None]
        return img
    if k == 'strands':
        img = np.broadcast_to(base, shp).copy()
        st = np.sin(U * 2 * pi * 30 + 1.7 * np.sin(U * 2 * pi * 7)) * 0.5 + 0.5
        lum = 0.10 if base.mean() < 0.3 else 0.06
        img = img * (1 + lum * (st[..., None] - 0.5)) + 0.025 * (V[..., None] ** 3)
        return img
    if k == 'check':
        nu, nv = spec.get('nu', 4), spec.get('nv', 5)
        fu = (U * nu) % 1.0; fv = (V * nv) % 1.0
        mu = (fu < 0.38).astype(float); mv = (fv < 0.38).astype(float)
        st = hexrgb(spec['stripe']); ln = hexrgb(spec['line'])
        img = np.broadcast_to(base, shp).copy()
        both = (mu * mv)[..., None]; one = np.clip(mu + mv - 2 * mu * mv, 0, 1)[..., None]
        img = img * (1 - one) + (0.55 * st + 0.45 * base) * one
        img = img * (1 - both) + st * both
        lu = ((fu > 0.64) & (fu < 0.69)).astype(float)[..., None]
        lv = ((fv > 0.64) & (fv < 0.69)).astype(float)[..., None]
        img = img * (1 - lu * 0.45) + ln * lu * 0.45
        img = img * (1 - lv * 0.45) + ln * lv * 0.45
        return img
    if k == 'batik':
        mo = hexrgb(spec['motif']); dk = hexrgb(spec['dark']); bd = hexrgb(spec['border'])
        img = np.broadcast_to(base, shp).copy()
        n_u, n_v = 6, 5
        fu = (U * n_u) % 1.0 - 0.5; fv = (V * n_v + 0.5 * (np.floor(U * n_u) % 2)) % 1.0 - 0.5
        d = np.abs(fu) + np.abs(fv)
        ring = ((d > 0.24) & (d < 0.31)).astype(float)[..., None]
        dot = (d < 0.1).astype(float)[..., None]
        img = img * (1 - ring) + mo * ring
        img = img * (1 - dot) + mo * dot
        # hem border band (low v) and a fine line above it
        band = (V < 0.16).astype(float)[..., None]
        img = img * (1 - band) + bd * band
        zig = (np.abs(((U * 18) % 1.0) - 0.5) * 0.12 + 0.05 > np.abs(V - 0.08)).astype(float)[..., None] * band
        img = img * (1 - zig) + mo * zig
        line = ((V > 0.18) & (V < 0.2)).astype(float)[..., None]
        img = img * (1 - line) + dk * line
        return img
    if k == 'news':
        ink = hexrgb(spec['ink'])
        img = np.broadcast_to(base, shp).copy()
        rows = (((V * 16) % 1.0) < 0.42) & (V < 0.78) & (np.abs(U - 0.5) < 0.42)
        cols = (np.abs(((U * 3) % 1.0) - 0.5) < 0.43)
        m = (rows & cols).astype(float)[..., None] * 0.55
        img = img * (1 - m) + ink * m
        head = ((V > 0.84) & (V < 0.95) & (np.abs(U - 0.5) < 0.42)).astype(float)[..., None] * 0.9
        img = img * (1 - head) + hexrgb('#2a2622') * head
        return img
    if k == 'face':
        skin = hexrgb(spec['skin']); bl = hexrgb(spec['blush'])
        img = np.broadcast_to(skin, shp).copy()
        amt = spec.get('amt', 0.6)
        for az in (40,):
            u0 = 1.0 - 2.0 * az / 360.0; v0 = (90 - 17) / 180.0   # mirrored u: front=1; el = -17 deg
            g = np.exp(-(((U - u0) / 0.085) ** 2 + ((V - v0) / 0.055) ** 2))
            img = img * (1 - amt * g[..., None]) + bl * (amt * g[..., None])
        return img
    raise ValueError(k)

def build_palette(swatches, size, seed=7):
    rng = np.random.default_rng(seed)
    cell = size // GRID
    img = np.zeros((size, size, 3))
    px = (np.arange(cell) + 0.5) / cell
    uu = np.clip((px - MARGIN) / (1 - 2 * MARGIN), 0, 1)
    U, V = np.meshgrid(uu, uu)   # V along rows
    index = {}
    used = np.zeros((GRID, GRID), bool)
    big = [n for n, sp in swatches.items() if isinstance(sp, dict) and sp['kind'] in BIG_KINDS]
    order = big + [n for n in swatches if n not in big]
    for name in order:
        spec = swatches[name]; span = 2 if name in big else 1
        spot = next((c, r) for r in range(0, GRID - span + 1) for c in range(0, GRID - span + 1)
                    if not used[r:r + span, c:c + span].any())
        col, row = spot; used[row:row + span, col:col + span] = True
        n_px = cell * span
        px2 = (np.arange(n_px) + 0.5) / n_px
        uu2 = np.clip((px2 - MARGIN / span) / (1 - 2 * MARGIN / span), 0, 1)
        U2, V2 = np.meshgrid(uu2, uu2)
        img[row * cell:row * cell + n_px, col * cell:col * cell + n_px] = paint_swatch(spec, U2, V2)
        index[name] = (col, row, span)
    # felt / cotton fibre noise
    nz = (0.045 * (value_noise(size, max(4, size // 24), rng) - 0.5) +
          0.03 * (value_noise(size, max(8, size // 6), rng) - 0.5) +
          0.03 * (rng.random((size, size)) - 0.5))
    img = np.clip(img * (1 + nz[..., None]), 0, 1)
    return img, index

BIG_KINDS = ('check', 'batik', 'face')

def atlas_uv(index, sw, uv):
    col, row, span = index[sw]
    u = (col + MARGIN + clamp(uv[0]) * (span - 2 * MARGIN)) / GRID
    v = (row + MARGIN + clamp(uv[1]) * (span - 2 * MARGIN)) / GRID
    return (u, v)

# --------------------------------------------------------------------------------------
# Animation
# --------------------------------------------------------------------------------------
def P(): return {'rot': {}, 'hips': Vector((0, 0, 0)), 'mat': {}}
def rot(p, b, rx=0.0, ry=0.0, rz=0.0):
    r = p['rot'].setdefault(b, [0.0, 0.0, 0.0]); r[0] += rx; r[1] += ry; r[2] += rz
def limb(p, b, side, flex=0.0, ab=0.0, tw=0.0):
    s = sgn(side); rot(p, f'{b}.{side}', flex, -s * ab, s * tw)
def get(p, b, i):
    return p['rot'].get(b, [0, 0, 0])[i]

def idle_arms(p, C, side, k=1.0):
    st = C.get('idle_arms', 'relaxed')
    if st == 'clasp':
        limb(p, 'upperarm', side, flex=-16 * k, ab=-7 * k)
        limb(p, 'forearm', side, flex=-68 * k, tw=-38 * k)
        limb(p, 'hand', side, flex=-10 * k)
    elif st == 'cane' and side == C.get('cane_side', 'L'):
        limb(p, 'upperarm', side, flex=-14 * k, ab=3 * k)
        limb(p, 'forearm', side, flex=-4 * k)
        limb(p, 'hand', side, flex=6 * k)
    else:
        limb(p, 'upperarm', side, flex=-2 * k, ab=2 * k)
        limb(p, 'forearm', side, flex=-10 * k)

def leg_ik(S, hip_dy, hip_dz, ank_dy=0.0, ank_dz=0.0, hips_rx=0.0):
    hy, hz = hip_dy, S.hip_z + hip_dz
    ay, az = ank_dy, S.ankle_z + ank_dz
    dy, dz = ay - hy, az - hz
    d = min(math.hypot(dy, dz), (S.l1 + S.l2) * 0.9995)
    alpha = atan2(dy, -dz)
    beta = acos(clamp((S.l1 ** 2 + d * d - S.l2 ** 2) / (2 * S.l1 * d), -1, 1))
    thigh_w = degrees(alpha - beta)
    knee = 180 - degrees(acos(clamp((S.l1 ** 2 + S.l2 ** 2 - d * d) / (2 * S.l1 * S.l2), -1, 1)))
    return thigh_w - hips_rx, knee, -(thigh_w + knee)

def ground(p, S, legs, hips_rx=0.0, bias=0.0):
    """drop/raise hips so the lowest ankle sits at rest ankle height. legs: {side:(thigh_local, knee)}"""
    lows = []
    for side, (th, kn) in legs.items():
        a1 = radians(th + hips_rx); a2 = radians(th + hips_rx + kn)
        lows.append(S.l1 * cos(a1) + S.l2 * cos(a2))
    reach = max(lows)
    p['hips'].z += -(S.leg_len - reach) + bias

def breathe(p, ph, amp=1.0):
    b = sin(ph)
    rot(p, 'spine', rx=-0.7 * b * amp); rot(p, 'chest', rx=-1.5 * b * amp)
    rot(p, 'upperarm.L', ry=-0.8 * b * amp); rot(p, 'upperarm.R', ry=0.8 * b * amp)

def c_idle(t, S, C):
    p = P(); e = C['energy']; ph = 2 * pi * t
    breathe(p, 2 * ph)
    sway = sin(ph)
    dx = 0.010 * S.H * sway * e
    hr = -2.2 * sway * e
    rot(p, 'hips', ry=hr); rot(p, 'spine', ry=-hr * 0.7); rot(p, 'chest', ry=-hr * 0.4)
    th = degrees(atan2(dx, S.leg_len))
    for side in 'LR':
        rot(p, 'thigh.' + side, ry=th - hr); rot(p, 'foot.' + side, ry=-th)
        limb(p, 'shin', side, flex=2); limb(p, 'thigh', side, flex=-1); limb(p, 'foot', side, flex=-1)
    p['hips'] += Vector((dx, 0, -S.leg_len * (1 - cos(radians(th))) - 0.002 * S.H))
    for side, o in (('L', 0), ('R', pi)):
        idle_arms(p, C, side)
        limb(p, 'upperarm', side, flex=1.6 * sin(ph + o) * e)
    rot(p, 'head', rx=2.0 * sin(2 * ph + 1) * e, rz=7 * sin(ph + 0.7) * e, ry=1.5 * sin(ph))
    return p

def walk_pose(p, S, C, ph, A, Aarm, kneeA, lean, injured=None, t_phase=None):
    legs = {}
    for side, off in (('L', 0.0), ('R', pi)):
        a = ph + off
        amp = A * (0.7 if side == injured else 1.0)
        th = -amp * sin(a)
        kn = 5 + kneeA * (0.55 if side == injured else 1.0) * max(0.0, cos(a)) ** 1.5
        ft = -(th + kn) - 10 * max(0.0, cos(a)) * (0.4 if side == injured else 1.0) + 6 * max(0.0, -cos(a)) * max(0.0, sin(a))
        limb(p, 'thigh', side, flex=th - lean * 0.3)
        limb(p, 'shin', side, flex=kn)
        limb(p, 'foot', side, flex=ft + lean * 0.3)
        legs[side] = (th - lean * 0.3 + 0.0, kn)
    rot(p, 'hips', rx=lean * 0.3)
    ground(p, S, legs, hips_rx=lean * 0.3)
    rot(p, 'hips', rz=-5 * sin(ph))
    rot(p, 'chest', rz=7 * sin(ph))
    rot(p, 'head', rz=-2.5 * sin(ph))
    p['hips'].x += -0.010 * S.H * cos(ph)
    rot(p, 'hips', ry=2.0 * cos(ph)); rot(p, 'spine', ry=-1.5 * cos(ph))
    rot(p, 'spine', rx=lean * 0.35); rot(p, 'chest', rx=lean * 0.35)
    for side, off in (('L', 0.0), ('R', pi)):
        s = sin(ph + off)
        if C.get('idle_arms') == 'cane' and side == C.get('cane_side', 'L'):
            # cane planted ahead with the opposite leg: small swing, cane stays near-vertical
            limb(p, 'upperarm', side, flex=-12 + 0.35 * Aarm * s, ab=5)
            limb(p, 'forearm', side, flex=-4)
            limb(p, 'hand', side, flex=-(lean * 0.7) + 8 - 0.35 * Aarm * s)
            continue
        limb(p, 'upperarm', side, flex=Aarm * s, ab=4)
        limb(p, 'forearm', side, flex=-14 - 16 * max(0.0, -s))
    return legs

def c_walk(t, S, C):
    p = P(); e = C['energy']; ph = 2 * pi * t
    walk_pose(p, S, C, ph, A=18 + 6 * e, Aarm=14 + 12 * e, kneeA=38 + 10 * e, lean=4)
    rot(p, 'head', rx=-1.5 * cos(2 * ph))
    return p

def c_run(t, S, C):
    p = P(); e = C['energy']; ph = 2 * pi * t
    lean = 12 + 4 * e
    legs = walk_pose(p, S, C, ph, A=28 + 10 * min(e, 1.2), Aarm=0, kneeA=70 + 20 * min(e, 1.2), lean=lean)
    for side, off in (('L', 0.0), ('R', pi)):
        s_ = sin(ph + off)
        limb(p, 'upperarm', side, flex=(36 + 12 * e) * s_ - 8, ab=6)     # pumping, elbows bent
        limb(p, 'forearm', side, flex=-78 + 14 * s_)
        limb(p, 'forearm', side, flex=14 + 16 * max(0.0, -s_))           # undo walk_pose forearm swing
        limb(p, 'hand', side, flex=-10)
    p['hips'].z += 0.018 * S.H * e * max(0.0, -cos(2 * ph))              # flight bounce
    rot(p, 'chest', rz=4 * sin(ph))
    rot(p, 'head', rx=-lean * 0.55)                                      # keep eyes up while leaning
    return p

_LIMP_T = None
def limp_phase(t):
    global _LIMP_T
    if _LIMP_T is None:
        phs = np.linspace(0, 2 * pi, 2001)
        spd = 1 + 0.5 * np.cos(phs)          # fast through R-stance (cos>0)
        dt = 1 / spd; cum = np.concatenate([[0], np.cumsum((dt[1:] + dt[:-1]) * 0.5 * (phs[1] - phs[0]))])
        cum /= cum[-1]; _LIMP_T = (cum, phs)
    cum, phs = _LIMP_T
    return float(np.interp(t % 1.0, cum, phs))

def c_limp(t, S, C):
    p = P(); ph = limp_phase(t)
    walk_pose(p, S, C, ph, A=15, Aarm=8, kneeA=32, lean=8, injured='R')
    rst = max(0.0, cos(ph)) ** 2           # R leg (injured) carrying weight
    p['hips'].z -= 0.02 * S.H * rst
    rot(p, 'spine', ry=5 * rst - 1.5, rx=3 * rst); rot(p, 'chest', ry=3 * rst)
    rot(p, 'head', rx=5 * rst - 2, ry=-3 * rst)
    limb(p, 'upperarm', 'R', ab=14 + 6 * rst, flex=-6)
    limb(p, 'forearm', 'R', flex=-18)
    limb(p, 'upperarm', 'L', ab=6, flex=-10 * rst)
    return p

def c_talk(t, S, C):
    p = P(); e = C['energy']; ph = 2 * pi * t
    breathe(p, 2 * ph, 0.7)
    rot(p, 'hips', ry=-1.2 * sin(ph)); rot(p, 'spine', ry=0.8 * sin(ph))
    limb(p, 'upperarm', 'R', flex=-26 - 9 * sin(2 * ph) * e, ab=13 + 6 * sin(ph), tw=-6)
    limb(p, 'forearm', 'R', flex=-58 + 20 * sin(2 * ph + 0.8) * e, tw=-12 + 12 * sin(2 * ph))
    limb(p, 'hand', 'R', flex=-10 + 12 * sin(2 * ph + 1.4), ab=-8)
    g = max(0.0, sin(ph + 2.2))
    if C.get('idle_arms') == 'cane':
        idle_arms(p, C, 'L')
    else:
        limb(p, 'upperarm', 'L', flex=-8 - 12 * g * e, ab=5 + 4 * g)
        limb(p, 'forearm', 'L', flex=-24 - 34 * g * e, tw=-8 * g)
    rot(p, 'head', rx=3.0 * sin(4 * ph) * e - 1, rz=9 * sin(ph) * e, ry=3 * sin(2 * ph + 1))
    rot(p, 'chest', rz=4 * sin(ph) * e)
    for side in 'LR':
        limb(p, 'shin', side, flex=2); limb(p, 'thigh', side, flex=-1); limb(p, 'foot', side, flex=-1)
    return p

def c_wave(t, S, C):
    p = P(); e = C['energy']
    env = smooth(0.0, 0.2, t) * (1 - smooth(0.8, 1.0, t))
    wv = sin(2 * pi * 3.0 * (t - 0.2)) if 0.2 < t < 0.87 else 0.0
    limb(p, 'upperarm', 'R', ab=108 * env, flex=-18 * env)
    limb(p, 'forearm', 'R', ab=(52 + 26 * wv * min(1.0, e)) * env, flex=-10 * env)
    limb(p, 'hand', 'R', ab=12 * wv * env)
    idle_arms(p, C, 'L', 1.0)
    rot(p, 'chest', ry=5 * env, rx=-2 * env)
    rot(p, 'head', ry=-6 * env, rx=-3 * env, rz=-5 * env)
    bounce = 0.006 * S.H * e * env * abs(sin(2 * pi * 3 * t))
    p['hips'].z += -bounce
    for side in 'LR':
        th, kn, ft = leg_ik(S, 0, -bounce)
        limb(p, 'thigh', side, flex=th); limb(p, 'shin', side, flex=kn); limb(p, 'foot', side, flex=ft)
    idle_arms(p, C, 'R', 1 - env)
    return p

def c_beckon(t, S, C):
    p = P(); e = C['energy']; ph = 2 * pi * 2 * t
    c = 0.5 - 0.5 * cos(ph)
    limb(p, 'upperarm', 'R', flex=-62, ab=24, tw=-8)
    limb(p, 'forearm', 'R', flex=-12 - 72 * c, tw=-20)
    limb(p, 'hand', 'R', flex=-12 - 30 * (0.5 - 0.5 * cos(ph + 0.6)))
    idle_arms(p, C, 'L', 1.0)
    rot(p, 'chest', rz=-8, rx=-1); rot(p, 'spine', rz=-4)
    rot(p, 'head', rz=12, rx=3 * sin(ph) - 2, ry=-3)
    breathe(p, pi * t * 2, 0.6)
    for side in 'LR':
        limb(p, 'shin', side, flex=3); limb(p, 'thigh', side, flex=-1.5); limb(p, 'foot', side, flex=-1.5)
    limb(p, 'thigh', 'R', ab=3); limb(p, 'foot', 'R', ab=-3)
    return p

def c_cower(t, S, C):
    p = P(); e = C['energy']
    sh = sin(2 * pi * 4 * t)
    drop = 0.38 * S.leg_len
    hy = 0.10 * S.leg_len
    hrx = 12
    rot(p, 'hips', rx=hrx)
    p['hips'] += Vector((0, hy, -drop + 0.003 * S.H * sh))
    for side in 'LR':
        th, kn, ft = leg_ik(S, hy, -drop, 0.0, 0.0, hips_rx=hrx)
        limb(p, 'thigh', side, flex=th, ab=4); limb(p, 'shin', side, flex=kn); limb(p, 'foot', side, flex=ft)
        limb(p, 'foot', side, ab=-4)
    rot(p, 'spine', rx=16); rot(p, 'chest', rx=14, rz=1.6 * sh)
    rot(p, 'head', rx=14, rz=-1.0 * sh)
    for side in 'LR':
        limb(p, 'upperarm', side, flex=-168, ab=30, tw=0)
        limb(p, 'forearm', side, flex=-78 + 3 * sh, ab=-40, tw=-10)
        limb(p, 'hand', side, flex=-15)
    return p

def po_sit(C):
    po = C.get('posture', {}); return po.get('spine', 0) + po.get('chest', 0) + 4   # torso lean to cancel

def c_sit(t, S, C):
    p = P(); e = C['energy']; ph = 2 * pi * t
    seat = 0.45
    new_hip = seat + S.leg_r * 0.95
    dz = new_hip - S.hip_z
    p['hips'] += Vector((0, 0.0, dz))
    rot(p, 'hips', rx=-4)
    th_w = -86.0
    knee_z = new_hip + S.l1 * sin(radians(th_w + 90))
    dangle = (knee_z - S.l2) > S.ankle_z + 0.01
    for side, off in (('L', 0.0), ('R', pi)):
        if dangle:
            swing = 14 * sin(2 * ph * 2 + off) * min(1.0, e)
            shin_w = 12 + swing
            kn = shin_w - th_w
            ft = -shin_w + 8
        else:
            cz = clamp((knee_z - S.ankle_z) / S.l2, -1, 1)
            shin_w = -degrees(acos(cz))
            kn = shin_w - th_w
            ft = -shin_w
        limb(p, 'thigh', side, flex=th_w + 4, ab=5)
        limb(p, 'shin', side, flex=kn)
        limb(p, 'foot', side, flex=ft)
        if C.get('idle_arms') == 'cane' and side == C.get('cane_side', 'L'):
            limb(p, 'upperarm', side, flex=-24, ab=12)      # hand resting on the cane, cane near-vertical
            limb(p, 'forearm', side, flex=-2)
            limb(p, 'hand', side, flex=-po_sit(C) + 6)
    rot(p, 'spine', rx=5); rot(p, 'chest', rx=3)
    breathe(p, 2 * ph, 0.8)
    rot(p, 'head', rz=12 * sin(ph) * e, rx=3 * sin(2 * ph + 0.5))
    # relaxed hands: palms resting on the tops of the thighs, elbows soft, shoulders down (2-bone IK)
    for side in 'LR':
        if C.get('idle_arms') == 'cane' and side == C.get('cane_side', 'L'): continue
        rest_hand_on_thigh(p, S, C, side, frac=0.74 + 0.02 * sin(ph + (0 if side == 'L' else 1.3)))
    return p

def Emat(p, b, extra=0.0):
    r = p['rot'].get(b, [0.0, 0.0, 0.0])
    return Euler((radians(r[0] + extra), radians(r[1]), radians(r[2])), 'XYZ').to_matrix()

def rest_hand_on_thigh(p, S, C, side, frac=0.62):
    po = C.get('posture', {})
    s_ = sgn(side); J = S.joints[side]; H = S.H
    Wh = Emat(p, 'hips')
    Ws = Wh @ Emat(p, 'spine', po.get('spine', 0))
    Wc = Ws @ Emat(p, 'chest', po.get('chest', 0))
    hips_h = Vector((0, 0, S.hip_z)) + p['hips']
    spine_h = hips_h + Wh @ Vector((0, 0, S.spine_z - S.hip_z))
    chest_h = spine_h + Ws @ Vector((0, 0, S.chest_z - S.spine_z))
    sh = chest_h + Wc @ (J['sh'] - Vector((0, 0, S.chest_z)))
    # thigh top surface
    Wt = Wh @ Emat(p, 'thigh.' + side)
    th_h = hips_h + Wh @ Vector((s_ * S.leg_x, 0, 0))
    tdir = Wt @ Vector((0, 0, -1))
    low = C['outfit'].get('lower') or {}
    extra = 0.03 * H if low.get('type') in ('skirt', 'sarong') else 0.012 * H
    top_off = S.leg_r + extra
    hand_c = th_h + tdir * (S.l1 * frac) + Vector((-s_ * 0.15 * S.leg_r, 0, top_off + S.hand_r * 0.62))
    hdir = Vector((s_ * -0.15, -0.93, -0.33)).normalized()
    wr = hand_c - hdir * S.hand_r * 1.0
    lu, lf = S.up_len, S.fore_len
    d = wr - sh; dist = min(d.length, (lu + lf) * 0.995)
    dn = d.normalized()
    a = (lu * lu + dist * dist - lf * lf) / (2 * dist)
    hgt = sqrt(max(0.0, lu * lu - a * a))
    pole = Vector((s_ * 0.75, 0.35, -0.2))
    pole = (pole - dn * pole.dot(dn)).normalized()
    el = sh + dn * a + pole * hgt
    wr = sh + dn * dist
    rest = J['dir']
    Wu = rest.rotation_difference((el - sh).normalized()).to_matrix()
    Wf = rest.rotation_difference((wr - el).normalized()).to_matrix()
    Wha = rest.rotation_difference(hdir).to_matrix()
    p['mat']['upperarm.' + side] = Wc.inverted() @ Wu
    p['mat']['forearm.' + side] = Wu.inverted() @ Wf
    p['mat']['hand.' + side] = Wf.inverted() @ Wha

def c_cheer(t, S, C):
    p = P(); e = C['energy']
    env = smooth(0.0, 0.22, t) * (1 - smooth(0.72, 1.0, t))
    hop = max(0.0, sin(2 * pi * 2 * (t - 0.22))) if 0.22 < t < 0.72 else 0.0
    wig = sin(2 * pi * 4 * t) * env
    for side in 'LR':
        limb(p, 'upperarm', side, ab=(55 + 25 * min(e, 1.2)) * env, flex=(-70 * env) + 8 * wig)
        limb(p, 'forearm', side, flex=-55 * env, tw=-10 * env)
        limb(p, 'hand', side, flex=-15 * env)
    idle_arms(p, C, 'L', 1 - env); idle_arms(p, C, 'R', 1 - env)
    rot(p, 'chest', rx=-5 * env); rot(p, 'head', rx=-8 * env, rz=6 * wig)
    crouch = 0.05 * S.leg_len * env * (1 - hop) * e
    lift = 0.035 * S.H * hop * e * e
    for side in 'LR':
        th, kn, ft = leg_ik(S, 0, -crouch)
        limb(p, 'thigh', side, flex=th); limb(p, 'shin', side, flex=kn); limb(p, 'foot', side, flex=ft + 10 * hop)
    p['hips'].z += -crouch + lift
    return p

def c_nod(t, S, C):
    p = P()
    env = smooth(0.0, 0.12, t) * (1 - smooth(0.82, 1.0, t))
    n = 0.5 - 0.5 * cos(2 * pi * 2 * t)
    rot(p, 'head', rx=13 * env * n, rz=3 * env)
    rot(p, 'chest', rx=3 * env * n)
    for side in 'LR': idle_arms(p, C, side)
    return p

CLIPS = [  # name, duration(s), loop, fn
    ('Idle', 3.0, True, c_idle),
    ('Walk', None, True, c_walk),       # None -> character walk_period
    ('Run', 'run', True, c_run),        # 'run' -> character run_period
    ('Talk', 2.0, True, c_talk),
    ('Wave', 1.6, False, c_wave),
    ('Beckon', 1.2, True, c_beckon),
    ('Cower', 1.0, True, c_cower),
    ('Sit', 3.0, True, c_sit),
    ('Limp', 1.4, True, c_limp),
    ('Cheer', 1.2, False, c_cheer),
    ('Nod', 1.0, False, c_nod),
]

def apply_posture(p, C, clip):
    po = C.get('posture', {})
    rot(p, 'spine', rx=po.get('spine', 0)); rot(p, 'chest', rx=po.get('chest', 0))
    rot(p, 'head', rx=po.get('head', 0))

# --------------------------------------------------------------------------------------
# Blender object assembly
# --------------------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS

def make_armature(S, name):
    ad = bpy.data.armatures.new(name + '_Armature')
    ob = bpy.data.objects.new(name, ad)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    H = S.H
    pos = {
        'root': (Vector((0, 0, 0)), Vector((0, 0, 0.12 * H))),
        'hips': (Vector((0, 0, S.hip_z)), Vector((0, 0, S.spine_z))),
        'spine': (Vector((0, 0, S.spine_z)), Vector((0, 0, S.chest_z))),
        'chest': (Vector((0, 0, S.chest_z)), Vector((0, 0, S.neck_z))),
        'head': (Vector((0, 0, S.neck_z)), Vector((0, 0, S.H))),
    }
    for side in 'LR':
        J = S.joints[side]; s = sgn(side)
        pos['upperarm.' + side] = (J['sh'], J['el'])
        pos['forearm.' + side] = (J['el'], J['wr'])
        pos['hand.' + side] = (J['wr'], J['tip'])
        x = s * S.leg_x
        pos['thigh.' + side] = (Vector((x, 0, S.hip_z)), Vector((x, 0, S.knee_z)))
        pos['shin.' + side] = (Vector((x, 0, S.knee_z)), Vector((x, 0, S.ankle_z)))
        pos['foot.' + side] = (Vector((x, 0, S.ankle_z)), Vector((x, -S.foot_len * 0.68, S.foot_h * 0.6)))
    for bn in BONES:
        b = eb.new(bn); b.head, b.tail = pos[bn]; b.roll = 0.0
    for bn in BONES:
        if bn in PARENT:
            eb[bn].parent = eb[PARENT[bn]]
            eb[bn].use_connect = False
    eb['root'].use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob

def make_materials(name, img, sheen):
    mats = []
    for mname, rough, spec, sh in (('NPC_Felt', 0.88, 0.25, sheen), ('NPC_Gloss', 0.22, 0.5, False)):
        m = bpy.data.materials.new(f'{mname}')
        m.use_nodes = True
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Linear'
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = rough
        if 'Specular IOR Level' in bsdf.inputs: bsdf.inputs['Specular IOR Level'].default_value = spec
        if sh:
            bsdf.inputs['Sheen Weight'].default_value = 0.22
            bsdf.inputs['Sheen Roughness'].default_value = 0.35
            bsdf.inputs['Sheen Tint'].default_value = (0.45, 0.45, 0.45, 1.0)
        m.use_backface_culling = True
        mats.append(m)
    return mats

def build_palette_for(C, mbs, tier):
    name = C['name']
    swatches = dict(C['palette'])
    for k, v in COMMON_SWATCHES.items(): swatches.setdefault(k, v)
    used = []
    for mb in mbs:
        for f in mb.faces:
            if f[2] not in used: used.append(f[2])
    missing = [u for u in used if u not in swatches]
    if missing: raise KeyError(f'{name}: missing swatches {missing}')
    sw_used = {k: swatches[k] for k in swatches if k in used}
    img_np, index = build_palette(sw_used, tier['tex'])
    size = tier['tex']
    img = bpy.data.images.new(f'{name}_Palette', size, size, alpha=False)
    rgba = np.concatenate([img_np, np.ones((size, size, 1))], axis=2).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return index, make_materials(name, img, tier['sheen']), img_np

def make_mesh(obname, mb, index, mats, arm_ob, parent_bone=None):
    me = bpy.data.meshes.new(obname)
    me.from_pydata([tuple(c) for c in mb.co], [], [f[0] for f in mb.faces])
    uvl = me.uv_layers.new(name='UVMap')
    uvs = []
    for f in mb.faces:
        for uv in f[1]: uvs.extend(atlas_uv(index, f[2], uv))
    uvl.data.foreach_set('uv', uvs)
    mat_used = sorted(set(f[3] for f in mb.faces))
    remap = {}
    for mi in mat_used:
        me.materials.append(mats[mi]); remap[mi] = len(me.materials) - 1
    me.polygons.foreach_set('material_index', [remap[f[3]] for f in mb.faces])
    me.polygons.foreach_set('use_smooth', [True] * len(mb.faces))
    me.validate(clean_customdata=False)
    bm = bmesh.new(); bm.from_mesh(me)
    thr = radians(58)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a = e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0)
            if a > thr: e.smooth = False
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(obname, me)
    bpy.context.scene.collection.objects.link(ob)
    if parent_bone is None:
        ob.parent = arm_ob
        mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = arm_ob
        groups = {bn: ob.vertex_groups.new(name=bn) for bn in BONES if bn != 'root'}
        for vi, w in enumerate(mb.w):
            items = sorted([(b_, x) for b_, x in w.items() if x > 1e-4], key=lambda k: -k[1])[:4]
            tot = sum(x for _, x in items)
            for b_, x in items:
                groups[b_].add([vi], x / tot, 'REPLACE')
    else:
        # rigid prop parented to a bone (exports as a child node of that joint)
        ob.parent = arm_ob; ob.parent_type = 'BONE'; ob.parent_bone = parent_bone
        bpy.context.view_layer.update()
        ob.matrix_world = Matrix.Identity(4)
    return ob

def bake_clips(arm_ob, S, C):
    rest = {b.name: b.matrix_local.to_3x3() for b in arm_ob.data.bones}
    arm_ob.animation_data_create()
    info = []
    for pb in arm_ob.pose.bones: pb.rotation_mode = 'QUATERNION'
    for name, dur, loop, fn in CLIPS:
        if dur is None: dur = C.get('walk_period', 1.0)
        if dur == 'run': dur = C.get('run_period', 0.66)
        act = bpy.data.actions.new(name); act.use_fake_user = True
        arm_ob.animation_data.action = act
        nf = max(2, int(round(dur * FPS)))
        prev = {}
        for f in range(nf + 1):
            t = f / nf
            p = fn(t, S, C)
            apply_posture(p, C, name)
            for pb in arm_ob.pose.bones:
                r = p['rot'].get(pb.name, (0.0, 0.0, 0.0))
                M = Euler((radians(r[0]), radians(r[1]), radians(r[2])), 'XYZ').to_matrix()
                if pb.name in p.get('mat', {}): M = p['mat'][pb.name]      # IK-solved bones
                B = rest[pb.name]
                qv = (B.inverted() @ M @ B).to_quaternion()
                if pb.name in prev and prev[pb.name].dot(qv) < 0: qv.negate()
                prev[pb.name] = qv.copy()
                pb.rotation_quaternion = qv
                pb.keyframe_insert('rotation_quaternion', frame=f)
                if pb.name == 'hips':
                    pb.location = rest['hips'].inverted() @ p['hips']
                    pb.keyframe_insert('location', frame=f)
                elif pb.name == 'root':
                    pb.location = (0, 0, 0)
                    pb.keyframe_insert('location', frame=f)
        info.append(dict(name=name, duration=round(nf / FPS, 3), frames=nf, loop=loop))
        arm_ob.animation_data.action = None
    # stash every action in its own NLA track so nothing is orphaned
    for a in bpy.data.actions:
        tr = arm_ob.animation_data.nla_tracks.new(); tr.name = a.name
        st = tr.strips.new(a.name, 0, a); tr.mute = True
    for pb in arm_ob.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    return info

def export(path, arm_ob, mesh_obs):
    bpy.ops.object.select_all(action='DESELECT')
    arm_ob.select_set(True)
    for mo in mesh_obs: mo.select_set(True)
    bpy.context.view_layer.objects.active = arm_ob
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
              export_texcoord=True, export_normals=True, export_tangents=False, export_materials='EXPORT',
              export_image_format='JPEG', export_jpeg_quality=90, export_image_quality=90,
              export_skins=True, export_animations=True, export_animation_mode='ACTIONS',
              export_force_sampling=True, export_frame_step=1, export_optimize_animation_size=True,
              export_optimize_animation_keep_anim_armature=True, export_def_bones=False,
              export_leaf_bone=False, export_rest_position_armature=True, export_influence_nb=4,
              export_all_influences=False, export_morph=False, export_lights=False, export_cameras=False,
              export_extras=False, export_anim_slide_to_zero=False, export_negative_frame='SLIDE',
              export_nla_strips=False, export_bake_animation=False)
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    kw = {k: v for k, v in kw.items() if k in props}
    bpy.ops.export_scene.gltf(**kw)

def walk_speed(S, C):
    e = C['energy']; A = radians(18 + 6 * e)
    return 4 * S.leg_len * 0.97 * sin(A) / C.get('walk_period', 1.0)

def run_speed(S, C):
    e = C['energy']; A = radians(28 + 10 * min(e, 1.2))
    return 4 * S.leg_len * 0.9 * sin(A) * 1.25 / C.get('run_period', 0.66)

def build_character(cid, tier_name):
    C = copy.deepcopy(CHARACTERS[cid]); tier = TIERS[tier_name]; q = tier['q']
    # geometry pass; if over the tier's triangle budget, lower the detail factor and rebuild
    for attempt in range(8):
        S = derive(C)
        mb = MB()
        build_torso(mb, S, C, q)
        for side in 'LR':
            build_arm(mb, S, C, q, side); build_leg(mb, S, C, q, side); build_foot(mb, S, C, q, side)
        build_head(mb, S, C, q)
        build_hair(mb, S, C, q)
        build_headwear(mb, S, C, q)
        build_collar(mb, S, C, q)
        build_top_details(mb, S, C, q)
        build_props(mb, S, C, q)
        extras = build_extras(S, C, q)          # [(node name, MB, parent bone)]
        ntri = sum(len(f[0]) - 2 for m in [mb] + [e[1] for e in extras] for f in m.faces)
        if ntri <= tier['tri_budget'] * 0.985: break
        q *= 0.95
    reset_scene()
    arm_ob = make_armature(S, C['name'])
    index, mats, img_np = build_palette_for(C, [mb] + [e[1] for e in extras], tier)
    mesh_ob = make_mesh(C['name'] + '_Mesh', mb, index, mats, arm_ob)
    extra_obs = [make_mesh(nm, emb, index, mats, arm_ob, parent_bone=pb) for nm, emb, pb in extras]
    tris = ntri
    matnames = sorted(set(m.name for o in [mesh_ob] + extra_obs for m in o.data.materials))
    clips = bake_clips(arm_ob, S, C)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, C['file'] + tier['suffix'] + '.glb')
    export(path, arm_ob, [mesh_ob] + extra_obs)
    # height (bbox of mesh in rest)
    zs = [c.z for c in mb.co]
    info = dict(id=cid, tier=tier_name, file=os.path.basename(path), bytes=os.path.getsize(path),
                tris=tris, verts=len(mb.co), materials=matnames, texture=tier['tex'],
                height=round(max(zs), 3), design_height=C['body']['height'],
                bones=[b.name for b in arm_ob.data.bones], clips=clips,
                walk_speed_mps=round(walk_speed(S, C), 3), run_speed_mps=round(run_speed(S, C), 3),
                sit_seat_height=0.45, thigh_len=round(S.l1, 3),
                hand_R_world=[round(x, 3) for x in S.joints['R']['wr']],
                extra_nodes=[e[0] for e in extras])
    over = tris > tier['tri_budget']
    print(f"[NPC] {cid:7s} {tier_name:7s} q={q:.2f} tris={tris:5d}{' OVER BUDGET' if over else ''} verts={len(mb.co)} "
          f"size={info['bytes'] / 1024:.0f}KB height={info['height']} mats={matnames}")
    try:
        import imageio  # noqa
    except Exception:
        pass
    return info

def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    only = None; tiers = ['desktop', 'mobile']
    for i, a in enumerate(argv):
        if a == '--only': only = argv[i + 1].split(',')
        if a == '--out':
            global OUT_DIR
            OUT_DIR = argv[i + 1]
        if a == '--tier':
            v = argv[i + 1]; tiers = ['desktop', 'mobile'] if v == 'both' else [v]
    ids = only or list(CHARACTERS.keys())
    report = []
    for cid in ids:
        for tn in tiers:
            report.append(build_character(cid, tn))
    rp = os.path.join(OUT_DIR, 'npc_build_report.json')
    with open(rp, 'w') as fh: json.dump(report, fh, indent=1)
    print('[NPC] report ->', rp)

if __name__ == '__main__':
    main()
