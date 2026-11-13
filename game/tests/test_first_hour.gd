extends SceneTree
var checks: int = 0
var failures: int = 0
func _initialize() -> void: call_deferred("run")
func check(value: bool, text: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(text)
func settle() -> void:
	for index: int in range(12): await process_frame
func fits(outer: Control, inner: Control) -> bool:
	return outer.get_global_rect().grow(1).encloses(inner.get_global_rect())
func run() -> void:
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1280,720)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await settle()
	var notice: Label = desktop.get("notification")
	var chat: Control = desktop.messengers.chordly
	chat.hint_requested.disconnect(desktop._request_mission_hint)
	var requests: Array = []
	chat.hint_requested.connect(func(channel: String, peer: String) -> void: requests.append([channel,peer]))
	var context: Dictionary = {"contract_id":"intro_terminal","client":"k0rvid","title":"Prendre ses marques — un premier dossier", "goal":"Lire le document de préparation du dossier, sans exécuter son contenu. Une seule lecture correcte suffit pour terminer cette étape.","running":true}
	chat.set_mission_context(context)
	chat._select_peer("k0rvid")
	desktop._open("Chordly")
	var frame: Control = desktop.apps.Chordly
	frame.position = Vector2(60,60)
	frame.size = Vector2(600,420)
	chat.composer.text = "Mon brouillon\nDeuxième ligne"
	chat.composer.select(0,0,0,3)
	await settle()
	check(chat._mission_panel.visible, "Accès à la console, au but et à l’indice dans le bon dossier")
	var goal: Button
	var console: Button
	for button: Node in chat._mission_panel.find_children("*","Button",true,false):
		check(fits(frame,button), "Action du dossier visible à 600 × 420 : " + button.text)
		if button.text == "Objectif": goal=button
		if button.text == "Console": console=button
	goal.pressed.emit()
	await settle()
	check(frame.size.y<=421, "Le dossier ne force pas une fenêtre plus haute que 420 px")
	check(chat._mission_goal.visible and fits(frame,chat.composer), "L’objectif reste consultable sans masquer la rédaction")
	chat._request_hint()
	check(requests==[["chordly","k0rvid"]] and chat.composer.text=="Mon brouillon\nDeuxième ligne", "L’indice garde le brouillon et cible le client")
	chat.set_hint_busy(true);chat._request_hint()
	check(requests.size()==1 and chat._hint_button.disabled, "Une demande d’indice en cours ne se répète pas")
	chat.set_hint_busy(false)
	chat.set_mission_context(context)
	check(chat.composer.has_selection() and chat.composer.get_selected_text()=="Mon", "Actualiser l’objectif conserve la sélection du brouillon")
	console.pressed.emit()
	check(desktop.apps.Terminal.opened, "Le bouton Console ouvre le terminal du jeu")
	chat.set_mission_context({"contract_id":"intro_terminal","client":"k0rvid","title":"Premier dossier","goal":"Lire le document.","running":true})
	await settle()
	check(chat._mission_goal.custom_minimum_size.y < 42, "Un objectif court ne réserve pas un grand espace vide")
	for index: int in range(18): chat.add_message({"id":"scroll-"+str(index),"peer":"k0rvid","sender":"k0rvid","text":"Une observation datée à relire dans le dossier. ".repeat(3),"time":"09/11 09:00"},false)
	frame.size.y=600
	chat._scroll_bottom()
	await settle()
	frame.size.y=420
	await settle()
	check(chat._at_bottom(), "Réduire la fenêtre conserve les derniers messages à l’écran")
	chat._scroll.scroll_vertical=0
	await settle()
	frame.size.y=600
	await settle()
	check(chat._scroll.scroll_vertical==0, "Redimensionner respecte la lecture d’anciens messages")
	chat._select_peer("miette");chat._request_hint()
	check(not chat._mission_panel.visible and requests.size()==1, "Le dossier et ses actions ne débordent pas sur un autre contact")
	chat._select_peer("k0rvid")
	desktop._social_ready=false
	desktop._message_notifications.clear();desktop._notification_cooldown=0;desktop._toast.hide()
	desktop.active_app="Terminal"
	var world: Dictionary = {"messages":[{"id":"initial","channel":"chordly","peer":"k0rvid","sender":"k0rvid","text":"Archive","time":"09/11 09:00"}],"forum_messages":[{"id":"old-pm","author":"bytewarden","subject":"Ancienne proposition","body":"Dossier privé.","read":false}]}
	desktop._update_social(world)
	check(desktop._message_notifications.is_empty() and not desktop._toast.visible, "Le chargement des archives ne produit pas de rafale")
	world.messages.append({"id":"new-a","channel":"chordly","peer":"k0rvid","sender":"k0rvid","text":"Première nouvelle","time":"09/11 09:01"})
	world.messages.append({"id":"new-b","channel":"chordly","peer":"k0rvid","sender":"k0rvid","text":"Seconde nouvelle","time":"09/11 09:01"})
	desktop._update_social(world)
	check(desktop._message_notifications.Chordly.count==2, "Les messages sont regroupés par application")
	desktop._flush_message_notifications()
	check(notice.text=="2 nouveaux messages · Chordly" and desktop._notification_cooldown>0, "Une rafale donne une seule notification lisible")
	world.forum_messages.append({"id":"new-pm","author":"bytewarden","subject":"Nouvelle proposition","body":"Dossier privé.","read":false})
	desktop._update_social(world)
	desktop._flush_message_notifications()
	check(notice.text=="2 nouveaux messages · Chordly" and desktop._message_notifications.size()==1, "Une nouvelle alerte attend la fin de lecture de la précédente")
	chat._select_peer("miette")
	chat.add_message({"id":"unread-miette","peer":"miette","sender":"miette","text":"Message reçu en arrière-plan."},true)
	desktop._activate_notification()
	check(int(chat._unread_by_peer.get("miette",0))==1, "Le clic ne marque pas une autre conversation comme lue")
	check(desktop.active_app=="Chordly" and chat.selected_peer=="k0rvid", "Cliquer une notification rejoint la bonne conversation")
	check(chat.composer.text=="Mon brouillon\nDeuxième ligne", "Le raccourci de notification conserve le brouillon")
	desktop._notification_cooldown=0
	desktop._flush_message_notifications()
	desktop._activate_notification()
	check(desktop.forum_view.selected_section=="Messages", "Une notification de MP rejoint la boîte privée du forum")
	desktop._message_notifications.clear();desktop._notification_cooldown=0;desktop._toast.hide()
	desktop._open("Chordly")
	world.messages.append({"id":"new-c","channel":"chordly","peer":"k0rvid","sender":"k0rvid","text":"Déjà visible","time":"09/11 09:02"})
	desktop._update_social(world)
	check(desktop._message_notifications.is_empty(), "Une conversation déjà lue à l’écran ne déclenche pas de toast")
	desktop.queue_free()
	await process_frame
	print("Premiers pas et notifications : %s contrôles, %s échec(s)" % [checks,failures])
	quit(1 if failures else 0)
