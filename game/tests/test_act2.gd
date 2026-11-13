extends SceneTree
var checks: int = 0
var failures: int = 0
class Transport extends RefCounted:
	var calls: Array = []
	func request(path: String, payload: Variant = null) -> Dictionary:
		calls.append([path,payload])
		if path.ends_with("/bloodhound") or path.ends_with("/bloodhound/import"):
			return {"data":{"files":["/home/operator/loot/orbe.zip"],"source":"/home/operator/loot/orbe.zip","nodes":[{"id":"u","name":"AUDIT@ORBE.LAB","kind":"users"},{"id":"g","name":"OPÉRATEURS@ORBE.LAB","kind":"groups"}],"edges":[{"source":"u","target":"g","type":"MemberOf"}]}}
		return {"data":{}}
func _initialize() -> void: call_deferred("run")
func check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(message)
func settle() -> void:
	for i: int in range(10): await process_frame
func run() -> void:
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1280,720)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await settle()
	var transport: Transport = Transport.new()
	desktop.session.request_transport = transport
	desktop.session.game_id = "act2-test"
	desktop._open("BloodHound")
	await settle()
	check(desktop.apps.has("BloodHound"),"L’analyse BloodHound est accessible depuis le bureau")
	var analysis: Control = desktop.apps.BloodHound.get_meta("analysis")
	check(analysis.files.item_count==1,"L’archive locale est proposée")
	check(analysis.graph.edges.size()==1,"Le graphe montre la relation importée")
	analysis.search.text = "AUDIT"
	analysis.search.text_changed.emit("AUDIT")
	await settle()
	var nodes: Array = analysis.graph.nodes
	check(nodes.size()==1,"La recherche filtre les objets collectés")
	analysis.search.text = ""
	analysis.search.text_changed.emit("")
	await analysis._import()
	check(transport.calls.any(func(call: Array) -> bool: return call[0].ends_with("/bloodhound/import") and call[1].path=="/home/operator/loot/orbe.zip"),"L’import passe par la validation moteur")
	check(analysis.graph.edges.size()==1,"Réimporter ne duplique pas les relations")
	desktop.apps.BloodHound.size = Vector2(720,500)
	await settle()
	check(analysis.size.x <= desktop.apps.BloodHound.size.x and desktop.apps.BloodHound.size.y<=501,"L’analyse tient dans la fenêtre sans agrandissement forcé")
	desktop._profile = {"journey":{"title":"Acte II — Une vieille passation","detail":"Cendre te propose le premier dossier.","app":"Telegrid","peer":"cendre","contract_id":"act2_passation"},"act2":{"completed":0.0,"total":10.0,"unlocked":true,"chapters":[{"id":"act2_passation","number":1,"title":"Une vieille passation","peer":"cendre","channel":"telegrid","status":"available"}]}}
	desktop._profile.merge({"tier":2,"route":"tor","forum_unlocked":true,"campaign":{"invitation_accepted":true},"access":{"forums":{"exployt":{"unlocked":true,"reason":""}}}})
	desktop.forum_view.update_data([],desktop._profile,"NightShift",false)
	desktop.forum_view.navigate("exployt","","Campagne")
	await settle()
	var labels: Array[Node] = desktop.forum_view.find_children("*","Label",true,false)
	check(labels.any(func(label: Node) -> bool: return label.text.contains("Acte II")),"La campagne affiche l’acte II")
	check(labels.any(func(label: Node) -> bool: return label.text == "0 / 10 dossiers validés"),"Les compteurs JSON restent des nombres entiers lisibles")
	var section_buttons: Array[Node] = desktop.forum_view.find_children("*","Button",true,false)
	check(section_buttons.any(func(button: Node) -> bool: return button.text == "Campagne"),"Exployt expose son onglet de campagne")
	check(section_buttons.any(func(button: Node) -> bool: return button.text == "Contacter cendre sur Telegrid"),"Le premier dossier mène au nouveau contact")
	check(section_buttons.filter(func(button: Node) -> bool: return button.text == "Contacter cendre sur Telegrid").size()==1,"La première piste reste visible avant le départ et sans action dupliquée")
	var historic: Dictionary = analysis._data.duplicate(true)
	historic["stale"] = true
	analysis.apply_data(historic)
	check(analysis.status.text.contains("précédent"),"Une ancienne collecte est signalée comme telle")
	desktop.queue_free()
	await settle()
	print("Acte II et analyse : %s contrôles, %s échec(s)" % [checks,failures])
	quit(1 if failures else 0)
