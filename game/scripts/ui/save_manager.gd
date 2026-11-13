extends Control
const MenuStyle = preload("res://scripts/ui/menu_style.gd")
const UI = preload("res://scripts/ui/style.gd")
signal closed
signal loaded
var session: RefCounted
var slots: Array = []
var records: ItemList
var name_input: LineEdit
var details: Label
var status: Label
var actions: Array[Button] = []
var confirm: ConfirmationDialog
var pending: Callable
var allow_write: bool = true
var _working: bool = false
var _center: CenterContainer
var _panel: PanelContainer

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var shade: ColorRect = ColorRect.new()
	shade.color = Color(0.01, 0.02, 0.04, 0.96)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(shade)
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	add_child(scroll)
	var center: CenterContainer = CenterContainer.new()
	_center = center
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(center)
	var panel: PanelContainer = MenuStyle.panel(26)
	_panel = panel
	panel.custom_minimum_size = Vector2(950, 640)
	center.add_child(panel)
	var box: VBoxContainer = VBoxContainer.new()
	box.add_theme_constant_override("separation", 15)
	panel.add_child(box)
	box.add_child(UI.label("SAUVEGARDES", 28))
	box.add_child(UI.label("Chaque emplacement contient la carrière entière, les conversations et la mission en cours.", 14))
	records = ItemList.new()
	records.max_text_lines = 2
	records.add_theme_stylebox_override("panel", UI.box(MenuStyle.BG, MenuStyle.BORDER, 3, 8))
	records.add_theme_stylebox_override("selected", UI.box(Color("59372e"), MenuStyle.ACCENT, 2, 0))
	records.add_theme_stylebox_override("selected_focus", UI.box(Color("59372e"), MenuStyle.ACCENT, 2, 0))
	records.custom_minimum_size.y = 330
	records.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(records)
	records.item_selected.connect(_select_slot)
	details = UI.label("Sélectionne un emplacement pour voir ses détails.", 14)
	details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	details.custom_minimum_size.y = 50
	box.add_child(details)
	name_input = LineEdit.new()
	name_input.placeholder_text = "Nom de la sauvegarde"
	name_input.max_length = 80
	box.add_child(name_input)
	var row: HBoxContainer = HBoxContainer.new()
	box.add_child(row)
	_action(row, "Nouvel emplacement", _save_new)
	_action(row, "Écraser", func() -> void: _ask("Remplacer cet emplacement manuel par la carrière actuelle ?", _overwrite))
	_action(row, "Charger", func() -> void: _ask("Charger cette sauvegarde ? La progression courante sera conservée dans Récupération avant chargement.", _load_slot))
	_action(row, "Supprimer", func() -> void: _ask("Supprimer définitivement cet emplacement ?", _delete_slot))
	_action(row, "Retour", _close)
	status = UI.label("Lecture des sauvegardes…", 14)
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(status)
	confirm = ConfirmationDialog.new()
	confirm.title = "Confirmation"
	confirm.get_ok_button().text = "Confirmer"
	confirm.get_cancel_button().text = "Annuler"
	confirm.confirmed.connect(func() -> void: if pending.is_valid(): pending.call())
	add_child(confirm)
	resized.connect(_resize_panel)
	_resize_panel()
	records.grab_focus()
	if session != null: await refresh()

func _action(row: HBoxContainer, text: String, callback: Callable) -> void:
	var button: Button = MenuStyle.button(text, callback, text == "Charger")
	row.add_child(button)
	actions.append(button)

func _busy(value: bool) -> void:
	_working = value
	for button: Button in actions: button.disabled = value
	if not value: _update_actions()

func selected() -> Dictionary:
	var indices: PackedInt32Array = records.get_selected_items()
	return slots[indices[0]] if indices.size() > 0 else {}

func _ask(text: String, callback: Callable) -> void:
	if selected().is_empty(): status.text = "Sélectionne d’abord un emplacement."; return
	pending = callback
	confirm.dialog_text = text
	confirm.popup_centered(Vector2i(620, 180))

func refresh() -> void:
	_busy(true)
	var result: Dictionary = await session.request("/api/saves")
	_busy(false)
	if result.has("error"): status.text = result.error; return
	set_slots(result.data.slots)

func set_slots(value: Array) -> void:
	var previous_id: String = str(selected().get("id", ""))
	slots = value
	records.clear()
	details.text = "Sélectionne un emplacement pour voir ses détails."
	for slot: Dictionary in slots:
		if not slot.get("valid", false):
			records.add_item("ENDOMMAGÉE · %s · %s" % [slot.name, slot.get("error", "Illisible")])
			continue
		var kind: String = {"manual": "Manuelle", "auto": "Auto", "recovery": "Récupération"}.get(slot.get("kind", "manual"), "Manuelle")
		records.add_item("%s · %s · %s · %s UTC" % [kind, slot.name, slot.mission, str(slot.date).substr(0, 19).replace("T", " ")])
	status.text = "%s emplacement(s). Les autosauvegardes tournent sur trois emplacements ; les sauvegardes manuelles sont conservées." % slots.size()
	if not slots.is_empty():
		var index: int = 0
		for candidate: int in range(slots.size()):
			if slots[candidate].id == previous_id: index = candidate; break
		records.select(index)
		_select_slot(index)
	_update_actions()

func _save_new() -> void:
	if not allow_write: return
	await _perform("/api/saves/write", {"name": name_input.text})

func _overwrite() -> void:
	var slot: Dictionary = selected()
	if not str(slot.get("id", "")).begins_with("manual-"): status.text = "Seul un emplacement manuel peut être écrasé ici."; return
	await _perform("/api/saves/write", {"name": name_input.text, "slot_id": slot.id, "confirm": true})

func _load_slot() -> void:
	var slot: Dictionary = selected()
	if not slot.get("valid", false): status.text = "Cette sauvegarde est endommagée ; choisis un autre emplacement."; return
	await _perform("/api/saves/load", {"slot_id": slot.id, "confirm": true}, true)

func _delete_slot() -> void:
	await _perform("/api/saves/delete", {"slot_id": selected().id, "confirm": true})

func _perform(path: String, payload: Dictionary, enter_game: bool = false) -> void:
	_busy(true)
	var result: Dictionary = await session.request(path, payload)
	_busy(false)
	if result.has("error"): status.text = result.error; return
	if enter_game: loaded.emit(); return
	await refresh()
	status.text += "\nOpération terminée."


func _select_slot(index: int) -> void:
	var slot: Dictionary = slots[index]
	name_input.text = str(slot.name)
	_update_actions()
	if not slot.get("valid", false): details.text = slot.get("error", "Sauvegarde illisible."); return
	details.text = "%s · %s · palier %s · %s ₵\nTick %s · %s min en mission · %s UTC" % [slot.get("handle", ""), slot.mission, int(slot.get("tier", 0)), int(slot.money), int(slot.tick), int(float(slot.get("play_seconds", 0)) / 60), str(slot.date).substr(0, 19).replace("T", " ")]


func _resize_panel() -> void:
	if _panel == null: return
	_center.custom_minimum_size.y = size.y
	_panel.custom_minimum_size.x = minf(950, maxf(700, size.x - 40))
	records.custom_minimum_size.y = clampf(size.y - 500, 180, 330)

func _close() -> void:
	if _working: return
	closed.emit()
	queue_free()

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE and not _working:
		if confirm.visible: confirm.hide()
		else: _close()
		get_viewport().set_input_as_handled()


func _update_actions() -> void:
	if _working or actions.size() < 5: return
	var slot: Dictionary = selected()
	actions[0].disabled = not allow_write
	actions[1].disabled = not allow_write or not str(slot.get("id", "")).begins_with("manual-")
	actions[2].disabled = not slot.get("valid", false)
	actions[3].disabled = slot.is_empty()
