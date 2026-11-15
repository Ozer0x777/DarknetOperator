extends SceneTree
const Avatars = preload("res://scripts/ui/avatars.gd")
var checks: int = 0
var failures: int = 0
func _initialize() -> void: call_deferred("run")
func check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(message)
func settle() -> void:
	for i: int in range(5): await process_frame
func run() -> void:
	root.size = Vector2i(1280, 720)
	root.content_scale_size = Vector2i.ZERO
	var forum: Control = load("res://scripts/ui/forum.gd").new()
	root.add_child(forum)
	forum.setup()
	forum.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var fixture: String = (OS.get_environment("REDTEAM_VALIDATION_DIR") if not OS.get_environment("REDTEAM_VALIDATION_DIR").is_empty() else ProjectSettings.globalize_path("res://../build/validation")).path_join("social-preview.json")
	if not FileAccess.file_exists(fixture):
		check(false, "Le corpus des profils existe")
		quit(1)
		return
	var world: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(fixture))
	var portraits: Dictionary = world.profiles
	check(Avatars.PORTRAITS.size() == portraits.size(), "Chaque personnage public possède un avatar")
	for handle: String in portraits:
		check(Avatars.PORTRAITS.has(handle), "Avatar attribué à " + handle)
		if Avatars.PORTRAITS.has(handle): check(load(Avatars.PORTRAITS[handle]) is Texture2D, "Portrait importé : " + handle)
	check(forum.BANNERS.size() == 3, "Chaque forum possède sa bannière")
	for path: String in forum.BANNERS.values(): check(load(path) is Texture2D, "Bannière importée : " + path)
	var probe: PanelContainer = PanelContainer.new()
	probe.add_child(Label.new())
	root.add_child(probe)
	Avatars.apply(probe, "Madame_TLS", true)
	check(probe.get_child_count() == 2 and not probe.get_child(0).visible, "Portrait rond remplace le monogramme")
	check(probe.get_child(1).get_meta("round_avatar", false), "Le masque rond reste réservé à la messagerie")
	Avatars.apply(probe, "JoueurInconnu")
	check(probe.get_child_count() == 1 and probe.get_child(0).visible, "Le joueur inconnu garde son monogramme sans portrait résiduel")
	probe.queue_free()
	var rows: Array = [
		{"id":"a","forum":"breachboard","section":"Discussion","category":"Culture & pauses","title":"Une exposition","author":"Madame_TLS","body":"Une discussion à plusieurs voix.","unread":2,"last_minute":20,"created_minute":1,"count":2,"participants":["Madame_TLS","miette"]},
		{"id":"b","forum":"breachboard","section":"Discussion","category":"Matériel","title":"Une réparation","author":"nullpointer","body":"Du matériel réparé.","unread":0,"last_minute":10,"created_minute":5,"count":0,"participants":["nullpointer"]},
	]
	forum.update_data([], {"tier":3,"route":"relay","forum_unlocked":true}, "Operator", false)
	forum.set_world({"profiles":portraits,"threads":rows,"forum_counts":{"a":2,"b":0}})
	forum.navigate("breachboard", "", "Discussion")
	await settle()
	check(forum._topics().size() == 2 and forum._topics()[0].id == "a", "Tri par activité réelle")
	forum._topic_sort = 1
	check(forum._topics()[0].id == "b", "Tri par date d’ouverture")
	forum._category = "Culture & pauses"
	forum.render()
	check(forum._topics().size() == 1 and forum._topics()[0].id == "a", "Catégorie filtre sans mélanger les sujets")
	forum._category = ""
	forum._unread_only = true
	check(forum._topics().size() == 1, "Le filtre non lu suit les données du moteur")
	forum.navigate("breachboard", "a", "Discussion")
	await settle()
	var forum_portrait: PanelContainer = forum.find_children("ForumAvatar", "PanelContainer", true, false)[0]
	check(forum_portrait.size == Vector2(200, 200), "Le portrait du sujet est affiché en 200 pixels")
	forum._reply.text = "Mon brouillon reste ici."
	forum.set_replies("a", [{"author":"miette","text":"J’y suis allée aussi.","time":"09/11 09:00"}])
	check(forum._reply.text == "Mon brouillon reste ici.", "Recevoir des réponses conserve le brouillon")
	check(forum._topics().is_empty(), "Un sujet lu sort du filtre")
	check(forum._topics(false).size() == 2, "Un sujet ouvert reste accessible malgré les filtres de liste")
	forum._show_member("Madame_TLS")
	await settle()
	check(forum._member_card.find_children("Portrait", "TextureRect", true, false).size() == 1, "Le profil montre le bon portrait")
	var profile_portrait: TextureRect = forum._member_card.find_children("Portrait", "TextureRect", true, false)[0]
	check(profile_portrait.size == Vector2(200, 200), "Le portrait de profil est affiché en 200 pixels")
	if forum._member_dialog.size.x > 500 or forum._member_dialog.size.y > 400:
		print("Profile geometry: ", forum._member_dialog.size, " card: ", forum._member_card.size, " minimum: ", forum._member_card.get_combined_minimum_size())
		for child: Node in forum._member_dialog.get_children():
			if child is Control: print(child.name, " visible=", child.visible, " size=", child.size, " min=", child.get_combined_minimum_size())
	check(forum._member_dialog.size.x >= 400 and forum._member_dialog.size.x <= 500 and forum._member_dialog.size.y >= 320 and forum._member_dialog.size.y <= 400, "La fiche de profil reste compacte")
	check("\n".join(forum._member_card.find_children("*", "Label", true, false).map(func(label: Node) -> String: return label.text)).contains("CTI"), "Le profil public conserve sa biographie")
	forum._member_dialog.hide()
	forum._unread_only = false
	forum.navigate("breachboard", "", "Discussion")
	forum.size = Vector2(600, 600)
	await settle()
	check(forum.find_children("ForumFilters", "HFlowContainer", true, false).size() == 1, "Les catégories restent accessibles en fenêtre compacte")
	forum.queue_free()
	await settle()
	print("Forums et avatars : %s contrôles, %s échec(s)" % [checks, failures])
	quit(1 if failures else 0)
