extends VBoxContainer
## Navigateur interne et forums : index, recherche, sujets, profils et réponses.
const Avatars = preload("res://scripts/ui/avatars.gd")
const DraftStore = preload("res://scripts/ui/draft_store.gd")
const Composer = preload("res://scripts/ui/message_composer.gd")
const SocialStyle = preload("res://scripts/ui/social_style.gd")
const UI = preload("res://scripts/ui/style.gd")
signal accept_contract(contract_id: String)
signal resume_requested
signal reply_requested(thread_id: String, text: String)
signal thread_selected(thread_id: String)
signal open_app(app_name: String)
signal open_service(url: String)
signal invitation_requested(message_id: String)
signal contact_requested(peer: String, channel: String)
var contracts: Array = []
var profile: Dictionary = {}
var handle: String = "invité"
var selected_forum: String = "breachboard"
var selected_section: String = "Contrats"
var selected_thread: String = ""
var replies: Dictionary = {}
var _community: Array = []
var _private_messages: Array = []
var _only_side_jobs: bool = false
var _open_topic_locked: bool = false
var members: Dictionary = {}
var _activity: Dictionary = {}
var _scroll: ScrollContainer
var _member_dialog: AcceptDialog
var _body: VBoxContainer
var _url: LineEdit
var _search: LineEdit
var _reply: TextEdit
var _reply_status: Label
var _history: Array[Dictionary] = []
var _history_index: int = -1
var _back: Button
var _forward: Button
var _busy: bool = false
var _accent: Color
var _background: Color
var _tabs: Array[Dictionary] = []
var _tab_index: int = 0
var _tab_scroll: ScrollContainer
var _tab_row: HBoxContainer
var _browser_menu: PopupMenu
var _drafts: Dictionary = {}
var _draft_store: RefCounted = DraftStore.new()
var _draft_timer: Timer
var _pending_replies: Dictionary = {}
var _reply_feedback: Dictionary = {}
var _topic_query: String = ""
var _empty_search: Label
var _compact: bool = false
var _reply_panel: PanelContainer
var _reply_counter: Label
var _publish: Button
var _reset_scroll: bool = false
var _bookmarks: Dictionary = {}
var _surface: Color

func setup() -> void:
	name = "ForumBrowser"
	_draft_timer = Timer.new()
	_draft_timer.one_shot = true
	_draft_timer.wait_time = 0.4
	_draft_timer.timeout.connect(_save_drafts)
	add_child(_draft_timer)
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 0)
	_community = JSON.parse_string(FileAccess.get_file_as_string("res://data/community.json"))
	var tabs: PanelContainer = UI.panel(Color("1c1b22"), 5)
	add_child(tabs)
	_tab_scroll = ScrollContainer.new()
	_tab_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_tab_scroll.custom_minimum_size.y = 36
	_tab_scroll.follow_focus = true
	tabs.add_child(_tab_scroll)
	_tab_row = HBoxContainer.new()
	_tab_row.add_theme_constant_override("separation", 6)
	_tab_scroll.add_child(_tab_row)
	for forum: String in ["breachboard", "exployt", "xsx"]:
		_tabs.append({"forum": forum, "thread": "", "section": "Contrats", "history": [], "index": -1})
	var nav: PanelContainer = UI.panel(Color("2b2a33"), 6)
	add_child(nav)
	var nav_row: HBoxContainer = HBoxContainer.new()
	nav.add_child(nav_row)
	_back = UI.button("‹", func() -> void: _browse_history(-1), Color("2b2a33"))
	_forward = UI.button("›", func() -> void: _browse_history(1), Color("2b2a33"))
	nav_row.add_child(_back)
	nav_row.add_child(_forward)
	nav_row.add_child(UI.button("↻", render, Color("2b2a33")))
	nav_row.add_child(UI.button("⌂", func() -> void: navigate(selected_forum), Color("2b2a33")))
	_url = LineEdit.new()
	_url.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_url.add_theme_stylebox_override("normal", UI.box(Color("1c1b22"), Color.TRANSPARENT, 5, 7))
	_url.text_submitted.connect(_address)
	nav_row.add_child(_url)
	_url.placeholder_text = "Rechercher ou saisir une adresse"
	_url.add_theme_stylebox_override("focus", UI.box(Color("1c1b22"), Color("80b6ff"), 6, 8))
	nav_row.add_child(UI.button("☰", func() -> void: _browser_menu.position = Vector2i(get_global_mouse_position()); _browser_menu.popup(), Color("2b2a33")))
	_browser_menu = PopupMenu.new()
	for item: String in ["Nouvel onglet", "Copier l’adresse", "Actualiser", "À propos du navigateur"]: _browser_menu.add_item(item)
	_browser_menu.id_pressed.connect(func(id: int) -> void:
		if id == 0: new_tab()
		elif id == 1: DisplayServer.clipboard_set(_url.text)
		elif id == 2: render()
		else:
			_member_dialog.title = "Navigateur du jeu"
			_member_dialog.dialog_text = "Interface inspirée de Firefox. Navigation limitée aux sites et services du monde simulé."
			_member_dialog.popup_centered(Vector2i(480, 180)))
	add_child(_browser_menu)
	var bookmarks: PanelContainer = UI.panel(Color("23222a"), 5)
	add_child(bookmarks)
	var bookmark_row: HBoxContainer = HBoxContainer.new()
	bookmarks.add_child(bookmark_row)
	for entry: Array in [["breachboard", "BreachBoard"], ["exployt", "Exployt"], ["xsx", "XSX"]]:
		var forum: String = entry[0]
		var bookmark: Button = UI.button("▣  " + entry[1], func() -> void: navigate(forum), Color("23222a"), 5)
		bookmark.visible = not profile.has("access") or profile.access.get("forums", {}).get(forum, {}).get("unlocked", false)
		_bookmarks[forum] = bookmark
		bookmark_row.add_child(bookmark)

	_scroll = ScrollContainer.new()
	var scroll: ScrollContainer = _scroll
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(scroll)
	_body = VBoxContainer.new()
	_body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_body.add_theme_constant_override("separation", 0)
	scroll.add_child(_body)
	_member_dialog = AcceptDialog.new()
	add_child(_member_dialog)
	resized.connect(_adapt_layout)
	navigate("breachboard")

func update_data(new_contracts: Array, new_profile: Dictionary, identity: String, busy: bool) -> void:
	contracts = new_contracts
	profile = new_profile
	_set_draft_identity(identity)
	handle = identity
	_busy = busy
	_render_tabs()
	for forum: String in _bookmarks:
		_bookmarks[forum].visible = not profile.has("access") or profile.access.get("forums", {}).get(forum, {}).get("unlocked", false)
	render()

func navigate(forum: String, thread: String = "", section: String = "Contrats", record: bool = true) -> void:
	if is_instance_valid(_reply):
		_drafts[str(_reply.get_meta("thread", ""))] = _reply.text
	_save_drafts()
	if selected_forum != forum or selected_section != section:
		_topic_query = ""
	_reset_scroll = selected_forum != forum or selected_thread != thread or selected_section != section
	selected_forum = forum
	selected_thread = thread
	selected_section = section
	if record:
		_history.resize(_history_index + 1)
		_history.append({"forum": forum, "thread": thread, "section": section})
		_history_index = _history.size() - 1
	_store_tab()
	_render_tabs()
	render()
	if not thread.is_empty():
		thread_selected.emit(thread)

func _browse_history(step: int) -> void:
	var index: int = _history_index + step
	if index < 0 or index >= _history.size():
		return
	_history_index = index
	var entry: Dictionary = _history[index]
	navigate(entry.forum, entry.thread, entry.section, false)

func _address(address: String) -> void:
	if address.begins_with("https://127.0.0.1:") or address.begins_with("https://localhost:"):
		open_service.emit(address)
		return
	var lower: String = address.to_lower()
	for brand: String in ["breachboard", "exployt", "xsx"]:
		if lower.contains(brand):
			navigate(brand)
			return
	_url.text = "Adresse interne inconnue — BreachBoard / Exployt / XSX"

func _set_palette() -> void:
	var p: Dictionary = {
		"breachboard": {"accent": "db7944", "background": "17191c", "surface": "25282d"},
		"exployt": {"accent": "79a9d4", "background": "101820", "surface": "1c2b37"},
		"xsx": {"accent": "9cb89c", "background": "0e1310", "surface": "1b251e"},
	}[selected_forum]
	_accent = Color(p.accent)
	_background = Color(p.background)
	_surface = Color(p.surface)
	SocialStyle.apply(self, _surface, _accent)

func render() -> void:
	if _body == null:
		return
	var draft: String = _reply.text if is_instance_valid(_reply) and str(_reply.get_meta("thread", "")) == selected_thread else str(_drafts.get(selected_thread, ""))
	var search_focus: bool = is_instance_valid(_search) and _search.has_focus()
	var search_caret: int = _search.caret_column if search_focus else 0
	var reply_selection: Array[int] = []
	if is_instance_valid(_reply) and _reply.has_selection():
		reply_selection.assign([_reply.get_selection_from_line(), _reply.get_selection_from_column(), _reply.get_selection_to_line(), _reply.get_selection_to_column()])
	var reply_focus: bool = is_instance_valid(_reply) and _reply.has_focus()
	var caret_line: int = _reply.get_caret_line() if reply_focus else 0
	var caret_column: int = _reply.get_caret_column() if reply_focus else 0
	var previous_scroll: int = 0 if _reset_scroll else _scroll.scroll_vertical
	_reset_scroll = false
	_set_palette()
	UI.clear(_body)
	_reply = null
	_search = null
	_empty_search = null
	_url.text = "https://" + ("breachboard.fake" if selected_forum == "breachboard" else selected_forum + ".onion") + "/forums/" + (selected_section.to_lower() if selected_thread.is_empty() else "threads/" + selected_thread)
	_back.disabled = _history_index <= 0
	_forward.disabled = _history_index >= _history.size() - 1
	_build_masthead()
	var locked: String = lock_reason()
	if not locked.is_empty():
		var panel: PanelContainer = UI.panel(_background, 32)
		_body.add_child(panel)
		var box: VBoxContainer = VBoxContainer.new()
		box.add_theme_constant_override("separation", 18)
		panel.add_child(box)
		box.add_child(UI.label("Accès restreint", 25, _accent))
		box.add_child(UI.rich(locked))
		var configure: Button
		if not profile.get("forum_unlocked", true):
			configure = UI.button("Retrouver k0rvid sur Chordly", func() -> void: open_app.emit("Chordly"), _surface)
		elif selected_forum == "exployt" and profile.get("route", "freeshield") not in ["tor", "relay"] and profile.get("campaign", {}).get("invitation_accepted", false):
			configure = UI.button("Configurer la route Tor", func() -> void: open_app.emit("Boutique"), _surface)
		else:
			configure = UI.button("Revenir à la campagne sur BreachBoard", func() -> void: navigate("breachboard", "", "Campagne"), _surface)
		configure.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		box.add_child(configure)
		return
	var inner: PanelContainer = UI.panel(_background, 16)
	_body.add_child(inner)
	var content: VBoxContainer = VBoxContainer.new()
	content.add_theme_constant_override("separation", 12)
	inner.add_child(content)
	var crumbs: HBoxContainer = HBoxContainer.new()
	content.add_child(crumbs)
	crumbs.add_child(UI.button("Forums", func() -> void: navigate(selected_forum), _background, 2))
	crumbs.add_child(UI.label(" › " + selected_section + (" › Sujet" if not selected_thread.is_empty() else ""), 12, Color("92989f")))
	if selected_thread.is_empty():
		_build_index(content)
	else:
		_build_thread(content)
	var total_posts: int = 0
	var total_threads: int = 0
	for entry: Dictionary in _community:
		if entry.forum == selected_forum:
			total_threads += 1
			total_posts += 1 + int(profile.get("forum_counts", {}).get(entry.id, 0))
	content.add_child(UI.wrapped("Statistiques · %s sujets de discussion · %s messages archivés" % [total_threads, total_posts], 11, Color("858e94")))
	var footer: PanelContainer = UI.panel(_background, 18)
	footer.add_child(UI.wrapped("Contact  ·  Règles  ·  Confidentialité     |     " + selected_forum + " / communauté du jeu", 11, Color("858e94")))
	_body.add_child(footer)
	if is_instance_valid(_reply):
		_reply.text = draft
		_update_reply_state()
		if reply_focus:
			_reply.grab_focus()
			_reply.set_caret_line(caret_line)
			_reply.set_caret_column(caret_column)
			if reply_selection.size() == 4: _reply.select(reply_selection[0], reply_selection[1], reply_selection[2], reply_selection[3])
	if search_focus and is_instance_valid(_search):
		_search.grab_focus()
		_search.caret_column = search_caret
	for button: Node in _body.find_children("*", "Button", true, false):
		if button.get_parent() is VBoxContainer and button.size_flags_horizontal == Control.SIZE_FILL:
			button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_scroll.set_deferred("scroll_vertical", previous_scroll)

func lock_reason() -> String:
	if profile.has("access"):
		return str(profile.access.get("forums", {}).get(selected_forum, {}).get("reason", "Forum inconnu."))
	if not profile.get("forum_unlocked", true): return "Aucune invitation pour le moment. Retrouve k0rvid sur Chordly et termine tes premiers dossiers."
	var tier: int = int(profile.get("tier", 0))
	if selected_forum in ["exployt", "xsx"] and profile.get("campaign", {}).get("new_progression", false) and not profile.get("campaign", {}).get("invitation_accepted", false):
		return "Une invitation doit être reçue et acceptée dans les MP de BreachBoard après l’acte I."
	if selected_forum == "exployt":
		if tier < 2:
			return "Ce forum est réservé aux membres de palier 2. Termine le contrat de passage sur BreachBoard."
		if profile.get("route", "freeshield") not in ["tor", "relay"]:
			return "Ce forum se consulte via Tor. Choisis et active une route Tor dans la boutique."
	if selected_forum == "xsx" and tier < 3:
		return "Accès sur invitation. Le contrat de passage au palier 3 débloque ce salon privé."
	return ""

func _build_masthead() -> void:
	var panel: PanelContainer = UI.panel(_background, 16)
	_body.add_child(panel)
	var box: VBoxContainer = VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	panel.add_child(box)
	var heading: HBoxContainer = HBoxContainer.new()
	box.add_child(heading)
	var descriptor: Dictionary = {"breachboard": "Communauté · entraide · petites annonces", "exployt": "Discussions techniques · membres confirmés", "xsx": "Espace privé · accès sur invitation"}
	box.add_child(UI.wrapped(descriptor[selected_forum], 12, Color("aab2be")))
	var brand: String = {"breachboard": "BREACHBOARD", "exployt": "exployt", "xsx": "[ x s x ]"}[selected_forum]
	var title: Label = UI.label(brand, 22 if _compact else (28 if selected_forum != "xsx" else 30), _accent)
	if selected_forum in ["exployt", "xsx"]: title.add_theme_font_override("font", UI.MONO)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	heading.add_child(title)
	var account: VBoxContainer = VBoxContainer.new()
	heading.add_child(account)
	account.custom_minimum_size.x = 160
	var identity: Label = UI.label("● " + handle + "  ▾", 13)
	identity.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	account.add_child(identity)
	account.add_child(UI.label("Réputation locale : %s" % _local_reputation(), 11, Color("9a9fa7")))
	var nav: HFlowContainer = HFlowContainer.new()
	nav.name = "SectionNavigation"
	nav.add_theme_constant_override("h_separation", 6)
	nav.add_theme_constant_override("v_separation", 6)
	box.add_child(nav)
	var sections: Array[String] = ["Discussion","Contrats","Marché","Activité"]
	if selected_forum == "breachboard": sections.append_array(["Campagne","Messages"])
	elif selected_forum == "exployt" and not profile.get("act2",{}).is_empty(): sections.append("Campagne")
	for section: String in sections:
		var unread_messages: int = _private_messages.filter(func(message: Dictionary) -> bool: return not message.get("read", false)).size()
		var caption: String = section + (" (%s)" % unread_messages if section == "Messages" and unread_messages > 0 else "")
		var b: Button = UI.button(caption, func() -> void: navigate(selected_forum, "", section), _surface if section == selected_section else _background)
		if section == selected_section:
			var active_style: StyleBoxFlat = UI.box(_surface, _accent, 4, 8)
			active_style.border_width_top = 0
			active_style.border_width_left = 0
			active_style.border_width_right = 0
			active_style.border_width_bottom = 2
			b.add_theme_stylebox_override("normal", active_style)
			b.add_theme_color_override("font_color", _accent.lightened(0.25))
		nav.add_child(b)
	var spacer: Control = Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nav.add_child(spacer)
	if selected_thread.is_empty() and selected_section not in ["Messages", "Campagne"]:
		_search = LineEdit.new()
		_search.placeholder_text = "Rechercher un sujet ou un auteur…"
		_search.clear_button_enabled = true
		UI.field(_search, _surface.darkened(0.3), _accent)
		_search.custom_minimum_size.x = 240
		_search.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		_search.text = _topic_query
		_search.text_changed.connect(_filter_topics)
		box.add_child(_search)

## filtered : applique le filtre « Petits contrats » de la liste. Un sujet ouvert
## se cherche sans ce filtre, sinon un contrat principal devient « introuvable ».
func _topics(filtered: bool = true) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	if selected_section in ["Contrats", "Activité"]:
		for contract: Dictionary in contracts:
			if contract.get("forum") != selected_forum or (filtered and _only_side_jobs and selected_section == "Contrats" and not contract.get("side_job", false)):
				continue
			result.append({"id": contract.contract_id, "title": contract.title, "author": contract.client.handle, "reputation": contract.client.forum_rep, "age": contract.client.account_age_days, "body": contract.body, "contract": contract, "pinned": false})
	if selected_section != "Contrats":
		for entry: Dictionary in _community:
			if entry.forum == selected_forum and (entry.section == selected_section or selected_section == "Activité"):
				result.append(entry)
	result.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		if a.get("pinned", false) != b.get("pinned", false): return a.get("pinned", false)
		return int(_activity.get(a.id, {}).get("last_minute", 0)) > int(_activity.get(b.id, {}).get("last_minute", 0)))
	return result

func _build_index(content: VBoxContainer) -> void:
	if selected_section == "Messages":
		content.add_child(UI.label("Messages privés", 23))
		content.add_child(UI.rich("Propositions confidentielles, suivis et invitations adressés à ton profil.", 13))
		for message: Dictionary in _private_messages:
			var id: String = str(message.id)
			var item: PanelContainer = UI.panel(_surface, 14, 3)
			content.add_child(item)
			var box: VBoxContainer = VBoxContainer.new()
			item.add_child(box)
			box.add_child(UI.button(("● " if not message.get("read", false) else "") + str(message.subject), func() -> void: navigate("breachboard", id, "Messages"), _surface, 4))
			box.add_child(UI.label("De " + str(message.author) + " · conversation privée", 12, _accent))
		if _private_messages.is_empty(): content.add_child(UI.label("Aucun message privé pour le moment.", 14))
		return
	if selected_section == "Campagne":
		_render_campaign(content)
		return
	var introduction: HFlowContainer = HFlowContainer.new()
	introduction.add_theme_constant_override("h_separation", 18)
	introduction.add_theme_constant_override("v_separation", 8)
	content.add_child(introduction)
	introduction.add_child(UI.label({"Contrats": "Offres & contrats", "Discussion": "Communauté & discussions", "Marché": "Services & matériel", "Activité": "Derniers messages"}[selected_section], 23))
	if selected_section == "Contrats":
		var filter: Button = UI.button("Toutes les annonces" if _only_side_jobs else "Petits contrats", func() -> void: _only_side_jobs = not _only_side_jobs; render(), _surface)
		filter.tooltip_text = "Afficher toutes les annonces" if _only_side_jobs else "Voir les petits contrats facultatifs"
		filter.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		introduction.add_child(filter)
	content.add_child(UI.wrapped("Sujets de la communauté" if selected_section != "Contrats" else "Consultez le profil du client et les conditions avant de répondre.", 12, Color("a7acb2")))
	var table: VBoxContainer = VBoxContainer.new()
	table.name = "Topics"
	table.add_theme_constant_override("separation", 4)
	content.add_child(table)
	var header: PanelContainer = UI.panel(_surface.darkened(0.18), 12, 4)
	table.add_child(header)
	var columns: HBoxContainer = HBoxContainer.new()
	columns.add_theme_constant_override("separation", 12)
	header.add_child(columns)
	var topic: Label = UI.label("SUJET", 11, _accent)
	topic.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	columns.add_child(topic)
	for label: String in ([] if _compact else ["RÉPONSES", "VUES", "DERNIER MESSAGE"]):
		var l: Label = UI.label(label, 10, Color("a0a7ae"))
		l.custom_minimum_size.x = 75 if label in ["RÉPONSES", "VUES"] else 150
		if label in ["RÉPONSES", "VUES"]: l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		columns.add_child(l)
	for entry: Dictionary in _topics():
		_topic_row(table, entry)
	_empty_search = UI.label("Aucun sujet ne correspond à la recherche.", 13, Color("a7acb2"))
	_empty_search.visible = false
	content.add_child(_empty_search)
	_filter_topics(_topic_query)
	if _topics().is_empty():
		table.add_child(UI.rich("Aucun sujet dans cette catégorie pour le moment.", 13))
	if selected_section == "Marché":
		content.add_child(UI.button("Ouvrir le catalogue des services et du matériel", func() -> void: open_app.emit("Boutique"), _surface))

func _topic_row(parent: Node, topic: Dictionary) -> void:
	var panel: PanelContainer = UI.panel(_surface.lightened(0.025) if topic.get("pinned", false) else _surface, 12, 5)
	panel.set_meta("topic", (str(topic.title) + " " + str(topic.author)).to_lower())
	parent.add_child(panel)
	var row: HBoxContainer = HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	panel.add_child(row)
	var thumbnail: PanelContainer = UI.panel(_accent.darkened(0.6), 0, 3)
	thumbnail.custom_minimum_size = Vector2(40, 40) if _compact else Vector2(44, 44)
	thumbnail.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var monogram: Label = UI.label(str(topic.author).left(1).to_upper(), 23, _accent)
	monogram.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	thumbnail.add_child(monogram)
	Avatars.apply(thumbnail, str(topic.author))
	row.add_child(thumbnail)
	var body: VBoxContainer = VBoxContainer.new()
	body.add_theme_constant_override("separation", 6)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(body)
	var id: String = topic.id
	var link: Button = UI.button(str(topic.title), func() -> void: navigate(selected_forum, id, selected_section), _surface, 0)
	link.alignment = HORIZONTAL_ALIGNMENT_LEFT
	link.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	link.add_theme_font_size_override("font_size", 15)
	link.tooltip_text = str(topic.title)
	var flags: HFlowContainer = HFlowContainer.new()
	flags.add_theme_constant_override("h_separation", 6)
	if topic.get("pinned", false): flags.add_child(UI.badge("ÉPINGLÉ", _accent))
	if topic.get("locked", false): flags.add_child(UI.badge("VERROUILLÉ", Color("a6b1bd")))
	if topic.has("contract"):
		flags.add_child(UI.badge("DÉJÀ RÉGLÉ" if topic.contract.get("completed", false) else "CONTRAT", _accent))
	if flags.get_child_count() > 0: body.add_child(flags)
	else: flags.free()
	body.add_child(link)
	body.add_child(UI.wrapped(str(topic.author) + " · " + str(topic.get("created_time", "Annonce")), 11, Color("b2bac5")))
	var activity: Dictionary = _activity.get(id, {})
	var reply_count: int = int(profile.get("forum_counts", {}).get(id, replies.get(id, []).size()))
	var view_count: int = int(activity.get("views", topic.get("views", 0)))
	var last_author: String = str(activity.get("last_author", topic.author))
	var last_time: String = str(activity.get("last_time", topic.get("created_time", "Annonce")))
	if _compact:
		body.add_child(UI.wrapped("%s réponses · %s vues · Dernier : %s · %s" % [reply_count, view_count, last_author, last_time], 11, Color("a5adb8")))
	else:
		for value: String in [str(reply_count), str(view_count), last_author + "\n" + last_time]:
			var stat: Label = UI.label(value, 12, Color("b2bac5"))
			stat.custom_minimum_size.x = 150 if value.contains("\n") else 75
			stat.size_flags_vertical = Control.SIZE_SHRINK_CENTER
			if not value.contains("\n"): stat.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			stat.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
			row.add_child(stat)

func _filter_topics(text: String) -> void:
	_topic_query = text
	var visible_topics: int = 0
	var nodes: Array[Node] = _body.find_children("Topics", "VBoxContainer", true, false)
	for table: Node in nodes:
		for row: Node in table.get_children():
			if row.has_meta("topic"):
				row.visible = text.strip_edges().is_empty() or str(row.get_meta("topic")).contains(text.strip_edges().to_lower())
				if row.visible: visible_topics += 1
	if is_instance_valid(_empty_search):
		_empty_search.visible = visible_topics == 0 and not text.strip_edges().is_empty()

func _build_thread(content: VBoxContainer) -> void:
	if selected_section == "Messages":
		for message: Dictionary in _private_messages:
			if str(message.id) != selected_thread: continue
			content.add_child(UI.wrapped(str(message.subject), 22))
			_post(content, str(message.author), int(members.get(message.author, {}).get("reputation", 0)), str(message.body), int(members.get(message.author, {}).get("age", 1)), "MP", "Conversation privée")
			if message.has("contract_id"):
				var cid: String = str(message.contract_id)
				var button: Button = UI.button("Ouvrir le dossier privé", func() -> void: accept_contract.emit(cid), _accent.darkened(0.4))
				button.disabled = _busy and profile.get("active_contract", {}).get("contract_id", "") != cid if profile.get("active_contract") != null else _busy
				content.add_child(button)
			if message.has("invitation"):
				var mid: String = str(message.id)
				var accept: Button = UI.button("Invitation acceptée" if message.get("accepted", false) else "Accepter l’invitation sur Exployt", func() -> void: invitation_requested.emit(mid), _accent.darkened(0.4))
				accept.disabled = message.get("accepted", false)
				content.add_child(accept)
			return
		content.add_child(UI.label("Message introuvable", 18))
		return
	var topic: Dictionary = {}
	for entry: Dictionary in _topics(false):
		if entry.id == selected_thread:
			topic = entry
	_open_topic_locked = topic.get("locked", false)
	if topic.is_empty():
		content.add_child(UI.label("Sujet introuvable", 22))
		return
	var title: Label = UI.label(str(topic.title), 22)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	content.add_child(title)
	content.add_child(UI.wrapped("Discussion ouverte par " + str(topic.author) + " · " + str(topic.get("created_time", "Annonce")), 11, Color("9ea6b0")))
	_post(content, str(topic.author), int(topic.get("reputation", 0)), str(topic.body), int(topic.get("age", 412)), "#1", str(topic.get("created_time", "Annonce")))
	var posts: Array = replies.get(selected_thread, [])
	for i: int in range(posts.size()):
		var post: Dictionary = posts[i]
		_post(content, str(post.author), int(post.get("reputation", 0)), str(post.text), int(post.get("age", 1)), "#" + str(i + 2), str(post.get("time", "")))
	if topic.has("contract"):
		var contract: Dictionary = topic.contract
		if contract.get("affiliation", false):
			var terms: PanelContainer = UI.panel(_surface.darkened(0.15), 14, 5)
			terms.add_child(UI.rich("Conditions de règlement : la prime est modulée par les objectifs vérifiés et les sauvegardes. Part opérateur : 30 % avec Vesper, 100 % avec la licence Glasswing. La licence est un achat séparé ; son coût n’est pas remboursé par le contrat.", 13))
			content.add_child(terms)
		var accept: Button = UI.button("Accepter le contrat · %s ₵" % int(contract.reward), func() -> void: accept_contract.emit(contract.contract_id), _accent.darkened(0.4))
		var active: Dictionary = profile.get("active_contract", {}) if profile.get("active_contract") != null else {}
		var same_contract: bool = active.get("contract_id") == contract.contract_id or contract.get("is_active", false)
		accept.disabled = false if same_contract else (_busy or not active.is_empty() or not contract.get("unlocked", true))
		if same_contract:
			accept.text = "Reprendre ce contrat"
		elif contract.get("completed", false):
			accept.text = "Rejouer · sans prime ni modification des choix"
		elif _busy or not active.is_empty():
			accept.text = "Une autre mission est en cours"
		elif not contract.get("unlocked", true):
			accept.text = str(contract.get("locked_reason", "Contrat verrouillé"))
		content.add_child(accept)
		if not same_contract and not active.is_empty():
			content.add_child(UI.button("Reprendre : " + str(active.get("title", "mission sauvegardée")), func() -> void: resume_requested.emit(), _surface))
	if topic.get("locked", false):
		content.add_child(UI.label("Ce sujet est verrouillé. La discussion reste consultable.", 13, _accent))
		return
	var reply_panel: PanelContainer = UI.panel(_surface, 16, 6)
	_reply_panel = reply_panel
	content.add_child(reply_panel)
	var box: VBoxContainer = VBoxContainer.new()
	reply_panel.add_child(box)
	box.add_theme_constant_override("separation", 12)
	box.add_child(UI.label("Réponse rapide", 16, _accent))
	_reply = Composer.new()
	_reply.enter_sends = false
	_reply.submitted.connect(_submit_reply)
	_reply.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	_reply.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	UI.field(_reply, _surface.darkened(0.25), _accent)
	_reply.set_meta("thread", selected_thread)
	_reply.placeholder_text = "Écrire une réponse au sujet…"
	_reply.custom_minimum_size.y = 125
	_reply.text_changed.connect(_update_reply_state)
	box.add_child(_reply)
	_reply_status = UI.wrapped("", 12, Color("a9b1bb"))
	box.add_child(_reply_status)
	var actions: HFlowContainer = HFlowContainer.new()
	actions.add_theme_constant_override("h_separation", 16)
	box.add_child(actions)
	_publish = UI.button("Publier la réponse", _submit_reply, _accent.darkened(0.4))
	_publish.tooltip_text = "Publier · Ctrl+Entrée"
	actions.add_child(_publish)
	_reply_counter = UI.label("0 / 2 000 · Ctrl+Entrée pour publier", 11, Color("b2bac5"))
	actions.add_child(_reply_counter)

func _post(parent: Node, author: String, reputation: int, text: String, age: int, number: String, posted_at: String = "") -> void:
	if author == handle: reputation = _local_reputation()
	var panel: PanelContainer = UI.panel(_surface, 0, 6)
	panel.clip_contents = true
	panel.set_meta("forum_post", author)
	parent.add_child(panel)
	var row: BoxContainer = VBoxContainer.new() if _compact else HBoxContainer.new()
	row.add_theme_constant_override("separation", 0)
	panel.add_child(row)
	var identity: PanelContainer = UI.panel(_surface.darkened(0.18), 12)
	identity.custom_minimum_size.x = 0 if _compact else 148
	row.add_child(identity)
	var profile_box: BoxContainer = HBoxContainer.new() if _compact else VBoxContainer.new()
	profile_box.add_theme_constant_override("separation", 10)
	identity.add_child(profile_box)
	var avatar: PanelContainer = UI.panel(_accent.darkened(0.55), 0, 5)
	avatar.name = "ForumAvatar"
	avatar.custom_minimum_size = Vector2(40, 40) if _compact else Vector2(72, 72)
	avatar.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	avatar.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	var initial: Label = UI.label(author.left(1).to_upper(), 20 if _compact else 40, _accent.lightened(0.3))
	initial.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	avatar.add_child(initial)
	Avatars.apply(avatar, author)
	profile_box.add_child(avatar)
	var names: VBoxContainer = VBoxContainer.new()
	names.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	profile_box.add_child(names)
	var username: Button = UI.button(author, func() -> void: _show_member(author), _surface.darkened(0.18), 2)
	username.alignment = HORIZONTAL_ALIGNMENT_LEFT if _compact else HORIZONTAL_ALIGNMENT_CENTER
	username.add_theme_font_size_override("font_size", 15)
	username.add_theme_color_override("font_color", _accent.lightened(0.25))
	username.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	username.tooltip_text = "Consulter le profil de " + author
	names.add_child(username)
	var role: Label = UI.wrapped(str(members.get(author, {}).get("role", "Membre")), 11, _accent.lightened(0.2))
	role.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT if _compact else HORIZONTAL_ALIGNMENT_CENTER
	names.add_child(role)
	if not _compact:
		names.add_child(HSeparator.new())
		names.add_child(UI.label("Ancienneté   %s j" % age, 11, Color("b2bac5")))
		names.add_child(UI.label("Réputation   %s" % reputation, 12, Color("c8cdd4")))
	else:
		names.add_child(UI.wrapped("Réputation %s · %s j" % [reputation, age], 11, Color("b2bac5")))
	var message: PanelContainer = UI.panel(_surface, 16 if _compact else 20)
	message.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(message)
	var body: VBoxContainer = VBoxContainer.new()
	body.add_theme_constant_override("separation", 12)
	message.add_child(body)
	var heading: HBoxContainer = HBoxContainer.new()
	body.add_child(heading)
	var date: Label = UI.label(posted_at if not posted_at.is_empty() else "Message archivé", 11, Color("b2bac5"))
	date.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	date.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	heading.add_child(date)
	heading.add_child(UI.label(number, 11, _accent))
	body.add_child(HSeparator.new())
	_post_body(body, text)
	var quote: Button = UI.button("↪  Citer", func() -> void: _quote_post(author, text), _surface.lightened(0.05), 7)
	quote.visible = selected_section != "Messages"
	quote.disabled = _open_topic_locked
	quote.size_flags_horizontal = Control.SIZE_SHRINK_END
	body.add_child(quote)

func _post_body(parent: VBoxContainer, text: String) -> void:
	var block: PackedStringArray = []
	var quoted: bool = false
	for line: String in text.split("\n"):
		var is_quote: bool = line.begins_with("> ")
		if not block.is_empty() and is_quote != quoted:
			_post_block(parent, "\n".join(block), quoted)
			block.clear()
		quoted = is_quote
		block.append(line.substr(2) if is_quote else line)
	if not block.is_empty(): _post_block(parent, "\n".join(block), quoted)

func _post_block(parent: VBoxContainer, text: String, quoted: bool) -> void:
	if not quoted:
		if not text.strip_edges().is_empty(): parent.add_child(UI.rich(text.strip_edges(), 15))
		return
	var quote: PanelContainer = UI.panel(_surface.darkened(0.2), 12, 4)
	var border: StyleBoxFlat = UI.box(_surface.darkened(0.2), _accent.darkened(0.25), 4, 12)
	border.border_width_top = 0
	border.border_width_bottom = 0
	border.border_width_right = 0
	border.border_width_left = 3
	quote.add_theme_stylebox_override("panel", border)
	quote.add_child(UI.rich(text, 14, Color("bdc5d0")))
	parent.add_child(quote)

func _quote_post(author: String, text: String) -> void:
	if not is_instance_valid(_reply): return
	var quotation: String = "> " + author + " : " + text.replace("\n", " ").left(300) + "\n\n"
	_reply.text += ("\n\n" if not _reply.text.is_empty() else "") + quotation
	_reply.set_caret_line(_reply.get_line_count() - 1)
	_reply.grab_focus()
	_update_reply_state()
	_reveal_reply.call_deferred(weakref(_reply_panel))

func _update_reply_state() -> void:
	if not is_instance_valid(_reply) or not is_instance_valid(_publish): return
	var length: int = _reply.text.length()
	var pending: bool = _pending_replies.has(selected_thread)
	_reply.editable = not pending
	_publish.disabled = pending or _reply.text.strip_edges().is_empty() or length > 2000
	_publish.text = "Publication…" if pending else "Publier la réponse"
	_reply_status.text = str(_reply_feedback.get(selected_thread, ""))
	_drafts[selected_thread] = _reply.text
	_draft_timer.start()
	_reply_counter.text = "%s / 2 000 · Ctrl+Entrée pour publier" % length
	_reply_counter.add_theme_color_override("font_color", Color("ffb4a6") if length > 2000 else Color("b2bac5"))

func _adapt_layout() -> void:
	var compact: bool = size.x < 880
	if compact == _compact: return
	_compact = compact
	render.call_deferred()

func _submit_reply() -> void:
	if not is_instance_valid(_reply) or _pending_replies.has(selected_thread): return
	var text: String = _reply.text.strip_edges()
	if text.is_empty():
		return
	if _reply.text.length() > 2000:
		_reply_status.text = "La réponse est limitée à 2 000 caractères."
		return
	_pending_replies[selected_thread] = text
	_reply_feedback[selected_thread] = "Publication…"
	_update_reply_state()
	reply_requested.emit(selected_thread, text)

func set_replies(thread_id: String, posts: Array) -> void:
	# Le sondage recharge le sujet ouvert : pas de reconstruction (sélection, annulation du brouillon) sans nouveau message.
	var unchanged: bool = replies.has(thread_id) and replies[thread_id] == posts
	replies[thread_id] = posts
	if not profile.has("forum_counts"): profile["forum_counts"] = {}
	profile.forum_counts[thread_id] = posts.size()
	if thread_id == selected_thread and not unchanged:
		render()

func acknowledge_reply(thread_id: String, sent: bool, error: String = "") -> void:
	if not _pending_replies.has(thread_id): return
	var text: String = str(_pending_replies[thread_id])
	_pending_replies.erase(thread_id)
	_reply_feedback[thread_id] = "Réponse publiée." if sent else error
	if sent and str(_drafts.get(thread_id, "")).strip_edges() == text: _drafts.erase(thread_id)
	if selected_thread == thread_id and is_instance_valid(_reply):
		if sent and _reply.text.strip_edges() == text: _reply.clear()
		_update_reply_state()
	_save_drafts()

func reply_error(message: String) -> void:
	acknowledge_reply(selected_thread, false, message)

func set_world(data: Dictionary) -> void:
	members = data.get("profiles", {})
	var topics: Array = data.get("threads", [])
	var changed: bool = _community != topics or profile.get("forum_counts", {}) != data.get("forum_counts", {}) or _private_messages != data.get("forum_messages", [])
	_private_messages = data.get("forum_messages", []).duplicate(true)
	_community = topics.duplicate(true)
	profile["forum_counts"] = data.get("forum_counts", {}).duplicate(true)
	for topic: Dictionary in topics: _activity[topic.id] = topic
	if changed: render()

func _show_member(author: String) -> void:
	var member: Dictionary = {"role": "Membre", "age": 1, "reputation": _local_reputation(), "bio": "Ton profil de membre."} if author == handle else members.get(author, {})
	_member_dialog.title = "Profil de " + author
	_member_dialog.dialog_text = "%s\n%s\nInscrit depuis %s jours · Réputation %s\n\n%s" % [author, member.get("role", "Membre"), int(member.get("age", 1)), int(member.get("reputation", 0)), member.get("bio", "Aucune présentation publique.")]
	_member_dialog.popup_centered(Vector2i(450, 230))


func _store_tab() -> void:
	if _tabs.is_empty(): return
	_tabs[_tab_index] = {"forum": selected_forum, "thread": selected_thread, "section": selected_section, "history": _history.duplicate(true), "index": _history_index}

func _render_tabs() -> void:
	UI.clear(_tab_row)
	for i: int in range(_tabs.size()):
		if profile.has("access") and not profile.access.get("forums", {}).get(_tabs[i].forum, {}).get("unlocked", false) and i != _tab_index: continue
		var index: int = i
		var active: bool = i == _tab_index
		var panel: PanelContainer = UI.panel(Color("42414d") if active else Color("1c1b22"), 4, 6)
		_tab_row.add_child(panel)
		var row: HBoxContainer = HBoxContainer.new()
		panel.add_child(row)
		var title: String = {"breachboard": "BreachBoard", "exployt": "Exployt", "xsx": "XSX"}.get(_tabs[i].forum, "Nouvel onglet")
		var tab: Button = UI.button("◉  " + title, func() -> void: _switch_tab(index), Color("42414d") if active else Color("1c1b22"), 5)
		tab.custom_minimum_size.x = 125
		row.add_child(tab)
		if active: _reveal_tab.call_deferred(weakref(tab))
		row.add_child(UI.button("×", func() -> void: _close_tab(index), Color("42414d") if active else Color("1c1b22"), 4))
	_tab_row.add_child(UI.button("+", new_tab, Color("1c1b22")))

func _switch_tab(index: int) -> void:
	_store_tab()
	_tab_index = index
	var tab: Dictionary = _tabs[index]
	_history.assign(tab.history)
	_history_index = int(tab.index)
	navigate(tab.forum, tab.thread, tab.section, false)

func new_tab() -> void:
	_store_tab()
	_tabs.append({"forum": "breachboard", "thread": "", "section": "Discussion", "history": [], "index": -1})
	_tab_index = _tabs.size()-1
	_history.clear()
	_history_index = -1
	navigate("breachboard", "", "Discussion")

func _close_tab(index: int) -> void:
	if _tabs.size() == 1:
		navigate("breachboard")
		return
	_store_tab()
	_tabs.remove_at(index)
	if index < _tab_index: _tab_index -= 1
	_tab_index = mini(_tab_index, _tabs.size()-1)
	var tab: Dictionary = _tabs[_tab_index]
	_history.assign(tab.history)
	_history_index = int(tab.index)
	navigate(tab.forum, tab.thread, tab.section, false)

func focus_address() -> void:
	_url.grab_focus()
	_url.select_all()


func _reveal_tab(reference: WeakRef) -> void:
	var button: Control = reference.get_ref()
	if is_instance_valid(button) and _tab_scroll.is_ancestor_of(button):
		_tab_scroll.ensure_control_visible(button)

func _set_draft_identity(identity: String) -> void:
	if identity.is_empty() or _draft_store.identity == identity: return
	_save_drafts()
	_draft_store.configure(identity, "forums")
	_drafts = _draft_store.values.duplicate(true)
	_pending_replies.clear()
	_reply_feedback.clear()
	if is_instance_valid(_reply): _reply.text = str(_drafts.get(selected_thread, ""))

func _save_drafts() -> void:
	if is_instance_valid(_reply): _drafts[str(_reply.get_meta("thread", ""))] = _reply.text
	var clean: Dictionary = {}
	for key: String in _drafts:
		if not str(_drafts[key]).strip_edges().is_empty(): clean[key] = _drafts[key]
	if _draft_store.save(clean) != OK and is_instance_valid(_reply_status):
		_reply_status.text = "Le brouillon reste disponible ici, mais son enregistrement a échoué."

func _exit_tree() -> void:
	_save_drafts()

func _reveal_reply(reference: WeakRef) -> void:
	var control: Control = reference.get_ref()
	if is_instance_valid(control) and _scroll.is_ancestor_of(control):
		_scroll.ensure_control_visible(control)

func _local_reputation() -> int:
	return int(profile.get("forum_reputation", {}).get(selected_forum, profile.get("reputation", 0) if selected_forum == "breachboard" else 0))


func _render_campaign(content: VBoxContainer) -> void:
	var is_second: bool = selected_forum == "exployt" and not profile.get("act2", {}).is_empty()
	var current: Dictionary = profile.get("act2", {}) if is_second else profile.get("campaign", {})
	content.add_child(UI.wrapped("Acte II — Gagner des accès" if is_second else "Acte I — Se faire un nom", 23))
	content.add_child(UI.wrapped("%s / %s dossiers validés" % [int(current.get("completed",0)),int(current.get("total",10))],14,_accent))
	var next_step: Dictionary = profile.get("journey", {})
	if not next_step.is_empty():
		var next_panel: PanelContainer = UI.panel(_surface,14,6)
		var next_box: VBoxContainer = VBoxContainer.new()
		next_panel.add_child(next_box)
		next_box.add_child(UI.wrapped(str(next_step.get("title","Prochaine piste")),16,_accent))
		next_box.add_child(UI.rich(str(next_step.get("detail","")),13))
		var destination: String = str(next_step.get("app", ""))
		var peer: String = str(next_step.get("peer", ""))
		if destination in ["Chordly", "Telegrid", "Sessyon"]:
			next_box.add_child(UI.button("Contacter "+peer+" sur "+destination, func() -> void: contact_requested.emit(peer,destination.to_lower()),_surface.lightened(0.05)))
		elif destination == "Boutique":
			next_box.add_child(UI.button("Configurer la route",func() -> void: open_app.emit("Boutique"),_surface.lightened(0.05)))
		elif destination == "BreachBoard" and not profile.get("campaign",{}).get("invitation_accepted",false) and int(current.get("completed",0))==10:
			next_box.add_child(UI.button("Consulter l’invitation dans les MP",func() -> void: navigate("breachboard","","Messages"),_surface.lightened(0.05)))
		content.add_child(next_panel)
	for chapter: Dictionary in current.get("chapters", []):
		var box: VBoxContainer = VBoxContainer.new()
		var panel: PanelContainer = UI.panel(_surface,12,3)
		panel.add_child(box)
		content.add_child(panel)
		box.add_child(UI.wrapped("%02d  %s" % [int(chapter.number),str(chapter.title)],16))
		box.add_child(UI.wrapped({"completed":"Validé","available":"Disponible","locked":"Poursuivre les dossiers précédents"}.get(str(chapter.status),""),12,_accent))
		var direct_piste: bool = str(next_step.get("contract_id", "")) == str(chapter.id) and str(next_step.get("app", "")) in ["Chordly", "Telegrid", "Sessyon"]
		if chapter.status == "available" and not direct_piste:
			var peer: String = str(chapter.peer)
			var ident: String = str(chapter.id)
			if is_second: box.add_child(UI.button("Contacter "+peer+" sur Telegrid",func() -> void: contact_requested.emit(peer,"telegrid"),_surface.lightened(0.05)))
			elif int(chapter.number) in [3,9,10]: box.add_child(UI.button("Consulter les MP du forum",func() -> void: navigate("breachboard","","Messages"),_surface.lightened(0.05)))
			elif int(chapter.number)==2: box.add_child(UI.button("Consulter l’annonce",func() -> void: navigate("breachboard",ident,"Contrats"),_surface.lightened(0.05)))
			else: box.add_child(UI.button("Contacter "+peer+" sur Chordly",func() -> void: contact_requested.emit(peer,"chordly"),_surface.lightened(0.05)))
	if not is_second and profile.get("act2",{}).get("unlocked",false):
		content.add_child(UI.button("Ouvrir l’acte II sur Exployt",func() -> void: navigate("exployt","","Campagne"),_surface.lightened(0.05)))
