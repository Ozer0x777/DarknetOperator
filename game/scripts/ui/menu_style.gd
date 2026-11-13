extends RefCounted
const UI = preload("res://scripts/ui/style.gd")
const BG = Color("111215")
const SURFACE = Color("172126")
const BORDER = Color("30484d")
const ACCENT = Color("83ddc6")
const WHITE = Color("edf5f1")
const MUTED = Color("a2b6b8")

static func panel(padding: int = 28) -> PanelContainer:
	var node: PanelContainer = UI.panel(SURFACE, padding, 4)
	node.add_theme_stylebox_override("panel", UI.box(SURFACE, BORDER, 4, padding))
	return node

static func style_button(node: Button, primary: bool = false) -> void:
	node.add_theme_stylebox_override("normal", UI.box(ACCENT if primary else Color.TRANSPARENT, Color.TRANSPARENT, 3, 18))
	node.add_theme_stylebox_override("hover", UI.box(ACCENT.lightened(0.12) if primary else Color("292b31"), Color.TRANSPARENT, 3, 18))
	node.add_theme_stylebox_override("pressed", UI.box(ACCENT.darkened(0.12) if primary else Color("34363d"), Color.TRANSPARENT, 3, 18))
	node.add_theme_stylebox_override("disabled", UI.box(Color("191a1e"), Color.TRANSPARENT, 3, 18))
	node.add_theme_stylebox_override("focus", UI.box(Color.TRANSPARENT, WHITE, 3, 3))
	for key: String in ["font_color", "font_hover_color", "font_pressed_color"]:
		node.add_theme_color_override(key, BG if primary else WHITE)
	node.add_theme_color_override("font_disabled_color", Color("53555f"))
	for key: String in ["normal", "hover", "pressed", "disabled"]:
		var style: StyleBox = node.get_theme_stylebox(key)
		style.content_margin_top = 10
		style.content_margin_bottom = 10

static func button(text: String, action: Callable, primary: bool = false) -> Button:
	var node: Button = UI.button(text, action)
	node.custom_minimum_size.y = 48
	node.alignment = HORIZONTAL_ALIGNMENT_LEFT
	style_button(node, primary)
	return node
