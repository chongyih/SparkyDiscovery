extends SkeletonModifier3D
## Additive poses after imported animation; the pail handle follows the right mitten.
var carry := 0.0
var crouch := 0.0
var quiet := 0.0
var prop: Node3D
var carry_rotation := Quaternion.IDENTITY
var hand_position := Vector3.ZERO

func _process_modification() -> void:
	var rig := get_skeleton()
	for bone_name in ["arm.R", "arm.L", "head"]:
		var bone := rig.find_bone(bone_name)
		if bone < 0: continue
		var rest := rig.get_bone_rest(bone).basis.get_rotation_quaternion()
		var axis := (rig.get_bone_global_rest(bone).basis.inverse() * Vector3.RIGHT).normalized()
		var current := rig.get_bone_pose_rotation(bone)
		if bone_name == "arm.R":
			current = current.slerp(carry_rotation, carry)
		elif bone_name == "arm.L":
			current = current.slerp(rest * Quaternion(axis, -1.3), crouch)
		else:
			current = current * Quaternion(Vector3.RIGHT, crouch * 0.3 + quiet * 0.13)
		rig.set_bone_pose_rotation(bone, current)
	var arm := rig.find_bone("arm.R")
	var palm := rig.get_bone_global_rest(arm).affine_inverse() * Vector3(-0.93, 0.85, 0.006)
	hand_position = rig.global_transform * (rig.get_bone_global_pose(arm) * palm)
	if is_instance_valid(prop) and prop.visible:
		prop.global_position = hand_position - Vector3.UP * 0.52

func carry_hand_world() -> Vector3:
	# Sample the current transform directly: the last rendered position can be stale
	# after a checkpoint restore or a camera-staging reposition in this same frame.
	var rig := get_skeleton()
	var arm := rig.find_bone("arm.R")
	var parent := rig.get_bone_parent(arm)
	var arm_pose := Transform3D(Basis(carry_rotation), rig.get_bone_pose_position(arm))
	var arm_global := rig.get_bone_global_pose(parent) * arm_pose
	var palm := rig.get_bone_global_rest(arm).affine_inverse() * Vector3(-0.93, 0.85, 0.006)
	return rig.global_transform * (arm_global * palm)
