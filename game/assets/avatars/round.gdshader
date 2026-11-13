shader_type canvas_item;
void fragment() {
    vec4 color = texture(TEXTURE, UV) * COLOR;
    color.a *= 1.0 - smoothstep(0.48, 0.50, length(UV - vec2(0.5)));
    COLOR = color;
}
