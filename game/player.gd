extends CharacterBody3D

const SPEED := 4.2
var enabled := false
var visual: Node3D
var animator: AnimationPlayer
var camera: Camera3D
var seated := false
var skeleton: Skeleton3D

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
	if skeleton:
		for bone_name in ["leg.L", "leg.R"]:
			var bone := skeleton.find_bone(bone_name)
			if bone >= 0:
				var rest_basis := skeleton.get_bone_global_rest(bone).basis
				var axis := (rest_basis.inverse() * Vector3.RIGHT).normalized()
				var rest_rotation := skeleton.get_bone_rest(bone).basis.get_rotation_quaternion()
				skeleton.set_bone_pose_rotation(bone, rest_rotation * Quaternion(axis, deg_to_rad(-75.0)))
		var head_bone := skeleton.find_bone("head")
		if head_bone >= 0:
			# A small glance towards the gathering keeps both eyes readable in the wide shot.
			skeleton.set_bone_pose_rotation(head_bone, Quaternion(Vector3.UP, -0.35))

func _physics_process(delta: float) -> void:
	if seated:
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
