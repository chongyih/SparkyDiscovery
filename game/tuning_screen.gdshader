shader_type spatial;
render_mode unshaded, cull_disabled;
uniform float clarity : hint_range(0.0, 1.0) = 0.0;
void fragment() {
	vec2 uv = UV;
	float noise = fract(sin(dot(floor(uv * vec2(180.0, 120.0)), vec2(12.9898, 78.233)) + floor(TIME * 18.0)) * 43758.5453);
	float wobble = sin(uv.y * 22.0 + TIME * 8.0) * (1.0 - clarity) * 0.15;
	// An abstract monochrome tuning pattern; archival footage starts after seating.
	float bars = 0.2 + floor(clamp(uv.x + wobble, 0.0, 0.99) * 6.0) / 7.0;
	float pattern = mix(bars, 0.7, step(0.72, uv.y));
	float shade = mix(noise, pattern, clarity);
	shade *= 0.92 + 0.08 * sin(uv.y * 380.0);
	ALBEDO = vec3(shade) * vec3(0.88, 1.0, 0.92);
}
