extends SceneTree
## Les états proviennent des douze parcours API, avec leurs vraies consoles sauvegardées.
class OfflineTransport extends RefCounted:
	func request(_path: String, _payload: Variant = null) -> Dictionary:
		return {"error":"Rejeu local : aucun serveur HTTP nécessaire."}
var failures: int = 0
var checks: int = 0
func _initialize() -> void: call_deferred("run")
func check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(message)
func run() -> void:
	var filename: String = (OS.get_environment("REDTEAM_VALIDATION_DIR") if not OS.get_environment("REDTEAM_VALIDATION_DIR").is_empty() else ProjectSettings.globalize_path("res://../build/validation")).path_join("act3-qualification.json")
	check(FileAccess.file_exists(filename), "Le corpus API de l’acte III existe")
	if failures:
		quit(1)
		return
	var corpus: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(filename))
	check(int(corpus.missions) == 12 and int(corpus.resumes) == 24, "Douze missions et vingt-quatre reprises réelles")
	root.size = Vector2i(1280, 720)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	for i: int in range(5): await process_frame
	desktop.session.request_transport = OfflineTransport.new()
	for record: Dictionary in corpus.records:
		var saved: Dictionary = record.state
		desktop._restore_console_windows(saved)
		for i: int in range(5): await process_frame
		check(saved.status == "ENDED" and saved.winner == "RED", "Le dossier API est réellement réussi : " + str(record.contract))
		for id: String in saved.terminals:
			if id != "main" and not id.begins_with("term-"): continue
			check(desktop.terminal_views.has(id), "Console restaurée : " + id)
			if desktop.terminal_views.has(id):
				var view: Control = desktop.terminal_views[id]
				check(view.context.get("hostname", "") == saved.terminals[id].hostname, "L’origine reste propre à chaque console")
				if saved.terminal_transcripts.has(id) and not saved.terminal_transcripts[id].is_empty():
					check(not view.output.get_parsed_text().is_empty(), "Le texte sauvegardé reste visible")
	var windows_record: Dictionary = corpus.records.filter(func(item: Dictionary) -> bool: return item.contract == "act3_winrm")[0]
	desktop._restore_console_windows(windows_record.state)
	for i: int in range(5): await process_frame
	var win: Control = desktop.terminal_views["term-6"]
	check(win.context.shell == "powershell" and win.context.user == "audit", "La session WinRM reprend avec le compte lecteur")
	check(desktop.terminal_views["term-2"].context.foreground != null, "Le serveur Chisel reste au premier plan")
	check(desktop.terminal_views["term-3"].context.foreground != null, "Le client Chisel reste dans sa propre console")
	check(desktop.terminal_views.main.context.hostname == "kali", "Kali reste indépendant de WinRM")
	desktop._profile = {"act2":{"completed":10,"total":10,"chapters":[]},"act3":{"completed":0,"total":12,"unlocked":true,"chapters":[{"id":"act3_decouverte","number":1,"title":"Une machine qu’on ne voit pas","status":"available"}]},"journey":{"title":"Acte III · 1/12","detail":"Traverse attend le premier constat.","app":"Telegrid","peer":"traverse","contract_id":"act3_decouverte"},"tier":2,"route":"tor","forum_unlocked":true,"campaign":{"invitation_accepted":true},"access":{"forums":{"exployt":{"unlocked":true,"reason":""}}}}
	desktop.forum_view.update_data([], desktop._profile, "NightShift", false)
	desktop.forum_view.navigate("exployt", "", "Campagne")
	for i: int in range(5): await process_frame
	var labels: Array[Node] = desktop.forum_view.find_children("*", "Label", true, false)
	check(labels.any(func(label: Node) -> bool: return label.text == "Acte III - Les frontières invisibles"), "La campagne affiche la tranche de l’acte III")
	check(labels.any(func(label: Node) -> bool: return label.text == "0 / 12 dossiers validés"), "Le compteur affiche les douze dossiers")
	desktop.queue_free()
	for i: int in range(5): await process_frame
	print("Acte III : %s contrôles, %s échec(s)" % [checks, failures])
	quit(1 if failures else 0)
