extends ScrollContainer
## Un appareil matériel fictif, indépendant du navigateur et des communautés.
const UI = preload("res://scripts/ui/style.gd")
signal device_action(action: String, request_id: String)
var _data: Dictionary = {}
var _busy: bool = false
var _error: String = ""

func setup() -> void:
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	render()

func set_data(data: Dictionary, busy: bool = false, error: String = "") -> void:
	_data = data.duplicate(true)
	_busy = busy
	_error = error
	render()

func _action(action: String, id: String = "") -> void:
	if _busy: return
	_busy = true
	render()
	device_action.emit(action, id)

func render() -> void:
	UI.clear(self)
	var content: VBoxContainer = VBoxContainer.new()
	content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	content.add_theme_constant_override("separation", 12)
	add_child(content)
	content.add_child(UI.label("ColdVault", 28, Color("a7e7cf")))
	content.add_child(UI.wrapped("Portefeuille matériel simulé · indépendant des forums", 12, Color("a8b5c4")))
	var balance: Label = UI.label("%s ₵" % int(_data.get("balance", 0)), 32)
	balance.set_meta("wallet_balance", true)
	content.add_child(balance)
	var device: PanelContainer = UI.panel(Color("101c21"), 16, 10)
	content.add_child(device)
	var screen: VBoxContainer = VBoxContainer.new()
	device.add_child(screen)
	screen.add_child(UI.label(str(_data.get("device_id", "Appareil personnel")), 12, Color("a7e7cf")))
	var connected: bool = _data.get("connected", false)
	var unlocked: bool = _data.get("unlocked", false)
	screen.add_child(UI.label("Appareil déconnecté" if not connected else ("Appareil verrouillé" if not unlocked else "Appareil prêt à confirmer"), 15))
	var actions: HFlowContainer = HFlowContainer.new()
	screen.add_child(actions)
	if not connected:
		actions.add_child(UI.button("Connecter l’appareil", func() -> void: _action("connect")))
	elif not unlocked:
		actions.add_child(UI.button("Déverrouiller sur l’appareil", func() -> void: _action("unlock")))
	if connected: actions.add_child(UI.button("Déconnecter", func() -> void: _action("disconnect")))
	var pending: Dictionary = _data.get("pending", {}) if _data.get("pending") != null else {}
	if not pending.is_empty():
		screen.add_child(UI.label("VÉRIFIER LE PAIEMENT", 11, Color("a7e7cf")))
		screen.add_child(UI.wrapped(str(pending.get("label", "Achat")), 16))
		screen.add_child(UI.wrapped(str(pending.get("recipient", "Fournisseur")), 12))
		screen.add_child(UI.label("%s ₵" % int(pending.get("amount", 0)), 24))
		var id: String = str(pending.get("id", ""))
		var confirm: Button = UI.button("Confirmer sur l’appareil", func() -> void: _action("approve", id), Color("245444"))
		confirm.disabled = not connected or not unlocked
		screen.add_child(confirm)
		screen.add_child(UI.button("Refuser le paiement", func() -> void: _action("cancel", id)))
	if not _error.is_empty(): content.add_child(UI.wrapped(_error, 12, Color("ffb8a6")))
	content.add_child(UI.label("HISTORIQUE DU PORTEFEUILLE", 11, Color("a8b5c4")))
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.custom_minimum_size.y = 170
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	content.add_child(scroll)
	var list: VBoxContainer = VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)
	var entries: Array = _data.get("entries", []).duplicate(true)
	entries.reverse()
	for entry: Dictionary in entries:
		var item: PanelContainer = UI.panel(Color("242e38"), 10, 4)
		list.add_child(item)
		var row: VBoxContainer = VBoxContainer.new()
		item.add_child(row)
		var amount: int = int(entry.get("amount", 0))
		row.add_child(UI.wrapped(("+" if amount > 0 else "") + str(amount) + " ₵ · " + str(entry.get("label", "Mouvement")), 13))
		row.add_child(UI.label("Solde après opération : %s ₵" % int(entry.get("balance", 0)), 11, Color("a8b5c4")))
	if _busy:
		for button: Node in find_children("*", "Button", true, false): button.disabled = true
