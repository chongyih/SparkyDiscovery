extends CharacterBody3D

const SPEED := 4.2
var enabled := false
var visual: Node3D
var animator: AnimationPlayer
var camera: Camera3D
var seated := false
var skeleton: Skeleton3D
var scripted_motion := false
var sit_blend := 1.0:
	set(value):
		sit_blend = value
		apply_seat_pose(value)
var reach_rest := Quaternion.IDENTITY
var reach_blend := 0.0:
	set(value):
		reach_blend = value
		if skeleton:
			var bone := skeleton.find_bone("arm.L")
			if bone >= 0:
				skeleton.set_bone_pose_rotation(bone, Quaternion(Vector3.RIGHT, -0.9 * value) * reach_rest)

func prepare_reach() -> void:
	animator.stop()
	play_animation("Idle")
	animator.advance(0)
	animator.pause()
	reach_rest = skeleton.get_bone_pose_rotation(skeleton.find_bone("arm.L"))
	reach_blend = 0

func resume_idle() -> void:
	animator.stop()
	play_animation("Idle")

func _ready() -> void:
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.32
	capsule.height = 1.5
	shape.shape = capsule
	shape.position.y = 0.75
	add_child(shape)
	visual = load("res://assets/sparky/sparky.glb").instantiate()
	visual.scale = Vector3.ONE * 0.95
	add_child(visual)
	animator = visual.find_child("AnimationPlayer", true, false) as AnimationPlayer
	skeleton = visual.find_child("Skeleton3D", true, false) as Skeleton3D
	if animator:
		for animation_name in animator.get_animation_list():
			if "Idle" in animation_name or "Walk" in animation_name:
				animator.get_animation(animation_name).loop_mode = Animation.LOOP_LINEAR
		play_animation("Idle")
	# The mesh fibres should not produce thousands of tiny fur shadows.
	for mesh in visual.find_children("*", "MeshInstance3D", true, false):
		if "pile" in mesh.name.to_lower():
			mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

func play_animation(suffix: String) -> void:
	if not animator:
		return
	for animation_name in animator.get_animation_list():
		if animation_name.ends_with(suffix):
			if animator.current_animation != animation_name:
				animator.play(animation_name, 0.18)
			return

func set_seated(active: bool) -> void:
	if seated == active:
		return
	seated = active
	velocity = Vector3.ZERO
	if animator:
		animator.stop()
	if skeleton:
		skeleton.reset_bone_poses()
	play_animation("Idle")
	if not seated:
		return
	# Keep the relaxed idle arms, then bring the short plush legs over the seat edge.
	if animator:
		animator.advance(0.0)
		animator.pause()
	sit_blend = 1.0

func apply_seat_pose(weight: float) -> void:
	if skeleton:
		for bone_name in ["leg.L", "leg.R"]:
			var bone := skeleton.find_bone(bone_name)
			if bone >= 0:
				var rest_basis := skeleton.get_bone_global_rest(bone).basis
				var axis := (rest_basis.inverse() * Vector3.RIGHT).normalized()
				var rest_rotation := skeleton.get_bone_rest(bone).basis.get_rotation_quaternion()
				skeleton.set_bone_pose_rotation(bone, rest_rotation * Quaternion(axis, deg_to_rad(-75.0) * weight))
		var head_bone := skeleton.find_bone("head")
		if head_bone >= 0:
			# A small glance towards the gathering keeps both eyes readable in the wide shot.
			skeleton.set_bone_pose_rotation(head_bone, Quaternion(Vector3.UP, -0.35 * weight))

func react_to_broadcast(seconds: float) -> void:
	if not seated or not skeleton:
		return
	var head_bone := skeleton.find_bone("head")
	if head_bone < 0:
		return
	# The head dips during the long pause, then briefly turns towards the couple.
	var dip := smoothstep(22.0, 26.0, seconds) * (1.0 - smoothstep(51.0, 57.0, seconds))
	var glance := smoothstep(29.0, 32.0, seconds) * (1.0 - smoothstep(38.0, 42.0, seconds))
	skeleton.set_bone_pose_rotation(head_bone, Quaternion(Vector3.UP, -0.35 - 0.6 * glance) * Quaternion(Vector3.RIGHT, 0.13 * dip))

func _physics_process(delta: float) -> void:
	if seated or scripted_motion:
		return
	var direction := Vector3.ZERO
	if enabled and camera:
		var axis := Input.get_vector("move_left", "move_right", "move_up", "move_down")
		var right := camera.global_basis.x
		var back := camera.global_basis.z
		right.y = 0
		back.y = 0
		direction = (right.normalized() * axis.x + back.normalized() * axis.y).limit_length()
	velocity.x = move_toward(velocity.x, direction.x * SPEED, delta * 22)
	velocity.z = move_toward(velocity.z, direction.z * SPEED, delta * 22)
	if not is_on_floor():
		velocity.y -= 18.0 * delta
	else:
		velocity.y = 0
	move_and_slide()
	if direction.length() > 0.05:
		visual.rotation.y = lerp_angle(visual.rotation.y, atan2(direction.x, direction.z), delta * 12)
		play_animation("Walk")
	else:
		play_animation("Idle")
	if position.y < -4:
		position = Vector3(0, 0.1, 14)
