extends SceneTree
var checks: int = 0
var failures: int = 0
func _initialize() -> void: call_deferred("run")
func check(value: bool, caption: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(caption)
func settle() -> void:
	for index: int in range(12): await process_frame
func run() -> void:
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1280,720)
	var audio: Node = root.get_node("Audio")
	var original: Dictionary = audio.preferences.duplicate(true)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await settle()
	check(desktop.apps.has("Lecteur audio"),"Le lecteur est une application du bureau")
	desktop._open("Lecteur audio")
	var frame: Control = desktop.apps["Lecteur audio"]
	frame.size = Vector2(520,420)
	await settle()
	var player: Control = frame.find_children("*","ItemList",true,false)[0].get_parent()
	check(frame.size.y<=421 and frame.get_global_rect().grow(1).encloses(player.get_global_rect()),"Le lecteur tient dans une fenêtre compacte")
	check(player.playlist.item_count==audio._game_order.size(),"La playlist montre les morceaux disponibles")
	var first: String = audio.current_track
	audio.next_track()
	await settle()
	check(audio.current_track!=first and player.title.text==audio.TITLES[audio.current_track],"Suivant actualise le morceau et le titre")
	player.pause.pressed.emit()
	check(audio._paused and player.pause.text=="Reprendre","Le bouton Pause commande le service global")
	player.pause.pressed.emit()
	check(not audio._paused,"Le bouton Reprendre rétablit la lecture")
	player.volume.value = 37
	check(is_equal_approx(float(audio.preferences.music),0.37),"Le lecteur règle le volume musical séparément")
	player.playlist.item_activated.emit(0)
	check(audio.current_track==audio._game_order[0] and audio.preferences.selection=="auto","Choisir un morceau conserve l’enchaînement automatique")
	desktop._notify("Mission validée", "Chordly", false)
	audio.next_track()
	await settle()
	check((desktop.get("notification") as Label).text=="Mission validée" and not desktop._pending_music.is_empty(),"La notification musicale ne remplace pas une information de mission")
	desktop._toast.hide()
	await settle()
	check((desktop.get("notification") as Label).text.begins_with("♪ Lecture :") and desktop._toast.get_meta("open_app")=="Lecteur audio","La notification musicale affiche le titre et mène au lecteur")
	desktop._activate_notification()
	check(desktop.active_app=="Lecteur audio","Cliquer la notification ouvre le lecteur")
	var kept: String = audio.current_track
	frame.close_window()
	await settle()
	check(audio.current_track==kept,"Fermer le lecteur ne coupe pas le morceau")
	desktop.queue_free()
	await process_frame
	audio.preferences=original
	audio._apply_volumes()
	print("Lecteur et notifications audio : %s contrôles, %s échec(s)" % [checks,failures])
	quit(1 if failures else 0)
