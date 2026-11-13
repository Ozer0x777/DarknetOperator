extends SceneTree
## Commandes des nouveaux dossiers, capturées par l'API, saisies dans les contrôles réels.
class Transport extends RefCounted:
	var expected: Dictionary = {}
	var profile: Dictionary = {}
	var calls: int = 0
	var mismatch: String = ""
	func request(path: String, payload: Variant = null) -> Dictionary:
		if path.ends_with("/terminal"):
			calls += 1
			var console: String = {"c": "main", "s": "remote", "g": "gophish"}.get(str(expected.get("kind", "")), "")
			if payload.get("line") != expected.get("line") or payload.get("console_id") != console:
				mismatch = JSON.stringify(payload)
			return {"data": expected.get("response", {})}
		if path == "/api/profile": return {"data": profile}
		if path == "/api/contracts": return {"data": []}
		if path == "/api/social": return {"data": {"threads": [], "contacts": [], "messages": [], "offers": []}}
		mismatch = path
		return {"error": path}
var checks: int = 0
var failures: int = 0
func check(value: bool, description: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(description)
func _initialize() -> void: call_deferred("run")
func run() -> void:
	root.size = Vector2i(1440, 900)
	for variant: String in ["sqlmap", "connecteur"]:
		var corpus: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../build/validation/act1-%s.json" % variant))
		for record: Dictionary in corpus.records:
			if not str(record.contract_id).begins_with("act1_") and record.contract_id != "mauvaise_adresse": continue
			var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
			root.add_child(desktop)
			var transport: Transport = Transport.new()
			transport.profile = corpus.report.profile
			desktop.session.request_transport = transport
			desktop.session.game_id = "replay-act1"
			desktop.session.handle = "NightShift"
			desktop._profile = transport.profile.duplicate(true)
			desktop.session.apply_state(record.initial)
			await process_frame
			print("Acte I : " + record.contract_id + " / " + variant)
			for operation: Dictionary in record.operations:
				if operation.kind not in ["c", "s", "g"]:
					desktop.session.apply_state(operation.state)
					continue
				desktop.session.apply_state(operation.before)
				var id: String = {"c": "main", "s": "remote", "g": "gophish"}[operation.kind]
				if not desktop.terminal_views.has(id): desktop._create_terminal(id, "Console " + id)
				var view: Control = desktop.terminal_views[id]
				transport.expected = operation
				desktop._open(desktop.console_apps[id])
				await process_frame
				var secret: bool = view.input.secret
				var previous: int = view.output.get_parsed_text().length()
				view.input.text = str(operation.line)
				view.input.grab_focus()
				var before: int = transport.calls
				var key: InputEventKey = InputEventKey.new()
				key.keycode = KEY_ENTER
				key.pressed = true
				root.push_input(key, true)
				await process_frame
				check(transport.calls == before + 1 and transport.mismatch.is_empty(), "Commande envoyée dans sa console : " + str(operation.line))
				if secret: check(not view.output.get_parsed_text().substr(previous).contains(str(operation.line)), "Secret MySQL/SSH masqué")
				desktop.session.apply_state(operation.state)
				check(view.context.get("shell") == operation.state.terminals[id].get("shell"), "Contexte Linux/Windows restauré")
			desktop.session.apply_state(record.success)
			check(desktop.report.text.contains("SUCCESS"), "Débriefing : " + str(record.contract_id))
			desktop.queue_free()
			await process_frame
	print("Acte I — terminaux : %s contrôles, %s échec(s)" % [checks, failures])
	quit(1 if failures else 0)
