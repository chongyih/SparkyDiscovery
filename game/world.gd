extends Node3D
## Reusable, deliberately illustrative sets; not reconstructions of specific streets.

const CREAM := Color("eadcc3")
const TEAL := Color("285b58")
const INK := Color("243d42")
const GOLD := Color("edbb62")
const BRICK := Color("b86750")
var stations: Array[Node3D] = []
var markers: Array[Node3D] = []
var labels: Array[Label3D] = []
var sign_font: FontVariation
var active_index := -1
var clock := 0.0
var tv_screen: MeshInstance3D
var spare_aerial: Node3D
var tv_aerial: Node3D
var materials: Dictionary = {}
var community: Node3D
var neighbour_visual: Node3D
var neighbour_walking := false
var neighbour_limbs: Array[Node3D] = []

func material(color: Color, emission: bool = false) -> StandardMaterial3D:
	var key := str(color) + str(emission)
	if materials.has(key):
		return materials[key]
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.87
	if emission:
		mat.emission_enabled = true
		mat.emission = color
		mat.emission_energy_multiplier = 0.4
	materials[key] = mat
	return mat

func box(parent: Node3D, at: Vector3, size: Vector3, color: Color, solid := false) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	var resource := BoxMesh.new()
	resource.size = size
	mesh.mesh = resource
	mesh.material_override = material(color)
	mesh.position = at
	parent.add_child(mesh)
	if solid:
		var body := StaticBody3D.new()
		var collider := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = size
		collider.shape = shape
		body.add_child(collider)
		mesh.add_child(body)
	return mesh

func cylinder(parent: Node3D, at: Vector3, radius: float, height: float, color: Color, top := -1.0) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	var resource := CylinderMesh.new()
	resource.bottom_radius = radius
	resource.top_radius = radius if top < 0 else top
	resource.height = height
	resource.radial_segments = 12
	mesh.mesh = resource
	mesh.material_override = material(color)
	mesh.position = at
	parent.add_child(mesh)
	return mesh

func ball(parent: Node3D, at: Vector3, radius: float, color: Color) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	var resource := SphereMesh.new()
	resource.radius = radius
	resource.height = radius * 2
	resource.radial_segments = 16
	resource.rings = 8
	mesh.mesh = resource
	mesh.material_override = material(color)
	mesh.position = at
	parent.add_child(mesh)
	return mesh

func sign_text(parent: Node3D, at: Vector3, text: String, size := 38, color := CREAM) -> Label3D:
	if not sign_font:
		# The UI's Inter, at the semi-bold weight of Godot's default font, keeps signs as legible.
		sign_font = FontVariation.new()
		sign_font.base_font = load("res://assets/fonts/Inter.ttf")
		sign_font.variation_opentype = {TextServerManager.get_primary_interface().name_to_tag("wght"): 600}
	var label := Label3D.new()
	label.text = text
	label.font = sign_font
	label.font_size = size
	label.pixel_size = 0.009
	label.modulate = color
	label.outline_size = 0
	label.position = at
	parent.add_child(label)
	return label

func build(chapter: Dictionary) -> void:
	# Homes and their shared ground floor face a separate shopping street.
	# The surrounding scenery is illustrative, not a replica of a named location.
	box(self, Vector3(0, -0.2, 6), Vector3(90, 0.4, 90), Color("c5bfa6"), true)
	box(self, Vector3(0, 0.025, 7.5), Vector3(48, 0.05, 9), Color("899790"))
	box(self, Vector3(0, 0.028, -2.5), Vector3(5, 0.055, 16), Color("a6afa0"))
	for z in [3.0, 12.0]:
		box(self, Vector3(0, 0.055, z), Vector3(48, 0.1, 0.12), CREAM)
	for x in range(-21, 24, 4):
		box(self, Vector3(x, 0.065, 7.5), Vector3(1.8, 0.015, 0.08), CREAM)
	for x in range(-23, 24, 2):
		box(self, Vector3(x, 0.02, -3.5), Vector3(0.022, 0.025, 13), Color("b0ac95"))
	for z in range(-9, 4, 2):
		box(self, Vector3(0, 0.02, z), Vector3(48, 0.025, 0.022), Color("b0ac95"))
	var shop_names := ["PROVISIONS", "KEDAI • STORE", "RADIO • TELEVISION", "KOPI & TEH", "BICYCLE REPAIRS"]
	var colors := [Color("c8d2bb"), Color("dfb796"), Color("c9d3bb"), Color("e0c988"), Color("c4d5d3")]
	for i in range(5):
		shop(Vector3((i - 2) * 8.0, 0, 20), colors[i], shop_names[i], PI)
	# Low boundary walls are visible and collidable; no invisible movement clamps.
	for x in [-24.0, 24.0]:
		box(self, Vector3(x, 0.7, 6), Vector3(0.35, 1.4, 40), CREAM, true)
		for z in range(-12, 27, 3):
			box(self, Vector3(x, 0.9, z), Vector3(0.6, 1.8, 0.6), TEAL.lightened(0.2))
	box(self, Vector3(0, 0.7, 26), Vector3(48, 1.4, 0.35), CREAM, true)
	box(self, Vector3(0, 0.7, -13), Vector3(48, 1.4, 0.35), CREAM, true)
	for x in [-16, 16]:
		box(self, Vector3(x, 0.02, -1), Vector3(8, 0.07, 6), Color("799577"))
		for z in [-3.5, 1.5]:
			tree(Vector3(x, 0, z))
		var bench_x := float(x) - signf(float(x)) * 2.6
		box(self, Vector3(bench_x, 0.055, 0), Vector3(3.2, 0.07, 2.0), Color("c6c5b3"))
		bench(Vector3(bench_x, 0, 0))
	for at in [Vector3(-21, 0, -2), Vector3(20, 0, -1), Vector3(-20, 0, 12.8), Vector3(20, 0, 12.8)]:
		tree(at)
	for x in [-18.0, -9.0, 7.0, 18.0]:
		lamp(Vector3(x, 0, 2.1))
	bench(Vector3(-10, 0, 0))
	# A small coffee table and a bus shelter add places to explore between objectives.
	cylinder(self, Vector3(15, 0.75, -5), 0.8, 0.1, CREAM)
	cylinder(self, Vector3(15, 0.4, -5), 0.09, 0.75, INK)
	for x in [13.7, 16.3]:
		cylinder(self, Vector3(x, 0.45, -5), 0.32, 0.7, BRICK)
	box(self, Vector3(8, 3.2, 14), Vector3(4, 0.16, 2), TEAL)
	for x in [6.2, 9.8]:
		box(self, Vector3(x, 1.6, 14.7), Vector3(0.12, 3.2, 0.12), INK, true)
	bench(Vector3(8, 0, 14.3), PI)
	box(self, Vector3(8, 2.91, 13.04), Vector3(3.6, 0.42, 0.12), TEAL)
	var bus_sign := sign_text(self, Vector3(8, 2.91, 12.97), "BUS STOP", 34, CREAM)
	bus_sign.rotation.y = PI
	for task in chapter.tasks:
		make_station(task)
	community = preload("res://game/community.gd").new()
	add_child(community)
	community.build(self)
	# Distant roofs and trees extend the view beyond the playable block.
	for i in range(9):
		var at := Vector3((i - 4) * 8, 0, -22)
		box(self, at + Vector3(0, 3, 0), Vector3(6, 6, 5), colors[i % colors.size()].darkened(0.12))
		box(self, at + Vector3(0, 6.05, 0), Vector3(6.3, 0.2, 5.2), BRICK)
	for i in range(8):
		tree(Vector3((i - 4) * 8, 0, 32))
	bake_static(self, [community] + stations)

## Merges the static meshes under `root` into one mesh per material, so the scenery
## costs a few dozen draw calls instead of hundreds. Anything under a node in `keep`
## moves or toggles at runtime and stays a separate instance.
func bake_static(root: Node3D, keep: Array) -> void:
	var surfaces := {}
	for mesh: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		if not is_instance_valid(mesh):
			continue
		var to_root := mesh.transform
		var parent := mesh.get_parent() as Node3D
		var dynamic := not mesh.visible or mesh in keep
		while parent != root and not dynamic:
			dynamic = parent in keep or not parent.visible
			to_root = parent.transform * to_root
			parent = parent.get_parent() as Node3D
		if dynamic:
			continue
		var surface: SurfaceTool = surfaces.get(mesh.material_override)
		if not surface:
			surface = SurfaceTool.new()
			surface.begin(Mesh.PRIMITIVE_TRIANGLES)
			surfaces[mesh.material_override] = surface
		surface.append_from(mesh.mesh, 0, to_root)
		# Colliders hang off their mesh; keep them in the same place under `root`.
		for body in mesh.get_children():
			mesh.remove_child(body)
			body.transform = to_root * body.transform
			root.add_child(body)
		mesh.free()
	for mat in surfaces:
		var merged := MeshInstance3D.new()
		merged.mesh = surfaces[mat].commit()
		merged.material_override = mat
		root.add_child(merged)

func shop(at: Vector3, color: Color, title: String, facing := 0.0) -> void:
	var root := Node3D.new()
	root.position = at
	root.rotation.y = facing
	add_child(root)
	box(root, Vector3(0, 2.1, 0), Vector3(5.8, 4.2, 2.9), color, true)
	box(root, Vector3(0, 4.24, 0), Vector3(6.1, 0.2, 3.2), BRICK, true)
	box(root, Vector3(0, 3.97, 1.54), Vector3(6, 0.19, 0.25), CREAM)
	box(root, Vector3(0, 2.2, 1.52), Vector3(5.8, 0.19, 0.22), CREAM)
	for x in [-1.85, 0.0, 1.85]:
		box(root, Vector3(x, 3.1, 1.48), Vector3(1.03, 1.15, 0.13), CREAM)
		box(root, Vector3(x, 3.1, 1.58), Vector3(0.84, 0.97, 0.09), TEAL)
		for slat in range(5):
			box(root, Vector3(x, 2.74 + slat * 0.18, 1.65), Vector3(0.8, 0.035, 0.05), TEAL.lightened(0.18))
		box(root, Vector3(x, 0.9, 1.49), Vector3(1.3, 1.65, 0.08), INK)
	box(root, Vector3(0, 2.35, 2.8), Vector3(5.25, 0.47, 0.22), TEAL, true)
	sign_text(root, Vector3(0, 2.35, 2.93), title, 29)
	for x in [-2.7, 2.7]:
		box(root, Vector3(x, 1.05, 2.12), Vector3(0.17, 2.1, 0.17), CREAM)
	box(root, Vector3(0, 2.32, 1.95), Vector3(5.95, 0.12, 1.6), TEAL, true)

func tree(at: Vector3) -> void:
	cylinder(self, at + Vector3(0, 0.2, 0), 0.85, 0.4, CREAM)
	cylinder(self, at + Vector3(0, 1.6, 0), 0.16, 3.0, Color("7d6248"), 0.1)
	var green := Color("438173")
	ball(self, at + Vector3(0, 3.2, 0), 1.15, green)
	ball(self, at + Vector3(0.6, 3.55, 0), 0.8, green.lightened(0.08))
	ball(self, at + Vector3(-0.45, 3.65, 0.1), 0.75, green.lightened(0.14))

func lamp(at: Vector3) -> void:
	cylinder(self, at + Vector3(0, 1.65, 0), 0.055, 3.3, INK)
	box(self, at + Vector3(0, 3.4, 0), Vector3(0.34, 0.45, 0.34), GOLD)
	box(self, at + Vector3(0, 3.66, 0), Vector3(0.46, 0.09, 0.46), INK)

func bench(at: Vector3, facing := 0.0) -> void:
	var root := Node3D.new()
	root.position = at
	root.rotation.y = facing
	add_child(root)
	box(root, Vector3(0, 0.5, 0), Vector3(2.5, 0.12, 0.7), Color("997958"), true)
	box(root, Vector3(0, 0.95, -0.3), Vector3(2.5, 0.55, 0.09), Color("997958"))
	for x in [-0.9, 0.9]:
		box(root, Vector3(x, 0.25, 0), Vector3(0.12, 0.5, 0.55), INK)

func person(parent: Node3D, at: Vector3, shirt: Color) -> void:
	var skin := Color("bf926f")
	cylinder(parent, at + Vector3(0, 0.8, 0), 0.3, 0.8, shirt, 0.25)
	cylinder(parent, at + Vector3(0, 1.24, 0), 0.09, 0.18, skin)
	ball(parent, at + Vector3(0, 1.46, 0), 0.25, skin)
	var hair := ball(parent, at + Vector3(0, 1.57, -0.035), 0.255, Color("3c3430"))
	hair.scale.y = 0.6
	for side in [-1.0, 1.0]:
		ball(parent, at + Vector3(side * 0.085, 1.48, 0.233), 0.029, Color("39372f"))
		var brow := box(parent, at + Vector3(side * 0.085, 1.545, 0.23), Vector3(0.08, 0.018, 0.018), Color("574737"))
		brow.rotation.z = side * 0.08
		ball(parent, at + Vector3(side * 0.247, 1.46, 0), 0.05, skin)
		cylinder(parent, at + Vector3(side * 0.3, 0.92, 0), 0.085, 0.35, shirt)
	ball(parent, at + Vector3(0, 1.44, 0.265), 0.044, skin.lightened(0.04))
	box(parent, at + Vector3(0, 1.355, 0.225), Vector3(0.09, 0.018, 0.02), Color("805e4c"))
	for y in [0.78, 0.93, 1.08]:
		ball(parent, at + Vector3(0, y, 0.28), 0.018, CREAM)
	for x in [-0.15, 0.15]:
		var leg := Node3D.new()
		leg.position = at + Vector3(x, 0.5, 0)
		parent.add_child(leg)
		neighbour_limbs.append(leg)
		box(leg, Vector3(0, -0.25, 0), Vector3(0.18, 0.5, 0.23), INK)
		ball(parent, at + Vector3(x * 2.1, 0.72, 0), 0.12, Color("bf926f"))

func aerial(parent: Node3D, at: Vector3) -> Node3D:
	var prop := Node3D.new()
	prop.position = at
	parent.add_child(prop)
	for angle in [-0.65, 0.65]:
		var rod := cylinder(prop, Vector3(angle * 0.3, 0.35, 0), 0.025, 0.95, CREAM)
		rod.rotation.z = angle
	box(prop, Vector3.ZERO, Vector3(0.45, 0.1, 0.3), INK)
	return prop

func make_station(task: Dictionary) -> void:
	var root := Node3D.new()
	root.position = task.at
	add_child(root)
	stations.append(root)
	match task.kind:
		"person":
			var neighbour := Node3D.new()
			neighbour.rotation.y = PI
			neighbour_visual = neighbour
			root.add_child(neighbour)
			person(neighbour, Vector3.ZERO, BRICK)
		"aerial":
			box(root, Vector3(0, 0.75, 0), Vector3(1.8, 0.15, 0.85), Color("98714d"), true)
			for x in [-0.7, 0.7]:
				box(root, Vector3(x, 0.35, 0), Vector3(0.12, 0.7, 0.65), INK)
			spare_aerial = aerial(root, Vector3(0, 0.9, 0))
		"tv":
			box(root, Vector3(0, 0.92, 0), Vector3(2.4, 0.14, 1.0), Color("8c654b"), true)
			for x in [-0.95, 0.95]:
				box(root, Vector3(x, 0.45, 0), Vector3(0.16, 0.9, 0.8), Color("664c38"))
			box(root, Vector3(0, 1.82, 0), Vector3(2.25, 1.65, 0.8), Color("78553e"), true)
			box(root, Vector3(-0.15, 1.84, 0.405), Vector3(1.74, 1.34, 0.025), Color("292c29"))
			tv_screen = MeshInstance3D.new()
			var screen_quad := QuadMesh.new()
			screen_quad.size = Vector2(1.6, 1.2)
			tv_screen.mesh = screen_quad
			tv_screen.position = Vector3(-0.15, 1.84, 0.425)
			tv_screen.material_override = material(Color("718a83"))
			root.add_child(tv_screen)
			for y in [1.93, 2.3]:
				ball(root, Vector3(0.94, y, 0.44), 0.075, CREAM)
			for y in [1.24, 1.34, 1.44, 1.54, 1.64]:
				box(root, Vector3(0.93, y, 0.413), Vector3(0.23, 0.03, 0.015), INK)
			tv_aerial = aerial(root, Vector3(0, 2.72, 0))
			tv_aerial.visible = false
	var marker := Node3D.new()
	root.add_child(marker)
	var gem := box(marker, Vector3(0, 2.8, 0), Vector3(0.22, 0.22, 0.22), GOLD)
	gem.rotation.z = PI / 4
	gem.material_override = material(GOLD, true)
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 0.8
	torus.outer_radius = 0.88
	torus.rings = 24
	torus.ring_segments = 8
	ring.mesh = torus
	ring.material_override = material(GOLD)
	ring.position.y = 0.12
	marker.add_child(ring)
	markers.append(marker)
	var names := {"person": task.speaker.to_upper(), "aerial": "SPARE AERIAL", "tv": "TELEVISION"}
	var label := sign_text(root, Vector3(0, 3.22, 0), names[task.kind], 40, CREAM)
	label.pixel_size = 0.009
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.outline_size = 7
	label.outline_modulate = INK
	labels.append(label)

func set_active(index: int) -> void:
	active_index = index
	for i in markers.size():
		markers[i].visible = i == index
		labels[i].visible = i == index

func _process(delta: float) -> void:
	clock += delta
	if is_instance_valid(neighbour_visual):
		neighbour_visual.position.y = absf(sin(clock * 8)) * 0.025 if neighbour_walking else 0.0
		for i in neighbour_limbs.size():
			neighbour_limbs[i].rotation.x = sin(clock * 8 + i * PI) * 0.38 if neighbour_walking else 0.0
	if active_index >= 0 and active_index < markers.size():
		markers[active_index].get_child(0).position.y = 2.8 + sin(clock * 2.5) * 0.12
