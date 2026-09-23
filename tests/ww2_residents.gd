extends SceneTree
var failures := 0
func _initialize() -> void: call_deferred("run")
func check(value: bool, description: String) -> void:
	print(("PASS: " if value else "FAIL: ") + description)
	if not value: failures += 1
func run() -> void:
	var world = load("res://game/ww2_world.gd").new()
	root.add_child(world)
	world.build(load("res://game/ww2.gd").WAR_CHAPTER)
	world.set_process(false)
	var dust_gradient: Gradient = world.dust.material_override.albedo_texture.gradient
	check(is_zero_approx(dust_gradient.sample(1.0).a), "Dust texture edge is fully transparent")
	var smooth_alpha := true
	var previous_alpha := 1.0
	for i in 101:
		var opacity := dust_gradient.sample(i / 100.0).a
		if opacity > previous_alpha + 0.00001 or opacity > 0.18001: smooth_alpha = false
		previous_alpha = opacity
	check(smooth_alpha, "Dust opacity falls towards its edge without an opaque ring")
	check(not world.cup.visible, "No unattended cup floats beside Mei outdoors")
	var cart_clear := true
	var doorway_clear := true
	var monotonic := true
	var last_steps := [0, 0]
	for step in 2400:
		world._process(1.0 / 60.0)
		for i in 2:
			var p: Vector3 = world.evacuees[i].position
			# Expanded footprint covers the cart, wheels, handles and a civilian's body.
			if p.x > -9.85 and p.x < -6.15 and p.z > 2.55 and p.z < 7.15: cart_clear = false
			if p.z < -2.4 and p.z > -3.6 and absf(p.x) > 1.2: doorway_clear = false
			if world.route_steps[i] < last_steps[i]: monotonic = false
			last_steps[i] = world.route_steps[i]
	check(cart_clear, "Residents stay clear of the cart from spawn through arrival")
	check(doorway_clear, "Residents cross the doorway in clear lanes")
	check(monotonic, "Route progress never reverses at the door")
	for i in 2:
		check(world.evacuees[i].seated and world.route_steps[i] == world.resident_routes[i].size(), "Resident %d reaches a seat" % i)
		check(world.resident_bags[i].get_parent() == world, "Resident puts luggage beside the bench")
	var head_before: Vector3 = world.evacuees[0].head.rotation
	for i in 120: world._process(1.0 / 60.0)
	check(world.evacuees[0].head.rotation.distance_to(head_before) > 0.01, "Seated residents have idle movement")
	world.close_shelter()
	world.begin_pour()
	var cup_attached := true
	var table_clear := true
	var handoff_gap := 10.0
	for i in 480:
		world._process(1.0 / 60.0)
		if world.relief_clock < 4.8:
			if world.cup.global_position.distance_to(world.mei.hands[1].global_position) > 0.12: cup_attached = false
		if world.relief_clock > 4.6 and world.relief_clock < 4.8:
			handoff_gap = minf(handoff_gap, world.mei.hands[1].global_position.distance_to(world.evacuees[0].hands[1].global_position))
		if world.mei.position.z < -8.7: table_clear = false
	check(handoff_gap < 0.06, "Both hands meet before the cup transfers")
	check(cup_attached, "Cup stays in Mei's hand while pouring and carrying")
	check(table_clear, "Mei stays clear of the water table")
	check(world.water_delivered, "Mei delivers water to a resident")
	check(world.evacuees[0].seat_activity == "drink", "Recipient drinks from the cup")
	check(world.tan.position.distance_to(Vector3(-1.05, 0, -8.55)) < 1.4, "Tan stays beside Sparky during the handoff")
	check(world.tan.hands[0].global_position.distance_to(world.comfort_target) < 0.06, "Tan rests his hand on Sparky’s shoulder")
	world.finish_relief()
	world.queue_free()
	await process_frame
	print("RESIDENT FAILURES: ", failures)
	quit(1 if failures else 0)
