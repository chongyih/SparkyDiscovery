extends "res://game/world.gd"
## An imagined civilian street, not a reconstruction of a named raid or shelter.
var tan: Node3D
var mei: Node3D
var pail: Node3D
var door: MeshInstance3D
var shutter: MeshInstance3D
var dust: CPUParticles3D
var flash: OmniLight3D
var keys: Node3D
var cup: Node3D
var animations_paused := false
var shelter_closed := false
var pouring := false
var pour_clock := 0.0
var jug: Node3D
var water_stream: MeshInstance3D
var lantern: OmniLight3D
var evacuees: Array[Node3D] = []
var shop_gate: Node3D
var shutters_closing := false
const WATER_SPOT := Vector3(-2.15, 0.785, -9.4)
const SEAT_SPOTS := [Vector3(-3.7, -0.07, -6.6), Vector3(3.7, -0.07, -7.2)]
var resident_routes: Array = []
var route_steps: Array[int] = []
var resident_bags: Array[Node3D] = []
var relief_active := false
var water_delivered := false
var relief_clock := 0.0
var comfort_target := Vector3(-0.6, 1.15, -8.5)

func build(_chapter: Dictionary) -> void:
	box(self, Vector3(0, -0.2, 1), Vector3(30, 0.4, 32), Color("8b8070"), true)
	box(self, Vector3(0, 0.015, 5), Vector3(25, 0.03, 7), Color("66645f"))
	for x in [-14.0, 14.0]:
		box(self, Vector3(x, 2, 0), Vector3(0.4, 4, 30), Color("6a6254"), true)
	for z in [-14.0, 15.0]:
		box(self, Vector3(0, 2, z), Vector3(28, 4, 0.4), Color("6a6254"), true)
	# Low shophouses: timber shutters, tiled roofs, no postwar housing block or TV.
	for x in [-10.0, -5.0, 0.0, 5.0, 10.0]:
		box(self, Vector3(x, 3.2, 12), Vector3(4.8, 6.4, 5), Color("b6a489").darkened(absf(x) * 0.018), true)
		box(self, Vector3(x, 6.5, 12), Vector3(5, 0.25, 5.4), BRICK.darkened(0.25))
		box(self, Vector3(x, 2.8, 9.2), Vector3(4.8, 0.2, 1.4), Color("66594a"), true)
		for offset in [-1.0, 1.0]:
			box(self, Vector3(x + offset, 4.6, 9.45), Vector3(1.3, 1.6, 0.13), TEAL.darkened(0.2))
			for angle in [-0.65, 0.65]:
				var tape := box(self, Vector3(x + offset, 4.6, 9.35), Vector3(0.055, 1.75, 0.035), CREAM)
				tape.rotation.z = angle
		for y in [0.35, 0.9, 1.5, 2.1]:
			box(self, Vector3(x, y, 9.28), Vector3(4.4, 0.035, 0.08), Color("423e34"))
		for offset in range(-2, 3):
			box(self, Vector3(x + offset * 0.85, 1.3, 9.4), Vector3(0.8, 2.5, 0.12), Color("716650"))
		box(self, Vector3(x, 3.35, 9.32), Vector3(4.4, 0.6, 0.1), Color("493f34"))
		var sign := sign_text(self, Vector3(x, 3.35, 9.24), "TAN • PROVISIONS" if x == 0 else "PROVISIONS", 27)
		sign.rotation.y = PI
	# Shelter: walk through a broad doorway; side walls and roof give a real enclosed ending.
	box(self, Vector3(0, 1.8, -11), Vector3(10, 3.6, 0.3), Color("766f5e"), true)
	for x in [-5.0, 5.0]:
		box(self, Vector3(x, 1.8, -7), Vector3(0.3, 3.6, 8), Color("766f5e"), true)
		box(self, Vector3(x * 0.7, 1.8, -3), Vector3(3, 3.6, 0.3), Color("766f5e"), true)
	box(self, Vector3(0, 3.7, -7), Vector3(10.3, 0.2, 8.4), Color("5f584c"), true)
	door = box(self, Vector3(1.8, 1.4, -3), Vector3(0.16, 2.8, 2.7), Color("514b3d"))
	sign_text(self, Vector3(0, 3.05, -2.8), "SHELTER", 38)
	for side in [-1.0, 1.0]:
		for row in range(3):
			for col in range(3):
				var sack := ball(self, Vector3(side * (2.7 + col * 0.65), 0.23 + row * 0.36, -2.3), 0.4, Color("a99a73"))
				sack.scale = Vector3(1.15, 0.6, 0.8)
		bench(Vector3(side * 3.85, 0, -6.9), -side * PI / 2)
	for x in [-3.0, 0.0, 3.0]:
		box(self, Vector3(x, 0.08, -10), Vector3(1.5, 0.16, 1), Color("9a907b"))
	var lamp := OmniLight3D.new()
	lantern = lamp
	lamp.position = Vector3(0, 2.6, -7)
	lamp.light_color = Color("ffd59b")
	lamp.light_energy = 1.5
	lamp.omni_range = 8
	add_child(lamp)
	shelter_lamp(Vector3(0, 2.7, -7), 3.4)
	# Courtyard water and a handcart of possessions.
	cylinder(self, Vector3(9, 0.65, 1), 0.7, 1.3, Color("776552"))
	box(self, Vector3(-8, 0.7, 4), Vector3(2.6, 0.25, 1.6), Color("69523d"), true)
	for x in [-8.9, -7.1]:
		var wheel := cylinder(self, Vector3(x, 0.4, 4), 0.4, 0.13, INK)
		wheel.rotation.z = PI / 2
	for x in [-8.7, -7.8]:
		box(self, Vector3(x, 1.15, 4), Vector3(0.7, 0.6, 1), Color("a59b85"))
	tan = actor(Vector3(0, 0, 7.5), BRICK.darkened(0.2), "Uncle Tan")
	tan.rotation.y = PI
	mei = actor(Vector3(-1.8, 0, -1.7), Color("627c79"), "Mei")
	mei.pose = "beckon"
	pail = make_pail(self)
	pail.scale = Vector3.ONE * 0.65
	pail.position = Vector3(7.3, 0, 1)
	keys = Node3D.new()
	add_child(keys)
	keys.position = Vector3(6, 0.04, 2)
	key_ring(keys, Vector3.ZERO, 0.085, Color("9b9d94"))
	for i in 2:
		var key := Node3D.new()
		keys.add_child(key)
		key.position = Vector3(-0.055 if i == 0 else 0.055, 0.004 * i, 0.08)
		key.rotation.y = -0.45 if i == 0 else 0.65
		var brass := Color("ae9565")
		key_ring(key, Vector3.ZERO, 0.06, brass)
		box(key, Vector3(0, 0, 0.17), Vector3(0.027, 0.025, 0.23), brass)
		for tooth in [0.22, 0.28]:
			box(key, Vector3(0.026, 0, tooth), Vector3(0.065, 0.025, 0.027), brass)
	keys.visible = false
	cup = cylinder(self, Vector3.ZERO, 0.08, 0.14, CREAM)
	cup.visible = false
	shutter = box(self, Vector3(8, 1.6, 9.15), Vector3(0.9, 2.6, 0.12), Color("76654d"))
	dust = CPUParticles3D.new()
	dust.emitting = false
	dust.visible = false
	dust.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	dust.position = Vector3(7, 1.6, 5)
	dust.amount = 36
	dust.lifetime = 8
	dust.one_shot = true
	dust.explosiveness = 0.85
	dust.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	dust.emission_box_extents = Vector3(5, 1, 1)
	dust.direction = Vector3(-0.5, 0.4, -1)
	dust.spread = 65
	dust.initial_velocity_min = 0.6
	dust.initial_velocity_max = 1.8
	dust.gravity = Vector3(0, -0.06, 0)
	dust.scale_amount_min = 0.3
	dust.scale_amount_max = 1.1
	var mote := QuadMesh.new()
	mote.size = Vector2(3, 3)
	dust.mesh = mote
	var gradient := Gradient.new()
	# Set every stop together: inserting stops changes numeric indices and can
	# otherwise leave Gradient's default opaque-white endpoint in place.
	gradient.offsets = PackedFloat32Array([0.0, 0.35, 0.7, 1.0])
	gradient.colors = PackedColorArray([
		Color(0.5, 0.44, 0.35, 0.18),
		Color(0.5, 0.44, 0.35, 0.08),
		Color(0.5, 0.44, 0.35, 0.015),
		Color(0.5, 0.44, 0.35, 0.0),
	])
	var texture := GradientTexture2D.new()
	texture.gradient = gradient
	texture.fill = GradientTexture2D.FILL_RADIAL
	texture.fill_from = Vector2(0.5, 0.5)
	texture.fill_to = Vector2(1, 0.5)
	var dust_mat := StandardMaterial3D.new()
	dust_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	dust_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	dust_mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	dust_mat.albedo_texture = texture
	dust.material_override = dust_mat
	add_child(dust)
	dust.emitting = false
	flash = OmniLight3D.new()
	flash.position = Vector3(8, 5, 8)
	flash.omni_range = 22
	flash.light_color = Color("ffd5a0")
	flash.light_energy = 0
	add_child(flash)
	for task in _chapter.tasks:
		var marker := Node3D.new()
		marker.position = task.at
		add_child(marker)
		var gem := box(marker, Vector3(0, 2.8, 0), Vector3(0.22, 0.22, 0.22), GOLD)
		gem.rotation.z = PI / 4
		markers.append(marker)
		var label := sign_text(marker, Vector3(0, 2.25, 0), task.label, 28)
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.outline_size = 5
		labels.append(label)
	add_details()
	bake_static(self, [tan, mei, pail, keys, cup, shutter, door, jug, water_stream, shop_gate] + markers + evacuees)

func actor(at: Vector3, shirt: Color, title: String) -> Node3D:
	var actor_root := preload("res://game/ww2_actor.gd").new()
	actor_root.name = title
	actor_root.position = at
	add_child(actor_root)
	actor_root.build(self, title == "Mei", shirt)
	return actor_root

func make_pail(parent: Node3D) -> Node3D:
	var prop := Node3D.new()
	parent.add_child(prop)
	cylinder(prop, Vector3(0, 0.23, 0), 0.22, 0.43, Color("77817c"), 0.28)
	cylinder(prop, Vector3(0, 0.45, 0), 0.24, 0.012, Color("719399"))
	for x in [-0.27, 0.27]:
		box(prop, Vector3(x, 0.62, 0), Vector3(0.025, 0.36, 0.025), INK)
	box(prop, Vector3(0, 0.8, 0), Vector3(0.55, 0.035, 0.035), INK)
	return prop

func aftermath() -> void:
	shutter.rotation.z = 0.32
	keys.visible = true

func close_shelter() -> void:
	shelter_closed = true
	door.position = Vector3(0, 1.4, -3)
	door.rotation.y = PI / 2
	tan.position = Vector3(0.65, 0, -7.85)
	tan.rotation = Vector3(0, -1.6, 0)
	mei.position = Vector3(-3.15, 0, -8.35)
	mei.rotation.y = 0
	tan.pose = "listen"
	mei.pose = "listen"
	keys.visible = false
	jug.visible = true
	jug.position = Vector3(-3.05, 0.89, -9.2)
	cup.visible = true
	cup.position = Vector3(-2.85, 0.855, -9.2)
	# A fast player can arrive before the background walk finishes; the interior cut
	# settles those neighbours directly into the same final seats.
	settle_residents()

func settle_residents() -> void:
	for i in evacuees.size():
		route_steps[i] = resident_routes[i].size()
		seat_resident(i)

func seat_resident(i: int) -> void:
	var resident: Node3D = evacuees[i]
	resident.position = SEAT_SPOTS[i]
	resident.rotation.y = PI / 2 if i == 0 else -PI / 2
	resident.seated = true
	resident.last_position = resident.position
	resident.tick(1.0 / 60.0)
	if resident_bags[i].get_parent() != self: resident_bags[i].reparent(self)
	resident_bags[i].position = Vector3(resident.position.x, 0.43, resident.position.z + 0.8)
	resident_bags[i].rotation = Vector3.ZERO

func update_residents(delta: float) -> void:
	for i in evacuees.size():
		var resident: Node3D = evacuees[i]
		var route: Array = resident_routes[i]
		if route_steps[i] < route.size():
			var target: Vector3 = route[route_steps[i]]
			var direction := target - resident.position
			if direction.length() <= 0.08:
				resident.position = target
				route_steps[i] += 1
				if route_steps[i] == route.size(): seat_resident(i)
			else:
				resident.rotation.y = lerp_angle(resident.rotation.y, atan2(direction.x, direction.z), minf(1, delta * 8))
				resident.position = resident.position.move_toward(target, delta * 0.9)
		resident.tick(delta)

func _process(delta: float) -> void:
	if animations_paused: return
	super._process(delta)
	if not is_instance_valid(tan): return
	tan.tick(delta)
	mei.tick(delta)
	update_residents(delta)
	if relief_active:
		update_relief(delta)
	elif water_delivered:
		comfort_sparky(7.6)
		cup.global_position = evacuees[0].hands[1].global_position + Vector3(0, 0.05, 0.03)
	if shutters_closing:
		shop_gate.rotation.y = move_toward(shop_gate.rotation.y, 0, delta * 0.75)

func begin_pour() -> void:
	relief_active = true
	relief_clock = 0
	pouring = true
	mei.pose = "pour"
	mei.position = Vector3(-3.15, 0, -8.35)
	mei.rotation.y = 0

func update_relief(delta: float) -> void:
	relief_clock += delta
	var t := relief_clock
	if t < 2.4:
		jug.global_position = mei.hands[0].global_position + Vector3(0, 0.1, 0.03)
		cup.global_position = mei.hands[1].global_position + Vector3(0, 0.05, 0.05)
		var tilt := sin(clampf(t / 2.4, 0, 1) * PI)
		jug.rotation.z = -tilt * 0.75
		water_stream.visible = tilt > 0.45
		var from := jug.global_position + Vector3(0.12, 0.07, 0)
		var to := cup.global_position + Vector3(0, 0.09, 0)
		water_stream.global_position = (from + to) * 0.5
		water_stream.scale.y = from.distance_to(to)
		water_stream.quaternion = Quaternion(Vector3.UP, (from - to).normalized())
	else:
		pouring = false
		water_stream.visible = false
		jug.position = Vector3(-3.05, 0.89, -9.2)
		jug.rotation = Vector3.ZERO
		mei.pose = "carry_cup" if t < 4.8 else "listen"
		mei.position = Vector3(-3.15, 0, -8.35).lerp(Vector3(-2.85, 0, -6.6), smoothstep(2.4, 4.0, t))
		mei.rotation.y = atan2(-3.7 - mei.position.x, -6.6 - mei.position.z)
		if t >= 3.8 and t < 5.3:
			var receiver = evacuees[0]
			var meeting: Vector3 = (mei.arms[1].global_position + receiver.arms[1].global_position) * 0.5 + Vector3(0, -0.18, 0)
			var reach_weight := smoothstep(3.8, 4.5, t) * (1.0 - smoothstep(4.9, 5.3, t))
			mei.reach_hand(1, meeting, reach_weight)
			receiver.reach_hand(1, meeting, reach_weight)
		if t < 4.8:
			var offered: Vector3 = mei.hands[1].global_position + Vector3(0, 0.05, 0.03)
			cup.global_position = offered
		else:
			water_delivered = true
			evacuees[0].seat_activity = "drink"
			cup.global_position = evacuees[0].hands[1].global_position + Vector3(0, 0.05, 0.03)
	comfort_sparky(t)

func comfort_sparky(t: float) -> void:
	tan.position = Vector3(0.65, 0, -7.85).lerp(Vector3(-0.25, 0, -8.1), smoothstep(0.0, 2.0, t))
	tan.rotation.y = atan2(-1.05 - tan.position.x, -8.55 - tan.position.z)
	tan.pose = "listen"
	tan.reach_hand(0, comfort_target, smoothstep(1.8, 3.0, t))

func finish_relief() -> void:
	update_relief(maxf(0, 7.6 - relief_clock))
	relief_active = false
	pouring = false
	water_stream.visible = false

func add_details() -> void:
	# Shop fittings and possessions tell the story without extending the task list.
	for x in [-10.0, -5.0, 0.0, 5.0, 10.0]:
		for y in [3.85, 5.5]:
			box(self, Vector3(x, y, 9.31), Vector3(4.7, 0.09, 0.18), CREAM.darkened(0.25))
		for offset in [-2.25, 2.25]:
			box(self, Vector3(x + offset, 1.3, 8.65), Vector3(0.16, 2.6, 0.16), Color("79654f"), true)
		for tile in range(12):
			box(self, Vector3(x - 2.3 + tile * 0.42, 6.64, 12), Vector3(0.045, 0.04, 5.3), Color("7e513d"))
	for z in [-1.0, 0.0, 1.0, 2.0]:
		box(self, Vector3(10, 0.025, z), Vector3(6, 0.01, 0.025), Color("756e60"))
	for x in [7.0, 8.0, 9.0, 10.0, 11.0, 12.0]:
		box(self, Vector3(x, 0.025, 0.5), Vector3(0.025, 0.01, 4), Color("756e60"))
	for z in [0.18, 0.67, 1.15]:
		cylinder(self, Vector3(9, z, 1), 0.714, 0.04, Color("4f5148"))
	for x in [-8.8, -7.5]:
		var roll := cylinder(self, Vector3(x, 1.57, 4), 0.2, 1.15, Color("7c8071"))
		roll.rotation.z = PI / 2
		box(self, Vector3(x, 1.65, 4), Vector3(0.1, 0.35, 0.36), Color("b9a884"))
		box(self, Vector3(x, 0.7, 5.4), Vector3(0.09, 0.09, 2.5), Color("65523e"))
	# A warm doorway lamp remains visible after the dust, leading back to Mei.
	var guide := OmniLight3D.new()
	guide.position = Vector3(0, 2.7, -2.4)
	guide.light_color = Color("ffd498")
	guide.light_energy = 1.7
	guide.omni_range = 5
	add_child(guide)
	# A bracket fixed to the doorway header carries the entrance lantern.
	box(self, Vector3(0, 3.4, -3), Vector3(4, 0.18, 0.22), Color("544b3d"))
	box(self, Vector3(0, 3.4, -2.72), Vector3(0.07, 0.07, 0.65), Color("383a34"))
	shelter_lamp(Vector3(0, 2.75, -2.5), 3.4)
	for x in [-3.0, 2.7]:
		box(self, Vector3(x, 0.46, -9.6), Vector3(0.7, 0.75, 0.6), Color("826b50"))
		box(self, Vector3(x, 0.88, -9.6), Vector3(0.35, 0.08, 0.12), INK)
	jug = Node3D.new()
	add_child(jug)
	cylinder(jug, Vector3.ZERO, 0.09, 0.21, Color("9a8160"), 0.075)
	box(jug, Vector3(0.1, 0.06, 0), Vector3(0.11, 0.045, 0.06), Color("9a8160"))
	jug.visible = false
	water_stream = cylinder(self, Vector3.ZERO, 0.012, 1, Color("8caeb2"))
	water_stream.visible = false
	shop_gate = Node3D.new()
	shop_gate.position = Vector3(-1.4, 0, 9.16)
	shop_gate.rotation.y = -0.75
	add_child(shop_gate)
	for x in [0.25, 0.75, 1.25, 1.75, 2.25]:
		box(shop_gate, Vector3(x, 1.25, 0), Vector3(0.47, 2.4, 0.09), Color("5b5748"))
	# One table holds the pail, jug and cups; keep the aisle in front clear.
	box(self, Vector3(-2.8, 0.72, -9.45), Vector3(2.2, 0.13, 0.85), Color("977a57"), true)
	for x in [-3.6, -2.0]:
		box(self, Vector3(x, 0.35, -9.45), Vector3(0.1, 0.7, 0.6), Color("63523e"))
	for x in [-3.45, -3.15, -2.85]:
		cylinder(self, Vector3(x, 0.87, -9.5), 0.07, 0.15, CREAM)
	for z in [-4.2, -7, -10.1]:
		box(self, Vector3(0, 3.4, z), Vector3(9.8, 0.16, 0.18), Color("544b3d"))
	for x in [-1.0, 1.0]:
		box(self, Vector3(x, 0.045, -9.6), Vector3(1.2, 0.09, 1.6), Color("9e9478"))
		var bedding := cylinder(self, Vector3(x, 0.23, -10.1), 0.15, 0.85, Color("777f74"))
		bedding.rotation.z = PI / 2
	for i in 2:
		# Both start north of the cart's footprint and handles.
		var walker := actor(Vector3(-11 + i * 1.4, 0, 0.5 + i * 0.9), Color("858169") if i == 0 else Color("927c68"), "Neighbour")
		var bag := Node3D.new()
		walker.hands[0].add_child(bag)
		walker.carrying_bag = true
		# Narrow across the body, long fore-to-aft, suspended from a real handle.
		box(bag, Vector3(0, -0.27, 0), Vector3(0.18, 0.32, 0.43), Color("695544"))
		for z in [-0.215, 0.215]:
			box(bag, Vector3(0, -0.27, z), Vector3(0.19, 0.33, 0.018), Color("493b30"))
		for z in [-0.07, 0.07]:
			box(bag, Vector3(0, -0.07, z), Vector3(0.035, 0.12, 0.035), Color("382f28"))
		box(bag, Vector3.ZERO, Vector3(0.035, 0.035, 0.17), Color("382f28"))
		box(bag, Vector3(-0.1, -0.19, 0), Vector3(0.018, 0.05, 0.06), Color("b29b63"))
		resident_bags.append(bag)
		evacuees.append(walker)
		var lane := -0.65 if i == 0 else 0.65
		resident_routes.append([Vector3(-6, 0, 0.5 + i * 0.9), Vector3(lane, 0, -0.8), Vector3(lane, 0, -4.5), Vector3(lane, 0, -6.6 - i * 0.6), Vector3(-3.25 if i == 0 else 3.25, 0, -6.6 - i * 0.6)])
		route_steps.append(0)

func shelter_lamp(at: Vector3, mount_height: float) -> void:
	# Warm glass enclosed by a metal cage, visibly suspended from its support.
	var metal := Color("383a34")
	var fixture := Node3D.new()
	fixture.position = at
	add_child(fixture)
	cylinder(fixture, Vector3.ZERO, 0.105, 0.22, Color("d8bd7c"))
	cylinder(fixture, Vector3(0, -0.14, 0), 0.15, 0.06, metal)
	cylinder(fixture, Vector3(0, 0.14, 0), 0.16, 0.07, metal, 0.09)
	for x in [-0.095, 0.095]:
		for z in [-0.095, 0.095]:
			box(fixture, Vector3(x, 0, z), Vector3(0.022, 0.28, 0.022), metal)
	var stem_length := mount_height - at.y - 0.175
	cylinder(fixture, Vector3(0, 0.175 + stem_length * 0.5, 0), 0.018, stem_length, metal)
	cylinder(fixture, Vector3(0, mount_height - at.y, 0), 0.09, 0.045, metal)

func key_ring(parent: Node3D, at: Vector3, radius: float, color: Color) -> void:
	var ring := MeshInstance3D.new()
	var shape := TorusMesh.new()
	shape.inner_radius = radius - 0.014
	shape.outer_radius = radius + 0.014
	shape.rings = 16
	shape.ring_segments = 8
	ring.mesh = shape
	ring.material_override = material(color)
	ring.position = at
	parent.add_child(ring)
