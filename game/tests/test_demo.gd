extends SceneTree
var checks: int = 0
var failures: int = 0
class Transport extends RefCounted:
	var calls: Array = []
	func request(path: String, payload: Variant = null) -> Dictionary:
		calls.append([path, payload])
		if path == "/api/profile/continue": return {"data": {"handle": "NightShift", "play_mode": "campaign", "money": 340}}
		if path == "/api/social": return {"data": {"journey": {"title": "Vérifier un accès", "app": "Chordly", "peer": "k0rvid", "contract_id": "intro_login"}, "contacts": [{"id": "k0rvid", "name": "k0rvid", "channel": "chordly", "kind": "direct", "members": ["k0rvid"]}], "offers": [], "messages": []}}
		return {"data": {}}
func _initialize() -> void: call_deferred("run")
func check(value: bool, text: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(text)
func settle() -> void:
	for i: int in range(12): await process_frame
func run() -> void:
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1280,720)
	var menu: Control = load("res://scenes/main_menu.tscn").instantiate()
	root.add_child(menu)
	await settle()
	menu.new_dialog.show()
	await settle()
	check(menu.mode_select.item_count == 2, "Deux parcours proposés à la création")
	check(menu.mode_select.selected == 0, "La campagne reste le choix par défaut")
	check(Rect2(Vector2.ZERO, Vector2(root.size)).encloses(menu.mode_select.get_global_rect()), "Choix du parcours visible en 720p")
	menu.queue_free()
	await settle()
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await settle()
	var transport: Transport = Transport.new()
	desktop.session.request_transport = transport
	var chat: Control = desktop.messengers.chordly
	desktop._update_social({"journey": {"title": "Démo terminée", "detail": "Miette conserve tes preuves. Les primes et décisions restent sauvegardées.", "app": "Chordly", "peer": "miette", "action": "continue_campaign"}, "contacts": [{"id": "miette", "name": "miette", "kind": "direct", "channel": "chordly", "members": ["miette"], "bio": "Confiance établie - preuves vérifiées."}], "messages": [], "offers": []})
	desktop._open("Chordly")
	var frame: Control = desktop.apps.Chordly
	frame.position = Vector2(60,60)
	frame.size = Vector2(600,420)
	await settle()
	check(chat.selected_peer == "miette", "Une fin de démo rechargée ouvre le bon contact")
	var actions: Array[Node] = chat._stream.find_children("*", "Button", true, false)
	var button: Button = null
	for action: Button in actions:
		if action.text == "Continuer la campagne": button = action
	check(button != null, "La conclusion propose une poursuite explicite")
	check(frame.get_global_rect().encloses(chat.composer.get_global_rect()), "Conclusion et rédaction tiennent en fenêtre compacte")
	check(chat._details_bio.text.contains("Confiance établie"), "Le contact expose la relation acquise")
	if button != null: button.pressed.emit()
	await settle()
	check(transport.calls.any(func(call: Array) -> bool: return call[0] == "/api/profile/continue"), "La poursuite utilise la sauvegarde courante")
	check(desktop.get("_profile").get("play_mode") == "campaign", "Le retour API est appliqué au bureau")
	check(chat.selected_peer == "k0rvid", "La prochaine carte est ouverte chez k0rvid")
	check(chat._journey.get("contract_id") == "intro_login", "La prochaine compétence remplace la conclusion")
	desktop.queue_free()
	await settle()
	print("Démo et continuité : %s contrôles, %s échec(s)" % [checks,failures])
	quit(1 if failures else 0)
