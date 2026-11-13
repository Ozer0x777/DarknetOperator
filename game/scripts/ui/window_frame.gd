extends PanelContainer
## Fenêtre intégrée : déplacements, redimensionnement, focus et contrôles Xfwm.
const UI = preload("res://scripts/ui/style.gd")
signal activated
signal minimized
signal closed
var body: VBoxContainer
var title_label: Label
var app_id: String
var workspace: int = 0
var opened: bool = false
var minimized_state: bool = false
var maximized: bool = false
var min_size: Vector2i = Vector2i(480, 300)
var _restore: Rect2
var _drag: bool = false
var _resize: bool = false
var _origin: Vector2
var _start: Rect2
var _edge: Vector2i
var _title: PanelContainer
var _resize_handles: Array[Control] = []

func setup(id: String, title: String, icon_name: String, dimensions: Vector2i) -> VBoxContainer:
	app_id = id
	get_parent_control().resized.connect(_parent_resized)
	name = id
	focus_mode = Control.FOCUS_ALL
	custom_minimum_size = Vector2(min_size)
	size = dimensions
	var border: StyleBoxFlat = UI.box(Color("22242e"), Color("101116"), 4, 1)
	border.shadow_color = Color(0, 0, 0, 0.38)
	border.shadow_size = 16
	border.shadow_offset = Vector2(0, 5)
	add_theme_stylebox_override("panel", border)
	var column: VBoxContainer = VBoxContainer.new()
	column.add_theme_constant_override("separation", 0)
	add_child(column)
	_title = UI.panel(Color("282a36"), 0, 3)
	_title.custom_minimum_size.y = 30
	_title.mouse_filter = Control.MOUSE_FILTER_STOP
	_title.gui_input.connect(_title_input)
	column.add_child(_title)
	var row: HBoxContainer = HBoxContainer.new()
	row.mouse_filter = Control.MOUSE_FILTER_PASS
	row.add_theme_constant_override("separation", 2)
	_title.add_child(row)
	var image: TextureRect = UI.icon(icon_name, 19)
	image.custom_minimum_size.x = 28
	row.add_child(image)
	title_label = UI.label(title, 13)
	title_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(title_label)
	for entry: Array in [["−", minimize_window], ["□", toggle_maximize], ["×", close_window]]:
		var b: Button = UI.button(entry[0], entry[1], Color("282a36"), 0)
		b.custom_minimum_size = Vector2(29, 28)
		b.focus_mode = Control.FOCUS_NONE
		row.add_child(b)
	var content: PanelContainer = UI.panel(Color("23252f"))
	content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(content)
	body = VBoxContainer.new()
	body.add_theme_constant_override("separation", 0)
	content.add_child(body)
	_build_resize_handles()
	visible = false
	return body

func _build_resize_handles() -> void:
	# PanelContainer étire tous ses enfants Control. Seul cet overlay doit
	# occuper le cadre ; ses enfants restent positionnés sur les bordures.
	var overlay: Control = Control.new()
	overlay.name = "ResizeOverlay"
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(overlay)
	for edge: Vector2i in [Vector2i(-1, -1), Vector2i(0, -1), Vector2i(1, -1), Vector2i(-1, 0), Vector2i(1, 0), Vector2i(-1, 1), Vector2i(0, 1), Vector2i(1, 1)]:
		var handle: Control = Control.new()
		handle.mouse_filter = Control.MOUSE_FILTER_STOP
		overlay.add_child(handle)
		_resize_handles.append(handle)
		if edge.x == 0:
			handle.anchor_right = 1
			handle.offset_left = 7
			handle.offset_right = -7
		elif edge.x == 1:
			handle.anchor_left = 1
			handle.anchor_right = 1
			handle.offset_left = -6
		else:
			handle.offset_right = 6
		if edge.y == 0:
			handle.anchor_bottom = 1
			handle.offset_top = 7
			handle.offset_bottom = -7
		elif edge.y == 1:
			handle.anchor_top = 1
			handle.anchor_bottom = 1
			handle.offset_top = -6
		else:
			handle.offset_bottom = 6
		handle.mouse_default_cursor_shape = Control.CURSOR_HSIZE if edge.y == 0 else (Control.CURSOR_VSIZE if edge.x == 0 else (Control.CURSOR_FDIAGSIZE if edge.x == edge.y else Control.CURSOR_BDIAGSIZE))
		handle.gui_input.connect(func(event: InputEvent) -> void: _resize_input(event, edge))

func open_window(on_workspace: int) -> void:
	workspace = on_workspace
	opened = true
	minimized_state = false
	show()
	focus_window()

func focus_window() -> void:
	move_to_front()
	grab_focus()
	activated.emit()

func minimize_window() -> void:
	minimized_state = true
	hide()
	minimized.emit()

func close_window() -> void:
	opened = false
	minimized_state = false
	hide()
	closed.emit()

func work_area() -> Rect2:
	return Rect2(Vector2(0, 32), get_parent_control().size - Vector2(0, 32))

func toggle_maximize() -> void:
	if maximized:
		position = _restore.position
		size = _restore.size
	else:
		_restore = Rect2(position, size)
		var area: Rect2 = work_area()
		position = area.position
		size = area.size
	maximized = not maximized
	for handle: Control in _resize_handles:
		handle.mouse_filter = Control.MOUSE_FILTER_IGNORE if maximized else Control.MOUSE_FILTER_STOP
	focus_window()

func _title_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		focus_window()
		if event.double_click and event.pressed:
			toggle_maximize()
		elif event.pressed and not maximized:
			_drag = true
			_origin = get_global_mouse_position()
			_start = Rect2(position, size)

func _resize_input(event: InputEvent, edge: Vector2i) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed and not maximized:
		focus_window()
		_resize = true
		_edge = edge
		_origin = get_global_mouse_position()
		_start = Rect2(position, size)

func _input(event: InputEvent) -> void:
	if not visible:
		return
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var hovered: Control = get_viewport().gui_get_hovered_control()
		if hovered == self or (hovered != null and is_ancestor_of(hovered)):
			focus_window()
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and not event.pressed:
		_drag = false
		_resize = false
	if event is InputEventMouseMotion:
		var delta: Vector2 = get_global_mouse_position() - _origin
		if _drag:
			position = _start.position + delta
			position.x = clampf(position.x, -size.x + 120, get_parent_control().size.x - 120)
			position.y = clampf(position.y, 32, get_parent_control().size.y - 35)
			get_viewport().set_input_as_handled()
		elif _resize:
			var new_size: Vector2 = _start.size + delta * Vector2(_edge)
			if _edge.x != 0:
				size.x = maxf(min_size.x, new_size.x)
				if _edge.x == -1:
					position.x = _start.end.x - size.x
			if _edge.y != 0:
				size.y = maxf(min_size.y, new_size.y)
				if _edge.y == -1:
					position.y = _start.end.y - size.y
			get_viewport().set_input_as_handled()

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		focus_window()

func _parent_resized() -> void:
	if maximized:
		var area: Rect2 = work_area()
		position = area.position
		size = area.size
	elif opened:
		position.x = minf(position.x, get_parent_control().size.x - 120)
		position.y = clampf(position.y, 32, get_parent_control().size.y - 35)
