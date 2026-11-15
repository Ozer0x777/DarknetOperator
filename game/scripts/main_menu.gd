extends Control
const AudioSettings = preload("res://scripts/ui/audio_settings.gd")
const UI = preload("res://scripts/ui/style.gd")
const MenuStyle = preload("res://scripts/ui/menu_style.gd")
const Session = preload("res://scripts/session.gd")
const SaveManager = preload("res://scripts/ui/save_manager.gd")
var session: RefCounted
var desktop: Control
var menu: Control
var continue_button: Button
var new_button: Button
var saves_button: Button
var message: Label
var profile: Dictionary = {}
var new_dialog: Control
var handle_input: LineEdit
var mode_select: OptionButton
var _busy: bool = false
var _menu_margin: MarginContainer
var _menu_row: HBoxContainer
var _menu_left: VBoxContainer
var _brand_logo: TextureRect
var _spacers: Array[Control] = []

func _ready() -> void:
	get_node("/root/Audio").set_context("menu")
	get_window().title = "Darknet Operator"
	get_tree().auto_accept_quit = false
	_build()
	resized.connect(_resize_menu)
	_resize_menu()
	session = Session.new(self)
	session.failure.connect(func(text: String) -> void: message.text = text)
	if "--offline-test" in OS.get_cmdline_user_args(): return
	_set_busy(true)
	if await session.ensure_engine(): await refresh()
	_set_busy(false)

func _build() -> void:
	var theme_style: Theme = Theme.new()
	theme_style.default_font = UI.FONT
	theme_style.default_font_size = 17
	theme = theme_style
	menu = Control.new()
	menu.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(menu)
	var background: ColorRect = ColorRect.new()
	background.color = MenuStyle.BG
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	menu.add_child(background)
	for asset: String in ["res://assets/branding/darknet-operator-orbital-keyart-v2.png", "res://assets/branding/menu-orbital-shade-v2.svg"]:
		var layer: TextureRect = TextureRect.new()
		layer.texture = load(asset)
		layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		layer.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		layer.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED if asset.ends_with(".png") else TextureRect.STRETCH_SCALE
		layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
		menu.add_child(layer)

	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	menu.add_child(scroll)
	var margin: MarginContainer = MarginContainer.new()
	_menu_margin = margin
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for side: String in ["left", "right"]: margin.add_theme_constant_override("margin_" + side, 70)
	for side: String in ["top", "bottom"]: margin.add_theme_constant_override("margin_" + side, 52)
	scroll.add_child(margin)
	var row: HBoxContainer = HBoxContainer.new()
	_menu_row = row
	row.add_theme_constant_override("separation", 64)
	margin.add_child(row)
	var left: VBoxContainer = VBoxContainer.new()
	_menu_left = left
	left.custom_minimum_size.x = 420
	left.add_theme_constant_override("separation", 8)
	row.add_child(left)
	var eyebrow: Label = UI.label("D / O     -     CAMPAGNE SOLO", 13, MenuStyle.ACCENT)
	eyebrow.add_theme_font_override("font", UI.MONO)
	left.add_child(eyebrow)
	_space(left, 32)
	_brand_logo = TextureRect.new()
	var logo_source: Texture2D = load("res://assets/branding/darknet-operator-logo-v1.png")
	var logo_atlas: AtlasTexture = AtlasTexture.new()
	logo_atlas.atlas = logo_source
	var logo_size: Vector2 = logo_source.get_size()
	logo_atlas.region = Rect2(logo_size * Vector2(0.045, 0.27), logo_size * Vector2(0.91, 0.46))
	_brand_logo.texture = logo_atlas
	_brand_logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_brand_logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_brand_logo.custom_minimum_size.y = 122
	left.add_child(_brand_logo)
	_space(left, 14)
	left.add_child(UI.label("Observer. Comprendre. Décider.", 18, MenuStyle.MUTED))
	_space(left, 32)
	continue_button = MenuStyle.button("Continuer    →", _enter_game, true)
	new_button = MenuStyle.button("Nouvelle partie", func() -> void: new_dialog.show(); handle_input.grab_focus())
	saves_button = MenuStyle.button("Charger une sauvegarde", _show_saves)
	for button: Button in [continue_button, new_button, saves_button]:
		button.custom_minimum_size.y = 56
		left.add_child(button)
	_space(left, 14)
	left.add_child(MenuStyle.button("Paramètres", _settings))
	left.add_child(MenuStyle.button("Crédits", _credits))
	left.add_child(MenuStyle.button("Quitter", _quit))
	var spacer: Control = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	left.add_child(spacer)
	left.add_child(UI.label("VERSION %s  /  EN DÉVELOPPEMENT" % str(ProjectSettings.get_setting("application/config/version", "0.6.0")), 11, Color("686b75")))
	var right: VBoxContainer = VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(right)
	var breathing_room: Control = Control.new()
	breathing_room.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right.add_child(breathing_room)
	var card: PanelContainer = MenuStyle.panel(22)
	right.add_child(card)
	var summary: VBoxContainer = VBoxContainer.new()
	summary.add_theme_constant_override("separation", 10)
	card.add_child(summary)
	summary.add_child(UI.label("VOTRE CARRIÈRE", 12, MenuStyle.ACCENT))
	message = UI.label("Chargement de votre carrière…", 17, MenuStyle.WHITE)
	message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	message.custom_minimum_size.y = 54
	summary.add_child(message)
	new_dialog = Control.new()
	new_dialog.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	new_dialog.z_index = 20
	add_child(new_dialog)
	var dim: ColorRect = ColorRect.new()
	dim.color = Color(0.01, 0.02, 0.04, 0.94)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	new_dialog.add_child(dim)
	var center: CenterContainer = CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	new_dialog.add_child(center)
	var form: PanelContainer = MenuStyle.panel(28)
	form.custom_minimum_size = Vector2(620, 260)
	center.add_child(form)
	var fields: VBoxContainer = VBoxContainer.new()
	fields.add_theme_constant_override("separation", 18)
	form.add_child(fields)
	fields.add_child(UI.label("NOUVELLE CARRIÈRE", 26))
	var explanation: Label = UI.label("La carrière actuelle sera archivée dans un emplacement manuel. Choisis ton pseudo pour recommencer au tutoriel.", 16)
	explanation.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	fields.add_child(explanation)
	handle_input = LineEdit.new()
	handle_input.placeholder_text = "Pseudo : 3 à 24 caractères"
	handle_input.max_length = 24
	handle_input.custom_minimum_size.y = 42
	fields.add_child(handle_input)
	mode_select = OptionButton.new()
	mode_select.name = "PlayMode"
	mode_select.add_item("Campagne complète - prélude puis acte I")
	mode_select.add_item("Démo - trois exercices puis un dossier ouvert")
	mode_select.custom_minimum_size.y = 42
	mode_select.tooltip_text = "La démo conserve tes acquis pour poursuivre ensuite la campagne."
	fields.add_child(mode_select)
	var form_actions: HBoxContainer = HBoxContainer.new()
	fields.add_child(form_actions)
	form_actions.add_child(MenuStyle.button("Annuler", new_dialog.hide))
	form_actions.add_child(MenuStyle.button("Proposer un pseudo", _suggest_handle))
	form_actions.add_child(MenuStyle.button("Créer la partie", func() -> void: new_dialog.hide(); _new_game(), true))
	handle_input.text_submitted.connect(func(_text: String) -> void: new_dialog.hide(); _new_game())
	new_dialog.hide()
	continue_button.disabled = true

func _set_busy(value: bool) -> void:
	_busy = value
	new_button.disabled = value
	saves_button.disabled = value
	continue_button.disabled = value or not _has_career()
	MenuStyle.style_button(continue_button, _has_career())
	MenuStyle.style_button(new_button, not _has_career())

func _has_career() -> bool:
	return not profile.get("recovery_required", false) and (not str(profile.get("handle", "")).is_empty() or profile.get("has_active", false) or not profile.get("completed", []).is_empty())

func refresh() -> void:
	var result: Dictionary = await session.request("/api/saves")
	if result.has("error"): message.text = result.error; return
	profile = result.data.profile
	message.text = "%s · palier %s · %s ₵\n%s" % [profile.get("handle", "Nouvelle carrière"), int(profile.get("tier", 0)), int(profile.get("money", 100)), profile.get("active_contract", {}).get("title", "Bureau") if profile.get("active_contract") != null else "Aucune mission active"]
	if result.data.get("recovered", false): message.text += "\nLa copie précédente a été récupérée après une erreur de sauvegarde."
	if profile.get("recovery_required", false): message.text = "Carrière endommagée. Ouvre Sauvegardes / Charger pour récupérer un emplacement valide. Les fichiers d’origine sont conservés."
	_set_busy(false)
	if menu.visible: (continue_button if _has_career() else new_button).grab_focus()

func _new_game() -> void:
	if _busy: return
	_set_busy(true)
	var result: Dictionary = await session.request("/api/profile/new", {"handle": handle_input.text, "confirm": true, "play_mode": "demo" if mode_select.selected == 1 else "campaign"})
	_set_busy(false)
	if result.has("error"): message.text = result.error; return
	profile = result.data
	await _enter_game()

func _enter_game() -> void:
	if _busy or not _has_career(): return
	menu.hide()
	desktop = load("res://scenes/desktop.tscn").instantiate()
	desktop.external_engine = true
	desktop.engine_url = session.base_url
	desktop.auto_resume = profile.get("has_active", false)
	desktop.return_to_menu.connect(_leave_game)
	add_child(desktop)

func _leave_game() -> void:
	if is_instance_valid(desktop):
		desktop.queue_free()
		await get_tree().process_frame
	menu.show()
	get_node("/root/Audio").set_context("menu")
	await refresh()

func _show_saves() -> void:
	if _busy: return
	var manager: Control = SaveManager.new()
	manager.session = session
	manager.closed.connect(func() -> void: saves_button.grab_focus())
	manager.loaded.connect(func() -> void:
		manager.queue_free()
		await refresh()
		await _enter_game())
	add_child(manager)

func _settings() -> void:
	var dialog: AcceptDialog = AcceptDialog.new()
	dialog.title = "Paramètres"
	dialog.min_size = Vector2i(650, 400)
	dialog.dialog_text = ""
	var audio_scroll: ScrollContainer = ScrollContainer.new()
	audio_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	dialog.add_child(audio_scroll)
	audio_scroll.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	audio_scroll.offset_left = 20
	audio_scroll.offset_right = -20
	audio_scroll.offset_top = 16
	audio_scroll.offset_bottom = -65
	var audio_options: VBoxContainer = AudioSettings.new()
	audio_options.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	audio_scroll.add_child(audio_options)
	var button: Button = dialog.add_button("Plein écran / Fenêtre", false, "fullscreen")
	button.pressed.connect(func() -> void: DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN else DisplayServer.WINDOW_MODE_FULLSCREEN))
	add_child(dialog)
	dialog.popup_centered(Vector2i(650, 400))
	dialog.confirmed.connect(dialog.queue_free)
	dialog.canceled.connect(dialog.queue_free)

func _credits() -> void:
	var dialog: AcceptDialog = AcceptDialog.new()
	dialog.title = "Crédits"
	dialog.dialog_text = "Darknet Operator - projet en développement\nClient Godot · moteur local Python\nPolices et ressources : licences conservées dans game/assets.\nMusiques et effets originaux : compositions synthétisées pour le jeu.\n\nLe nom définitif et les crédits de publication seront complétés avant la sortie."
	add_child(dialog)
	dialog.popup_centered(Vector2i(650, 250))
	dialog.confirmed.connect(dialog.queue_free)

## Fermer le jeu ne doit jamais dépendre du moteur : on tente une sauvegarde,
## puis on quitte même si elle échoue. Une seconde demande quitte aussitôt.
var _quitting: bool = false

func _quit() -> void:
	if _quitting or session == null:
		get_tree().quit()
		return
	_quitting = true
	_set_busy(true)
	message.text = "Sauvegarde avant de quitter… (cliquer à nouveau pour quitter sans attendre)"
	var result: Dictionary = await session.request("/api/profile/menu", {})
	if result.has("error"): push_warning("Sauvegarde avant fermeture impossible : " + str(result.error))
	get_tree().quit()

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST: _quit()

func _exit_tree() -> void:
	if session != null: session.shutdown()


func _space(parent: VBoxContainer, height: float) -> void:
	var node: Control = Control.new()
	node.set_meta("original_height", height)
	node.custom_minimum_size.y = height
	_spacers.append(node)
	parent.add_child(node)


func _resize_menu() -> void:
	if _menu_margin == null: return
	var compact: bool = size.y < 820
	_menu_margin.custom_minimum_size.y = size.y
	for side: String in ["left", "right"]: _menu_margin.add_theme_constant_override("margin_" + side, 40 if compact else 70)
	for side: String in ["top", "bottom"]: _menu_margin.add_theme_constant_override("margin_" + side, 24 if compact else 52)
	_menu_row.add_theme_constant_override("separation", 32 if compact else 64)
	_menu_left.custom_minimum_size.x = 350 if compact else 420
	_menu_left.add_theme_constant_override("separation", 5 if compact else 8)
	_brand_logo.custom_minimum_size.y = 98 if compact else 122
	for spacer: Control in _spacers: spacer.custom_minimum_size.y = float(spacer.get_meta("original_height")) * (0.35 if compact else 1.0)
	for button: Node in _menu_left.get_children():
		if button is Button: button.custom_minimum_size.y = (44 if compact else 56) if button in [continue_button, new_button, saves_button] else (40 if compact else 48)

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE and new_dialog.visible:
		new_dialog.hide()
		new_button.grab_focus()
		get_viewport().set_input_as_handled()


func _suggest_handle() -> void:
	if _busy: return
	var result: Dictionary = await session.request("/api/handles")
	if not result.has("error") and not result.data.get("handles", []).is_empty():
		handle_input.text = result.data.handles[0]
		handle_input.grab_focus()
