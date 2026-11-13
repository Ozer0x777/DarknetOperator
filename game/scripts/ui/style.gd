extends RefCounted
## Primitives communes ; les applications définissent ensuite leurs propres thèmes.
const FONT = preload("res://assets/fonts/Cantarell.otf")
const MONO = preload("res://assets/fonts/DejaVuSansMono.ttf")

static func box(color: Color, border: Color = Color.TRANSPARENT, radius: int = 0, padding: int = 0) -> StyleBoxFlat:
	var s: StyleBoxFlat = StyleBoxFlat.new()
	s.bg_color = color
	s.border_color = border
	s.set_border_width_all(1 if border.a > 0 else 0)
	s.set_corner_radius_all(radius)
	s.set_content_margin_all(padding)
	return s

static func label(text: String, size: int = 14, color: Color = Color("dcdee4")) -> Label:
	var n: Label = Label.new()
	n.text = text
	n.add_theme_font_size_override("font_size", size)
	n.add_theme_color_override("font_color", color)
	n.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return n

static func button(text: String, action: Callable, color: Color = Color("30323c"), padding: int = 8) -> Button:
	var n: Button = Button.new()
	n.text = text
	n.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	n.add_theme_stylebox_override("normal", box(color, Color.TRANSPARENT, 3, padding))
	n.add_theme_stylebox_override("hover", box(color.lightened(0.15), Color.TRANSPARENT, 3, padding))
	n.add_theme_stylebox_override("pressed", box(color.lightened(0.22), Color.TRANSPARENT, 3, padding))
	n.add_theme_stylebox_override("focus", box(Color.TRANSPARENT, Color("a4c8f2"), 4, padding))
	n.add_theme_stylebox_override("disabled", box(color.darkened(0.18), Color.TRANSPARENT, 3, padding))
	n.add_theme_color_override("font_disabled_color", Color("9ca6b3"))
	n.pressed.connect(action)
	return n

static func panel(color: Color, padding: int = 0, radius: int = 0) -> PanelContainer:
	var n: PanelContainer = PanelContainer.new()
	n.add_theme_stylebox_override("panel", box(color, Color.TRANSPARENT, radius, padding))
	return n

static func icon(name: String, size: int = 24) -> TextureRect:
	var n: TextureRect = TextureRect.new()
	n.texture = load("res://assets/icons/%s.svg" % name)
	n.custom_minimum_size = Vector2(size, size)
	n.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	n.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	n.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return n

static func rich(text: String = "", size: int = 14, color: Color = Color("dcdee4")) -> RichTextLabel:
	var n: RichTextLabel = RichTextLabel.new()
	n.text = text
	n.fit_content = true
	n.scroll_active = false
	n.selection_enabled = true
	# Le clic donne le focus : Ctrl+C copie la sélection vers le presse-papiers du système.
	n.focus_mode = Control.FOCUS_CLICK
	n.bbcode_enabled = false
	n.add_theme_color_override("default_color", color)
	n.add_theme_font_size_override("normal_font_size", size)
	n.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	copy_menu(n)
	return n

## Clic droit : Copier (la sélection, ou tout le texte sans sélection) et Tout sélectionner.
static func copy_menu(n: RichTextLabel) -> void:
	var menu: PopupMenu = PopupMenu.new()
	menu.add_item("Copier", 0)
	menu.add_item("Tout sélectionner", 1)
	n.add_child(menu)
	menu.id_pressed.connect(func(id: int) -> void:
		if id == 1:
			n.grab_focus()
			n.select_all()
			return
		var text: String = n.get_selected_text()
		DisplayServer.clipboard_set(text if not text.is_empty() else n.get_parsed_text()))
	n.gui_input.connect(func(event: InputEvent) -> void:
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
			menu.position = Vector2i(n.get_screen_position() + event.position)
			menu.popup()
			n.accept_event())

static func clear(parent: Node) -> void:
	for child: Node in parent.get_children():
		parent.remove_child(child)
		child.queue_free()

static func field(control: Control, color: Color, accent: Color) -> void:
	control.add_theme_stylebox_override("normal", box(color, color.lightened(0.12), 6, 9))
	control.add_theme_stylebox_override("focus", box(Color.TRANSPARENT, accent, 6, 9))
	control.add_theme_color_override("font_color", Color("e2e7ed"))
	control.add_theme_color_override("font_placeholder_color", Color("a8b2bf"))
	control.add_theme_color_override("caret_color", accent.lightened(0.3))
	control.add_theme_color_override("selection_color", Color(accent, 0.35))

static func wrapped(text: String, size: int = 14, color: Color = Color("dcdee4")) -> Label:
	var result: Label = label(text, size, color)
	result.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return result

static func badge(text: String, accent: Color) -> PanelContainer:
	var result: PanelContainer = panel(accent.darkened(0.78), 5, 4)
	result.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	result.add_child(label(text, 10, accent.lightened(0.25)))
	return result

static func icon_button(name: String, tooltip: String, action: Callable, color: Color) -> Button:
	var result: Button = button("", action, color, 6)
	result.icon = load("res://assets/icons/%s.svg" % name)
	result.add_theme_constant_override("icon_max_width", 19)
	result.custom_minimum_size = Vector2(32, 32)
	result.tooltip_text = tooltip
	return result
