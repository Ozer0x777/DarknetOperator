extends SceneTree
## Rejoue les commandes API dans les vrais contrôles Godot. Aucun serveur n'est lancé.
class RecordedTransport extends RefCounted:
	var record: Dictionary = {}
	var expected: Dictionary = {}
	var mismatch: String = ""
	var calls: int = 0
	func request(path: String, payload: Variant = null) -> Dictionary:
		if path.ends_with("/terminal"):
			calls += 1
			if payload.get("line") != expected.get("line") or payload.get("console_id") != expected.get("console_id"):
				mismatch = "La commande envoyée par le client diffère du corpus : " + JSON.stringify(payload)
				return {"error": mismatch}
			return {"data": expected.response}
		if path == "/api/profile": return {"data": record.profile}
		if path == "/api/contracts": return {"data": record.contracts}
		# Le règlement rafraîchit désormais aussi les cartes des contacts.
		if path == "/api/social": return {"data": {"contacts": [], "messages": [], "offers": [], "threads": [], "forum_counts": {}}}
		if path == "/api/profile/resume": return {"data": {"id": "replay", "state": record.resumed}}
		if path.ends_with("/start") or path.ends_with("/resume"): return {"data": {"status": "ok"}}
		if path == "/api/social/read": return {"data": {"status": "read"}}
		mismatch = "Requête inattendue dans le corpus : " + path
		return {"error": mismatch}
var checks: int = 0
var failures: int = 0
func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error(message)
func _initialize() -> void: call_deferred("run")
func desktop_for(record: Dictionary) -> Control:
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	var transport: RecordedTransport = RecordedTransport.new()
	transport.record = record
	desktop.session.request_transport = transport
	desktop.session.handle = "Operator"
	desktop.session.game_id = "replay"
	desktop.session.contracts = record.contracts
	desktop._profile = record.profile.duplicate(true)
	desktop.session.apply_state(record.initial)
	return desktop
func run() -> void:
	root.size = Vector2i(1440, 900)
	root.content_scale_size = Vector2i(1440, 900)
	var file: String = "res://../build/validation/ui-replays.json"
	if not FileAccess.file_exists(file):
		push_error("Corpus absent : lance python3 scripts/check_ui.py")
		quit(1)
		return
	var corpus: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(file))
	for record: Dictionary in corpus.successes:
		var desktop: Control = desktop_for(record)
		var transport: RecordedTransport = desktop.session.request_transport
		await process_frame
		print("Rejeu : " + record.contract_id + " / " + record.variant)
		for step: Dictionary in record.steps:
			desktop.session.apply_state(step.before_state)
			var id: String = step.console_id
			if not desktop.terminal_views.has(id):
				var number: int = id.trim_prefix("term-").to_int()
				desktop._create_terminal(id, "Terminal %s" % number)
			var view: Control = desktop.terminal_views[id]
			transport.expected = step
			desktop._open(desktop.console_apps[id])
			await process_frame
			check(view.input.editable, "Saisie accessible : " + record.contract_id + " / " + step.line)
			var secret: bool = view.input.secret
			var previous: int = view.output.get_parsed_text().length()
			view.input.text = step.line
			view.input.grab_focus()
			var before_calls: int = transport.calls
			var enter: InputEventKey = InputEventKey.new()
			enter.keycode = KEY_ENTER
			enter.pressed = true
			root.push_input(enter, true)
			await process_frame
			check(transport.calls == before_calls + 1 and transport.mismatch.is_empty(), "Entrée envoie la commande et la bonne console")
			if secret: check(not view.output.get_parsed_text().substr(previous).contains(step.line), "Mot de passe non affiché pendant la saisie")
			desktop.session.apply_state(step.state)
			check(view.context.get("shell") == step.state.terminals[id].get("shell"), "Shell restauré depuis la réponse du moteur")
			if view.context.get("shell") == "powershell": check(view.prompt.text.begins_with("PS "), "Invite PowerShell")
		desktop.session.apply_state(record.success)
		check(desktop.report.text.contains("SUCCESS"), "Débriefing de réussite : " + record.contract_id)
		check(desktop.report.text.contains(str(int(record.success.contract.payout))), "Règlement affiché")
		await desktop._resume_saved()
		check(desktop.session.state.status == "RUNNING", "Reprise réelle du contrôleur de bureau")
		for id: String in record.resumed.terminals:
			if id.begins_with("term-"): check(desktop.terminal_views.has(id), "Fenêtre de console restaurée : " + id)
		check(transport.mismatch.is_empty(), "Transport du rejeu cohérent")
		desktop.queue_free()
		await process_frame
	for record: Dictionary in corpus.failures:
		var desktop: Control = desktop_for(record)
		await process_frame
		await desktop._resume_saved()
		check(desktop.session.state.status == "RUNNING", "Reprise avant défaite : " + record.contract_id)
		desktop.session.apply_state(record.failure)
		check(desktop.report.text.contains("FAILED"), "Débriefing de défaite : " + record.contract_id)
		check(desktop.report.text.contains("Règlement reçu : 0"), "Aucun paiement en cas de défaite")
		desktop.queue_free()
		await process_frame
	print("Rejeux de scénarios Godot : %s contrôles, %s échec(s)" % [checks, failures])
	quit(1 if failures else 0)
