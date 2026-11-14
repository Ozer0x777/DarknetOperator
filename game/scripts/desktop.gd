extends Control
signal return_to_menu
var external_engine: bool = false
var engine_url: String = ""
var auto_resume: bool = false
var _seen_forum_messages: Dictionary = {}
var _social_ready: bool = false
var _message_notifications: Dictionary = {}
var _notification_cooldown: float = 0.0
var _hint_busy: bool = false
## Bureau natif inspiré de Xfce : fenêtres, panneau, applications et terminal.
const Session = preload("res://scripts/session.gd")
const UI = preload("res://scripts/ui/style.gd")
const DesktopWindow = preload("res://scripts/ui/window_frame.gd")
const Wallpaper = preload("res://scripts/ui/wallpaper.gd")
const Messenger = preload("res://scripts/ui/messenger.gd")
const AudioSettings = preload("res://scripts/ui/audio_settings.gd")
const Wallet = preload("res://scripts/ui/wallet.gd")
const Forum = preload("res://scripts/ui/forum.gd")
const GophishView = preload("res://scripts/ui/gophish.gd")
const TerminalView = preload("res://scripts/ui/terminal_view.gd")
const FileManager = preload("res://scripts/ui/file_manager.gd")
const INK: Color = Color("0c111b")
const PANEL: Color = Color("282a36")
const ACCENT: Color = Color("45b6eb")
const MUTED: Color = Color("8b9bb0")
var session: RefCounted
var apps: Dictionary = {}
var terminal_views: Dictionary = {}
var console_apps: Dictionary = {}
var console_counter: int = 1
var tools_catalog: RichTextLabel
var gophish_view: GophishView
var _gophish_busy: bool = false
var terminal: RichTextLabel
var terminal_input: TextEdit
var messengers: Dictionary = {}
var wallet_view: Wallet
var _wallet_busy: bool = false
var forum_view: Forum
var workspace: int = 0
var active_app: String = ""
var taskbar: HBoxContainer
var workspace_buttons: Array[Button] = []
var tasks: Dictionary = {}
var unread_counts: Dictionary = {}
var _applications: PanelContainer
var _application_list: VBoxContainer
var _application_search: LineEdit
var _toast: PanelContainer
var _top_panel: PanelContainer
var _toast_timer: float = 0.0
var _pending_music: String = ""
var _showing_desktop: bool = false
var _desktop_restored: Array[String] = []
var _context: PopupMenu
var _terminal_context: Label
var network: Tree
var files: FileManager
var report: RichTextLabel
var profile_label: Label
var route_label: Label
var clock: Label
var notification: Label
var paused: bool = false
var _last_outcome: String = ""
var _last_messages: int = 0
var _profile: Dictionary = {}
var shop: VBoxContainer
var _guidance: CheckButton
var _world_time: String = ""
var resume_button: Button
var objectives_text: RichTextLabel
var operation_specs: Array = []
var routes: OptionButton

func _ready() -> void:
	get_node("/root/Audio").set_context("desktop")
	get_viewport().gui_embed_subwindows = true
	_build_theme()
	_build_desktop()
	session = Session.new(self)
	if not engine_url.is_empty(): session.base_url = engine_url
	session.updated.connect(_update_state)
	session.social_updated.connect(_update_social)
	session.terminal_output.connect(_console_output)
	session.completion_ready.connect(func(id: String, result: Dictionary) -> void:
		if terminal_views.has(id): terminal_views[id].apply_completion(result))
	session.failure.connect(_error)
	session.context_updated.connect(_console_context)
	session.open_url.connect(_open_service)
	for messenger: Messenger in messengers.values():
		messenger.mission_requested.connect(_accept)
		messenger.hint_requested.connect(_request_mission_hint)
	get_node("/root/Audio").track_changed.connect(_music_changed)
	_music_changed(get_node("/root/Audio").current_track)
	_load_identity()
	if "--offline-test" in OS.get_cmdline_user_args():
		return
	if not external_engine and not await session.ensure_engine():
		_open("Terminal")
		return
	if await session.bootstrap():
		if not _profile.get("handle", "").is_empty():
			session.handle = _profile.handle
		var specs: Dictionary = await session.request("/api/abilities", null, TYPE_ARRAY)
		if not specs.has("error"):
			operation_specs = specs.data
		await session.request("/api/profile/enroll", {})
		await _refresh_profile()
		_render_board()
		var intro: String = "k0rvid · Salut. J'ai un premier job pour toi. Ouvre BreachBoard pour consulter l'annonce du cabinet Ravelle."
		if int(_profile.get("campaign_version", 1)) < 3 and "tuto_p0" not in _profile.get("completed", []) and not _profile.get("has_active", false):
			if not _profile.get("forum_unlocked", true): intro = "Salut. On commence ici, en privé. Je te propose de petits dossiers pour voir comment tu travailles ; le forum viendra ensuite. Ouvre le dossier proposé dans notre conversation."
			messengers.chordly.add_message({"id": "intro:k0rvid", "sender": "k0rvid", "peer": "k0rvid", "text": intro, "link": _profile.get("forum_unlocked", true)}, false)
			_notify("Nouveau message de k0rvid · Chordly", "Chordly")
		for messenger: Messenger in messengers.values():
			messenger.set_identity(session.handle)
		await _load_messages()
		await session.refresh_social()
		profile_label.text = session.handle
		_open("BreachBoard" if _profile.get("forum_unlocked", true) else "Chordly")
		_save_identity()
		if auto_resume and _profile.get("has_active", false): await _resume_saved()
		else:
			var saved_workspace: Dictionary = await session.request("/api/workspace/state")
			if not saved_workspace.has("error"):
				_restore_console_windows(saved_workspace.data)
				route_label.text = "Bureau · aucune mission active"
	else:
		_open("Terminal")

func _process(delta: float) -> void:
	if session != null:
		session.poll(delta)
	clock.text = Time.get_time_string_from_system().substr(0, 5) if _world_time.is_empty() else _world_time.right(5)
	clock.tooltip_text = "Horloge du monde · " + _world_time + " · 1 minute pour 6 secondes"
	_notification_cooldown = maxf(0, _notification_cooldown - delta)
	if _notification_cooldown <= 0 and not _message_notifications.is_empty(): _flush_message_notifications()
	if not _pending_music.is_empty() and not _toast.visible and _message_notifications.is_empty():
		_notify("♪ Lecture : " + _pending_music, "Lecteur audio", false)
		_pending_music = ""
	if _toast_timer > 0:
		_toast_timer -= delta
		if _toast_timer <= 0:
			_toast.hide()

func _box(color: Color, border: Color = Color.TRANSPARENT, radius: int = 6) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = color
	style.border_color = border
	style.set_border_width_all(1)
	style.set_corner_radius_all(radius)
	style.content_margin_left = 14
	style.content_margin_right = 14
	style.content_margin_top = 9
	style.content_margin_bottom = 9
	return style

func _build_theme() -> void:
	var t: Theme = Theme.new()
	t.default_font = UI.FONT
	t.default_font_size = 14
	t.set_color("font_color", "Label", Color("dce6f2"))
	t.set_color("default_color", "RichTextLabel", Color("c4d3e6"))
	t.set_stylebox("panel", "PanelContainer", _box(PANEL, Color("263447")))
	t.set_stylebox("normal", "Button", _box(Color("1c2a3b"), Color("314760")))
	t.set_stylebox("hover", "Button", _box(Color("263c53"), ACCENT))
	t.set_stylebox("pressed", "Button", _box(Color("163e58"), ACCENT))
	t.set_stylebox("disabled", "Button", _box(Color("19202a")))
	t.set_color("font_disabled_color", "Button", Color("637083"))
	t.set_stylebox("normal", "LineEdit", _box(INK, Color("293e56")))
	t.set_stylebox("focus", "LineEdit", _box(INK, ACCENT))
	t.set_color("font_color", "LineEdit", Color("d6e9ee"))
	t.set_color("caret_color", "LineEdit", ACCENT)
	t.set_stylebox("panel", "Tree", _box(INK))
	t.set_stylebox("embedded_border", "Window", _box(Color("282a36"), Color("3a526d")))
	t.set_constant("embedded_border", "Window", 3)
	t.set_constant("title_height", "Window", 34)
	t.set_font_size("title_font_size", "Window", 15)
	theme = t

func _label(text: String, font_size: int = 15, color: Color = Color("dce6f2")) -> Label:
	var node: Label = Label.new()
	node.text = text
	node.add_theme_font_size_override("font_size", font_size)
	node.add_theme_color_override("font_color", color)
	return node

func _button(text: String, callback: Callable) -> Button:
	var node: Button = Button.new()
	node.text = text
	node.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	node.pressed.connect(callback)
	return node

func _build_desktop() -> void:
	var wallpaper: Control = Wallpaper.new()
	wallpaper.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(wallpaper)
	_build_panel()
	_build_icons()
	_build_applications_menu()
	_build_notifications()
	_build_terminal()
	for entry: Array in [["chordly", "Chordly"], ["telegrid", "Telegrid"], ["sessyon", "Sessyon"]]:
		var body: VBoxContainer = _window(entry[1], Vector2i(210, 100), Vector2i(1010, 650))
		var messenger: Messenger = Messenger.new()
		body.add_child(messenger)
		messenger.setup(entry[0], "operator")
		messenger.send_message.connect(_send_message)
		messenger.conversation_read.connect(_read_conversation)
		messenger.open_app.connect(_open)
		messenger.continue_campaign.connect(_continue_campaign)
		var app_name: String = entry[1]
		messenger.unread_changed.connect(func(count: int) -> void: _unread_changed(app_name, count))
		messengers[entry[0]] = messenger
	var forum_content: VBoxContainer = _window("BreachBoard", Vector2i(170, 70), Vector2i(1100, 730))
	resume_button = _button("Reprendre la mission sauvegardée", _resume_saved)
	resume_button.visible = false
	forum_content.add_child(resume_button)
	forum_view = Forum.new()
	if "--offline-test" not in OS.get_cmdline_user_args():
		forum_view.profile = {"forum_unlocked": false, "access": {"forums": {
			"breachboard": {"unlocked": false, "reason": "Retrouve k0rvid sur Chordly."},
			"exployt": {"unlocked": false, "reason": "Invitation requise."},
			"xsx": {"unlocked": false, "reason": "Recommandation requise."}}}}
	forum_content.add_child(forum_view)
	forum_view.setup()
	forum_view.accept_contract.connect(_accept)
	forum_view.resume_requested.connect(_resume_saved)
	forum_view.open_app.connect(_open)
	forum_view.thread_selected.connect(_load_thread)
	forum_view.reply_requested.connect(_reply_thread)
	forum_view.open_service.connect(_open_service)
	forum_view.invitation_requested.connect(_accept_invitation)
	forum_view.contact_requested.connect(_open_contact)
	var net_content: VBoxContainer = _window("Réseau", Vector2i(510, 140), Vector2i(690, 460))
	net_content.add_child(_label("Réseau découvert", 21, ACCENT))
	network = Tree.new()
	network.columns = 3
	network.set_column_title(0, "Hôte")
	network.set_column_title(1, "Adresse")
	network.set_column_title(2, "État / Services")
	network.column_titles_visible = true
	network.hide_root = true
	network.size_flags_vertical = Control.SIZE_EXPAND_FILL
	net_content.add_child(network)
	var file_body: VBoxContainer = _window("Fichiers", Vector2i(260, 150), Vector2i(820, 530))
	files = FileManager.new()
	file_body.add_child(files)
	files.setup()
	files.open_app.connect(_launch_app)
	report = _rich(_window("Rapport", Vector2i(300, 110), Vector2i(840, 610)))
	var settings_body: VBoxContainer = _window("Paramètres", Vector2i(410, 100), Vector2i(660, 650))
	var settings_scroll: ScrollContainer = ScrollContainer.new()
	settings_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	settings_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	settings_body.add_child(settings_scroll)
	var settings: VBoxContainer = VBoxContainer.new()
	settings.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	settings.add_theme_constant_override("separation", 10)
	settings_scroll.add_child(settings)
	settings.add_child(AudioSettings.new())
	settings.add_child(HSeparator.new())
	settings.add_child(_label("Paramètres de la session", 23))
	settings.add_child(_button("Reprendre la mission sauvegardée", _resume_saved))
	settings.add_child(_button("Pause / Reprendre", _toggle_pause))
	var wait_button: Button = _button("Attendre 5 minutes dans le jeu", _wait_world)
	wait_button.tooltip_text = "Le monde, la mission et la défense avancent aussi pendant cette attente."
	settings.add_child(wait_button)
	_guidance = CheckButton.new()
	_guidance.text = "Recevoir les indices de mission automatiquement"
	_guidance.tooltip_text = "Les indices restent disponibles en écrivant aide au client, même si cette option est désactivée."
	_guidance.toggled.connect(_set_guidance)
	settings.add_child(_guidance)
	settings.add_child(_button("Plein écran / Fenêtre", _fullscreen))
	settings.add_child(_button("Sauvegarder la partie", _manual_save))
	settings.add_child(_button("Sauvegarder et revenir au menu", _go_menu))
	settings.add_child(_label("Super+T : terminal · Super+E : fichiers\nSuper+D : bureau · Alt+Tab : fenêtres", 13, MUTED))
	var player_body: VBoxContainer = _window("Lecteur audio", Vector2i(340,100), Vector2i(620,520))
	apps["Lecteur audio"].min_size = Vector2i(520,420)
	apps["Lecteur audio"].custom_minimum_size = Vector2(520,420)
	var player_scroll: ScrollContainer = ScrollContainer.new()
	player_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	player_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	player_body.add_child(player_scroll)
	var player: Control = preload("res://scripts/ui/music_player.gd").new()
	player.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	player_scroll.add_child(player)
	var wallet_body: VBoxContainer = _window("ColdVault", Vector2i(390, 90), Vector2i(630, 650))
	wallet_view = Wallet.new()
	wallet_body.add_child(wallet_view)
	wallet_view.setup()
	wallet_view.device_action.connect(_wallet_action)
	var shop_content: VBoxContainer = _window("Boutique", Vector2i(380, 120), Vector2i(690, 570))
	shop_content.add_child(_label("Services & matériel", 26, ACCENT))
	routes = OptionButton.new()
	for route: String in ["FreeShield", "NullVad", "VPN + Tor", "Tor + relais"]:
		routes.add_item(route)
	routes.item_selected.connect(_select_route)
	shop_content.add_child(_label("Route de connexion", 14, MUTED))
	shop_content.add_child(routes)
	var shop_scroll: ScrollContainer = ScrollContainer.new()
	shop_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	shop_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	shop_content.add_child(shop_scroll)
	shop = VBoxContainer.new()
	shop.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	shop.add_theme_constant_override("separation", 10)
	shop_scroll.add_child(shop)
	var tools: VBoxContainer = _window("Outils", Vector2i(430, 160), Vector2i(650, 480))
	tools.add_child(_label("Centre d'opération", 24))
	route_label = _label("Aucune opération active · poste local", 13, MUTED)
	route_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	tools.add_child(route_label)
	objectives_text = _rich(tools)
	objectives_text.custom_minimum_size.y = 80
	tools_catalog = _rich(tools)
	tools_catalog.text = "Outils disponibles en console.\nhelp · ls /usr/bin · which gophish\nGoPhish : gophish --help"
	tools.add_child(_button("Nouvelle console", _new_terminal))
	_context = PopupMenu.new()
	add_child(_context)
	for item: String in ["Ouvrir le terminal ici", "Dossier personnel", "Paramètres du bureau", "Afficher le bureau"]:
		_context.add_item(item)
	_context.id_pressed.connect(func(id: int) -> void:
		if id == 3: _toggle_desktop()
		else: _launch_app(["Terminal", "Fichiers", "Paramètres"][id]))

func _build_panel() -> void:
	var top: PanelContainer = UI.panel(Color("20212b"), 0)
	top.name = "XfcePanel"
	_top_panel = top
	top.z_index = 100
	top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top.offset_bottom = 32
	add_child(top)
	var bar: HBoxContainer = HBoxContainer.new()
	bar.add_theme_constant_override("separation", 3)
	top.add_child(bar)
	var menu: Button = UI.button("Applications", _show_menu, Color("20212b"), 4)
	menu.custom_minimum_size.x = 132
	menu.icon = load("res://assets/icons/dragon.svg")
	menu.expand_icon = true
	menu.add_theme_constant_override("icon_max_width", 24)
	bar.add_child(menu)
	for pair: Array in [["browser", "BreachBoard"], ["folder", "Fichiers"], ["terminal", "Terminal"]]:
		bar.add_child(_icon_button(pair[0], pair[1], 25))
	bar.add_child(VSeparator.new())
	for i: int in range(4):
		var b: Button = UI.button(str(i + 1), func() -> void: _switch_workspace(i), Color("20212b"), 3)
		b.custom_minimum_size.x = 26
		workspace_buttons.append(b)
		bar.add_child(b)
	bar.add_child(VSeparator.new())
	taskbar = HBoxContainer.new()
	taskbar.add_theme_constant_override("separation", 2)
	taskbar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var task_scroll: ScrollContainer = ScrollContainer.new()
	task_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	task_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	task_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	task_scroll.add_child(taskbar)
	bar.add_child(task_scroll)
	var desktop_button: Button = UI.button("▣", _toggle_desktop, Color("20212b"), 5)
	desktop_button.tooltip_text = "Afficher le bureau (Super+D)"
	bar.add_child(desktop_button)
	bar.add_child(_icon_button("network", "Outils", 22))
	var sound: Button = UI.button("♪", func() -> void: _open("Lecteur audio"), Color("20212b"), 4)
	var audio: Node = get_node("/root/Audio")
	var update_sound: Callable = func() -> void:
		sound.text = "♪ ×" if audio.preferences.muted else "♪"
		sound.tooltip_text = "Son coupé · ouvrir le lecteur" if audio.preferences.muted else "Ouvrir le lecteur audio · volumes dans Paramètres"
	audio.settings_changed.connect(update_sound)
	# Le service audio survit au bureau : sans cette déconnexion, la fonction était rappelée
	# avec un bouton libéré après chaque retour au menu.
	sound.tree_exiting.connect(func() -> void:
		if audio.settings_changed.is_connected(update_sound): audio.settings_changed.disconnect(update_sound))
	update_sound.call()
	bar.add_child(sound)
	profile_label = UI.label("operator", 12)
	profile_label.clip_text = true
	profile_label.custom_minimum_size.x = 85
	bar.add_child(profile_label)
	clock = UI.label("--:--", 13)
	clock.custom_minimum_size.x = 45
	bar.add_child(clock)
	bar.add_child(UI.button("⏻", func() -> void: _open("Paramètres"), Color("20212b"), 4))

func _build_icons() -> void:
	var column: VBoxContainer = VBoxContainer.new()
	column.position = Vector2(17, 65)
	column.add_theme_constant_override("separation", 13)
	add_child(column)
	for entry: Array in [["computer", "Système de fichiers"], ["home", "Dossier personnel"], ["trash", "Corbeille"]]:
		var button: Button = Button.new()
		button.custom_minimum_size = Vector2(95, 85)
		button.add_theme_stylebox_override("normal", UI.box(Color.TRANSPARENT))
		button.add_theme_stylebox_override("hover", UI.box(Color(0.25, 0.45, 0.7, 0.3), Color(0.4, 0.65, 0.9, 0.4), 3))
		var location: String = {"computer": "/", "home": "/home/operator", "trash": "trash:///"}[entry[0]]
		button.pressed.connect(func() -> void: _open("Fichiers"); files.navigate(location))
		column.add_child(button)
		var content: VBoxContainer = VBoxContainer.new()
		content.mouse_filter = Control.MOUSE_FILTER_IGNORE
		content.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		button.add_child(content)
		var icon: TextureRect = UI.icon(entry[0], 48)
		icon.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		content.add_child(icon)
		var label: Label = UI.label(entry[1], 12, Color.WHITE)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		label.add_theme_color_override("font_shadow_color", Color.BLACK)
		label.add_theme_constant_override("shadow_offset_x", 1)
		label.add_theme_constant_override("shadow_offset_y", 1)
		content.add_child(label)

func _icon_button(icon_name: String, app_name: String, diameter: int) -> Button:
	var button: Button = UI.button("", func() -> void: _launch_app(app_name), Color("20212b"), 3)
	button.icon = load("res://assets/icons/%s.svg" % icon_name)
	button.expand_icon = true
	button.add_theme_constant_override("icon_max_width", diameter)
	button.custom_minimum_size = Vector2(diameter + 8, diameter + 4)
	button.tooltip_text = app_name
	return button

func _build_applications_menu() -> void:
	_applications = UI.panel(Color("252733"), 9, 4)
	_applications.name = "ApplicationsMenu"
	_applications.position = Vector2(0, 33)
	_applications.custom_minimum_size = Vector2(390, 470)
	_applications.z_index = 200
	_applications.visible = false
	add_child(_applications)
	var column: VBoxContainer = VBoxContainer.new()
	column.add_theme_constant_override("separation", 10)
	_applications.add_child(column)
	_application_search = LineEdit.new()
	_application_search.placeholder_text = "Rechercher une application…"
	_application_search.text_changed.connect(func(_text: String) -> void: _render_applications())
	column.add_child(_application_search)
	_application_list = VBoxContainer.new()
	_application_list.add_theme_constant_override("separation", 1)
	column.add_child(_application_list)
	column.add_child(HSeparator.new())
	column.add_child(UI.button("Paramètres", func() -> void: _open("Paramètres")))
	column.add_child(UI.button("Sauvegarder et revenir au menu", _go_menu))

func _render_applications() -> void:
	UI.clear(_application_list)
	var search: String = _application_search.text.to_lower()
	for entry: Array in [["music", "Lecteur audio", "Lecteur audio"], ["terminal", "Terminal", "Émulateur de terminal"], ["folder", "Fichiers", "Gestionnaire de fichiers"], ["browser", "BreachBoard", "Navigateur Web"], ["browser", "GoPhish", "GoPhish - interface web"], ["network", "BloodHound", "BloodHound - collecte et relations AD"], ["chat", "Chordly", "Chordly - Messages privés"], ["telegram", "Telegrid", "Telegrid - Messagerie"], ["session", "Sessyon", "Sessyon - Messagerie privée"], ["network", "Réseau", "01 - Reconnaissance / réseau"], ["tools", "Outils", "Opérations de la mission"], ["shop", "Boutique", "Services et matériel"], ["wallet", "ColdVault", "Portefeuille matériel"], ["report", "Rapport", "Rapport d'opération"]]:
		if not search.is_empty() and not str(entry[2]).to_lower().contains(search) and not str(entry[1]).to_lower().contains(search):
			continue
		var id: String = entry[1]
		var button: Button = UI.button(entry[2], func() -> void: _launch_app(id), Color("252733"), 7)
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.icon = load("res://assets/icons/%s.svg" % entry[0])
		button.expand_icon = true
		button.add_theme_constant_override("icon_max_width", 22)
		if id == "Boutique":
			var access: Dictionary = _profile.get("access", {}).get("shop", {"unlocked": int(_profile.get("tier", 0)) >= 1, "reason": "Termine le dossier Ravelle."})
			button.disabled = not access.get("unlocked", false)
			button.tooltip_text = str(access.get("reason", ""))
		_application_list.add_child(button)

func _build_notifications() -> void:
	_toast = UI.panel(Color("282a36"), 16, 5)
	_toast.z_index = 300
	_toast.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	_toast.offset_left = -355
	_toast.offset_right = -15
	_toast.offset_top = 48
	_toast.offset_bottom = 135
	_toast.visible = false
	_toast.gui_input.connect(func(event: InputEvent) -> void:
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			_activate_notification())
	add_child(_toast)
	var column: VBoxContainer = VBoxContainer.new()
	_toast.add_child(column)
	column.add_child(UI.label("Notification", 13, ACCENT))
	notification = UI.label("", 13)
	notification.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(notification)

func _window(app_name: String, pos: Vector2i, dimensions: Vector2i) -> VBoxContainer:
	var win: DesktopWindow = DesktopWindow.new()
	var icons: Dictionary = {"Terminal": "terminal", "Fichiers": "folder", "Chordly": "chat", "Telegrid": "telegram", "Sessyon": "session", "BreachBoard": "browser", "GoPhish": "browser", "Boutique": "shop", "ColdVault": "wallet", "Outils": "tools", "Rapport": "report", "Paramètres": "settings", "Réseau": "network", "Lecteur audio": "music"}
	add_child(win)
	var body: VBoxContainer = win.setup(app_name, app_name, "terminal" if app_name.begins_with("Terminal") else icons.get(app_name, "folder"), dimensions)
	win.position = pos
	if app_name in ["BreachBoard", "Chordly", "Telegrid", "Sessyon"]: win.min_size = Vector2i(600, 420)
	elif app_name == "Fichiers": win.min_size = Vector2i(650, 420)
	win.custom_minimum_size = Vector2(win.min_size)
	win.activated.connect(func() -> void:
		active_app = app_name
		_applications.hide()
		_raise_overlays()
		_mark_active_conversation_read()
		_update_tasks())
	win.minimized.connect(func() -> void: _drop_hidden_active(); _update_tasks())
	win.closed.connect(func() -> void: _drop_hidden_active(); _update_tasks())
	win.closed.connect(func() -> void: _sound("close"))
	apps[app_name] = win
	if not app_name.begins_with("Terminal") and app_name not in ["GoPhish", "BreachBoard", "Chordly", "Telegrid", "Sessyon", "Fichiers"]:
		var margin: MarginContainer = MarginContainer.new()
		margin.size_flags_vertical = Control.SIZE_EXPAND_FILL
		for side: String in ["left", "right", "top", "bottom"]:
			margin.add_theme_constant_override("margin_" + side, 14)
		body.add_child(margin)
		var padded: VBoxContainer = VBoxContainer.new()
		padded.add_theme_constant_override("separation", 10)
		margin.add_child(padded)
		return padded
	return body

func _rich(parent: Node) -> RichTextLabel:
	var node: RichTextLabel = RichTextLabel.new()
	node.size_flags_vertical = Control.SIZE_EXPAND_FILL
	node.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	node.selection_enabled = true
	node.scroll_following = true
	node.bbcode_enabled = false
	parent.add_child(node)
	return node

func _build_terminal() -> void:
	_create_terminal("main", "Terminal")

func _create_terminal(id: String, app_name: String) -> void:
	var offset: int = (console_counter - 1) % 6 * 24
	var body: VBoxContainer = _window(app_name, Vector2i(170 + offset, 150 + offset), Vector2i(860, 500))
	var view: TerminalView = TerminalView.new()
	body.add_child(view)
	view.setup(id)
	view.command_submitted.connect(func(console_id: String, line: String) -> void: session.command(line, console_id))
	view.interrupted.connect(func(console_id: String) -> void: session.command("", console_id, true))
	view.new_window.connect(_new_terminal)
	view.completion_requested.connect(func(console_id: String, line: String, caret: int) -> void: session.complete(line, caret, console_id))
	terminal_views[id] = view
	console_apps[id] = app_name
	if session != null and session.state.get("terminals", {}).has(id): view.set_context(session.state.terminals[id])
	apps[app_name].closed.connect(func() -> void: _close_console(id))
	if id == "main":
		terminal = view.output
		terminal_input = view.input
		_terminal_context = view.prompt

func _new_terminal() -> void:
	if not terminal_views.has("main"):
		_create_terminal("main", "Terminal")
		_open("Terminal")
	elif not apps.Terminal.opened:
		_open("Terminal")
	else:
		console_counter += 1
		var id: String = "term-%s" % console_counter
		var app_name: String = "Terminal %s" % console_counter
		_create_terminal(id, app_name)
		_open(app_name)

func _launch_app(app_name: String) -> void:
	if app_name == "Terminal": _new_terminal()
	else: _open(app_name)

func _close_console(id: String) -> void:
	if not console_apps.has(id): return
	var app_name: String = console_apps[id]
	if session != null and "--offline-test" not in OS.get_cmdline_user_args(): session.close_console(id)
	var frame: Control = apps[app_name]
	apps.erase(app_name)
	console_apps.erase(id)
	terminal_views.erase(id)
	if id == "main":
		# Ces raccourcis ne doivent pas viser une console libérée.
		terminal = null
		terminal_input = null
		_terminal_context = null
	frame.queue_free()
	_update_tasks()

func _console_output(id: String, lines: Array) -> void:
	if terminal_views.has(id): terminal_views[id].append_lines(lines)

func _console_context(id: String, context: Dictionary) -> void:
	if terminal_views.has(id):
		var was_secret: bool = terminal_views[id].input.secret
		var was_running: bool = terminal_views[id].context.get("foreground") != null or int(terminal_views[id].context.get("pending", 0)) > 0
		terminal_views[id].set_context(context)
		if (was_running or was_secret != terminal_views[id].input.secret) and context.get("foreground") == null and int(context.get("pending", 0)) == 0 and console_apps.get(id) == active_app:
			terminal_views[id].input.grab_focus()

func _show_menu() -> void:
	_applications.visible = not _applications.visible
	if _applications.visible:
		_raise_overlays()
		_render_applications()
		_application_search.grab_focus()

## z_index ne règle que le dessin : l’ordre des nœuds décide qui reçoit le clic.
## Une fenêtre passée au premier plan ne doit pas capter les clics du panneau ou du menu.
func _raise_overlays() -> void:
	for overlay: Control in [_top_panel, _applications, _toast]:
		if overlay != null and overlay.get_parent() == self: move_child(overlay, get_child_count() - 1)

func _continue_campaign() -> void:
	var result: Dictionary = await session.request("/api/profile/continue", {})
	if result.has("error"):
		_notify(str(result.error), "Chordly")
		return
	_profile = result.data
	var world: Dictionary = await session.request("/api/social")
	if not world.has("error"): _update_social(world.data)
	messengers.chordly._select_peer("k0rvid")
	_notify("Campagne poursuivie : tes acquis sont conservés.", "Chordly")

func _create_bloodhound() -> void:
	var body: VBoxContainer = _window("BloodHound", Vector2i(190,90), Vector2i(1000,650))
	var analysis: Control = load("res://scripts/ui/bloodhound.gd").new()
	body.add_child(analysis)
	analysis.size_flags_vertical = Control.SIZE_EXPAND_FILL
	analysis.setup(session)
	apps.BloodHound.min_size = Vector2i(720,500)
	apps.BloodHound.set_meta("analysis", analysis)

func _open(app_name: String) -> void:
	if app_name == "Boutique":
		var access: Dictionary = _profile.get("access", {}).get("shop", {"unlocked": int(_profile.get("tier", 0)) >= 1, "reason": "La boutique se débloque après le dossier Ravelle."})
		if not access.get("unlocked", false):
			_notify(str(access.get("reason", "Boutique verrouillée.")), "Chordly")
			return
	if app_name == "BloodHound":
		if not apps.has("BloodHound"): _create_bloodhound()
		apps.BloodHound.get_meta("analysis").refresh()
	if app_name == "GoPhish" and not apps.has("GoPhish"): _create_gophish()
	if app_name == "Terminal" and not apps.has("Terminal"): _create_terminal("main", "Terminal")
	if not apps.has(app_name):
		return
	_applications.hide()
	_showing_desktop = false
	var win: DesktopWindow = apps[app_name]
	var opening: bool = not win.is_visible_in_tree()
	win.open_window(workspace)
	if opening: _sound("open")
	active_app = app_name
	if app_name.begins_with("Terminal"):
		for id: String in console_apps:
			if console_apps[id] == app_name: terminal_views[id].input.grab_focus()
	for channel: String in messengers:
		if {"chordly": "Chordly", "telegrid": "Telegrid", "sessyon": "Sessyon"}[channel] == app_name:
			messengers[channel].mark_read()
	if app_name == "Outils":
		_refresh_operations()
	if app_name == "GoPhish": _refresh_gophish()
	if app_name == "ColdVault": _refresh_wallet()
	if app_name == "Boutique":
		_refresh_shop()
	if app_name == "BreachBoard":
		_render_board()
	_update_tasks()

func _update_tasks() -> void:
	UI.clear(taskbar)
	tasks.clear()
	for app_name: String in apps:
		var frame: DesktopWindow = apps[app_name]
		if not frame.opened or frame.workspace != workspace:
			continue
		var count: int = unread_counts.get(app_name, 0)
		var button: Button = UI.button(app_name + (" (%s)" % count if count else ""), func() -> void:
			if active_app == app_name and frame.visible:
				frame.minimize_window()
			else: _open(app_name), Color("3b4053") if app_name == active_app else Color("252733"), 4)
		button.clip_text = true
		button.custom_minimum_size.x = 100
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		taskbar.add_child(button)
		tasks[app_name] = button
	for i: int in range(workspace_buttons.size()):
		workspace_buttons[i].modulate = Color("91c9ff") if i == workspace else Color("9297a5")

func _switch_workspace(index: int) -> void:
	_showing_desktop = false
	_desktop_restored.clear()
	workspace = clampi(index, 0, 3)
	for frame: DesktopWindow in apps.values():
		frame.visible = frame.opened and not frame.minimized_state and frame.workspace == workspace
	active_app = ""
	_update_tasks()

func _toggle_desktop() -> void:
	if _showing_desktop:
		for id: String in _desktop_restored:
			if apps[id].opened and apps[id].workspace == workspace:
				apps[id].show()
		_showing_desktop = false
	else:
		_desktop_restored.clear()
		for id: String in apps:
			if apps[id].visible:
				_desktop_restored.append(id)
				apps[id].hide()
		_showing_desktop = true
		_drop_hidden_active()

func _cycle_windows() -> void:
	var ids: Array[String] = []
	for id: String in apps:
		if apps[id].opened and apps[id].workspace == workspace:
			ids.append(id)
	if ids.is_empty(): return
	var index: int = ids.find(active_app)
	_open(ids[(index + 1) % ids.size()])

func _queue_message_notification(text: String, app_name: String, peer: String = "") -> void:
	var pending: Dictionary = _message_notifications.get(app_name, {"count": 0, "peers": []})
	pending["count"] = int(pending.count) + 1
	pending["text"] = text
	pending["peer"] = peer
	if not peer in pending.peers: pending.peers.append(peer)
	_message_notifications[app_name] = pending

func _flush_message_notifications() -> void:
	if _message_notifications.is_empty() or _notification_cooldown > 0: return
	var app_name: String = str(_message_notifications.keys()[0])
	var pending: Dictionary = _message_notifications[app_name]
	_message_notifications.erase(app_name)
	var channel: String = {"Chordly": "chordly", "Telegrid": "telegrid", "Sessyon": "sessyon"}.get(app_name, "")
	if not channel.is_empty() and active_app == app_name and pending.peers.size() == 1 and messengers[channel].selected_peer == pending.get("peer"):
		return
	var caption: String = "%s nouveaux messages · %s" % [int(pending.count), app_name] if int(pending.count) > 1 else str(pending.text)
	_notify(caption, app_name)
	_toast.set_meta("message_inbox", true)
	_toast.set_meta("open_peer", str(pending.peer) if pending.peers.size() == 1 else "")

func _activate_notification() -> void:
	var app_name: String = str(_toast.get_meta("open_app", ""))
	var peer: String = str(_toast.get_meta("open_peer", ""))
	var inbox: bool = bool(_toast.get_meta("message_inbox", false))
	var channel: String = {"Chordly": "chordly", "Telegrid": "telegrid", "Sessyon": "sessyon"}.get(app_name, "")
	# Sélectionner la cible avant l’ouverture évite de marquer l’ancien fil comme lu.
	if inbox and not channel.is_empty() and not peer.is_empty(): messengers[channel]._select_peer(peer)
	_open(app_name)
	if inbox and app_name == "BreachBoard": forum_view.navigate("breachboard", "", "Messages")
	if inbox and not channel.is_empty() and peer.is_empty():
		messengers[channel]._show_contacts = true
		messengers[channel]._adapt_layout()
	_toast.hide()

func _music_changed(kind: String) -> void:
	var audio: Node = get_node("/root/Audio")
	_pending_music = str(audio.TITLES.get(kind, kind))

func _notify(text: String, app_name: String = "", with_sound: bool = true) -> void:
	if with_sound: _sound({"Chordly": "chordly", "Telegrid": "telegrid", "Sessyon": "sessyon"}.get(app_name, "notify"))
	_notification_cooldown = 8
	notification.text = text
	_toast.show()
	_toast_timer = 7
	_toast.set_meta("open_app", app_name)
	_toast.set_meta("open_peer", "")
	_toast.set_meta("message_inbox", false)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		_applications.hide()
		if event.button_index == MOUSE_BUTTON_RIGHT:
			_context.position = Vector2i(get_global_mouse_position())
			_context.popup()

func _submit_command(line: String) -> void:
	if terminal_views.has("main"): terminal_views.main.submit(line)

func _terminal_key(event: InputEvent) -> void:
	if terminal_views.has("main"): terminal_views.main.key_input(event)

func _terminal_lines(lines: Array) -> void:
	_console_output("main", lines)

func _error(message: String) -> void:
	_sound("error")
	_notify(message, "", false)
	_terminal_lines(["Erreur : " + message])

func _render_board() -> void:
	if session != null and forum_view != null:
		var profile: Dictionary = _profile.duplicate(true)
		if session.state.get("status") == "RUNNING" and session.state.get("contract") != null:
			profile["active_contract"] = {"contract_id": session.state.contract.contract_id, "title": session.state.get("scenario_name", "Mission en cours")}
		forum_view.update_data(session.contracts, profile, session.handle, (not session.game_id.is_empty() and session.state.get("status") == "RUNNING") or session.busy)

func _accept(contract_id: String) -> void:
	if not session.game_id.is_empty() and session.state.get("status") == "RUNNING":
		if session.state.get("contract", {}).get("contract_id") == contract_id: _show_current_mission()
		else: _notify("Une autre mission est en cours. Reprends le dossier dans sa conversation.", "BreachBoard")
		return
	var active: Dictionary = _profile.get("active_contract", {}) if _profile.get("active_contract") != null else {}
	if active.get("contract_id") == contract_id:
		await _resume_saved()
		return
	_last_messages = 0
	_last_outcome = ""
	var route_names: Array[String] = ["freeshield", "nullvad", "tor", "relay"]
	# Le choix est conservé par le moteur pour le prochain contrat.
	paused = false
	var selected: Dictionary = await session.request("/api/profile/route", {"route": route_names[routes.selected]})
	if selected.has("error"):
		_error(selected.error)
		return
	if await session.start(contract_id):
		await _refresh_profile()
		_show_current_mission()

func _show_current_mission() -> void:
	apps.BreachBoard.minimize_window()
	var contract: Dictionary = session.state.get("contract", {})
	var channel: String = contract.get("channel", "chordly")
	if messengers.has(channel): messengers[channel]._select_peer(contract.get("client", "k0rvid"))
	_open({"chordly": "Chordly", "telegrid": "Telegrid", "sessyon": "Sessyon"}.get(channel, "Chordly"))
	if not contract.get("onboarding", false) and not contract.get("private_offer", false): _open("Terminal")
	_render_board()

func _update_state(state: Dictionary) -> void:
	get_node("/root/Audio").set_context("mission" if state.get("status") == "RUNNING" and not paused else "desktop")
	var contexts: Dictionary = state.get("terminals", {"main": state.get("terminal", {})})
	for id: String in contexts: _console_context(id, contexts[id])
	if gophish_view != null and apps.has("GoPhish") and apps.GoPhish.visible: _refresh_gophish(true)
	var discovered: Array = state.get("discovered", [])
	var scanned: Array = state.get("scanned", [])
	network.clear()
	var root: TreeItem = network.create_item()
	for host: Dictionary in state.get("hosts", []):
		if host.id not in discovered:
			continue
		var item: TreeItem = network.create_item(root)
		item.set_text(0, host.hostname)
		item.set_text(1, host.ip)
		var services: Array[String] = []
		if host.id in scanned:
			for service: Dictionary in host.services:
				services.append("%s/%s (%s)" % [service.name, service.port, service.get("state", "open")])
		item.set_text(2, host.status + " " + ", ".join(services))
	var objective_lines: Array[String] = ["OBJECTIFS"]
	for objective: Dictionary in state.get("objectives", []):
		var description: String = str(objective.type)
		match objective.type:
			"campaign_submitted": description = "Vérifier la soumission dans la campagne"
			"hash_recovered": description = "Vérifier la correspondance dans Hashcat"
			"investigation_step": description = {"erreur_prouvee": "Prouver l’erreur du contact", "cible_confirmee": "Confirmer la bonne cible", "livraison_validee": "Faire valider la livraison"}.get(str(objective.get("step", "")), "Vérifier les preuves du dossier")
			"intact_download": description = "Récupérer le fichier récent intact"
			"file_read": description = "Lire le dossier indiqué"
			"session_on_host": description = "Vérifier la connexion avec le compte fourni"
			"local_file_equals": description = "Rédiger la conclusion demandée"
			"host_file_equals": description = "Copier le document dans la session distante"
			"host_compromised": description = "Prendre le contrôle de la machine cible"
			"domain_compromised": description = "Prendre le contrôle du domaine"
			"credential_owned": description = "Récupérer le compte " + str(objective.get("username", ""))
			"file_exfiltrated": description = "Récupérer " + str(objective.get("file", ""))
			"encrypted_ratio": description = "Chiffrer %s %% du réseau" % objective.get("percent", 0)
			"backups_destroyed": description = "Détruire les sauvegardes de la cible"
		objective_lines.append(("✓ " if objective.get("met", false) else "○ ") + description)
	objectives_text.text = "\n".join(objective_lines)
	_guidance.set_pressed_no_signal(state.get("guidance_enabled", true))
	var messages: Array = state.get("messages", [])
	for i: int in range(messages.size()):
		var msg: Dictionary = messages[i].duplicate(true)
		var channel: String = msg.get("channel", "chordly")
		if not messengers.has(channel): continue
		msg["id"] = msg.get("id", session.game_id + ":" + str(i))
		msg["peer"] = msg.get("peer", state.get("contract", {}).get("client", "k0rvid") if state.get("contract") != null else "k0rvid")
		var title: String = {"chordly": "Chordly", "telegrid": "Telegrid", "sessyon": "Sessyon"}[channel]
		var notify: bool = not apps[title].visible or active_app != title
		var is_new: bool = not messengers[channel]._ids.has(str(msg.id))
		messengers[channel].add_message(msg, _social_ready and notify)
		if _social_ready and is_new and notify and i >= _last_messages and msg.get("sender") != session.handle:
			_queue_message_notification("%s · %s" % [msg.sender, str(msg.text).left(110)], title, str(msg.peer))
	_last_messages = messages.size()
	files.set_loot(state.get("loot", []))
	_refresh_operations()
	var trace: Dictionary = state.get("trace", {})
	route_label.text = "%s · tick %s/%s · exposition %s/%s%s" % [" → ".join(trace.get("route", ["poste local", "cible"])), state.tick, state.max_ticks, trace.get("progress", 0), trace.get("capacity", 0), " · PAUSE" if paused else ""]
	route_label.tooltip_text = "Exposition de la route simulée : aucune arrestation automatique. Une machine confinée redevient accessible après six ticks ; reconnecte ensuite ta console."
	var contract: Dictionary = state.get("contract", {}) if state.get("contract") != null else {}
	for kind: String in messengers:
		var context: Dictionary = {}
		if contract.get("channel", "") == kind and state.get("status") == "RUNNING":
			context = {"contract_id": contract.get("contract_id", ""), "client": contract.get("client", ""), "title": contract.get("title", "Dossier en cours"), "goal": contract.get("goal", ""), "running": true}
		messengers[kind].set_mission_context(context)
	var outcome: String = str(contract.get("outcome", ""))
	if outcome != "" and outcome != "<null>":
		var changed: bool = outcome != _last_outcome
		_last_outcome = outcome
		_show_report(state, changed and not contract.get("onboarding", false))
		if changed and contract.get("onboarding", false): _open("Chordly")
		if changed:
			_sound("success" if outcome == "SUCCESS" else "failure")
			_refresh_profile()
			_refresh_contracts()
			session.refresh_social()

func _show_report(state: Dictionary, show_window: bool = true) -> void:
	var contract: Dictionary = state.contract
	var text: String = "RAPPORT D'OPÉRATION\n\n%s · %s\n\n" % [state.scenario_name, contract.outcome]
	text += "Déroulement\n"
	for entry: Dictionary in state.get("debrief", {}).get("history", state.history):
		text += "[%s] %s\n" % [entry.tick, entry.message]
	text += "\nDétections côté défense\n"
	for alert: Dictionary in state.get("debrief", {}).get("alerts", state.alerts):
		text += "[%s] %s · %s\n" % [alert.detected_tick, alert.severity, alert.title]
	text += "\nTraçage\n"
	for entry: Dictionary in state.get("debrief", {}).get("trace", []):
		text += "[%s] %s\n" % [entry.tick, entry.message]
	text += "\nÉvénements de la défense\n"
	for entry: Dictionary in state.get("debrief", {}).get("logs", []):
		text += "[%s] %s · événement %s\n" % [entry.tick, entry.host, entry.event_id]
	var impact: Dictionary = state.get("debrief", {}).get("impact", {})
	if not impact.get("notes", []).is_empty():
		text += "\nConséquences vérifiées\n"
		text += "Machines chiffrées : %s · fichiers transférés : %s\n" % [impact.get("encrypted_hosts", []).size(), impact.get("exfiltrated_files", []).size()]
		for note: String in impact.get("notes", []):
			text += "• " + note + "\n"
	text += "\nRèglement reçu : %s ₵\n" % int(contract.get("payout", 0))
	text += "\nAnalyse\n"
	for hint: String in contract.get("debrief_hints", []):
		text += "• " + hint + "\n"
	report.text = text
	if show_window: _open("Rapport")

var _pause_busy: bool = false

## L’état local ne change qu’après confirmation du moteur.
func _toggle_pause() -> void:
	if _pause_busy or session.game_id.is_empty() or session.state.get("status") != "RUNNING":
		return
	_pause_busy = true
	var target: bool = not paused
	var accepted: bool = await session.control("pause" if target else "resume")
	_pause_busy = false
	if not accepted: return
	paused = target
	get_node("/root/Audio").set_context("desktop" if paused else "mission")
	_notify("Session suspendue" if paused else "Session reprise", "", false)

func _fullscreen() -> void:
	var full: bool = DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if full else DisplayServer.WINDOW_MODE_FULLSCREEN)

func _input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed: return
	for id: String in console_apps:
		if console_apps[id] == active_app and apps.has(active_app) and apps[active_app].is_visible_in_tree() and _keyboard_in(active_app) and terminal_views[id].handle_key(event):
			get_viewport().set_input_as_handled()
			return
	if event.echo: return
	var handled: bool = true
	if event.ctrl_pressed and event.keycode == KEY_L and active_app == "BreachBoard": forum_view.focus_address()
	elif event.ctrl_pressed and event.keycode == KEY_T and not event.alt_pressed and active_app == "BreachBoard": forum_view.new_tab()
	elif event.keycode == KEY_F11: _fullscreen()
	elif event.keycode == KEY_ESCAPE and _applications.visible: _applications.hide()
	elif event.keycode == KEY_F5: _manual_save()
	elif event.keycode == KEY_TAB and event.alt_pressed: _cycle_windows()
	elif event.keycode == KEY_T and ((event.ctrl_pressed and event.alt_pressed) or event.meta_pressed): _new_terminal()
	elif event.keycode == KEY_N and event.ctrl_pressed and event.shift_pressed and active_app.begins_with("Terminal"): _new_terminal()
	elif event.keycode == KEY_E and event.meta_pressed: _open("Fichiers")
	elif event.keycode == KEY_W and event.meta_pressed: _open("BreachBoard")
	elif event.keycode == KEY_D and (event.meta_pressed or (event.ctrl_pressed and event.alt_pressed)): _toggle_desktop()
	elif event.ctrl_pressed and event.alt_pressed and event.keycode in [KEY_LEFT, KEY_RIGHT]:
		_switch_workspace(posmod(workspace + (1 if event.keycode == KEY_RIGHT else -1), 4))
	else: handled = false
	if handled: get_viewport().set_input_as_handled()

## Échap ouvre les Paramètres seulement si aucun composant ne l’a utilisé
## (recherche Chordly, gestionnaire de sauvegardes, dialogues…).
func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_ESCAPE:
		_open("Paramètres")
		get_viewport().set_input_as_handled()

## Une fenêtre réduite, fermée ou masquée n'est plus la fenêtre active : sinon ses messages
## passaient pour lus à l'écran et le clavier partait vers un terminal invisible.
func _drop_hidden_active() -> void:
	if active_app.is_empty(): return
	if not apps.has(active_app) or not apps[active_app].is_visible_in_tree(): active_app = ""

## Cliquer dans une messagerie revient à lire la conversation affichée.
func _mark_active_conversation_read() -> void:
	var channel: String = {"Chordly": "chordly", "Telegrid": "telegrid", "Sessyon": "sessyon"}.get(active_app, "")
	if channel.is_empty() or not messengers.has(channel): return
	if int(messengers[channel]._unread_by_peer.get(messengers[channel].selected_peer, 0)) > 0: messengers[channel].mark_read()

## Le clavier revient au terminal actif seulement si le focus est dans sa fenêtre
## ou nulle part : un champ du menu Applications ou d’une autre fenêtre garde ses touches.
func _keyboard_in(app_name: String) -> bool:
	var focused: Control = get_viewport().gui_get_focus_owner()
	if focused == null: return true
	return apps.has(app_name) and (apps[app_name] == focused or apps[app_name].is_ancestor_of(focused))

func _load_identity() -> void:
	var config: ConfigFile = ConfigFile.new()
	if config.load("user://desktop.cfg") == OK:
		_profile.handle = config.get_value("identity", "handle", "")

func _save_identity() -> void:
	var config: ConfigFile = ConfigFile.new()
	config.set_value("identity", "handle", session.handle)
	config.save("user://desktop.cfg")

func _refresh_profile() -> void:
	var result: Dictionary = await session.request("/api/profile")
	if result.has("error"):
		return
	_profile = result.data
	if not str(_profile.get("handle", "")).is_empty():
		session.handle = _profile.handle
		for messenger: Messenger in messengers.values(): messenger.set_identity(session.handle)
		_save_identity()
	var route_ids: Array[String] = ["freeshield", "nullvad", "tor", "relay"]
	routes.select(maxi(0, route_ids.find(_profile.get("route", "freeshield"))))
	resume_button.visible = _profile.get("has_active", false)
	if resume_button.visible:
		resume_button.text = "Reprendre : " + str(_profile.get("active_contract", {}).get("title", "mission sauvegardée"))
	profile_label.text = session.handle
	profile_label.tooltip_text = "Confiance opérateur %s · Palier %s · Fonds dans ColdVault" % [_profile.reputation, _profile.tier]
	_render_applications()
	if _profile.has("wallet"): wallet_view.set_data(_profile.wallet)
	_render_board()

func _refresh_contracts() -> void:
	var result: Dictionary = await session.request("/api/contracts", null, TYPE_ARRAY)
	if not result.has("error"):
		session.contracts = result.data
	_render_board()

func _refresh_shop() -> void:
	var result: Dictionary = await session.request("/api/shop", null, TYPE_ARRAY)
	if result.has("error"):
		_error(result.error)
		return
	_render_shop(result.data)

func _render_shop(items: Array) -> void:
	UI.clear(shop)
	var note: Label = UI.wrapped("Achats facultatifs pour l’acte I. Matériel et route appliqués au prochain départ. Les paiements se confirment dans ColdVault. Un dossier déjà réussi ne verse plus de prime.", 13, MUTED)
	shop.add_child(note)
	if not items.is_empty() and int(items[0].get("reserve", 0)) > 0:
		note.text += " Réserve pour le prochain accès obligatoire : %s ₵." % int(items[0].reserve)
	for item: Dictionary in items:
		var id: String = item.id
		var panel: PanelContainer = UI.panel(Color("242a34"), 12, 6)
		shop.add_child(panel)
		var content: VBoxContainer = VBoxContainer.new()
		content.add_theme_constant_override("separation", 8)
		panel.add_child(content)
		content.add_child(UI.wrapped(str(item.name), 16))
		content.add_child(UI.rich(str(item.get("description", "")), 13, MUTED))
		var price: int = int(item.price)
		var caption: String = "Acquis" if item.get("owned", false) else ("Activer gratuitement" if price == 0 else "Préparer le paiement · %s ₵" % price)
		var button: Button = _button(caption, func() -> void: _buy(id))
		button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		button.disabled = item.get("owned", false) or not item.get("unlocked", true)
		content.add_child(button)
		if not str(item.get("reason", "")).is_empty() and not item.get("owned", false):
			content.add_child(UI.wrapped(str(item.reason), 12, MUTED))

func _buy(item_id: String) -> void:
	var result: Dictionary = await session.request("/api/shop/buy", {"item": item_id})
	if result.has("error"):
		_error(result.error)
	else:
		if result.data.get("paid", false):
			_notify("Service gratuit activé.", "Boutique")
			await _refresh_profile()
			_refresh_shop()
		else:
			wallet_view.set_data(result.data.get("wallet", {}))
			_open("ColdVault")

func _refresh_operations() -> void:
	if tools_catalog == null or session == null: return
	var lines: PackedStringArray = ["COMMANDES DISPONIBLES", "help · ls /usr/bin · which gophish", ""]
	for spec: Dictionary in operation_specs:
		lines.append(str(spec.get("cli", spec.name)))
	tools_catalog.text = "\n".join(lines)

func _restore_console_windows(saved_state: Dictionary) -> void:
	for id: String in saved_state.get("terminals", {}):
		if not id.begins_with("term-"): continue
		var number: int = id.trim_prefix("term-").to_int()
		if number < 2: continue
		console_counter = maxi(console_counter, number)
		if not terminal_views.has(id): _create_terminal(id, "Terminal %s" % number)
		_open(console_apps[id])
	var transcripts: Dictionary = saved_state.get("terminal_transcripts", {})
	if not transcripts.is_empty():
		for id: String in transcripts:
			if terminal_views.has(id): terminal_views[id].restore_transcript(transcripts[id])
		session.mark_history_seen(saved_state)
	session.apply_state(saved_state)

func _resume_saved() -> void:
	var result: Dictionary = await session.request("/api/profile/resume", {})
	if result.has("error"):
		_error(result.error)
		return
	session.game_id = result.data.id
	session.clear_history_seen()
	session.handle = result.data.state.player_handle
	_last_messages = 0
	_last_outcome = ""
	_restore_console_windows(result.data.state)
	for action: String in ["start", "resume"]:
		var response: Dictionary = await session.request("/api/games/%s/%s" % [session.game_id, action], {})
		if response.has("error"):
			if action == "start": session.game_id = ""
			_error(response.error)
			return
	paused = false
	session.connect_socket()
	await _refresh_profile()
	_show_current_mission()

func _exit_tree() -> void:
	if session != null:
		session.shutdown()

func _unread_changed(app_name: String, count: int) -> void:
	unread_counts[app_name] = count
	if apps.has(app_name): apps[app_name].title_label.text = app_name + (" (%s)" % count if count else "")
	if tasks.has(app_name):
		tasks[app_name].text = app_name + (" (%s)" % count if count else "")

func _request_mission_hint(channel: String, peer: String) -> void:
	if _hint_busy or session.game_id.is_empty() or session.state.get("status") != "RUNNING": return
	var contract: Dictionary = session.state.get("contract", {})
	if contract.get("client", "") != peer or contract.get("channel", "") != channel: return
	_hint_busy = true
	messengers[channel].set_hint_busy(true)
	var game_id: String = session.game_id
	var result: Dictionary = await session.request("/api/games/%s/chat" % game_id, {"channel": channel, "peer": peer, "text": "aide"})
	_hint_busy = false
	messengers[channel].set_hint_busy(false)
	if session.game_id != game_id: return
	if result.has("error"): _error(str(result.error))
	else: session.apply_state(result.data)

func _send_message(channel: String, text: String) -> void:
	if "--offline-test" in OS.get_cmdline_user_args():
		messengers[channel].acknowledge(false, "Moteur hors ligne.")
		return
	var peer: String = messengers[channel].selected_peer
	var contract: Dictionary = session.state.get("contract", {}) if session.state.get("contract") != null else {}
	var mission_client: bool = not session.game_id.is_empty() and session.state.get("status") == "RUNNING" and peer == contract.get("client", "") and channel == contract.get("channel", "")
	var path: String = "/api/games/%s/chat" % session.game_id if mission_client else "/api/social/chat"
	var result: Dictionary = await session.request(path, {"handle": session.handle, "channel": channel, "peer": peer, "text": text})
	messengers[channel].acknowledge(not result.has("error"), result.get("error", ""))
	_sound("error" if result.has("error") else "sent")
	if not result.has("error"):
		if mission_client: session.apply_state(result.data)
		else: _update_social(result.data)

func _update_social(data: Dictionary) -> void:
	for message: Dictionary in data.get("forum_messages", []):
		if _social_ready and not _seen_forum_messages.has(message.id) and not message.get("read", false):
			_queue_message_notification("Nouveau MP de " + str(message.author) + " · BreachBoard", "BreachBoard")
		_seen_forum_messages[message.id] = true
	_profile["forum_counts"] = data.get("forum_counts", {}).duplicate(true)
	_world_time = str(data.get("time", ""))
	forum_view.set_world(data)
	for messenger: Messenger in messengers.values():
		messenger.set_journey(data.get("journey", {}))
		messenger.set_offers(data.get("offers", []))
	for messenger: Messenger in messengers.values(): messenger.set_contacts(data.get("contacts", []))
	for message: Dictionary in data.get("messages", []):
		var channel: String = str(message.get("channel", "chordly"))
		if messengers.has(channel):
			var app: String = {"chordly": "Chordly", "telegrid": "Telegrid", "sessyon": "Sessyon"}[channel]
			var notify: bool = active_app != app or messengers[channel].selected_peer != message.get("peer")
			var is_new: bool = not messengers[channel]._ids.has(str(message.get("id", "")))
			var announce: bool = _social_ready and notify and not str(message.get("id", "")).begins_with("group:")
			messengers[channel].add_message(message, announce)
			if announce and is_new and message.get("sender") != session.handle:
				_queue_message_notification("%s · %s" % [str(message.get("sender", "")), str(message.get("text", "")).left(110)], app, str(message.get("peer", "")))
	if not _social_ready and data.get("journey", {}).get("action", "") == "continue_campaign":
		messengers.chordly._select_peer("miette")
	_social_ready = true
	if _should_refresh_thread(): _load_thread(forum_view.selected_thread, true)

func _read_conversation(channel: String, peer: String) -> void:
	if session == null or "--offline-test" in OS.get_cmdline_user_args(): return
	await session.request("/api/social/read", {"channel": channel, "peer": peer})

func _load_messages() -> void:
	var result: Dictionary = await session.request("/api/messages", null, TYPE_ARRAY)
	if result.has("error"): return
	for message: Dictionary in result.data:
		var channel: String = message.get("channel", "chordly")
		if messengers.has(channel): messengers[channel].add_message(message, false)

## Le sujet ouvert n’est relu que si le joueur peut le voir : un onglet resté ouvert dans un
## BreachBoard réduit ne doit ni solliciter le moteur ni compter comme une lecture d’enquête.
func _should_refresh_thread() -> bool:
	return not forum_view.selected_thread.is_empty() and apps.has("BreachBoard") and apps.BreachBoard.is_visible_in_tree()

static func _thread_path(id: String, refresh: bool) -> String:
	return "/api/forum/threads/%s%s" % [id, "?refresh=true" if refresh else ""]

## refresh : relecture automatique du sujet ouvert (sondage social), sans compter une vue.
func _load_thread(id: String, refresh: bool = false) -> void:
	if "--offline-test" in OS.get_cmdline_user_args(): return
	if forum_view.selected_section == "Messages":
		# À l’ouverture, puis seulement tant que le moteur le dit encore non lu (échec précédent).
		if not refresh or forum_view.message_unread(id): await session.request("/api/forum/messages/%s/read" % id, {})
		return
	var result: Dictionary = await session.request(_thread_path(id, refresh), null, TYPE_ARRAY)
	if not result.has("error"):
		if not _profile.has("forum_counts"): _profile["forum_counts"] = {}
		_profile.forum_counts[id] = result.data.size()
		forum_view.set_replies(id, result.data)

func _reply_thread(id: String, text: String) -> void:
	if "--offline-test" in OS.get_cmdline_user_args(): return
	var result: Dictionary = await session.request("/api/forum/threads/%s" % id, {"handle": session.handle, "text": text}, TYPE_ARRAY)
	forum_view.acknowledge_reply(id, not result.has("error"), str(result.get("error", "")))
	_sound("error" if result.has("error") else "sent")
	if not result.has("error"):
		if not _profile.has("forum_counts"): _profile["forum_counts"] = {}
		_profile.forum_counts[id] = result.data.size()
		forum_view.set_replies(id, result.data)

func _select_route(index: int) -> void:
	var ids: Array[String] = ["freeshield", "nullvad", "tor", "relay"]
	var result: Dictionary = await session.request("/api/profile/route", {"route": ids[index]})
	if result.has("error"):
		_error(result.error)
		routes.select(maxi(0, ids.find(_profile.get("route", "freeshield"))))
	else: await _refresh_profile()

func _create_gophish() -> void:
	var body: VBoxContainer = _window("GoPhish", Vector2i(180, 85), Vector2i(1080, 700))
	apps.GoPhish.min_size = Vector2i(850, 500)
	gophish_view = GophishView.new()
	body.add_child(gophish_view)
	gophish_view.setup()
	gophish_view.reload_requested.connect(_refresh_gophish)
	gophish_view.api_requested.connect(_gophish_api)

func _open_service(_url: String) -> void:
	_open("GoPhish")

func _gophish_path() -> String:
	return "/api/workspace/gophish" if session.game_id.is_empty() else "/api/games/%s/gophish" % session.game_id

## background : rafraîchissement automatique (tick), sans effacer une saisie en cours.
func _refresh_gophish(background: bool = false) -> void:
	if _gophish_busy or "--offline-test" in OS.get_cmdline_user_args(): return
	if gophish_view.authenticated:
		await _gophish_api("GET", "snapshot", {}, background)
		return
	_gophish_busy = true
	var result: Dictionary = await session.request(_gophish_path() + "/status")
	_gophish_busy = false
	if result.has("error") or not result.data.get("running", false): gophish_view.show_disconnected()
	else: gophish_view.show_login()

func _gophish_api(method: String, endpoint: String, payload: Dictionary, background: bool = false) -> void:
	if "--offline-test" in OS.get_cmdline_user_args(): return
	if _gophish_busy:
		# Un rafraîchissement automatique peut céder sa place ; un clic du joueur (Sign in,
		# Launch Campaign…) attend la requête en cours au lieu de disparaître sans message.
		if background: return
		while _gophish_busy: await get_tree().process_frame
	_gophish_busy = true
	var body: Dictionary = {"username": gophish_view.username, "password": gophish_view.password, "method": method, "endpoint": endpoint}
	if method == "POST": body.payload = payload
	var result: Dictionary = await session.request(_gophish_path(), body)
	_gophish_busy = false
	if result.has("error"):
		gophish_view.fail(result.error)
		if str(result.error).contains("Unable to connect"): gophish_view.authenticated = false; gophish_view.show_disconnected()
	else: gophish_view.apply_data(result.data, background)

func _set_guidance(enabled: bool) -> void:
	if session == null or session.game_id.is_empty(): return
	var result: Dictionary = await session.request("/api/games/%s/guidance" % session.game_id, {"enabled": enabled})
	if result.has("error"):
		_guidance.set_pressed_no_signal(not enabled)
		_error(result.error)
	else:
		session.state["guidance_enabled"] = enabled

func _wait_world() -> void:
	if session == null or "--offline-test" in OS.get_cmdline_user_args(): return
	var payload: Dictionary = {"minutes": 5}
	if not session.game_id.is_empty(): payload["game_id"] = session.game_id
	var result: Dictionary = await session.request("/api/world/wait", payload)
	if result.has("error"):
		_error(result.error)
		return
	_update_social(result.data.social)
	if result.data.get("state") != null: session.apply_state(result.data.state)


func _manual_save() -> void:
	var result: Dictionary = await session.request("/api/saves/write", {"name": "Manuelle · " + Time.get_datetime_string_from_system()})
	if result.has("error"): _error(result.error)
	else: _notify("Partie sauvegardée. Les emplacements se gèrent depuis le menu d’accueil.", "Paramètres")

func _go_menu() -> void:
	var result: Dictionary = await session.request("/api/profile/menu", {})
	if result.has("error"): _error(result.error); return
	paused = true
	return_to_menu.emit()


func _open_contact(peer: String, channel: String) -> void:
	if not messengers.has(channel): return
	messengers[channel]._select_peer(peer)
	_open({"chordly": "Chordly", "telegrid": "Telegrid", "sessyon": "Sessyon"}[channel])

func _accept_invitation(id: String) -> void:
	var result: Dictionary = await session.request("/api/forum/messages/%s/accept" % id, {})
	if result.has("error"):
		_error(result.error)
		return
	_profile = result.data
	_render_board()
	await session.refresh_social()
	_notify("Invitation acceptée. Exployt est accessible après configuration de ta route Tor.", "BreachBoard")

func _refresh_wallet() -> void:
	if "--offline-test" in OS.get_cmdline_user_args(): return
	var result: Dictionary = await session.request("/api/wallet")
	wallet_view.set_data({} if result.has("error") else result.data, false, str(result.get("error", "")))

func _wallet_action(action: String, request_id: String) -> void:
	if _wallet_busy: return
	_wallet_busy = true
	var result: Dictionary = await session.request("/api/wallet/device", {"action": action, "request_id": request_id})
	_wallet_busy = false
	if result.has("error"):
		_sound("error")
		wallet_view.set_data(wallet_view._data, false, str(result.error))
	else:
		wallet_view.set_data(result.data)
		if action == "approve": _sound("confirm")
		await _refresh_profile()
		if apps.Boutique.opened: _refresh_shop()

func _sound(kind: String) -> void:
	var audio: Node = get_node_or_null("/root/Audio")
	if audio != null: audio.play_effect(kind)
