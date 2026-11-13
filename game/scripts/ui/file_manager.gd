extends VBoxContainer
## Explorateur de fichiers virtuels, présentation proche de Thunar.
const UI = preload("res://scripts/ui/style.gd")
signal open_app(app_name: String)
var path: String = "/home/operator"
var loot: Array = []
var _location: LineEdit
var _items: ItemList
var _preview: RichTextLabel
var _status: Label
var _history: Array[String] = []
var _index: int = -1
var _back: Button

func setup() -> void:
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 0)
	var menu: HBoxContainer = HBoxContainer.new()
	for name_: String in ["Fichier", "Édition", "Affichage", "Aller", "Aide"]:
		var button: MenuButton = MenuButton.new()
		button.text = name_
		button.get_popup().add_item("Ouvrir le terminal" if name_ == "Fichier" else ("Dossier personnel" if name_ == "Aller" else "Actualiser"))
		button.get_popup().id_pressed.connect(func(_id: int) -> void:
			if name_ == "Fichier": open_app.emit("Terminal")
			elif name_ == "Aller": navigate("/home/operator")
			else: _render())
		menu.add_child(button)
	add_child(menu)
	var toolbar: PanelContainer = UI.panel(Color("2a2c38"), 6)
	add_child(toolbar)
	var row: HBoxContainer = HBoxContainer.new()
	toolbar.add_child(row)
	_back = UI.button("‹", back)
	row.add_child(_back)
	row.add_child(UI.button("↑", func() -> void: navigate(path.get_base_dir() if path != "/" else "/")))
	row.add_child(UI.button("⌂", func() -> void: navigate("/home/operator")))
	_location = LineEdit.new()
	_location.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_location.text_submitted.connect(navigate)
	row.add_child(_location)
	row.add_child(UI.button("↻", _render))
	var split: HSplitContainer = HSplitContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	split.split_offset = 160
	add_child(split)
	var places: PanelContainer = UI.panel(Color("252732"), 8)
	places.custom_minimum_size.x = 155
	split.add_child(places)
	var column: VBoxContainer = VBoxContainer.new()
	places.add_child(column)
	column.add_child(UI.label("EMPLACEMENTS", 11, Color("9199a7")))
	for entry: Array in [["home", "Dossier personnel", "/home/operator"], ["computer", "Système de fichiers", "/"], ["folder", "Bureau", "/home/operator/Desktop"], ["folder", "Documents", "/home/operator/Documents"], ["folder", "Téléchargements", "/home/operator/Downloads"], ["folder", "loot", "/home/operator/loot"], ["trash", "Corbeille", "trash:///"]]:
		var directory: String = entry[2]
		var button: Button = UI.button(entry[1], func() -> void: navigate(directory), Color("252732"), 6)
		button.icon = load("res://assets/icons/%s.svg" % entry[0])
		button.expand_icon = true
		button.add_theme_constant_override("icon_max_width", 18)
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		column.add_child(button)
	var right: VBoxContainer = VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	split.add_child(right)
	_items = ItemList.new()
	_items.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_items.max_columns = 4
	_items.fixed_column_width = 105
	_items.fixed_icon_size = Vector2i(48, 48)
	_items.icon_mode = ItemList.ICON_MODE_TOP
	_items.add_theme_stylebox_override("panel", UI.box(Color("20222c"), Color.TRANSPARENT, 0, 12))
	_items.item_activated.connect(_activate)
	_items.item_selected.connect(_select)
	right.add_child(_items)
	_preview = UI.rich()
	_preview.custom_minimum_size.y = 90
	_preview.fit_content = false
	_preview.scroll_active = true
	right.add_child(_preview)
	var copy: Button = UI.button("Copier la valeur sélectionnée", _copy)
	copy.size_flags_horizontal = Control.SIZE_SHRINK_END
	right.add_child(copy)
	_status = UI.label("", 12, Color("a4adbb"))
	add_child(_status)
	navigate(path)

func set_loot(values: Array) -> void:
	if JSON.stringify(loot) == JSON.stringify(values): return
	loot = values.duplicate(true)
	_render()

func navigate(directory: String) -> void:
	var allowed: Array[String] = ["/", "/home", "/home/operator", "/home/operator/Desktop", "/home/operator/Documents", "/home/operator/Downloads", "/home/operator/loot", "trash:///"]
	if directory not in allowed:
		_status.text = "Emplacement absent du système de fichiers virtuel."
		return
	path = directory
	_history.resize(_index + 1)
	_history.append(path)
	_index = _history.size() - 1
	_render()

func back() -> void:
	if _index <= 0: return
	_index -= 1
	path = _history[_index]
	_render()

func _render() -> void:
	if _items == null: return
	_items.clear()
	_preview.text = ""
	_location.text = path
	_back.disabled = _index <= 0
	if path in ["/", "/home", "/home/operator"]:
		var directories: Array = ["home"] if path == "/" else (["operator"] if path == "/home" else ["Desktop", "Documents", "Downloads", "loot"])
		for directory: String in directories:
			var i: int = _items.add_item(directory, load("res://assets/icons/folder.svg"))
			_items.set_item_metadata(i, {"directory": path.path_join(directory)})
	elif path == "/home/operator/loot":
		for credential: Dictionary in loot:
			var filename: String = str(credential.username) + (".ntlm" if credential.type == "NTLM_HASH" else ".txt")
			var i: int = _items.add_item(filename, load("res://assets/icons/report.svg"))
			_items.set_item_metadata(i, credential)
	_status.text = "%s élément(s) · %s" % [_items.item_count, path]

func _activate(index: int) -> void:
	var data: Dictionary = _items.get_item_metadata(index)
	if data.has("directory"): navigate(data.directory)
	else: _select(index)

func _select(index: int) -> void:
	var data: Dictionary = _items.get_item_metadata(index)
	if not data.has("directory"):
		_preview.text = "%s\n%s · %s\n\n%s" % [data.get("username", ""), data.get("type", ""), "valide" if data.get("valid", true) else "invalidé", data.get("value", "")]

func _copy() -> void:
	var selected: PackedInt32Array = _items.get_selected_items()
	if selected.is_empty(): return
	var data: Dictionary = _items.get_item_metadata(selected[0])
	if data.has("value"):
		DisplayServer.clipboard_set(str(data.value))
		_status.text = "Valeur copiée."
