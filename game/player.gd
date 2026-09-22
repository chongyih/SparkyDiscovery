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
	if skeleton:
		merge_parts()

## The model arrives as 41 skinned parts (59 draw calls). They share one skeleton and skin,
## so parts with the same material merge into one surface without changing the look.
func merge_parts() -> void:
	var skin: Skin
	var groups := {"Body": {}, "Fur": {}}
	for mesh in skeleton.get_children():
		if not mesh is MeshInstance3D:
			continue
		skin = mesh.skin
		var group: Dictionary = groups["Fur" if "pile" in mesh.name.to_lower() else "Body"]
		for i in mesh.mesh.get_surface_count():
			var mat: Material = mesh.get_active_material(i)
			if not group.has(mat):
				var surface := SurfaceTool.new()
				surface.begin(Mesh.PRIMITIVE_TRIANGLES)
				surface.set_material(mat)
				group[mat] = surface
			group[mat].append_from(mesh.mesh, i, mesh.transform)
		mesh.free()
	for group_name in groups:
		var merged := ArrayMesh.new()
		for surface: SurfaceTool in groups[group_name].values():
			surface.commit(merged)
		var part := MeshInstance3D.new()
		part.name = group_name
		part.mesh = merged
		part.skin = skin
		part.skeleton = NodePath("..")
		skeleton.add_child(part)
	var fur := skeleton.get_node("Fur") as MeshInstance3D
	# The fibres should not produce thousands of tiny fur shadows.
	fur.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# Past the 8 m gameplay zoom the fibres are sub-pixel; drop them in the distant menu shot.
	fur.visibility_range_end = 14.0

## Soft contact shadow for renderers where the sun casts no shadow.
func add_blob_shadow() -> void:
	var gradient := Gradient.new()
	gradient.set_color(0, Color(0, 0, 0, 0.42))
	gradient.set_color(1, Color(0, 0, 0, 0))
	var texture := GradientTexture2D.new()
	texture.gradient = gradient
	texture.fill = GradientTexture2D.FILL_RADIAL
	texture.fill_from = Vector2(0.5, 0.5)
	texture.fill_to = Vector2(0.5, 0.0)
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_texture = texture
	var plane := PlaneMesh.new()
	plane.size = Vector2(1.1, 1.1)
	var blob := MeshInstance3D.new()
	blob.name = "BlobShadow"
	blob.mesh = plane
	blob.material_override = mat
	blob.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# Sit just above the ground so the kerb and road do not flicker through it.
	blob.position.y = 0.02
	add_child(blob)

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
