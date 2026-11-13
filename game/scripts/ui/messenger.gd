extends HBoxContainer
## Trois langages visuels de messagerie ; données et interactions communes.
const Avatars = preload("res://scripts/ui/avatars.gd")
const DraftStore = preload("res://scripts/ui/draft_store.gd")
const MessageRow = preload("res://scripts/ui/message_row.gd")
const Composer = preload("res://scripts/ui/message_composer.gd")
const SocialStyle = preload("res://scripts/ui/social_style.gd")
const UI = preload("res://scripts/ui/style.gd")
signal mission_requested(contract_id: String)
signal send_message(channel: String, text: String)
signal open_app(app_name: String)
signal continue_campaign
signal hint_requested(channel: String, peer: String)
signal unread_changed(count: int)
signal conversation_read(channel: String, peer: String)
var channel: String = "chordly"
var _last_contact_entries: Array = []
var local_handle: String = "operator"
var selected_peer: String = "k0rvid"
var unread: int = 0
var messages: Array[Dictionary] = []
var _ids: Dictionary = {}
var _contacts: Dictionary = {}
var contact_profiles: Dictionary = {}
var _unread_by_peer: Dictionary = {}
var _details_bio: RichTextLabel
var _sidebar: VBoxContainer
var _list: VBoxContainer
var _stream: VBoxContainer
var _scroll: ScrollContainer
var composer: TextEdit
var _header_name: Label
var _header_status: Label
var _search: LineEdit
var _find: LineEdit
var _details: PanelContainer
var _profile_name: Label
var _identity_avatar: PanelContainer
var _header_avatar: PanelContainer
var _details_avatar: PanelContainer
var _details_name: Label
var _status: Label
var _brand: String
var _colors: Dictionary
var _mission: Dictionary = {}
var _mission_panel: PanelContainer
var _mission_title: Label
var _mission_goal: RichTextLabel
var _hint_button: Button
var _hint_busy: bool = false
var _offers: Array = []
var _journey: Dictionary = {}
var _drafts: Dictionary = {}
var _draft_store: RefCounted = DraftStore.new()
var _draft_timer: Timer
var _latest_by_peer: Dictionary = {}
var _activity_by_peer: Dictionary = {}
var _find_panel: HBoxContainer
var _find_count: Label
var _find_previous: Button
var _find_next: Button
var _result_nodes: Array[Control] = []
var _result_index: int = -1
var _pending_new: int = 0
var _scroll_revision: int = 0
var _stream_rebuilding: bool = false
var _rebuild_version: int = 0
var _follow_latest: bool = true
var _new_messages_button: Button
var _sending_peer: String = ""
var _sending_text: String = ""
var _send_button: Button
var _rail: PanelContainer
var _side_panel: PanelContainer
var _conversation: PanelContainer
var _contacts_button: Button
var _details_requested: bool = false
var _show_contacts: bool = false
var _counter: Label
var _emoji: PopupMenu

func setup(kind: String, handle: String) -> void:
	_draft_timer = Timer.new()
	_draft_timer.one_shot = true
	_draft_timer.wait_time = 0.4
	_draft_timer.timeout.connect(_save_drafts)
	add_child(_draft_timer)
	channel = kind
	local_handle = handle
	selected_peer = {"chordly": "k0rvid", "telegrid": "relay", "sessyon": "spectre"}[kind]
	_brand = {"chordly": "Chordly", "telegrid": "Telegrid", "sessyon": "Sessyon"}[kind]
	_colors = {
		"chordly": {"rail": "1e1f22", "side": "2b2d31", "main": "313338", "input": "383a40", "accent": "5865f2", "muted": "a5adb8", "incoming": "313338", "outgoing": "313338"},
		"telegrid": {"rail": "17212b", "side": "17212b", "main": "0e1621", "input": "17212b", "accent": "5288c1", "muted": "7f91a4", "incoming": "182533", "outgoing": "2b5278"},
		"sessyon": {"rail": "101b1b", "side": "182525", "main": "101b1b", "input": "233333", "accent": "00b87b", "muted": "8ba39d", "incoming": "243533", "outgoing": "00664d"},
	}[kind]
	SocialStyle.apply(self, Color(_colors.side), Color(_colors.accent))
	name = _brand + "View"
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 0)
	if kind != "telegrid":
		_build_rail()
	_build_sidebar()
	_build_conversation()
	_build_details()
	_select_peer(selected_peer)
	resized.connect(_adapt_layout)
	_adapt_layout.call_deferred()

func _build_rail() -> void:
	var panel: PanelContainer = UI.panel(Color(_colors.rail), 9)
	_rail = panel
	panel.custom_minimum_size.x = 66
	add_child(panel)
	var column: VBoxContainer = VBoxContainer.new()
	column.add_theme_constant_override("separation", 14)
	panel.add_child(column)
	var home: Button = UI.button("CH" if channel == "chordly" else "S", func() -> void: _search.grab_focus(), Color(_colors.accent), 0)
	home.custom_minimum_size = Vector2(44, 44)
	home.tooltip_text = "Messages privés"
	column.add_child(home)
	column.add_child(HSeparator.new())
	var contacts: Button = UI.button("☷", func() -> void: _search.grab_focus(), Color(_colors.side))
	contacts.tooltip_text = "Rechercher un contact"
	column.add_child(contacts)
	var spacer: Control = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(spacer)
	var settings: Button = UI.button("⚙", func() -> void: open_app.emit("Paramètres"), Color(_colors.side))
	settings.tooltip_text = "Paramètres"
	column.add_child(settings)

func _build_sidebar() -> void:
	var panel: PanelContainer = UI.panel(Color(_colors.side))
	_side_panel = panel
	panel.custom_minimum_size.x = 248 if channel == "chordly" else 260
	add_child(panel)
	_sidebar = VBoxContainer.new()
	_sidebar.add_theme_constant_override("separation", 0)
	panel.add_child(_sidebar)
	var header: PanelContainer = UI.panel(Color(_colors.side), 12)
	_sidebar.add_child(header)
	var h: VBoxContainer = VBoxContainer.new()
	header.add_child(h)
	h.add_theme_constant_override("separation", 12)
	h.add_child(UI.label(_brand if channel != "chordly" else "Messages", 18))
	_search = LineEdit.new()
	_search.placeholder_text = "Rechercher" if channel != "chordly" else "Retrouver une conversation"
	_search.add_theme_font_size_override("font_size", 12)
	_search.add_theme_stylebox_override("normal", UI.box(Color(_colors.rail), Color.TRANSPARENT, 4, 7))
	_search.clear_button_enabled = true
	UI.field(_search, Color(_colors.rail), Color(_colors.accent))
	_search.text_changed.connect(func(_text: String) -> void: _render_contacts())
	h.add_child(_search)
	var label_panel: PanelContainer = UI.panel(Color(_colors.side), 12)
	label_panel.add_child(UI.label("MESSAGES PRIVÉS" if channel == "chordly" else "CONVERSATIONS", 11, Color(_colors.muted)))
	_sidebar.add_child(label_panel)
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_sidebar.add_child(scroll)
	_list = VBoxContainer.new()
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_list.add_theme_constant_override("separation", 4)
	scroll.add_child(_list)
	var identity: PanelContainer = UI.panel(Color(_colors.rail), 10)
	_sidebar.add_child(identity)
	var row: HBoxContainer = HBoxContainer.new()
	identity.add_child(row)
	_identity_avatar = _avatar(local_handle, 32, Color(_colors.accent))
	row.add_child(_identity_avatar)
	var lines: VBoxContainer = VBoxContainer.new()
	lines.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(lines)
	_profile_name = UI.label(local_handle, 13)
	_profile_name.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	lines.add_child(_profile_name)
	lines.add_child(UI.label("En ligne" if channel != "sessyon" else "Identité active", 11, Color(_colors.muted)))

func _build_conversation() -> void:
	var panel: PanelContainer = UI.panel(Color(_colors.main))
	_conversation = panel
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_child(panel)
	var column: VBoxContainer = VBoxContainer.new()
	column.add_theme_constant_override("separation", 0)
	panel.add_child(column)
	var header: PanelContainer = UI.panel(Color(_colors.side), 11)
	header.custom_minimum_size.y = 64
	column.add_child(header)
	var row: HBoxContainer = HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	header.add_child(row)
	_contacts_button = UI.icon_button("menu", "Afficher ou masquer les conversations", func() -> void: _show_contacts = not _show_contacts; _details_requested = false; _adapt_layout(), Color(_colors.side))
	_contacts_button.tooltip_text = "Afficher ou masquer les conversations"
	row.add_child(_contacts_button)
	_header_avatar = _avatar(selected_peer, 34, Color(_colors.accent))
	row.add_child(_header_avatar)
	var names: VBoxContainer = VBoxContainer.new()
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(names)
	_header_name = UI.label("k0rvid", 16)
	_header_name.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	names.add_child(_header_name)
	_header_status = UI.label("En ligne", 11, Color(_colors.muted))
	_header_status.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	names.add_child(_header_status)
	var find_button: Button = UI.icon_button("search", "Rechercher dans la conversation", _toggle_find, Color(_colors.side))
	find_button.tooltip_text = "Rechercher dans la conversation"
	row.add_child(find_button)
	var details_button: Button = UI.icon_button("info", "Afficher le profil du contact", func() -> void: _details_requested = not _details_requested; _show_contacts = false; _adapt_layout(), Color(_colors.side))
	details_button.tooltip_text = "Afficher le profil du contact"
	row.add_child(details_button)
	_mission_panel = UI.panel(Color(_colors.side), 8)
	_mission_panel.name = "MissionToolbar"
	column.add_child(_mission_panel)
	var mission_column: VBoxContainer = VBoxContainer.new()
	mission_column.add_theme_constant_override("separation", 6)
	_mission_panel.add_child(mission_column)
	_mission_title = UI.label("", 13, Color(_colors.muted))
	_mission_title.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	mission_column.add_child(_mission_title)
	var mission_actions: HFlowContainer = HFlowContainer.new()
	mission_actions.add_theme_constant_override("h_separation", 6)
	mission_actions.add_theme_constant_override("v_separation", 4)
	mission_column.add_child(mission_actions)
	var console_button: Button = UI.button("Console", func() -> void: open_app.emit("Terminal"), Color(_colors.input), 6)
	console_button.tooltip_text = "Ouvrir le terminal principal · Ctrl+Alt+T ouvre une autre console"
	mission_actions.add_child(console_button)
	var goal_button: Button = UI.button("Objectif", _toggle_mission_goal, Color(_colors.input), 6)
	goal_button.tooltip_text = "Afficher le but du dossier sans quitter la conversation"
	mission_actions.add_child(goal_button)
	_hint_button = UI.button("Indice", _request_hint, Color(_colors.input), 6)
	_hint_button.tooltip_text = "Demander un indice au client sans modifier ton brouillon ; les indices deviennent progressivement plus précis"
	mission_actions.add_child(_hint_button)
	_mission_goal = UI.rich("", 13)
	_mission_goal.fit_content = false
	_mission_goal.scroll_active = true
	_mission_goal.custom_minimum_size.y = 26
	_mission_goal.resized.connect(_fit_mission_goal)
	_mission_goal.visible = false
	mission_column.add_child(_mission_goal)
	_mission_panel.visible = false
	_find_panel = HBoxContainer.new()
	_find_panel.visible = false
	column.add_child(_find_panel)
	_find = LineEdit.new()
	_find.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_find.placeholder_text = "Rechercher dans cette conversation…"
	_find.clear_button_enabled = true
	UI.field(_find, Color(_colors.input), Color(_colors.accent))
	_find.text_changed.connect(func(_text: String) -> void:
		_result_index = 0
		_render_messages())
	_find.text_submitted.connect(func(_text: String) -> void: _navigate_result(1))
	_find.gui_input.connect(func(event: InputEvent) -> void:
		if event is InputEventKey and event.pressed:
			if event.keycode == KEY_ESCAPE:
				_toggle_find()
				_find.accept_event()
			elif event.keycode == KEY_ENTER and event.shift_pressed:
				_navigate_result(-1)
				_find.accept_event())
	_find_panel.add_child(_find)
	_find_count = UI.label("", 11, Color(_colors.muted))
	_find_count.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_find_panel.add_child(_find_count)
	_find_previous = UI.button("↑", func() -> void: _navigate_result(-1), Color(_colors.side))
	_find_previous.tooltip_text = "Résultat précédent · Maj+Entrée"
	_find_panel.add_child(_find_previous)
	_find_next = UI.button("↓", func() -> void: _navigate_result(1), Color(_colors.side))
	_find_next.tooltip_text = "Résultat suivant · Entrée"
	_find_panel.add_child(_find_next)
	_scroll = ScrollContainer.new()
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_scroll.resized.connect(_stream_resized)
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(_scroll)
	_scroll.get_v_scroll_bar().value_changed.connect(func(_value: float) -> void:
		if not _stream_rebuilding: _follow_latest = _at_bottom()
		_update_new_messages())
	var margin: MarginContainer = MarginContainer.new()
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	margin.add_theme_constant_override("margin_left", 18)
	margin.add_theme_constant_override("margin_right", 18)
	margin.add_theme_constant_override("margin_top", 18)
	margin.add_theme_constant_override("margin_bottom", 15)
	_scroll.add_child(margin)
	_stream = VBoxContainer.new()
	_stream.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_stream.add_theme_constant_override("separation", 8 if channel == "chordly" else 7)
	margin.add_child(_stream)
	_new_messages_button = UI.button("Nouveaux messages ↓", _jump_to_latest, Color(_colors.accent))
	_new_messages_button.visible = false
	_new_messages_button.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_new_messages_button.tooltip_text = "Rejoindre les derniers messages"
	column.add_child(_new_messages_button)
	var composer_panel: PanelContainer = UI.panel(Color(_colors.main), 14)
	column.add_child(composer_panel)
	var composer_column: VBoxContainer = VBoxContainer.new()
	composer_panel.add_child(composer_column)
	_status = UI.label("", 11, Color(_colors.muted))
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	composer_column.add_child(_status)
	var input_panel: PanelContainer = UI.panel(Color(_colors.input), 6, 9)
	composer_column.add_child(input_panel)
	var input_row: HBoxContainer = HBoxContainer.new()
	input_panel.add_child(input_row)
	var attach: Button = UI.icon_button("attach", "Ouvrir les fichiers", func() -> void: open_app.emit("Fichiers"), Color(_colors.input))
	attach.tooltip_text = "Ouvrir les fichiers"
	attach.size_flags_vertical = Control.SIZE_SHRINK_END
	input_row.add_child(attach)
	composer = Composer.new()
	composer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	composer.placeholder_text = "Envoyer un message à @k0rvid"
	composer.custom_minimum_size.y = 44
	composer.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	composer.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	composer.scroll_fit_content_height = false
	UI.field(composer, Color(_colors.input), Color(_colors.accent))
	composer.add_theme_stylebox_override("normal", UI.box(Color(_colors.input), Color.TRANSPARENT, 5, 8))
	composer.submitted.connect(_send)
	input_row.add_child(composer)
	var emoji_button: Button = UI.icon_button("smile", "Réponses rapides", _show_emoji, Color(_colors.input))
	emoji_button.tooltip_text = "Réponses rapides"
	emoji_button.size_flags_vertical = Control.SIZE_SHRINK_END
	input_row.add_child(emoji_button)
	_send_button = UI.icon_button("send", "Envoyer le message · Entrée", _send, Color(_colors.accent))
	_send_button.tooltip_text = "Envoyer le message · Entrée"
	_send_button.size_flags_vertical = Control.SIZE_SHRINK_END
	_send_button.disabled = true
	input_row.add_child(_send_button)
	composer.text_changed.connect(_update_send_button)
	composer.resized.connect(_fit_composer)
	var hints: HBoxContainer = HBoxContainer.new()
	composer_column.add_child(hints)
	var hint: Label = UI.label("Entrée : envoyer · Maj+Entrée : nouvelle ligne", 10, Color(_colors.muted))
	hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hint.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	hints.add_child(hint)
	_counter = UI.label("0 / 2 000", 10, Color(_colors.muted))
	hints.add_child(_counter)
	_emoji = PopupMenu.new()
	for emoji: String in ["👍", "Merci !", "Bien reçu.", "Je m'en occupe."]:
		_emoji.add_item(emoji)
	_emoji.id_pressed.connect(func(id: int) -> void: composer.text += _emoji.get_item_text(id); _update_send_button(); composer.grab_focus())
	add_child(_emoji)

func _build_details() -> void:
	_details = UI.panel(Color(_colors.side), 18)
	_details.custom_minimum_size.x = 175
	_details.visible = false
	add_child(_details)
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_details.add_child(scroll)
	var box: VBoxContainer = VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override("separation", 15)
	scroll.add_child(box)
	_details_avatar = _avatar(selected_peer, 70, Color(_colors.accent))
	box.add_child(_details_avatar)
	_details_name = UI.wrapped(selected_peer, 18)
	box.add_child(_details_name)
	box.add_child(UI.label("PROFIL DU CONTACT", 11, Color(_colors.muted)))
	_details_bio = UI.rich("Consulte la réputation et l’historique de ce contact sur le forum avant d’accepter son contrat.", 13)
	box.add_child(_details_bio)
	box.add_child(UI.button("Voir le forum", func() -> void: open_app.emit("BreachBoard"), Color(_colors.accent)))

func _avatar(handle: String, diameter: int, color: Color) -> PanelContainer:
	var p: PanelContainer = UI.panel(color, 0, diameter / 2)
	p.custom_minimum_size = Vector2(diameter, diameter)
	p.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	p.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	var text: Label = UI.label(handle.left(1).to_upper(), maxi(13, diameter / 2), Color.WHITE)
	text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	p.add_child(text)
	Avatars.apply(p,handle,true)
	return p

func set_identity(handle: String) -> void:
	local_handle = handle
	_profile_name.text = handle
	_identity_avatar.get_child(0).text = handle.left(1).to_upper()
	if not handle.is_empty() and _draft_store.identity != handle:
		_save_drafts()
		_draft_store.configure(handle, channel)
		_drafts = _draft_store.values.duplicate(true)
		composer.text = str(_drafts.get(selected_peer, ""))
		_update_send_button()

func add_message(message: Dictionary, notify: bool = true) -> void:
	var id: String = str(message.get("id", JSON.stringify(message)))
	if _ids.has(id):
		# _ids donne la position du message : le bureau renvoie toute l'archive à chaque sondage,
		# et la reparcourir en entier pour chaque message coûtait un temps quadratique.
		var index: int = int(_ids[id])
		if index < 0 or index >= messages.size() or str(messages[index].get("id", "")) != id:
			index = -1
			for candidate: int in range(messages.size()):
				if str(messages[candidate].get("id", "")) == id:
					index = candidate
					break
			_ids[id] = index
		if index >= 0 and messages[index] != message:
			messages[index] = message.duplicate(true)
			_rebuild_contact_activity()
			_render_contacts()
			if message.get("peer") == selected_peer: _render_messages()
		return
	_ids[id] = messages.size()
	messages.append(message.duplicate(true))
	var peer: String = str(message.get("peer", message.get("sender", "k0rvid")))
	if peer == local_handle:
		peer = selected_peer
	_contacts[peer] = str(message.get("text", "")).replace("\n", " ")
	_rebuild_contact_activity()
	if notify and message.get("sender") != local_handle:
		_unread_by_peer[peer] = int(_unread_by_peer.get(peer, 0)) + 1
		unread += 1
		unread_changed.emit(unread)
	_render_contacts()
	if peer == selected_peer:
		if message.get("sender") != local_handle and is_visible_in_tree() and (not _at_bottom() or not _find.text.is_empty()):
			_pending_new += 1
		_render_messages()
		_update_new_messages()

func mark_read() -> void:
	unread = maxi(0, unread - int(_unread_by_peer.get(selected_peer, 0)))
	_unread_by_peer[selected_peer] = 0
	unread_changed.emit(unread)
	conversation_read.emit(channel, selected_peer)

func _render_contacts() -> void:
	UI.clear(_list)
	if _contacts.is_empty():
		_contacts[selected_peer] = "Aucune conversation pour l'instant"
	var shown: int = 0
	for peer: String in _ordered_peers():
		var info: Dictionary = contact_profiles.get(peer, {})
		var searchable: String = peer + " " + str(info.get("name", "")) + " " + str(_contacts[peer])
		if not _search.text.strip_edges().is_empty() and not searchable.to_lower().contains(_search.text.strip_edges().to_lower()):
			continue
		shown += 1
		var selected: bool = peer == selected_peer
		var count: int = int(_unread_by_peer.get(peer, 0))
		var fill: Color = Color(_colors.input) if selected else Color(_colors.side)
		var button: Button = UI.button("", func() -> void: _select_peer(peer), fill, 8)
		var selected_style: StyleBoxFlat = UI.box(fill, Color(_colors.accent) if selected else Color.TRANSPARENT, 6, 8)
		selected_style.border_width_top = 0
		selected_style.border_width_right = 0
		selected_style.border_width_bottom = 0
		selected_style.border_width_left = 3 if selected else 0
		button.add_theme_stylebox_override("normal", selected_style)
		button.set_meta("peer", peer)
		button.tooltip_text = str(info.get("name", peer)) + "\n" + str(_contacts[peer]).left(120)
		button.custom_minimum_size.y = 72
		_list.add_child(button)
		var row: HBoxContainer = HBoxContainer.new()
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.add_theme_constant_override("separation", 10)
		row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		row.offset_left = 12
		row.offset_right = -10
		row.offset_top = 12
		row.offset_bottom = -12
		button.add_child(row)
		var portrait: PanelContainer = _avatar(peer, 38, Color(_colors.accent))
		portrait.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		row.add_child(portrait)
		var labels: VBoxContainer = VBoxContainer.new()
		labels.mouse_filter = Control.MOUSE_FILTER_IGNORE
		labels.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		labels.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		labels.add_theme_constant_override("separation", 4)
		row.add_child(labels)
		var title: Label = UI.label(("# " if info.get("kind") == "group" else "") + str(info.get("name", peer)), 14, Color.WHITE if count > 0 or selected else Color("d4dbe4"))
		title.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		labels.add_child(title)
		var preview: Label = UI.label(str(_contacts[peer]), 12, Color(_colors.muted).lightened(0.1) if count > 0 else Color(_colors.muted))
		preview.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		preview.clip_text = true
		labels.add_child(preview)
		var metadata: VBoxContainer = VBoxContainer.new()
		metadata.mouse_filter = Control.MOUSE_FILTER_IGNORE
		metadata.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		metadata.add_theme_constant_override("separation", 6)
		row.add_child(metadata)
		var activity: Array = _activity_by_peer.get(peer, [])
		if activity.size() > 1 and int(activity[1]) >= 0 and int(activity[1]) < messages.size():
			var stamp: Label = UI.label(str(messages[int(activity[1])].get("time", "")).right(5), 10, Color(_colors.accent).lightened(0.25) if count > 0 else Color(_colors.muted))
			stamp.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
			metadata.add_child(stamp)
		if count > 0:
			var badge: PanelContainer = UI.panel(Color(_colors.accent), 4, 9)
			badge.mouse_filter = Control.MOUSE_FILTER_IGNORE
			badge.size_flags_horizontal = Control.SIZE_SHRINK_END
			badge.add_child(UI.label(str(count) if count < 100 else "99+", 11, Color.WHITE))
			metadata.add_child(badge)
	if shown == 0:
		var empty: PanelContainer = UI.panel(Color(_colors.side), 14)
		var text: Label = UI.label("Aucune conversation trouvée.\nEssaie un nom ou un mot du message.", 12, Color(_colors.muted))
		text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		empty.add_child(text)
		_list.add_child(empty)

func _update_send_button() -> void:
	var length: int = composer.text.length()
	_send_button.disabled = composer.text.strip_edges().is_empty() or length > 2000 or not _sending_peer.is_empty()
	if is_instance_valid(_counter):
		_counter.text = "%s / 2 000" % length
		_counter.add_theme_color_override("font_color", Color("ffb4a6") if length > 2000 else Color(_colors.muted))
	_drafts[selected_peer] = composer.text
	_draft_timer.start()
	_fit_composer.call_deferred()

func _select_peer(peer: String) -> void:
	_save_drafts()
	_drafts[selected_peer] = composer.text
	_pending_new = 0
	selected_peer = peer
	_refresh_mission_context()
	_show_contacts = false
	_status.text = "Envoi…" if peer == _sending_peer else ""
	_adapt_layout.call_deferred()
	composer.text = str(_drafts.get(peer, ""))
	composer.editable = peer != _sending_peer
	_find.clear()
	_result_index = -1
	_update_new_messages()
	var info: Dictionary = contact_profiles.get(peer, {})
	_header_name.text = str(info.get("name", peer))
	_header_avatar.get_child(0).text = peer.left(1).to_upper()
	_details_avatar.get_child(0).text = peer.left(1).to_upper()
	Avatars.apply(_header_avatar,peer,true)
	Avatars.apply(_details_avatar,peer,true)
	_details_name.text = str(info.get("name", peer))
	_update_contact_header()
	_details_bio.text = str(info.get("bio", "Consulte l’historique de ce contact sur le forum."))
	composer.placeholder_text = "Envoyer un message à @" + peer
	_update_send_button()
	mark_read()
	_render_contacts()
	_render_messages()
	_scroll_bottom()

func _render_messages() -> void:
	_stream_rebuilding = true
	_rebuild_version += 1
	_scroll_revision += 1
	var bar: VScrollBar = _scroll.get_v_scroll_bar()
	var follow: bool = bar.value >= bar.max_value - bar.page - 20
	var previous: float = bar.value
	_result_nodes.clear()
	UI.clear(_stream)
	var visible_messages: int = 0
	var last_date: String = ""
	var previous_sender: String = ""
	var previous_time: String = ""
	for message: Dictionary in messages:
		if str(message.get("peer", message.get("sender", ""))) != selected_peer:
			continue
		var text: String = str(message.get("text", ""))
		if not _find.text.is_empty() and not text.to_lower().contains(_find.text.to_lower()):
			continue
		visible_messages += 1
		var date_text: String = str(message.get("time", ""))
		date_text = date_text.left(5) if date_text.length() >= 11 and date_text[2] == "/" else "AUJOURD’HUI"
		var new_day: bool = date_text != last_date
		if new_day:
			var date: Label = UI.label(date_text, 11, Color(_colors.muted))
			date.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			var divider: HBoxContainer = HBoxContainer.new()
			divider.add_theme_constant_override("separation", 12)
			for side: int in range(2):
				var line: HSeparator = HSeparator.new()
				line.add_theme_stylebox_override("separator", SocialStyle.divider(Color(_colors.side).lightened(0.08)))
				line.size_flags_horizontal = Control.SIZE_EXPAND_FILL
				line.size_flags_vertical = Control.SIZE_SHRINK_CENTER
				divider.add_child(line)
				if side == 0: divider.add_child(date)
			_stream.add_child(divider)
			last_date = date_text
		var sender: String = str(message.get("sender", "?"))
		var current_time: String = str(message.get("time", ""))
		var grouped: bool = not new_day and previous_sender == sender and _same_message_group(previous_time, current_time)
		var outgoing: bool = sender == local_handle
		var row: Container = HBoxContainer.new() if channel == "chordly" else MessageRow.new()
		row.add_theme_constant_override("separation", 12)
		row.set_meta("message_group_start", not grouped)
		var spacing: MarginContainer = MarginContainer.new()
		spacing.add_theme_constant_override("margin_top", 10 if not grouped and visible_messages > 1 else 0)
		_stream.add_child(spacing)
		spacing.add_child(row)
		if not _find.text.is_empty(): _result_nodes.append(spacing)
		if channel == "chordly":
			if grouped:
				var gutter: Control = Control.new()
				gutter.custom_minimum_size.x = 38
				row.add_child(gutter)
			else:
				row.add_child(_avatar(sender, 38, Color("5865f2") if outgoing else Color("657c8a")))
		var bubble: PanelContainer = UI.panel(Color(_colors.outgoing if outgoing else _colors.incoming), 0 if channel == "chordly" else 10, 0 if channel == "chordly" else 9)
		if channel == "chordly":
			bubble.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		else:
			var longest: float = 0
			for line: String in text.split("\n"):
				longest = maxf(longest, UI.FONT.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x)
			row.natural_width = maxf(150, longest + 28)
			row.outgoing = outgoing
			bubble.size_flags_horizontal = Control.SIZE_FILL
		row.add_child(bubble)
		if not _find.text.is_empty() and _result_nodes.size() - 1 == _result_index:
			bubble.add_theme_stylebox_override("panel", UI.box(Color(_colors.input), Color(_colors.accent), 6, 10))
		var body: VBoxContainer = VBoxContainer.new()
		body.add_theme_constant_override("separation", 5)
		bubble.add_child(body)
		if channel == "chordly" and not grouped:
			var meta: HBoxContainer = HBoxContainer.new()
			body.add_child(meta)
			var sender_name: Label = UI.label(str(message.get("sender", "")), 14, Color("e2e7ed"))
			sender_name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			sender_name.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
			meta.add_child(sender_name)
			meta.add_child(UI.label("  " + str(message.get("time", "maintenant")).right(5), 11, Color(_colors.muted)))
		if channel != "chordly" and not outgoing and not grouped and contact_profiles.get(selected_peer, {}).get("kind") == "group":
			body.add_child(UI.wrapped(sender, 12, Color(_colors.accent).lightened(0.3)))
		_message_body(body, text)
		if message.get("link", false):
			var link: Button = UI.button("", func() -> void: open_app.emit("BreachBoard"), Color(_colors.input), 12)
			link.custom_minimum_size.y = 66
			link.tooltip_text = "Ouvrir le sujet sur BreachBoard"
			var preview: VBoxContainer = VBoxContainer.new()
			preview.mouse_filter = Control.MOUSE_FILTER_IGNORE
			preview.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
			preview.offset_left = 14
			preview.offset_right = -14
			preview.offset_top = 10
			preview.offset_bottom = -10
			preview.add_theme_constant_override("separation", 4)
			preview.add_child(UI.label("BREACHBOARD · SUJET DU FORUM", 10, Color(_colors.muted)))
			var caption: Label = UI.label("Consulter l’annonce et les échanges  ↗", 14, Color(_colors.accent).lightened(0.35))
			caption.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
			preview.add_child(caption)
			link.add_child(preview)
			body.add_child(link)
		if channel != "chordly":
			var stamp: Label = UI.label(str(message.get("time", "maintenant")).right(5) + (("  ✓✓" if message.get("status") == "read" else "  ✓") if outgoing else ""), 10, Color(_colors.muted))
			stamp.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
			body.add_child(stamp)
		previous_sender = sender
		previous_time = current_time
	if visible_messages == 0:
		var empty: PanelContainer = UI.panel(Color(_colors.main), 24)
		var text: Label = UI.label("Aucun message correspondant à la recherche." if not _find.text.is_empty() else "Le début de votre conversation avec " + _header_name.text + ".", 14, Color(_colors.muted))
		text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		empty.add_child(text)
		_stream.add_child(empty)
	if _find.text.is_empty() and contact_profiles.get(selected_peer, {}).get("typing", false):
		_stream.add_child(UI.label(selected_peer + " écrit…", 12, Color(_colors.muted)))
	if not _journey.is_empty() and _journey.get("peer", "") == selected_peer and _find.text.is_empty() and not _offers.any(func(offer: Dictionary) -> bool: return offer.get("peer") == selected_peer and _is_next_offer(offer)):
		var next_panel: PanelContainer = UI.panel(Color(_colors.side), 14, 7)
		next_panel.name = "NextStep"
		var next_content: VBoxContainer = VBoxContainer.new()
		next_content.add_theme_constant_override("separation", 8)
		next_panel.add_child(next_content)
		next_content.add_child(UI.wrapped(str(_journey.get("title", "Prochaine piste")), 15, Color(_colors.accent).lightened(0.3)))
		next_content.add_child(UI.rich(str(_journey.get("detail", "")), 13, Color(_colors.muted)))
		var destination: String = str(_journey.get("app", "Chordly"))
		if _journey.get("action", "") == "continue_campaign":
			next_content.add_child(UI.button("Continuer la campagne", func() -> void: continue_campaign.emit(), Color(_colors.accent)))
		if destination != _brand:
			next_content.add_child(UI.button("Ouvrir " + destination, func() -> void: open_app.emit(destination), Color(_colors.input)))
		_stream.add_child(next_panel)

	for offer: Dictionary in _offers:
		if offer.get("peer") != selected_peer or not _find.text.is_empty(): continue
		var card: PanelContainer = UI.panel(Color(_colors.input), 16, 8)
		_stream.add_child(card)
		var content: VBoxContainer = VBoxContainer.new()
		content.add_theme_constant_override("separation", 10)
		card.add_child(content)
		content.add_child(UI.wrapped(str(_journey.get("title", "DOSSIER PROPOSÉ")) if _is_next_offer(offer) else "DOSSIER FACULTATIF" if offer.get("side_job", false) else "DOSSIER PROPOSÉ", 11, Color(_colors.muted)))
		content.add_child(UI.wrapped(offer.title, 18))
		var description: Label = UI.label(offer.text, 13)
		description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		content.add_child(description)
		if _is_next_offer(offer):
			content.add_child(UI.rich(str(_journey.get("detail", "")), 13, Color(_colors.muted)))
		content.add_child(UI.label("Prime : %s ₵" % int(offer.reward), 12, Color(_colors.muted)))
		var blocked: String = str(offer.get("reason", ""))
		if not blocked.is_empty(): content.add_child(UI.wrapped(blocked, 12, Color(_colors.muted)))
		var accept: Button = UI.button("Reprendre le dossier" if offer.get("active", false) else "Ouvrir le dossier", func() -> void: mission_requested.emit(offer.id), Color(_colors.accent))
		accept.disabled = not blocked.is_empty()
		accept.tooltip_text = blocked
		content.add_child(accept)
	_refresh_find_controls()
	if not _result_nodes.is_empty():
		_reveal_result.call_deferred(weakref(_result_nodes[_result_index]))
	elif follow and _find.text.is_empty():
		_scroll_bottom()
	else:
		_scroll.set_deferred("scroll_vertical", int(previous))
	_finish_stream_rebuild(_rebuild_version)

func _finish_stream_rebuild(version: int) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	if not is_inside_tree() or version != _rebuild_version: return
	_stream_rebuilding = false
	_follow_latest = _at_bottom()

func _stream_resized() -> void:
	_adapt_layout()
	if not _stream_rebuilding and _follow_latest and _find.text.is_empty(): _scroll_bottom()

func _scroll_bottom() -> void:
	_scroll_revision += 1
	var revision: int = _scroll_revision
	await get_tree().process_frame
	if not is_inside_tree() or revision != _scroll_revision: return
	_scroll.scroll_vertical = int(_scroll.get_v_scroll_bar().max_value)
	_update_new_messages()

func _show_emoji() -> void:
	_emoji.position = Vector2i(get_global_mouse_position())
	_emoji.popup()

func _send() -> void:
	var text: String = composer.text.strip_edges()
	if text.is_empty() or not _sending_peer.is_empty(): return
	if composer.text.length() > 2000:
		_status.text = "Le message est limité à 2 000 caractères."
		return
	_sending_peer = selected_peer
	_sending_text = composer.text
	composer.editable = false
	_status.text = "Envoi…"
	_update_send_button()
	send_message.emit(channel, text)

func acknowledge(sent: bool, error: String = "") -> void:
	if sent: _drafts.erase(_sending_peer)
	if selected_peer == _sending_peer:
		_status.text = "" if sent else error
		if sent and composer.text == _sending_text: composer.clear()
	_sending_peer = ""
	_sending_text = ""
	composer.editable = true
	_update_send_button()
	_save_drafts()

func message_text() -> String:
	var lines: PackedStringArray = []
	for message: Dictionary in messages:
		lines.append(str(message.get("text", "")))
	return "\n".join(lines)

func set_contacts(entries: Array) -> void:
	# Sondage social toutes les 6 s : aucune reconstruction si les contacts n’ont pas changé.
	var relevant: Array = entries.filter(func(entry: Dictionary) -> bool: return entry.get("channel") == channel)
	if relevant == _last_contact_entries: return
	_last_contact_entries = relevant.duplicate(true)
	_rebuild_contact_activity()
	for entry: Dictionary in entries:
		if entry.get("channel") != channel: continue
		var peer: String = entry.id
		contact_profiles[peer] = entry.duplicate(true)
		if not _contacts.has(peer): _contacts[peer] = str(entry.get("bio", "" )).left(38)
	_render_contacts()
	_update_contact_header()

func _update_contact_header() -> void:
	var info: Dictionary = contact_profiles.get(selected_peer, {})
	_header_name.text = str(info.get("name", selected_peer))
	if info.get("kind") == "group":
		_header_status.text = "%s membres · %s" % [info.get("members", []).size(), "écrit…" if info.get("typing", false) else "discussion de groupe"]
	else:
		_header_status.text = "écrit…" if info.get("typing", false) else str(info.get("status_text", "Conversation privée"))

func _message_body(body: VBoxContainer, text: String) -> void:
	# Les blocs de code sont copiables séparément : aucune sélection du guide entier.
	var parts: PackedStringArray = text.split("`")
	for index: int in range(parts.size()):
		if parts[index].is_empty(): continue
		if index % 2 == 0:
			body.add_child(UI.rich(parts[index], 15))
		else:
			var code: String = parts[index]
			var panel: PanelContainer = UI.panel(Color(_colors.rail), 7, 4)
			body.add_child(panel)
			var row: HBoxContainer = HBoxContainer.new()
			panel.add_child(row)
			var command: LineEdit = LineEdit.new()
			command.text = code
			command.editable = false
			command.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			command.add_theme_font_override("font", UI.MONO)
			row.add_child(command)
			row.add_child(UI.button("Copier", func() -> void:
				DisplayServer.clipboard_set(code)
				_status.text = "Commande copiée · colle-la dans le terminal, puis Entrée.", Color(_colors.input), 5))


func _toggle_mission_goal() -> void:
	var follow: bool = _at_bottom() and _find.text.is_empty()
	_mission_goal.visible = not _mission_goal.visible
	_fit_mission_goal.call_deferred()
	if follow: _scroll_bottom()

func _fit_mission_goal() -> void:
	if not is_instance_valid(_mission_goal) or not _mission_goal.visible: return
	_mission_goal.custom_minimum_size.y = clampf(_mission_goal.get_content_height() + 4, 26, 56)

func _request_hint() -> void:
	if not _hint_busy and _mission.get("running", false) and _mission.get("client", "") == selected_peer:
		hint_requested.emit(channel, selected_peer)

func set_mission_context(value: Dictionary) -> void:
	if _mission.get("contract_id", "") != value.get("contract_id", ""):
		_mission_goal.visible = false
	_mission = value.duplicate(true)
	_refresh_mission_context()

func set_hint_busy(value: bool) -> void:
	_hint_busy = value
	_hint_button.disabled = value or not _mission.get("running", false)
	_hint_button.text = "Demande…" if value else "Indice"

func _refresh_mission_context() -> void:
	if not is_instance_valid(_mission_panel): return
	_mission_panel.visible = _mission.get("running", false) and _mission.get("client", "") == selected_peer
	_mission_title.text = str(_mission.get("title", "Dossier en cours"))
	_mission_title.tooltip_text = _mission_title.text
	_mission_goal.text = str(_mission.get("goal", ""))
	_fit_mission_goal.call_deferred()
	_hint_button.disabled = _hint_busy or not _mission.get("running", false)

func set_journey(value: Dictionary) -> void:
	var destination: String = str(value.get("app", ""))
	var relevant: Dictionary = {} if destination in ["Chordly", "Telegrid", "Sessyon"] and destination != _brand else value
	if _journey == relevant: return
	_journey = relevant.duplicate(true)
	_render_messages()

func _is_next_offer(offer: Dictionary) -> bool:
	return _journey.get("peer", "") == selected_peer and str(_journey.get("contract_id", "")) == str(offer.get("id", ""))

func set_offers(value: Array) -> void:
	var relevant: Array = value.filter(func(offer: Dictionary) -> bool: return offer.get("channel", channel) == channel)
	if _offers == relevant: return
	_offers = relevant.duplicate(true)
	_render_messages()

func _adapt_layout() -> void:
	if not is_instance_valid(_side_panel): return
	var narrow: bool = size.x < 760
	if is_instance_valid(_rail): _rail.visible = size.x >= 950
	_side_panel.custom_minimum_size.x = 190 if narrow else (228 if size.x < 950 else 248)
	_side_panel.visible = not narrow or _show_contacts
	_contacts_button.visible = narrow
	_details.visible = _details_requested
	if _details_requested and size.x < 1000: _side_panel.visible = false
	_details.custom_minimum_size.x = 160 if narrow else 190

func _same_message_group(previous: String, current: String) -> bool:
	if previous.is_empty() or current.is_empty(): return false
	var before: PackedStringArray = previous.right(5).split(":")
	var after: PackedStringArray = current.right(5).split(":")
	if before.size() != 2 or after.size() != 2: return false
	for part: String in [before[0], before[1], after[0], after[1]]:
		if not part.is_valid_int(): return false
	var delta: int = int(after[0]) * 60 + int(after[1]) - int(before[0]) * 60 - int(before[1])
	return delta >= 0 and delta <= 5

func _fit_composer() -> void:
	var lines: int = 0
	for index: int in range(composer.get_line_count()):
		lines += 1 + composer.get_line_wrap_count(index)
		if lines >= 5: break
	composer.custom_minimum_size.y = clampf(22 + lines * 19, 44, 120)

func _toggle_find() -> void:
	_find_panel.visible = not _find_panel.visible
	if _find_panel.visible: _find.grab_focus()
	else:
		_find.clear()
		_result_index = -1
		_render_messages()

func _refresh_find_controls() -> void:
	var count: int = _result_nodes.size()
	_result_index = clampi(_result_index, 0, count - 1) if count > 0 else -1
	_find_count.text = "%s / %s" % [_result_index + 1, count] if count > 0 else "0 résultat"
	_find_count.visible = not _find.text.is_empty()
	_find_previous.disabled = count == 0
	_find_next.disabled = count == 0

func _navigate_result(step: int) -> void:
	if _result_nodes.is_empty(): return
	_result_index = posmod(_result_index + step, _result_nodes.size())
	_render_messages()

func _at_bottom() -> bool:
	var bar: VScrollBar = _scroll.get_v_scroll_bar()
	return bar.value >= bar.max_value - bar.page - 20

func _update_new_messages() -> void:
	if not is_instance_valid(_new_messages_button): return
	if _at_bottom() and _find.text.is_empty(): _pending_new = 0
	_new_messages_button.visible = _pending_new > 0
	_new_messages_button.text = "%s nouveau%s message%s ↓" % [mini(_pending_new, 99), "x" if _pending_new > 1 else "", "s" if _pending_new > 1 else ""]

func _jump_to_latest() -> void:
	_pending_new = 0
	_find.clear()
	_find_panel.hide()
	_update_new_messages()
	_scroll_bottom()

func _activity_key(message: Dictionary) -> int:
	var time: String = str(message.get("time", ""))
	var clock_parts: PackedStringArray = time.right(5).split(":")
	if clock_parts.size() == 2 and clock_parts[0].is_valid_int() and clock_parts[1].is_valid_int():
		var day: int = 0
		if time.length() >= 11 and time[2] == "/": day = int(time.substr(3, 2)) * 31 + int(time.left(2))
		return (day * 24 + int(clock_parts[0])) * 60 + int(clock_parts[1])
	return int(message.get("minute", -1000000))

func _rebuild_contact_activity() -> void:
	_latest_by_peer.clear()
	_activity_by_peer.clear()
	for index: int in range(messages.size()):
		var message: Dictionary = messages[index]
		var peer: String = str(message.get("peer", message.get("sender", "")))
		if peer == local_handle: peer = selected_peer
		var key: int = _activity_key(message)
		var previous: Array = _activity_by_peer.get(peer, [-1000000000, -1])
		if key > int(previous[0]) or (key == int(previous[0]) and index > int(previous[1])):
			_activity_by_peer[peer] = [key, index]
			_latest_by_peer[peer] = str(message.get("text", "")).replace("\n", " ")
	for peer: String in _latest_by_peer: _contacts[peer] = _latest_by_peer[peer]

func _ordered_peers() -> Array:
	var peers: Array = _contacts.keys()
	peers.sort_custom(func(a: String, b: String) -> bool:
		var first: Array = _activity_by_peer.get(a, [-1000000000, -1])
		var second: Array = _activity_by_peer.get(b, [-1000000000, -1])
		if first[0] != second[0]: return int(first[0]) > int(second[0])
		if first[1] != second[1]: return int(first[1]) > int(second[1])
		return str(contact_profiles.get(a, {}).get("name", a)).naturalnocasecmp_to(str(contact_profiles.get(b, {}).get("name", b))) < 0)
	return peers

func _save_drafts() -> void:
	if is_instance_valid(composer): _drafts[selected_peer] = composer.text
	var clean: Dictionary = {}
	for peer: String in _drafts:
		if not str(_drafts[peer]).strip_edges().is_empty(): clean[peer] = _drafts[peer]
	if _draft_store.save(clean) != OK and is_instance_valid(_status):
		_status.text = "Le brouillon reste disponible ici, mais son enregistrement a échoué."

func _exit_tree() -> void:
	_save_drafts()

func _reveal_result(reference: WeakRef) -> void:
	await get_tree().process_frame
	if not is_inside_tree(): return
	var control: Control = reference.get_ref()
	if is_instance_valid(control) and _scroll.is_ancestor_of(control):
		_scroll.ensure_control_visible(control)
