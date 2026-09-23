extends Node3D
## Small articulated civilian characters, authored for this fictional encounter.
var torso: Node3D
var head: Node3D
var arms: Array[Node3D] = []
var hands: Array[Node3D] = []
var legs: Array[Node3D] = []
var shins: Array[Node3D] = []
var carrying_bag := false
var seated := false
var seat_activity := "rest"
var pose := "listen"
var phase := 0.0
var last_position := Vector3.ZERO
var female := false

func build(w: Node3D, is_mei: bool, shirt: Color) -> void:
	female = is_mei
	var skin := Color("bc8d69") if not female else Color("c89b7b")
	var ink := Color("342f2a")
	torso = Node3D.new()
	torso.position.y = 0.86
	add_child(torso)
	var body = w.cylinder(torso, Vector3(0, 0.14, 0), 0.29, 0.69, shirt, 0.33)
	body.scale.z = 0.68
	for y in [0.05, 0.22, 0.39]:
		w.ball(torso, Vector3(0, y, 0.21), 0.022, Color("d7c8ac"))
	if female:
		var skirt = w.cylinder(self, Vector3(0, 0.58, 0), 0.36, 0.53, shirt.darkened(0.18), 0.27)
		skirt.scale.z = 0.75
	else:
		w.box(torso, Vector3(-0.17, 0.25, 0.215), Vector3(0.17, 0.17, 0.022), shirt.darkened(0.1))
	for side in [-1.0, 1.0]:
		var arm := Node3D.new()
		arm.position = Vector3(side * 0.34, 0.4, 0)
		torso.add_child(arm)
		arms.append(arm)
		w.cylinder(arm, Vector3(0, -0.13, 0), 0.105, 0.28, shirt)
		w.cylinder(arm, Vector3(0, -0.32, 0), 0.072, 0.2, skin)
		var hand := Node3D.new()
		hand.position.y = -0.45
		arm.add_child(hand)
		w.ball(hand, Vector3.ZERO, 0.085, skin)
		hands.append(hand)
		var leg := Node3D.new()
		leg.position = Vector3(side * 0.14, 0.63, 0)
		add_child(leg)
		legs.append(leg)
		w.cylinder(leg, Vector3(0, -0.125, 0), 0.092, 0.25, Color("494c48"))
		var shin := Node3D.new()
		shin.position.y = -0.25
		leg.add_child(shin)
		shins.append(shin)
		w.cylinder(shin, Vector3(0, -0.125, 0), 0.086, 0.25, Color("494c48"))
		var shoe = w.ball(shin, Vector3(0, -0.31, 0.045), 0.12, Color("383931"))
		shoe.scale = Vector3(0.85, 0.5, 1.4)
	head = Node3D.new()
	head.position.y = 0.75
	torso.add_child(head)
	w.cylinder(torso, Vector3(0, 0.52, 0), 0.08, 0.15, skin)
	var face = w.ball(head, Vector3.ZERO, 0.265, skin)
	face.scale = Vector3(0.86, 1.05, 0.86)
	var hair = w.ball(head, Vector3(0, 0.14, -0.03), 0.27, ink)
	hair.scale = Vector3(0.94, 0.68, 0.94)
	if female:
		w.ball(head, Vector3(0, 0.04, -0.23), 0.13, ink)
		for side in [-1, 1]:
			var lock = w.ball(head, Vector3(side * 0.21, 0.02, -0.025), 0.095, ink)
			lock.scale = Vector3(0.42, 1.7, 0.8)
	else:
		for side in [-1, 1]:
			w.box(head, Vector3(side * 0.2, 0.04, -0.025), Vector3(0.02, 0.09, 0.12), Color("766e60"))
	for side in [-1.0, 1.0]:
		w.ball(head, Vector3(side * 0.08, 0.025, 0.215), 0.024, ink)
		var brow = w.box(head, Vector3(side * 0.08, 0.085, 0.219), Vector3(0.075, 0.015, 0.015), ink)
		brow.rotation.z = -side * 0.12
		w.ball(head, Vector3(side * 0.235, -0.01, 0), 0.044, skin)
	w.ball(head, Vector3(0, -0.035, 0.236), 0.039, skin.lightened(0.07))
	w.box(head, Vector3(0, -0.125, 0.21), Vector3(0.071, 0.012, 0.014), Color("815e50"))
	last_position = position

func tick(delta: float) -> void:
	var speed := position.distance_to(last_position) / maxf(delta, 0.001)
	last_position = position
	phase += delta
	var stride := sin(phase * 10) * minf(speed / 3, 1)
	var head_target := Vector3(0.02, 0, 0)
	var arm_targets := [Vector3(0, 0, 0.1), Vector3(0, 0, -0.1)]
	var lean := 0.0
	match pose:
		"beckon":
			arm_targets[1] = Vector3(-1.0 + sin(phase * 4) * 0.23, 0, -0.45)
			lean = -0.04
		"flinch":
			arm_targets[0] = Vector3(-2.1, 0, 0.45)
			arm_targets[1] = Vector3(-0.8, 0, -0.4)
			head_target.x = 0.38
			lean = 0.26
		"keys":
			arm_targets[0] = Vector3(-0.85, 0, -0.3)
			head_target = Vector3(0.32, 0.3, 0)
		"pour":
			arm_targets[0] = Vector3(-1.35, 0, 1.0)
			arm_targets[1] = Vector3(-0.75, 0, -0.65)
			head_target.x = 0.18
		"carry_cup":
			arm_targets[1] = Vector3(-0.9, 0, -0.3)
		"speak":
			arm_targets[1].x = -0.35 + sin(phase * 2) * 0.07
			head_target.y = sin(phase * 1.5) * 0.06
	if seated:
		head_target.y = sin(phase * 0.48) * 0.19
		arm_targets[0] = Vector3(-0.65, 0, 0.12)
		arm_targets[1] = Vector3(-0.65, 0, -0.12)
		lean = 0.035 + sin(phase * 0.8) * 0.014
		if seat_activity == "drink":
			var sip := smoothstep(0.3, 0.7, sin(phase * 0.65))
			arm_targets[1] = Vector3(-1.0 - sip * 0.9, 0, -0.5)
			head_target.x = -sip * 0.04
		else:
			arm_targets[0].x += sin(phase * 1.2) * 0.07
	if carrying_bag and not seated:
		arm_targets[0] = Vector3(0, 0, -0.3)
	var blend := 1 - exp(-delta * 9)
	torso.rotation.x = lerpf(torso.rotation.x, lean, blend)
	torso.position.y = lerpf(torso.position.y, 0.86 - (0.13 if pose == "flinch" else 0.0) + absf(stride) * 0.025, blend)
	head.rotation = head.rotation.lerp(head_target, blend)
	for i in 2:
		legs[i].rotation.x = -PI / 2 if seated else stride * (0.32 if i == 0 else -0.32)
		shins[i].rotation.x = PI / 2 if seated else 0
		shins[i].scale.y = 1.65 if seated else 1.0
		arms[i].scale = Vector3.ONE
		arms[i].rotation = arms[i].rotation.lerp(arm_targets[i] + Vector3(stride * (-0.18 if i == 0 else 0.18), 0, 0), blend)

func reach_hand(index: int, target: Vector3, weight: float) -> void:
	var arm := arms[index]
	var local_target: Vector3 = torso.to_local(target) - arm.position
	var reach := Quaternion(Vector3.DOWN, local_target.normalized())
	arm.quaternion = arm.quaternion.slerp(reach, clampf(weight, 0, 1))
	arm.scale.y = lerpf(1.0, clampf(local_target.length() / 0.45, 0.8, 1.3), weight)
