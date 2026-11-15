extends SceneTree
class RecordedTransport extends RefCounted:
	var step: Dictionary = {}
	var calls: int = 0
	var mismatch: String = ""
	func request(path: String, payload: Variant = null) -> Dictionary:
		if path == "/api/social/choice":
			calls += 1
			if payload != step.request:
				mismatch = "Le choix envoyé ne correspond pas à la scène enregistrée."
				return {"error": mismatch}
			return {"data": step.response}
		if path == "/api/social/read": return {"data": {}}
		mismatch = "Requête inattendue : " + path
		return {"error": mismatch}
var checks: int = 0
var failures: int = 0
func _initialize() -> void: call_deferred("run")
func check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(message)
func settle() -> void:
	for index: int in range(8): await process_frame
func run() -> void:
	var path: String = "res://../build/validation/tls-arc-replays.json"
	if not FileAccess.file_exists(path):
		push_error("Corpus absent : lance backend/tls_arc_validation.py.")
		quit(1)
		return
	var corpus: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
	root.size = Vector2i(1280,720)
	root.content_scale_size = Vector2i.ZERO
	for route: Dictionary in corpus.routes:
		var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
		root.add_child(desktop)
		await settle()
		var transport: RecordedTransport = RecordedTransport.new()
		desktop.session.request_transport = transport
		desktop.session.handle = "NightShift"
		var chat: Control = desktop.messengers.chordly
		chat._draft_store.directory_override = "/tmp/rts-tls-replay-%s-%s" % [OS.get_process_id(),route.stance]
		chat.set_identity("NightShift")
		desktop._open("Chordly")
		desktop.apps.Chordly.size = Vector2(600,600)
		for step: Dictionary in route.steps:
			transport.step = step
			desktop._update_social(step.before)
			chat._select_peer("Madame_TLS")
			chat.set_offers([])
			chat.set_journey({})
			await settle()
			var button: Button = chat._choice_list.get_node_or_null("Choice_" + str(step.option_id))
			check(button != null and not button.disabled, "Réponse disponible : " + str(step.scene_id))
			if button == null: continue
			button.pressed.emit()
			await settle()
			check(transport.mismatch.is_empty() and chat._choice_sending.is_empty(), "Choix transmis et confirmé : " + str(step.scene_id))
			desktop._update_social(step.published)
			await settle()
			check(chat._ids.has(step.reply_id), "La réponse du personnage est affichée : " + str(step.scene_id))
			check(chat._ids.has("scene:answer:" + str(step.scene_id)), "La réponse choisie reste dans l'historique")
		check(transport.calls == 6, "Six choix API rejoués pour le lien " + str(route.stance))
		check(chat.message_text().contains("BRUME-17"), "Les pièces de comparaison sont lisibles dans l'échange")
		desktop.queue_free()
		await settle()
	print("Arc TLS dans Godot : %s contrôles, %s échec(s)" % [checks,failures])
	quit(1 if failures else 0)
