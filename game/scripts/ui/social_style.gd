extends RefCounted
## Thème limité aux espaces sociaux : lecture, contraste et états interactifs.
const UI = preload("res://scripts/ui/style.gd")

static func apply(control: Control, surface: Color, accent: Color) -> void:
	var skin: Theme = Theme.new()
	skin.default_font = UI.FONT
	skin.default_font_size = 14
	skin.set_color("font_color", "Label", Color("e3e7ed"))
	skin.set_color("font_color", "Button", Color("e3e7ed"))
	skin.set_color("font_hover_color", "Button", Color.WHITE)
	skin.set_color("font_pressed_color", "Button", Color.WHITE)
	skin.set_color("font_disabled_color", "Button", Color("83909e"))
	skin.set_constant("line_separation", "RichTextLabel", 4)
	skin.set_constant("line_spacing", "TextEdit", 3)
	skin.set_stylebox("separator", "HSeparator", UI.box(surface.lightened(0.09)))
	skin.set_constant("separation", "HSeparator", 1)
	var track: StyleBoxFlat = UI.box(Color.TRANSPARENT)
	track.content_margin_left = 3
	track.content_margin_right = 3
	skin.set_stylebox("scroll", "VScrollBar", track)
	for state: String in ["grabber", "grabber_highlight", "grabber_pressed"]:
		var thumb: StyleBoxFlat = UI.box(surface.lightened(0.18) if state == "grabber" else accent.darkened(0.35), Color.TRANSPARENT, 3)
		thumb.content_margin_left = 3
		thumb.content_margin_right = 3
		skin.set_stylebox(state, "VScrollBar", thumb)
	control.theme = skin

static func divider(accent: Color) -> StyleBoxFlat:
	var result: StyleBoxFlat = UI.box(accent)
	result.content_margin_top = 1
	return result
