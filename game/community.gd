extends Node3D
## An imagined neighbourhood gathering, not a reconstruction of eyewitness reactions.
const BENCH_LAYOUT = [
	{"at": Vector3(-2.8, 0, -3.3), "facing": 2.15},
	{"at": Vector3(2.8, 0, -3.3), "facing": -2.15},
	{"at": Vector3(-2.8, 0, 0), "facing": 2.55},
	{"at": Vector3(2.8, 0, 0), "facing": -2.55},
]
var builder: Node3D
var residents: Array[Dictionary] = []
var playback_time := 0.0
var broadcasting := false
var reaction_paused := false
var fan: Node3D
var glow: OmniLight3D
var time := 0.0
var attention := 0.0
var conversing := false

func build(world: Node3D) -> void:
	builder = world
	var cream := Color("e5dcc3")
	var green := Color("789387")
	# The open ground floor belongs to the flats above it.
	builder.box(self, Vector3(0, 0.035, -2.8), Vector3(12.4, 0.07, 10.4), Color("c5c4af"))
	for x in range(-6, 7):
		builder.box(self, Vector3(x, 0.075, -2.8), Vector3(0.018, 0.01, 10.4), Color("a8b0a0"))
	for z in range(-8, 3):
		builder.box(self, Vector3(0, 0.075, z), Vector3(12.4, 0.01, 0.018), Color("a8b0a0"))
	for x in [-6.0, 6.0]:
		for z in [-7.6, -2.8, 2.0]:
			builder.box(self, Vector3(x, 2.2, z), Vector3(0.32, 4.4, 0.32), cream, true)
			builder.box(self, Vector3(x, 0.55, z), Vector3(0.35, 1.1, 0.35), green)
	builder.box(self, Vector3(0, 4.45, -2.8), Vector3(13, 0.18, 11), Color("999f92"), true)
	for z in [-7.7, 2.1]:
		builder.box(self, Vector3(0, 4.17, z), Vector3(12.5, 0.43, 0.25), cream)
	for x in [-5.9, 5.9]:
		builder.box(self, Vector3(x, 4.2, -2.8), Vector3(0.24, 0.4, 10), cream)
	build_residential_floors(cream, green)
	for x in [-3.4, 3.4]:
		var tube: MeshInstance3D = builder.cylinder(self, Vector3(x, 4.03, -3), 0.045, 1.4, Color("ffebbd"))
		tube.rotation.z = PI / 2
		var light := OmniLight3D.new()
		light.position = Vector3(x, 3.7, -3)
		light.light_color = Color("fff0d3")
		light.light_energy = 0.75
		light.omni_range = 7
		add_child(light)
	fan = Node3D.new()
	fan.position = Vector3(0, 4.05, -1.3)
	add_child(fan)
	builder.cylinder(fan, Vector3.ZERO, 0.15, 0.18, Color("5c716a"))
	for i in range(3):
		var blade: MeshInstance3D = builder.box(fan, Vector3.ZERO, Vector3(1.9, 0.035, 0.14), Color("70827a"))
		blade.rotation.y = i * TAU / 3
	for bench in BENCH_LAYOUT:
		wooden_bench(bench.at, bench.facing)
	# The reacting pair share the foreground-left bench, clear of Sparky and the TV.
	resident(seat_transform(2, -0.6), Color("80799c"), Color("c19773"), "wipe", true)
	resident(seat_transform(2, 0.6), Color("a57b58"), Color("ba8c67"), "comfort", true)
	resident(seat_transform(0, 0.8), Color("e2d4b4"), Color("8f6248"), "bow", false)
	resident(seat_transform(1, 0.7), Color("467b79"), Color("b88864"), "still", false)
	resident(seat_transform(3, -0.7), Color("879779"), Color("d0a483"), "still", false)
	resident(seat_transform(1, -0.7), Color("b86750"), Color("bf926f"), "arrival", false)
	residents[-1].root.visible = false
	# A child close to an adult gives the group a family scale.
	resident(seat_transform(3, 0.7, 0.15), Color("d4aa61"), Color("c99d7a"), "child", false)
	residents[-1].root.scale = Vector3.ONE * 0.72
	# Everyday shared objects: enamel cups, a thermos, a folded paper and a basket.
	builder.box(self, Vector3(4.9, 0.7, -4.5), Vector3(1.05, 0.12, 0.7), Color("927049"), true)
	for x in [4.5, 5.3]:
		builder.box(self, Vector3(x, 0.35, -4.5), Vector3(0.08, 0.7, 0.5), Color("4b5b51"))
	for x in [4.6, 4.95]:
		builder.cylinder(self, Vector3(x, 0.86, -4.35), 0.09, 0.2, cream)
		builder.cylinder(self, Vector3(x, 0.965, -4.35), 0.084, 0.008, Color("543e2a"))
	builder.cylinder(self, Vector3(5.15, 1.04, -4.65), 0.13, 0.58, Color("b75945"))
	builder.box(self, Vector3(-4.65, 0.25, -2.7), Vector3(0.6, 0.5, 0.4), Color("ad885c"))
	for i in range(5):
		builder.box(self, Vector3(-4.65, 0.05 + i * 0.1, -2.485), Vector3(0.6, 0.025, 0.02), Color("765b3f"))
	var paper_root := Node3D.new()
	paper_root.transform = seat_transform(2, 0.0)
	add_child(paper_root)
	builder.box(paper_root, Vector3(0, 0.635, 0), Vector3(0.55, 0.015, 0.38), cream)
	for i in range(4):
		builder.box(paper_root, Vector3(0, 0.645, -0.12 + i * 0.08), Vector3(0.4, 0.003, 0.02), Color("7c8178"))
	glow = OmniLight3D.new()
	glow.position = Vector3(0, 1.95, -4.7)
	glow.light_color = Color("bfdde7")
	glow.light_energy = 0
	glow.omni_range = 4.5
	add_child(glow)
	builder.bake_static(self, [fan] + residents.map(func(resident_data): return resident_data.root))

func seat_transform(bench_index: int, offset: float, height := 0.0) -> Transform3D:
	var bench: Dictionary = BENCH_LAYOUT[bench_index]
	var facing := Basis(Vector3.UP, bench.facing)
	return Transform3D(facing, bench.at + facing * Vector3(offset, height, 0))

func build_residential_floors(cream: Color, green: Color) -> void:
	# A fictional early slab block: three levels of flats and common corridors.
	# All upper geometry starts above the ground-floor slab, within its footprint.
	var plaster := Color("ddd9c7")
	var shadow := Color("4c6260")
	builder.box(self, Vector3(0, 2.2, -7.85), Vector3(12.4, 4.4, 0.24), plaster, true)
	# Rear service door and a small residents' noticeboard, behind the TV.
	builder.box(self, Vector3(-4.9, 1.15, -7.71), Vector3(1.05, 2.25, 0.05), green.darkened(0.25))
	builder.ball(self, Vector3(-4.55, 1.05, -7.66), 0.04, Color("c9bc91"))
	builder.box(self, Vector3(-2.8, 1.65, -7.69), Vector3(1.6, 0.95, 0.09), Color("8e7859"))
	for x in [-3.25, -2.8, -2.35]:
		builder.box(self, Vector3(x, 1.65, -7.63), Vector3(0.33, 0.61, 0.015), cream)
	for floor_index in range(3):
		var floor_y := 4.55 + floor_index * 2.9
		builder.box(self, Vector3(0, floor_y + 1.4, -3.7), Vector3(12.4, 2.8, 8.0), plaster, true)
		builder.box(self, Vector3(0, floor_y + 2.85, -2.8), Vector3(13, 0.18, 11), cream)
		# Front access corridor, parapet and evenly aligned supports.
		builder.box(self, Vector3(0, floor_y + 0.5, 2.32), Vector3(12.4, 0.85, 0.14), green)
		builder.box(self, Vector3(0, floor_y + 0.96, 2.32), Vector3(12.55, 0.08, 0.2), cream)
		for x in [-6.0, -2.0, 2.0, 6.0]:
			builder.box(self, Vector3(x, floor_y + 1.4, 2.0), Vector3(0.22, 2.8, 0.22), cream)
		for x in [-4.15, 0.0, 4.15]:
			builder.box(self, Vector3(x - 0.95, floor_y + 1.05, 0.325), Vector3(0.86, 2.1, 0.05), green.darkened(0.15))
			builder.box(self, Vector3(x + 0.55, floor_y + 1.5, 0.34), Vector3(1.55, 1.1, 0.07), cream)
			builder.box(self, Vector3(x + 0.55, floor_y + 1.5, 0.39), Vector3(1.35, 0.9, 0.055), shadow)
			for bar_x in [-0.42, 0.0, 0.42]:
				builder.box(self, Vector3(x + 0.55 + bar_x, floor_y + 1.5, 0.43), Vector3(0.045, 0.9, 0.04), cream)
		# Windows on both end walls keep the building legible from the street.
		for side in [-1.0, 1.0]:
			for z in [-5.6, -2.4]:
				builder.box(self, Vector3(side * 6.225, floor_y + 1.45, z), Vector3(0.06, 1.15, 1.55), cream)
				builder.box(self, Vector3(side * 6.265, floor_y + 1.45, z), Vector3(0.04, 0.97, 1.35), shadow)
	# Enclosed stairwell joins the east end; its entrance faces the street.
	builder.box(self, Vector3(7.6, 6.55, -2.8), Vector3(2.35, 13.1, 10.3), plaster, true)
	builder.box(self, Vector3(7.6, 13.15, -2.8), Vector3(2.65, 0.2, 10.6), cream)
	builder.box(self, Vector3(7.6, 1.2, 2.37), Vector3(1.45, 2.4, 0.07), shadow)
	for y in [3.6, 6.15, 9.05, 11.95]:
		for x in [7.1, 7.6, 8.1]:
			builder.box(self, Vector3(x, y, 2.39), Vector3(0.3, 0.65, 0.08), green.darkened(0.1))
	builder.box(self, Vector3(7.6, 2.8, 2.405), Vector3(0.85, 0.48, 0.06), green.darkened(0.25))
	builder.sign_text(self, Vector3(7.6, 2.8, 2.445), "12", 44, cream)

func wooden_bench(at: Vector3, facing := PI) -> void:
	var root := Node3D.new()
	root.position = at
	root.rotation.y = facing
	add_child(root)
	for z in [-0.22, 0.0, 0.22]:
		builder.box(root, Vector3(0, 0.58, z), Vector3(3.25, 0.09, 0.18), Color("92734d"), true)
	for y in [0.87, 1.08]:
		builder.box(root, Vector3(0, y, -0.31), Vector3(3.25, 0.16, 0.07), Color("a08056"))
	for x in [-1.35, 1.35]:
		builder.box(root, Vector3(x, 0.3, 0), Vector3(0.14, 0.6, 0.6), Color("4f6258"))
		builder.box(root, Vector3(x, 0.82, -0.31), Vector3(0.09, 0.7, 0.09), Color("4f6258"))

func limb(parent: Node3D, from: Vector3, to: Vector3, radius: float, color: Color) -> MeshInstance3D:
	var mesh: MeshInstance3D = builder.cylinder(parent, Vector3.ZERO, radius, 1.0, color)
	pose_limb(mesh, from, to)
	return mesh

func pose_limb(mesh: MeshInstance3D, from: Vector3, to: Vector3) -> void:
	var offset := to - from
	mesh.position = (from + to) * 0.5
	mesh.scale.y = offset.length()
	mesh.quaternion = Quaternion(Vector3.UP, offset.normalized())

func resident(seat: Transform3D, shirt: Color, skin: Color, reaction: String, elderly: bool) -> void:
	var root := Node3D.new()
	root.transform = seat
	add_child(root)
	builder.cylinder(root, Vector3(0, 0.98, 0), 0.25, 0.7, shirt, 0.21)
	builder.cylinder(root, Vector3(0, 1.35, 0), 0.09, 0.13, skin)
	# A flat neckline seam replaces the protruding collar pieces beneath the chin.
	builder.box(root, Vector3(0, 1.265, 0.18), Vector3(0.14, 0.025, 0.018), shirt.darkened(0.12))
	for y in [0.91, 1.06, 1.19]:
		builder.ball(root, Vector3(0, y, 0.25), 0.019, Color("ede1c9"))
	var head := Node3D.new()
	head.position = Vector3(0, 1.5, 0.02)
	root.add_child(head)
	builder.ball(head, Vector3.ZERO, 0.25, skin)
	var hair: MeshInstance3D = builder.ball(head, Vector3(0, 0.12, -0.045), 0.256, Color("a7a89c") if elderly else Color("393631"))
	hair.scale = Vector3(1, 0.6, 1)
	if reaction == "wipe":
		builder.ball(head, Vector3(0, 0.12, -0.27), 0.12, Color("a7a89c"))
	for side in [-1, 1]:
		builder.ball(head, Vector3(side * 0.085, 0.02, 0.23), 0.026, Color("39372f"))
		var brow: MeshInstance3D = builder.box(head, Vector3(side * 0.085, 0.076, 0.231), Vector3(0.078, 0.019, 0.012), Color("635748"))
		brow.rotation.z = side * 0.13
		builder.ball(head, Vector3(side * 0.247, 0, 0), 0.053, skin)
	builder.ball(head, Vector3(0, -0.02, 0.257), 0.043, skin.lightened(0.03))
	builder.box(head, Vector3(0, -0.105, 0.218), Vector3(0.075, 0.015, 0.012), Color("805e4c"))
	var arms: Array[Dictionary] = []
	for side in [-1, 1]:
		var shoulder := Vector3(side * 0.24, 1.23, 0)
		var elbow := Vector3(side * 0.35, 0.9, 0.15)
		var hand := Vector3(side * 0.21, 0.72, 0.38)
		arms.append({"upper": limb(root, shoulder, elbow, 0.087, shirt), "lower": limb(root, elbow, hand, 0.063, skin), "hand": builder.ball(root, hand, 0.085, skin), "side": side})
		var hip := Vector3(side * 0.13, 0.64, 0.02)
		var knee := Vector3(side * 0.15, 0.57, 0.43)
		limb(root, hip, knee, 0.11, Color("414f50"))
		limb(root, knee, Vector3(side * 0.15, 0.12, 0.48), 0.09, Color("414f50"))
		builder.box(root, Vector3(side * 0.15, 0.09, 0.56), Vector3(0.18, 0.12, 0.3), Color("493e34"))
	var hanky: MeshInstance3D = builder.box(root, Vector3(-0.21, 0.77, 0.43), Vector3(0.25, 0.27, 0.035), Color("fffaf0"))
	hanky.visible = reaction == "wipe"
	var tear: MeshInstance3D = builder.ball(head, Vector3(-0.097, -0.025, 0.242), 0.035, Color("c1dbe0"))
	tear.scale = Vector3(0.5, 1.6, 0.45)
	tear.visible = false
	residents.append({"root": root, "head": head, "arms": arms, "reaction": reaction, "hanky": hanky, "tear": tear})

func set_broadcast(active: bool) -> void:
	broadcasting = active
	reaction_paused = false
	playback_time = 0
	attention = 0
	conversing = false
	glow.light_energy = 0.65 if active else 0
	for resident_data in residents:
		resident_data["starting_gaze"] = resident_data.head.rotation.y
		if resident_data.reaction == "arrival":
			resident_data.root.visible = active
	update_reactions()

func update_reactions() -> void:
	# A visible lift, two small dabs, then a return towards the lap.
	# Drive every gesture from the footage clock so pause freezes the reactions too.
	var emotion := smoothstep(2.0, 5.0, playback_time) if broadcasting else 0.0
	# Three brief wipes across the two-minute excerpt, with long quiet rests.
	var cycle := -1.0
	for wipe_at in [7.0, 46.0, 91.0]:
		if playback_time >= wipe_at and playback_time < wipe_at + 5.5:
			cycle = playback_time - wipe_at
	var lift := 0.0
	if cycle >= 0.0:
		lift = smoothstep(0.0, 1.2, cycle) * (1.0 - smoothstep(3.8, 5.5, cycle))
	var dab := emotion * lift
	for resident_data in residents:
		var head: Node3D = resident_data.head
		head.rotation = Vector3(0, resident_data.get("starting_gaze", 0.0) * (1.0 - attention), 0)
		if resident_data.reaction == "wipe":
			head.rotation.x = emotion * (0.22 + 0.035 * sin(playback_time * 2.2))
			head.rotation.z = -emotion * 0.16
			resident_data.tear.visible = emotion > 0.55
		elif resident_data.reaction == "comfort":
			head.rotation.y += -emotion * 0.65
			head.rotation.z = -emotion * 0.12
		elif resident_data.reaction == "bow":
			head.rotation.x = emotion * 0.22
		elif resident_data.reaction == "child":
			head.rotation.z = emotion * 0.16
		elif resident_data.reaction == "arrival" and conversing:
			head.rotation.y = 0.7
		for arm in resident_data.arms:
			var side: int = arm.side
			var shoulder := Vector3(side * 0.24, 1.23, 0)
			var elbow := Vector3(side * 0.35, 0.9, 0.15)
			var hand := Vector3(side * 0.21, 0.72, 0.38)
			if resident_data.reaction == "wipe" and side == -1:
				elbow = elbow.lerp(Vector3(-0.48, 1.15, 0.28), dab)
				var eye: Vector3 = resident_data.root.to_local(head.to_global(Vector3(-0.1, 0.0, 0.3)))
				var tap := 0.022 * sin(cycle * TAU / 1.2)
				hand = hand.lerp(eye + Vector3(0, -0.06 + tap, 0.035), dab)
				resident_data.hanky.position = hand + Vector3(0, 0.06, -0.025)
				resident_data.hanky.rotation.z = -0.18 * dab
			elif resident_data.reaction == "comfort" and side == -1:
				# Reach the actual neighbour's shoulder, rather than waving behind the bench.
				var neighbour: Node3D = residents[0].root
				var contact: Vector3 = resident_data.root.to_local(neighbour.to_global(Vector3(0.25, 1.24, -0.035)))
				var pat := 0.075 * lift * pow(maxf(sin(playback_time * 2.6), 0.0), 2.0)
				contact.y += pat
				elbow = elbow.lerp((shoulder + contact) * 0.5 + Vector3(0, 0.14, -0.13), emotion)
				hand = hand.lerp(contact, emotion)
			pose_limb(arm.upper, shoulder, elbow)
			pose_limb(arm.lower, elbow, hand)
			arm.hand.position = hand

func _process(delta: float) -> void:
	time += delta
	if is_instance_valid(fan):
		fan.rotation.y += delta * 1.1
	if broadcasting and not reaction_paused:
		attention = minf(1.0, attention + delta * 0.55)
		update_reactions()
	elif not broadcasting:
		for i in residents.size():
			residents[i].head.rotation.y = sin(time * 0.5 + i * 1.8) * 0.24
