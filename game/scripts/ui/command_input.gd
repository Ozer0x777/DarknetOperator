extends TextEdit
## Une commande logique, affichée sur plusieurs lignes sans défilement horizontal.
signal text_submitted(value: String)
var max_length: int = 16384
var secret: bool = false:
	set(value):
		secret = value
		add_theme_color_override("font_color", Color.TRANSPARENT if value else Color("dcdee4"))
		add_theme_color_override("font_selected_color", Color.TRANSPARENT if value else Color("dcdee4"))
		_update_mask()
## Mot de passe : une étoile par caractère, le texte réel reste invisible.
var _mask: Label
var caret_column: int:
	get: return get_caret_column()
	set(value): set_caret_column(value)

func _ready() -> void:
	_mask = Label.new()
	_mask.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_mask.clip_text = true
	_mask.add_theme_color_override("font_color", Color("dcdee4"))
	add_child(_mask)
	_update_mask()
	wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	scroll_fit_content_height = false
	custom_minimum_size.y = 32
	gui_input.connect(_submit_key)
	text_changed.connect(_changed)
	resized.connect(func() -> void: _fit_height.call_deferred(); _update_mask())

func _submit_key(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode in [KEY_ENTER, KEY_KP_ENTER]:
		if editable: text_submitted.emit(text)
		accept_event()

func _changed() -> void:
	if text.length() > max_length:
		text = text.left(max_length)
		set_caret_column(text.length())
	_update_mask()
	_fit_height.call_deferred()

func _process(_delta: float) -> void:
	# clear() et l’affectation de text n’émettent pas text_changed.
	if _mask != null and _mask.text.length() != text.length(): _update_mask()

func _update_mask() -> void:
	if _mask == null: return
	set_process(secret)
	_mask.visible = secret
	_mask.text = "*".repeat(text.length()) if secret else ""
	if has_theme_font("font"): _mask.add_theme_font_override("font", get_theme_font("font"))
	_mask.add_theme_font_size_override("font_size", get_theme_font_size("font_size"))
	var box: StyleBox = get_theme_stylebox("normal")
	_mask.position = Vector2(box.get_margin(SIDE_LEFT), box.get_margin(SIDE_TOP) + get_theme_constant("line_spacing") / 2.0)
	_mask.size = Vector2(maxf(size.x - _mask.position.x, 0), get_line_height())

func _fit_height() -> void:
	if not is_inside_tree(): return
	var rows: int = 1 if secret else get_line_wrap_count(0) + 1
	custom_minimum_size.y = clampf(rows * get_line_height() + 10, 32, 150)
