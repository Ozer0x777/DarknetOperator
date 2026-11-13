extends TextureRect
## Illustration orbitale rétro ; marge sombre pour les raccourcis du bureau.
func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	texture = load("res://assets/backgrounds/orbital-drift-desktop-v1.png")
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
