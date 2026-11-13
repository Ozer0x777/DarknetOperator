extends VBoxContainer
## Interface web propre à GoPhish : tableaux et formulaires de ses ressources/API.
const UI = preload("res://scripts/ui/style.gd")
signal api_requested(method: String, endpoint: String, payload: Dictionary)
signal reload_requested
var username: String = ""
var password: String = ""
var authenticated: bool = false
var section: String = "Dashboard"
var resources: Dictionary = {}
var api_key: String = ""
var _body: VBoxContainer
var _status: Label
var _user: LineEdit
var _password: LineEdit
var _content: VBoxContainer
var _form_fields: Dictionary = {}
var _view_campaign: int = 0
## Écran affiché : "disconnected", "login" ou "app". Un rafraîchissement
## automatique ne reconstruit pas un écran identique ni un formulaire en cours.
var _screen: String = ""
var _form_open: bool = false

func setup() -> void:
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 0)
	var browser: PanelContainer = UI.panel(Color("2b2a33"), 7)
	add_child(browser)
	var bar: HBoxContainer = HBoxContainer.new()
	browser.add_child(bar)
	bar.add_child(UI.button("↻", func() -> void: reload_requested.emit()))
	var location: LineEdit = LineEdit.new()
	location.text = "https://127.0.0.1:3333"
	location.editable = false
	location.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.add_child(location)
	var white: PanelContainer = UI.panel(Color("ffffff"))
	white.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(white)
	_body = VBoxContainer.new()
	_body.add_theme_constant_override("separation", 0)
	white.add_child(_body)
	show_disconnected()

func _text(text: String, size: int = 14, color: Color = Color("333333")) -> Label:
	return UI.label(text, size, color)

func _field(placeholder: String = "") -> LineEdit:
	var field: LineEdit = LineEdit.new()
	field.placeholder_text = placeholder
	field.add_theme_color_override("font_color", Color("333333"))
	field.add_theme_color_override("font_placeholder_color", Color("999999"))
	field.add_theme_stylebox_override("normal", UI.box(Color.WHITE, Color("cccccc"), 4, 8))
	field.add_theme_stylebox_override("focus", UI.box(Color.WHITE, Color("66afe9"), 4, 8))
	return field

func _green(text: String, action: Callable) -> Button:
	return UI.button(text, action, Color("5cb85c"))

func show_disconnected() -> void:
	if _screen == "disconnected": return
	_screen = "disconnected"
	UI.clear(_body)
	var panel: PanelContainer = UI.panel(Color.WHITE, 40)
	_body.add_child(panel)
	var box: VBoxContainer = VBoxContainer.new()
	panel.add_child(box)
	box.add_child(_text("Unable to connect", 30))
	box.add_child(_text("Le serveur GoPhish ne répond pas sur 127.0.0.1:3333.", 15))
	box.add_child(_text("Démarre gophish dans une console, puis actualise cette page.", 14))
	box.add_child(_green("Try Again", func() -> void: reload_requested.emit()))

func show_login() -> void:
	# Identifiant et mot de passe en cours de saisie sont conservés.
	if _screen == "login" and not authenticated: return
	_screen = "login"
	UI.clear(_body)
	var center: CenterContainer = CenterContainer.new()
	center.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_body.add_child(center)
	var form: VBoxContainer = VBoxContainer.new()
	form.custom_minimum_size.x = 330
	form.add_theme_constant_override("separation", 14)
	center.add_child(form)
	form.add_child(_text("gophish", 42, Color("497b59")))
	form.add_child(_text("Please sign in", 24))
	_user = _field("Username")
	_password = _field("Password")
	_password.secret = true
	form.add_child(_user)
	form.add_child(_password)
	_status = _text("", 13, Color("a94442"))
	form.add_child(_status)
	form.add_child(_green("Sign in", _login))

func _login() -> void:
	username = _user.text
	password = _password.text
	api_requested.emit("GET", "snapshot", {})

func fail(message: String) -> void:
	if is_instance_valid(_status): _status.text = message

func apply_data(data: Dictionary, background: bool = false) -> void:
	var new_resources: Dictionary = data.get("resources", {})
	var new_key: String = data.get("api_key", "")
	if background and authenticated and _screen == "app":
		if new_resources == resources and new_key == api_key: return
		if _editing():
			# Formulaire ou champ en cours : données à jour, affichage intact.
			resources = new_resources
			api_key = new_key
			return
	authenticated = true
	resources = new_resources
	api_key = new_key
	render()

func _editing() -> bool:
	if _form_open: return true
	var focused: Control = get_viewport().gui_get_focus_owner() if is_inside_tree() else null
	return focused != null and (focused is LineEdit or focused is TextEdit) and _body.is_ancestor_of(focused)

func render() -> void:
	_screen = "app"
	_form_open = false
	UI.clear(_body)
	var header: PanelContainer = UI.panel(Color("222222"), 13)
	_body.add_child(header)
	var top: HBoxContainer = HBoxContainer.new()
	header.add_child(top)
	var brand: Label = UI.label("gophish", 23, Color("e9e9e9"))
	brand.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(brand)
	top.add_child(UI.button("admin ▾ / Logout", func() -> void: authenticated = false; username = ""; password = ""; show_login(), Color("222222")))
	var split: HBoxContainer = HBoxContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.add_theme_constant_override("separation", 0)
	_body.add_child(split)
	var side: PanelContainer = UI.panel(Color("f8f8f8"), 8)
	side.custom_minimum_size.x = 195
	split.add_child(side)
	var nav: VBoxContainer = VBoxContainer.new()
	side.add_child(nav)
	for page: String in ["Dashboard", "Campaigns", "Users & Groups", "Email Templates", "Landing Pages", "Sending Profiles", "Settings"]:
		var b: Button = UI.button(page, func() -> void: section = page; _view_campaign = 0; render(), Color("e7e7e7") if section == page else Color("f8f8f8"))
		b.add_theme_color_override("font_color", Color("337ab7"))
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		nav.add_child(b)
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	split.add_child(scroll)
	var margin: MarginContainer = MarginContainer.new()
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for edge: String in ["left", "right", "top", "bottom"]: margin.add_theme_constant_override("margin_" + edge, 23)
	scroll.add_child(margin)
	_content = VBoxContainer.new()
	_content.add_theme_constant_override("separation", 14)
	margin.add_child(_content)
	_content.add_child(_text(section, 30))
	_content.add_child(HSeparator.new())
	_status = _text("", 13, Color("a94442"))
	_content.add_child(_status)
	if section == "Dashboard": _dashboard()
	elif section == "Settings":
		_content.add_child(_text("API Key", 20))
		_content.add_child(_text("Use this key to authenticate requests to the Gophish API.", 13))
		var key: LineEdit = _field()
		key.text = api_key
		key.editable = false
		_content.add_child(key)
	elif section == "Campaigns": _campaigns()
	else: _resources()

func _dashboard() -> void:
	var campaigns: Array = resources.get("campaigns", [])
	var sent: int = 0
	var opened: int = 0
	var clicked: int = 0
	var submitted: int = 0
	# Entonnoir GoPhish : un clic implique une ouverture, une soumission implique un clic.
	for campaign: Dictionary in campaigns:
		for result: Dictionary in campaign.get("results", []):
			var status: String = str(result.get("status", ""))
			if status == "Error": continue
			sent += 1
			if status in ["Email Opened", "Clicked Link", "Submitted Data", "Email Reported"]: opened += 1
			if status in ["Clicked Link", "Submitted Data"]: clicked += 1
			if status == "Submitted Data": submitted += 1
	var row: HBoxContainer = HBoxContainer.new()
	_content.add_child(row)
	for metric: Array in [["Emails Sent", sent, "337ab7"], ["Email Opened", opened, "5bc0de"], ["Clicked Link", clicked, "f0ad4e"], ["Submitted Data", submitted, "5cb85c"]]:
		var panel: PanelContainer = UI.panel(Color(metric[2]), 12, 4)
		panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(panel)
		var box: VBoxContainer = VBoxContainer.new()
		panel.add_child(box)
		box.add_child(UI.label(str(metric[1]), 32, Color.WHITE))
		box.add_child(UI.label(metric[0], 12, Color.WHITE))
	_content.add_child(_text("Campaigns", 22))
	_content.add_child(_text("No campaigns created yet." if campaigns.is_empty() else "%s campaign(s)" % campaigns.size(), 14))
	_content.add_child(_green("View Campaigns", func() -> void: section = "Campaigns"; render()))

func _campaigns() -> void:
	_content.add_child(_green("+ New Campaign", _campaign_form))
	var rows: Array = resources.get("campaigns", [])
	_table_header(["Name", "Status", "Actions"])
	for campaign: Dictionary in rows:
		var row: HBoxContainer = HBoxContainer.new()
		_content.add_child(row)
		for text: String in [str(campaign.name), str(campaign.get("status", ""))]:
			var cell: Label = _text(text)
			cell.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(cell)
		var id: int = int(campaign.id)
		row.add_child(_green("View Results", func() -> void: _view_campaign = id; render()))
		if _view_campaign == id:
			_content.add_child(_text("Results for " + str(campaign.name), 21))
			for result: Dictionary in campaign.get("results", []): _content.add_child(_text("%s     %s" % [result.get("email", ""), result.get("status", "")]))

func _table_header(labels: Array) -> void:
	var header: HBoxContainer = HBoxContainer.new()
	_content.add_child(header)
	for text: String in labels:
		var label: Label = _text(text, 14)
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		header.add_child(label)

func _campaign_form() -> void:
	_form_open = true
	UI.clear(_content)
	_form_fields.clear()
	_content.add_child(_text("New Campaign", 28))
	_form_fields.name = _add_field("Name", "Campaign name")
	for entry: Array in [["template", "Email Template", "templates"], ["page", "Landing Page", "pages"], ["smtp", "Sending Profile", "smtp"], ["group", "Groups", "groups"]]:
		_content.add_child(_text(entry[1]))
		var option: OptionButton = OptionButton.new()
		option.add_theme_color_override("font_color", Color("333333"))
		option.add_theme_stylebox_override("normal", UI.box(Color.WHITE, Color("cccccc"), 3, 8))
		for value: Dictionary in resources.get(entry[2], []): option.add_item(value.name)
		_content.add_child(option)
		_form_fields[entry[0]] = option
	_form_fields.url = _add_field("URL", "http://landing.lab.invalid")
	_form_fields.url.text = "http://landing.lab.invalid"
	_status = _text("", 13, Color("a94442"))
	_content.add_child(_status)
	_content.add_child(_green("Launch Campaign", _launch_campaign))
	_content.add_child(UI.button("Cancel", render, Color("777777")))

func _add_field(label: String, placeholder: String = "") -> LineEdit:
	_content.add_child(_text(label))
	var field: LineEdit = _field(placeholder)
	_content.add_child(field)
	return field

func _launch_campaign() -> void:
	if _form_fields.name.text.strip_edges().is_empty(): fail("Please enter a campaign name."); return
	var payload: Dictionary = {"name": _form_fields.name.text, "url": _form_fields.url.text, "groups": []}
	for key: String in ["template", "page", "smtp", "group"]:
		var option: OptionButton = _form_fields[key]
		if option.selected < 0: fail("A resource is missing."); return
		var value: Dictionary = {"name": option.get_item_text(option.selected)}
		if key == "group": payload.groups.append(value)
		else: payload[key] = value
	api_requested.emit("POST", "campaigns", payload)

func _resources() -> void:
	var kind: String = {"Users & Groups": "groups", "Email Templates": "templates", "Landing Pages": "pages", "Sending Profiles": "smtp"}[section]
	_table_header(["Name", "ID"])
	for resource: Dictionary in resources.get(kind, []):
		_content.add_child(_text("%s       #%s" % [resource.get("name", ""), int(resource.get("id", 0))]))
	_content.add_child(_text("New " + section, 21))
	var name_field: LineEdit = _add_field("Name", "Name")
	var detail: LineEdit = _add_field({"groups": "Recipient email", "templates": "Subject", "pages": "HTML", "smtp": "SMTP host"}[kind])
	var capture_data: CheckBox = null
	var capture_passwords: CheckBox = null
	if kind == "pages":
		capture_data = CheckBox.new()
		capture_data.text = "Capture Submitted Data"
		capture_data.add_theme_color_override("font_color", Color("333333"))
		capture_data.add_theme_color_override("font_hover_color", Color("333333"))
		_content.add_child(capture_data)
		capture_passwords = CheckBox.new()
		capture_passwords.text = "Capture Passwords"
		capture_passwords.add_theme_color_override("font_color", Color("333333"))
		capture_passwords.add_theme_color_override("font_hover_color", Color("333333"))
		capture_passwords.add_theme_color_override("font_disabled_color", Color("888888"))
		capture_passwords.disabled = true
		_content.add_child(capture_passwords)
		capture_data.toggled.connect(func(enabled: bool) -> void:
			capture_passwords.disabled = not enabled
			if not enabled: capture_passwords.button_pressed = false)
	_content.add_child(_green("Save", func() -> void:
		var payload: Dictionary = {"name": name_field.text}
		match kind:
			"groups": payload.targets = [{"email": detail.text, "first_name": "", "last_name": "", "position": ""}]
			"templates": payload.subject = detail.text; payload.text = "Laboratory template"
			"pages": payload.html = detail.text; payload.capture_credentials = capture_data.button_pressed; payload.capture_passwords = capture_passwords.button_pressed
			"smtp": payload.host = detail.text; payload.from_address = "contact@lab.invalid"
		api_requested.emit("POST", kind, payload)))
