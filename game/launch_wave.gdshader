shader_type canvas_item;
uniform float greeting_time = 0.0;

void fragment() {
	// A compact region along the raised sleeve and paw, clear of the face and ear.
	vec2 shoulder = vec2(0.70, 0.57);
	vec2 paw = vec2(0.91, 0.37);
	vec2 axis = paw - shoulder;
	float along = clamp(dot(UV - shoulder, axis) / dot(axis, axis), 0.0, 1.0);
	float distance_to_arm = length(UV - (shoulder + axis * along));
	float weight = (1.0 - smoothstep(0.075, 0.135, distance_to_arm)) * smoothstep(0.05, 0.65, along);
	weight *= smoothstep(0.76, 0.84, UV.x);
	float progress = clamp(greeting_time / 2.4, 0.0, 1.0);
	float angle = sin(progress * 3.14159265) * sin(progress * 18.8495559) * 0.08 * weight;
	vec2 p = UV - shoulder;
	vec2 sample_uv = shoulder + mat2(vec2(cos(angle), -sin(angle)), vec2(sin(angle), cos(angle))) * p;
	COLOR = texture(TEXTURE, sample_uv);
}
