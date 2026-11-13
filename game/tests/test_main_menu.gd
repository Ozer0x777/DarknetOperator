extends SceneTree
var failures: int = 0
var checks: int = 0
class Transport extends RefCounted:
	var calls: Array = []
	func request(path: String, payload: Variant = null) -> Dictionary:
		calls.append([path, payload])
		if path == "/api/saves": return {"data": {"slots": [], "profile": {"handle": "Operator", "money": 100, "tier": 0}}}
		return {"data": {}}
func check(value: bool, message: String) -> void:
	checks += 1
	if not value: failures += 1; push_error(message)
func _initialize() -> void: call_deferred("run")
func run() -> void:
	root.size = Vector2i(1440, 900)
	var menu: Control = load("res://scenes/main_menu.tscn").instantiate()
	root.add_child(menu)
	await process_frame
	check(menu.continue_button.disabled, "Continuer désactivé sans carrière")
	check(menu.find_children("*", "Button", true, false).size() >= 6, "Actions du menu présentes")
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1280, 720)
	await process_frame
	await process_frame
	var buttons_fit: bool = true
	for button: Node in menu.menu.find_children("*", "Button", true, false):
		if button.is_visible_in_tree() and not Rect2(Vector2.ZERO, Vector2(root.size)).encloses(button.get_global_rect()): buttons_fit = false
	check(buttons_fit, "Actions visibles en 1280 × 720")
	menu.new_button.pressed.emit()
	check(menu.new_dialog.visible, "Formulaire de nouvelle partie")
	var escape: InputEventKey = InputEventKey.new()
	escape.pressed = true
	escape.keycode = KEY_ESCAPE
	menu._unhandled_key_input(escape)
	check(not menu.new_dialog.visible and menu.new_button.has_focus(), "Échap annule la nouvelle carrière et restaure le focus")
	menu.session.request_transport = Transport.new()
	await menu.refresh()
	check(not menu.continue_button.disabled, "Carrière existante proposée")
	menu.saves_button.pressed.emit()
	await process_frame
	var manager: Control = menu.get_child(menu.get_child_count()-1)
	manager.set_slots([{"id": "manual-" + "b".repeat(32), "name": "Abîmée", "valid": false, "error": "Corrompue"}])
	check(manager.actions[2].disabled and not manager.actions[3].disabled, "Sauvegarde abîmée supprimable mais non chargeable")
	manager.set_slots([{"id": "manual-" + "a".repeat(32), "name": "Avant serveur", "valid": true, "kind": "manual", "date": "2026-11-10T12:30:00", "mission": "Ravelle", "tick": 4, "money": 100}])
	await process_frame
	check(Rect2(Vector2.ZERO, Vector2(root.size)).encloses(manager.actions[-1].get_global_rect()), "Retour des sauvegardes visible en 720p")
	manager.records.select(0)
	manager._select_slot(0)
	check(manager.details.text.contains("Ravelle") and manager.details.text.contains("100"), "Détails de la sauvegarde sélectionnée")
	manager._ask("Charger ?", manager._load_slot)
	check(manager.confirm.visible, "Confirmation avant chargement")
	check(not menu.session.request_transport.calls.any(func(call: Array) -> bool: return call[0] == "/api/saves/load"), "Aucun chargement avant confirmation")
	manager.confirm.hide()
	manager.queue_free()
	await process_frame
	await menu._enter_game()
	await process_frame
	check(is_instance_valid(menu.desktop) and not menu.menu.visible, "Menu vers bureau")
	menu.desktop.return_to_menu.emit()
	await process_frame
	await process_frame
	check(menu.menu.visible, "Retour du bureau au menu")
	menu.queue_free()
	await process_frame
	print("Menu et sauvegardes : %s contrôles, %s échec(s)" % [checks, failures])
	quit(1 if failures else 0)
