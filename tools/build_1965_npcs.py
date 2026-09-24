"""
Sparky Discovery - Chapter 2 (Queenstown, 9 Aug 1965) NPC builder.

Reuses the Chapter 1 procedural builder (tools/build_ww2_npcs.py: body, rig, clips, palette,
export) and only swaps in the 1965 cast. Same bones and clip names as every other NPC.

Run (or use tools/build_1965_npcs.sh, which also meshopt-compresses the output):
  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python tools/build_1965_npcs.py -- [--only boon65,siti65] [--tier desktop|mobile|both] [--out DIR]

Costume notes (docs/research/1965-history.md, docs/research/ww2-costume.md):
  - Boon (30), kopitiam towkay: white cotton singlet, dark trousers, towel over the shoulder, slippers.
    Same face DNA as young Boon / old Mr. Boon (round head, wide grin, arched brows).
  - Siti (35), teacher: plain baju kurung in a sober blue, batik kain, cat-eye glasses, hair in a bun,
    a cloth bag of exercise books.
  - Farid (16): short-sleeved pale-teal striped shirt, khaki shorts, sandals. Side-parted short hair.
  - Ravi (16): white shirt, long dark trousers, sandals. Slim.
  - Mr. Rajan (63): grey hair and moustache, glasses, white short-sleeved shirt, belt, dark trousers.
  - Ah Pek Tan (70s): thin, stooped, white singlet, loose grey trousers, towel, wooden-look slippers.
  - Makcik Rohani (~45): floral baju kurung, batik kain, selendang over the shoulders.
  - Auntie Letchumi (~65): saree (approximated: blouse + bordered skirt + bordered pallu), grey bun.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_ww2_npcs as B  # noqa: E402

body = B.body

CAST_1965 = {
    # ---------------------------------------------------------------- Boon, 30
    'boon65': dict(
        name='Boon65', file='npc-boon65', age=30,
        body=body(height=1.64, head_frac=0.29, head_aspect=(1.0, 0.95), leg_frac=0.45,
                  torso_w=0.262, torso_depth=0.84, hip_ratio=0.97, belly=0.04, neck_r=0.043,
                  arm_r=0.037, leg_r=0.045, hand_r=0.044, foot_len=0.145, arm_len=1.02, arm_spread=12),
        energy=1.1, walk_period=0.95, run_period=0.64, posture=dict(spine=0, chest=-2, head=0),
        idle_arms='relaxed',
        palette={
            'skin': '#e3b892', 'skin_shade': '#cc9d78',
            'face': dict(kind='face', skin='#e3b892', blush='#e2937e'),
            'hair': dict(kind='strands', base='#191412'),
            'singlet': dict(kind='rib', base='#f3f0e8', amt=0.03),
            'trousers': dict(kind='twill', base='#39414d', amt=0.05),
            'towel': dict(kind='check', base='#f1ece0', stripe='#4f79a8', line='#f6f2ea', nu=2, nv=6),
            'slipper': '#2d2a28', 'sstrap': '#1f1d1c',
        },
        hair=dict(style='crop', sw='hair', scale=(1.04, 1.05, 1.04),
                  line=[(0, 32), (10, 28), (22, 33), (45, 26), (75, 12), (95, 6), (130, -14), (180, -28)]),
        face=dict(eye=0.95, eye_az=22, eye_el=-6, brow=dict(inner=2.5, outer=0.0, arch=2.0, r=1.1),
                  mouth=dict(w=10.0, smile=5.5, el=-28), nose=1.0, blush=0.45),
        outfit=dict(
            top=dict(sw='singlet', hem=('hip', -0.015), ease=0.008, flare=1.03, sleeve=0.0,
                     collar='singlet', top_z='armpit'),
            lower=dict(type='trousers', sw='trousers', hem=('ankle', 0.02), top='waist', ease=0.007,
                       leg_ease=0.013, leg_flare=1.18),
            feet=dict(type='flipflops', sw='slipper', strap='sstrap'),
        ),
        props=[dict(type='towel', side='L', sw='towel')],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Siti, 35 (teacher)
    'siti65': dict(
        name='Siti65', file='npc-siti65', age=35,
        body=body(height=1.56, head_frac=0.29, head_aspect=(0.97, 0.93), leg_frac=0.44,
                  torso_w=0.234, torso_depth=0.80, hip_ratio=1.03, belly=0.01, neck_r=0.038,
                  arm_r=0.032, leg_r=0.041, hand_r=0.040, foot_len=0.13, arm_len=1.0, arm_spread=12),
        energy=1.0, walk_period=0.98, run_period=0.66, posture=dict(spine=0, chest=-1, head=0),
        idle_arms='clasp',
        palette={
            'skin': '#b7825f', 'skin_shade': '#a26c4d',
            'face': dict(kind='face', skin='#b7825f', blush='#c26d5f'),
            'hair': dict(kind='strands', base='#1c1512'),
            'baju': dict(kind='twill', base='#4f6f8f', amt=0.03),
            'trim': '#d9c9a0',
            'batik': dict(kind='batik', base='#5a3b2a', motif='#e0c48e', dark='#33231a', border='#9a5a2e'),
            'sandal': '#5b4230', 'pin': '#c9a04a', 'frame': '#2c2320',
            'bag': dict(kind='twill', base='#b9a47c', amt=0.05), 'strap': '#8e7b58',
            'news': dict(kind='news', base='#e9dfc2', ink='#5d7b9c'),   # exercise books
        },
        hair=dict(style='bun', sw='hair', scale=(1.045, 1.055, 1.04), pin='pin',
                  line=[(0, 40), (8, 33), (25, 30), (50, 16), (72, -4), (95, -18), (135, -38), (180, -46)]),
        face=dict(eye=0.98, eye_az=21, eye_el=-5, brow=dict(inner=1.5, outer=-0.5, arch=1.5, r=1.0),
                  mouth=dict(w=8.5, smile=3.6, el=-27), nose=0.92, blush=0.45, lashes=True,
                  glasses=dict(sw='frame')),
        outfit=dict(
            top=dict(sw='baju', hem=('knee', 0.03), ease=0.016, flare=1.34,
                     sleeve=1.0, sleeve_ease=0.006, sleeve_flare=1.12, collar='round_trim', trim='trim'),
            lower=dict(type='skirt', sw='batik', hem=('ankle', 0.03), top='waist', ease=0.008, flare=1.12),
            feet=dict(type='sandals', sw='sandal'),
        ),
        props=[dict(type='news_bag', side='R', sw='bag', strap='strap', papers='news')],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Farid, 16
    'farid': dict(
        name='Farid', file='npc-farid', age=16,
        body=body(height=1.58, head_frac=0.30, head_aspect=(0.96, 0.92), leg_frac=0.46,
                  torso_w=0.236, torso_depth=0.76, hip_ratio=0.9, belly=0.0, neck_r=0.040,
                  arm_r=0.033, leg_r=0.041, hand_r=0.043, foot_len=0.15, arm_len=1.03, arm_spread=12),
        energy=1.25, walk_period=0.88, run_period=0.58, posture=dict(spine=0, chest=-3, head=1),
        idle_arms='relaxed',
        palette={
            'skin': '#a8734f', 'skin_shade': '#94623f',
            'face': dict(kind='face', skin='#a8734f', blush='#b0604d'),
            'hair': dict(kind='strands', base='#16110e'),
            'shirt': dict(kind='pinstripe', base='#cfe3e0', line='#7fa9b0', n=18),   # a Sunday shirt, not school white
            'shorts': dict(kind='twill', base='#a8966b', amt=0.05),
            'button': '#e3e1da', 'sole': '#3c3029', 'sstrap': '#5a4636',
        },
        hair=dict(style='short', sw='hair', scale=(1.04, 1.05, 1.035),
                  line=[(0, 38), (25, 34), (50, 30), (70, 10), (86, -10), (100, -12), (140, -28), (180, -36)]),
        face=dict(eye=1.02, eye_az=21, eye_el=-5, brow=dict(inner=0.5, outer=0.8, arch=1.6, r=1.1),
                  mouth=dict(w=9.5, smile=5.5, el=-28), nose=0.95, blush=0.35),
        outfit=dict(
            top=dict(sw='shirt', hem=('hip', -0.035), ease=0.010, flare=1.04, sleeve=0.42, sleeve_ease=0.010,
                     sleeve_flare=1.2, collar='shirt', buttons='button', pockets='L'),
            lower=dict(type='shorts', sw='shorts', hem=('knee', 0.06), top='waist', ease=0.007,
                       leg_ease=0.014, leg_flare=1.22),
            feet=dict(type='sandals', sw='sole', strap='sstrap'),
        ),
        props=[],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Ravi, 16
    'ravi': dict(
        name='Ravi', file='npc-ravi', age=16,
        body=body(height=1.62, head_frac=0.295, head_aspect=(0.94, 0.91), leg_frac=0.47,
                  torso_w=0.228, torso_depth=0.76, hip_ratio=0.9, belly=0.0, neck_r=0.039,
                  arm_r=0.031, leg_r=0.039, hand_r=0.042, foot_len=0.15, arm_len=1.03, arm_spread=10),
        energy=0.9, walk_period=0.98, run_period=0.64, posture=dict(spine=2, chest=0, head=-2),
        idle_arms='relaxed',
        palette={
            'skin': '#74492f', 'skin_shade': '#633d27',
            'face': dict(kind='face', skin='#74492f', blush='#7f4735'),
            'hair': dict(kind='strands', base='#120e0c'),
            'shirt': dict(kind='twill', base='#eef0f2', amt=0.025),
            'trousers': dict(kind='twill', base='#2b2f38', amt=0.05),
            'button': '#dcdad3', 'sandal': '#4d3526',
        },
        hair=dict(style='short', sw='hair', scale=(1.045, 1.055, 1.04),
                  line=[(0, 36), (30, 32), (60, 16), (86, -10), (100, -12), (140, -30), (180, -38)]),
        face=dict(eye=0.98, eye_az=20, eye_el=-4, brow=dict(inner=0.8, outer=0.2, arch=1.2, r=1.2),
                  mouth=dict(w=7.5, smile=2.5, el=-29), nose=1.1, blush=0.2),
        outfit=dict(
            top=dict(sw='shirt', hem=('hip', -0.03), ease=0.010, flare=1.04, sleeve=0.42, sleeve_ease=0.010,
                     sleeve_flare=1.18, collar='shirt', buttons='button', pockets='L'),
            lower=dict(type='trousers', sw='trousers', hem=('ankle', 0.015), top='waist', ease=0.006,
                       leg_ease=0.010, leg_flare=1.12),
            feet=dict(type='sandals', sw='sandal'),
        ),
        props=[],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Mr Rajan, 63
    'rajan65': dict(
        name='Rajan65', file='npc-rajan65', age=63,
        body=body(height=1.69, head_frac=0.285, head_aspect=(0.95, 0.91), leg_frac=0.45,
                  torso_w=0.262, torso_depth=0.82, hip_ratio=0.95, belly=0.06, neck_r=0.042,
                  arm_r=0.036, leg_r=0.045, hand_r=0.044, foot_len=0.15, arm_len=1.02, arm_spread=11),
        energy=0.85, walk_period=1.08, run_period=0.72, posture=dict(spine=3, chest=1, head=0),
        idle_arms='clasp',
        palette={
            'skin': '#7d5136', 'skin_shade': '#6c442c',
            'face': dict(kind='face', skin='#7d5136', blush='#8c4c3c'),
            'hair': dict(kind='strands', base='#9a9690'), 'brow': '#8b8781',
            'shirt': dict(kind='twill', base='#f2f0ea', amt=0.025),
            'trousers': dict(kind='twill', base='#4a4a46', amt=0.05),
            'belt': '#3a2a1e', 'brass': '#b8954a', 'button': '#dcdad3', 'shoe': '#2b1c14', 'frame': '#2a2522',
        },
        hair=dict(style='short', sw='hair', scale=(1.035, 1.045, 1.03), top_el=64,
                  line=[(0, 50), (40, 38), (70, 10), (86, -14), (100, -12), (140, -30), (180, -36)]),
        face=dict(eye=0.92, eye_az=20, eye_el=-4, brow=dict(inner=0.5, outer=0.0, arch=1.0, r=1.35, sw='brow'),
                  mouth=dict(w=7.5, smile=3.0, el=-30), nose=1.1, blush=0.2, moustache='thick', smile_lines=True,
                  glasses=dict(sw='frame')),
        outfit=dict(
            top=dict(sw='shirt', hem='waist', ease=0.011, flare=1.0, sleeve=0.42, sleeve_ease=0.010,
                     sleeve_flare=1.18, collar='shirt', buttons='button', pockets='L'),
            lower=dict(type='trousers', sw='trousers', hem=('ankle', 0.012), top='waist', ease=0.006,
                       leg_ease=0.008, leg_flare=1.1),
            feet=dict(type='shoes', sw='shoe'),
        ),
        props=[dict(type='belt', sw='belt', buckle='brass')],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Ah Pek Tan, 70s
    'ahpek': dict(
        name='AhPek', file='npc-ahpek', age=74,
        body=body(height=1.56, head_frac=0.29, head_aspect=(0.97, 0.93), leg_frac=0.44,
                  torso_w=0.232, torso_depth=0.80, hip_ratio=0.96, belly=0.02, neck_r=0.038,
                  arm_r=0.030, leg_r=0.038, hand_r=0.042, foot_len=0.14, arm_len=1.02, arm_spread=11),
        energy=0.6, walk_period=1.25, run_period=0.85, posture=dict(spine=12, chest=9, head=-14),
        idle_arms='clasp',
        palette={
            'skin': '#d9ad86', 'skin_shade': '#c2946e',
            'face': dict(kind='face', skin='#d9ad86', blush='#d98a76'),
            'hair': dict(kind='strands', base='#d7d3cb'), 'brow': '#c8c3ba',
            'singlet': dict(kind='rib', base='#ede9df', amt=0.035),
            'trousers': dict(kind='twill', base='#77786f', amt=0.05),
            'towel': dict(kind='check', base='#ede7da', stripe='#b0463f', line='#f3efe6', nu=2, nv=6),
            'slipper': '#5a3c28', 'sstrap': '#3a2a1f',
        },
        hair=dict(style='short', sw='hair', scale=(1.03, 1.04, 1.03), top_el=52,
                  line=[(0, 56), (30, 44), (60, 14), (85, -2), (100, -6), (140, -24), (180, -30)]),
        face=dict(eye=0.82, eye_az=21, eye_el=-6, brow=dict(inner=-1.0, outer=-2.5, arch=0.8, r=1.2, sw='brow'),
                  mouth=dict(w=8.0, smile=1.5, el=-29), nose=1.05, blush=0.3, smile_lines=True, lids=True),
        outfit=dict(
            top=dict(sw='singlet', hem=('hip', 0.035), ease=0.006, flare=1.0, sleeve=0.0,   # short: he sits all day
                     collar='singlet', top_z=('armpit', 0.012)),
            lower=dict(type='trousers', sw='trousers', hem=('shin_mid', 0.0), top='waist', ease=0.008,
                       leg_ease=0.016, leg_flare=1.28),
            feet=dict(type='flipflops', sw='slipper', strap='sstrap'),
        ),
        props=[dict(type='towel', side='R', sw='towel')],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Makcik Rohani, ~45
    'rohani': dict(
        name='Rohani', file='npc-rohani', age=46,
        body=body(height=1.53, head_frac=0.29, head_aspect=(0.98, 0.94), leg_frac=0.43,
                  torso_w=0.25, torso_depth=0.82, hip_ratio=1.06, belly=0.05, neck_r=0.039,
                  arm_r=0.034, leg_r=0.043, hand_r=0.041, foot_len=0.13, arm_len=1.0, arm_spread=12),
        energy=0.9, walk_period=1.02, run_period=0.70, posture=dict(spine=2, chest=1, head=-1),
        idle_arms='clasp',
        palette={
            'skin': '#a26d4a', 'skin_shade': '#8e5d3c',
            'face': dict(kind='face', skin='#a26d4a', blush='#ab5d4a'),
            'hair': dict(kind='strands', base='#1c1612'),
            'baju': dict(kind='floral', base='#c98a8f', flower='#f3e6da', centre='#8e4f5c', n=6),
            'trim': '#e8cf9a',
            'batik': dict(kind='batik', base='#3a5a4a', motif='#e6d6a8', dark='#203328', border='#8a6a3a'),
            'selendang': dict(kind='border', base='#f3ead8', band='#c98a8f'),
            'sandal': '#5e4232', 'pin': '#c9a04a',
        },
        hair=dict(style='bun', sw='hair', scale=(1.045, 1.055, 1.04), pin='pin',
                  line=[(0, 40), (8, 33), (25, 30), (50, 16), (72, -4), (95, -16), (135, -36), (180, -44)]),
        face=dict(eye=0.94, eye_az=21, eye_el=-5, brow=dict(inner=1.8, outer=-1.0, arch=1.6, r=0.95),
                  mouth=dict(w=8.0, smile=3.5, el=-28), nose=0.98, blush=0.55, lashes=True, smile_lines=True),
        outfit=dict(
            top=dict(sw='baju', hem=('knee', 0.02), ease=0.017, flare=1.36,
                     sleeve=1.0, sleeve_ease=0.007, sleeve_flare=1.14, collar='round_trim', trim='trim'),
            lower=dict(type='skirt', sw='batik', hem=('ankle', 0.03), top='waist', ease=0.009, flare=1.14),
            feet=dict(type='sandals', sw='sandal'),
        ),
        props=[dict(type='shawl', sw='selendang')],
        headwear=None,
    ),
    # ---------------------------------------------------------------- Auntie Letchumi, ~65
    # Saree approximated with the builder's parts: short-sleeved blouse, bordered skirt (the pleated
    # lower drape) and a bordered shawl for the pallu.
    'letchumi': dict(
        name='Letchumi', file='npc-letchumi', age=66,
        body=body(height=1.50, head_frac=0.29, head_aspect=(0.96, 0.93), leg_frac=0.43,
                  torso_w=0.245, torso_depth=0.82, hip_ratio=1.08, belly=0.05, neck_r=0.038,
                  arm_r=0.033, leg_r=0.042, hand_r=0.040, foot_len=0.13, arm_len=1.0, arm_spread=12),
        energy=0.7, walk_period=1.15, run_period=0.80, posture=dict(spine=7, chest=6, head=-8),
        idle_arms='clasp',
        palette={
            'skin': '#6a4129', 'skin_shade': '#593622',
            'face': dict(kind='face', skin='#6a4129', blush='#77402f'),
            'hair': dict(kind='strands', base='#a9a49c'), 'brow': '#5a5550',
            'blouse': dict(kind='twill', base='#7a2e3a', amt=0.03),
            'saree': dict(kind='border', base='#c9763a', band='#6b1f2a', line='#d9b24a'),
            'pallu': dict(kind='border', base='#c9763a', band='#6b1f2a'),
            'trim': '#d9b24a', 'sandal': '#4a3223', 'pin': '#d9b24a', 'gold': '#d9b24a',
        },
        hair=dict(style='bun', sw='hair', scale=(1.04, 1.05, 1.04), pin='pin',
                  line=[(0, 42), (25, 36), (55, 20), (80, 10), (100, 0), (140, -30), (180, -42)]),
        face=dict(eye=0.86, eye_az=21, eye_el=-5, brow=dict(inner=1.5, outer=-1.5, arch=1.2, r=0.95, sw='brow'),
                  mouth=dict(w=8.0, smile=4.0, el=-28), nose=1.05, blush=0.4, smile_lines=True),
        outfit=dict(
            top=dict(sw='blouse', hem='waist', ease=0.012, flare=1.02, sleeve=0.40, sleeve_ease=0.006,
                     sleeve_flare=1.06, collar='round_trim', trim='trim'),
            lower=dict(type='skirt', sw='saree', hem=('ankle', 0.035), top='waist', ease=0.009, flare=1.16),
            feet=dict(type='sandals', sw='sandal'),
        ),
        props=[dict(type='shawl', sw='pallu'), dict(type='bangle', side='L', sw='gold'),
               dict(type='bangle', side='R', sw='gold')],
        headwear=None,
    ),
}

B.CHARACTERS.clear()
B.CHARACTERS.update(CAST_1965)

if __name__ == '__main__':
    B.main()
