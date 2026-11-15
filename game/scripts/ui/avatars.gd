extends RefCounted
const PORTRAITS = {
  "bytewarden": "res://assets/avatars/bytewarden-orbital-v1.png",
  "mod_echo": "res://assets/avatars/mod_echo-orbital-v1.png",
  "nullpointer": "res://assets/avatars/nullpointer-orbital-v1.png",
  "packetloss": "res://assets/avatars/packetloss-orbital-v1.png",
  "relay": "res://assets/avatars/relay-orbital-v1.png",
  "spectre": "res://assets/avatars/spectre-orbital-v1.png",
  "hexane": "res://assets/avatars/hexane-orbital-v1.png",
  "nullroute": "res://assets/avatars/nullroute-orbital-v1.png",
  "0xvanta": "res://assets/avatars/0xvanta-orbital-v1.png",
  "hexcache": "res://assets/avatars/hexcache-orbital-v1.png",
  "cendre": "res://assets/avatars/cendre-orbital-v1.png",
  "traverse": "res://assets/avatars/traverse-orbital-v1.png",
  "iris": "res://assets/avatars/iris-orbital-v1.png",
  "quartz": "res://assets/avatars/quartz-orbital-v1.png",
  "k0rvid": "res://assets/avatars/k0rvid-orbital-v1.png",
  "miette": "res://assets/avatars/miette-orbital-v1.png",
  "sable": "res://assets/avatars/sable-orbital-v1.png",
  "Madame_TLS": "res://assets/avatars/madame-tls-orbital-v2.png",
  "urgent_client_01": "res://assets/avatars/urgent_client_01-orbital-v1.png"
}

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
