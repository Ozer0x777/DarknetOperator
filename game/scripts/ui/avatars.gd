extends RefCounted
const PORTRAITS = {"k0rvid":"res://assets/avatars/k0rvid-v1.png", "miette":"res://assets/avatars/miette-v1.png", "sable":"res://assets/avatars/sable-v1.png"}

static func apply(panel: PanelContainer, handle: String, rounded: bool = false) -> void:
	for child: Node in panel.get_children():
		if child is TextureRect:
			panel.remove_child(child)
			child.queue_free()
	var label: Label = panel.get_child(0) if panel.get_child_count() > 0 else null
	if label != null: label.visible = not PORTRAITS.has(handle)
	if not PORTRAITS.has(handle): return
	var portrait: TextureRect = TextureRect.new()
	portrait.name = "Portrait"
	portrait.texture = load(PORTRAITS[handle])
	portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	if rounded:
		var material: ShaderMaterial = ShaderMaterial.new()
		material.shader = load("res://assets/avatars/round.gdshader")
		portrait.material = material
		portrait.set_meta("round_avatar", true)
	portrait.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.clip_contents = true
	panel.add_child(portrait)
