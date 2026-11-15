extends SceneTree
const Messenger = preload("res://scripts/ui/messenger.gd")
var checks: int = 0
var failures: int = 0

func _initialize() -> void: call_deferred("run")
func check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(message)
func settle() -> void:
	for index: int in range(12): await process_frame
func click(control: Control) -> void:
	var event: InputEventMouseButton = InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_LEFT
	event.position = control.get_global_rect().get_center()
	event.pressed = true
	root.push_input(event, true)
	event = event.duplicate()
	event.pressed = false
	root.push_input(event, true)
	await process_frame

func run() -> void:
	root.size = Vector2i(600, 600)
	root.content_scale_size = Vector2i.ZERO
	var chat: Control = Messenger.new()
	root.add_child(chat)
	chat.setup("chordly", "ChoiceTest")
	chat.position = Vector2.ZERO
	chat.size = Vector2(600, 600)
	chat._draft_store.directory_override = "/tmp/rts-choices-%s" % OS.get_process_id()
	chat.set_contacts([
		{"id":"Madame_TLS", "name":"Madame_TLS", "channel":"chordly", "kind":"direct", "members":["Madame_TLS"], "bio":"CTI et OSINT. Sport et musique."},
		{"id":"miette", "name":"miette", "channel":"chordly", "kind":"direct", "members":["miette"], "bio":"J’apprends."}])
	chat._select_peer("Madame_TLS")
	chat.composer.text = "Brouillon personnel à conserver"
	chat.set_scene_choices([{"id":"tls-premier-lien", "channel":"chordly", "peer":"Madame_TLS", "author":"Madame_TLS", "question":"Quel lien préfères-tu ?", "options":[
		{"id":"professionnel", "text":"Gardons surtout un lien professionnel pour le moment."},
		{"id":"amitie", "text":"Ça me ferait plaisir de parler d’autre chose, en amis."},
		{"id":"attirance", "text":"J’aimerais te connaître. Et pas seulement comme une collègue."}]}])
	await settle()
	check(chat._choice_panel.visible and chat._choice_list.get_child_count() == 4, "La question propose trois réponses sans sélection automatique")
	check(chat.size.x <= 600 and chat._choice_panel.get_global_rect().end.y <= 600, "Les choix restent dans une fenêtre de 600 pixels")
	var chosen: Array[Dictionary] = []
	chat.dialogue_choice.connect(func(channel: String, peer: String, scene_id: String, option_id: String) -> void:
		chosen.append({"channel":channel,"peer":peer,"scene_id":scene_id,"option_id":option_id}))
	var professional: Button = chat._choice_list.get_node("Choice_professionnel")
	await click(professional)
	check(chosen.size() == 1 and chosen[0].option_id == "professionnel" and chosen[0].peer == "Madame_TLS", "Un clic réel transmet l'identifiant de la réponse et le bon personnage")
	chat._choose_dialogue("Madame_TLS", "tls-premier-lien", "attirance")
	check(chosen.size() == 1, "Un envoi en cours empêche une deuxième réponse contradictoire")
	chat._select_peer("miette")
	await settle()
	check(not chat._choice_panel.visible, "Les choix de Madame_TLS ne sont pas affichés chez miette")
	chat.acknowledge_choice(false, "Écriture impossible, réessaie.")
	chat._select_peer("Madame_TLS")
	await settle()
	check(chat._choice_panel.visible and not chat._choice_list.get_node("Choice_professionnel").disabled, "Un échec garde le choix disponible")
	check(chat.composer.text == "Brouillon personnel à conserver", "Choisir et changer de contact préserve le brouillon")
	chat._choose_dialogue("Madame_TLS", "tls-premier-lien", "amitie")
	chat.acknowledge_choice(true)
	await settle()
	check(not chat._choice_panel.visible, "Un choix confirmé disparaît")
	chat.set_scene_choices([])
	await settle()
	check(not chat._choice_panel.visible, "Une actualisation sans choix ne recrée pas de question")
	chat.composer.clear()
	chat._free_input_requested = false
	chat.size = Vector2(600, 420)
	chat.set_scene_choices([{"id":"compact", "channel":"chordly", "peer":"Madame_TLS", "author":"Madame_TLS", "options":[{"id":"a","text":"Une réponse courte."},{"id":"b","text":"Une autre réponse."},{"id":"c","text":"Je préfère garder mes distances."}]}])
	await settle()
	check(not chat._composer_panel.visible and chat._scroll.size.y > 100, "En fenêtre compacte, la question et ses réponses ont priorité sur la saisie libre")
	await click(chat._choice_list.get_child(0).get_node("ToggleFreeInput"))
	await settle()
	check(chat._composer_panel.visible, "La saisie libre reste accessible pendant une question à choix")
	chat.queue_free()
	await settle()
	print("Choix de dialogue : %s contrôles, %s échec(s)" % [checks, failures])
	quit(1 if failures else 0)
