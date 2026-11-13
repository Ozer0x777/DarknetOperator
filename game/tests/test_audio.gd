extends SceneTree
const AudioService = preload("res://scripts/audio_manager.gd")
const UI = preload("res://scripts/ui/style.gd")
var checks: int = 0
var failures: int = 0
func _initialize() -> void: call_deferred("run")
func check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(message)
func run() -> void:
	root.size = Vector2i(1280,720)
	root.gui_embed_subwindows = true
	await process_frame
	var service: Node = root.get_node("Audio")
	check(service != null and service._silent, "Service audio unique et silencieux pendant les tests hors ligne")
	var limiters: int = 0
	for index: int in range(AudioServer.get_bus_effect_count(0)):
		if AudioServer.get_bus_effect(0,index) is AudioEffectLimiter: limiters += 1
	check(limiters == 1, "Un limiteur unique protège le mixage général")
	check(service._music.size() == 2 and service._effects.size() == 6, "Deux lecteurs de fondu et six voix d’effets")
	for kind: String in service.TRACKS:
		var stream: AudioStream = service._streams[kind]
		check(stream is AudioStreamOggVorbis and stream.get_length() > 80, "Musique décodable : " + kind)
	for kind: String in service.EFFECTS:
		var stream: AudioStream = service._streams["fx:"+kind]
		check(stream != null and stream.get_length() > 0 and stream.get_length() < 1, "Effet court décodable : " + kind)
	service._silent = false
	service.set_context("desktop")
	check(service._music[service._current].playing, "Le lecteur démarre réellement avec le pilote muet de test")
	service.set_context("mission")
	await create_timer(2.75).timeout
	check(service._music[service._current].playing and not service._music[1-service._current].playing and is_equal_approx(service._music[service._current].volume_db, 0), "Le fondu garde une seule musique active à son terme")
	service.play_effect("confirm")
	check(service._effects[0].playing, "Un effet démarre sur une voix séparée de la musique")
	for player: AudioStreamPlayer in service._music: player.stop()
	for player: AudioStreamPlayer in service._effects: player.stop()
	service._silent = true
	var original: Dictionary = service.preferences.duplicate(true)
	service.set_volume("master", -1)
	check(service.preferences.master == 0 and AudioServer.is_bus_mute(0), "Volume général borné et silence à zéro")
	service.set_volume("master", 2)
	check(service.preferences.master == 1, "Volume maximal borné")
	service.set_volume("music", 0)
	check(AudioServer.is_bus_mute(AudioServer.get_bus_index("Music")) and not AudioServer.is_bus_mute(AudioServer.get_bus_index("Effects")), "Musique coupée sans couper les effets")
	service.set_volume("music", 0.2)
	service.set_muted(true)
	check(AudioServer.is_bus_mute(0), "Mode muet général")
	var heard: Array[String] = []
	service.effect_requested.connect(func(kind: String) -> void: heard.append(kind))
	service.play_effect("error")
	check(heard.is_empty(), "Aucun effet demandé lorsque le son est coupé")
	service.set_muted(false)
	service._last_effect.clear()
	service.play_effect("notify")
	service.play_effect("chordly")
	check(heard == ["notify"], "Une rafale de notifications ne superpose pas les alertes")
	service._last_effect.clear()
	heard.clear()
	var button: Button = UI.button("Test", func() -> void: pass)
	root.add_child(button)
	button.pressed.emit()
	check(heard == ["click"], "Les boutons reçoivent un retour sonore unique")
	button.queue_free()
	service.set_selection("auto")
	service.set_context("desktop")
	service._silent = false
	service.set_context("desktop")
	await create_timer(0.4).timeout
	var same: AudioStreamPlayer = service._music[service._current]
	var before: float = same.get_playback_position()
	var playing: String = service.current_track
	var changes: Array[String] = []
	service.track_changed.connect(func(kind: String) -> void: changes.append(kind))
	for phase: String in ["mission", "desktop", "mission", "desktop", "mission"]: service.set_context(phase)
	await create_timer(0.15).timeout
	check(service.current_track == playing and service._music[service._current] == same and same.get_playback_position() >= before, "Réussites, étapes et nouvelle mission conservent le lecteur et sa position")
	check(changes.is_empty(), "Aucun changement de morceau lors des changements de statut")
	service.toggle_pause()
	var paused_position: float = service.playback_position()
	await create_timer(0.2).timeout
	check(service._paused and absf(service.playback_position()-paused_position)<0.1, "Le lecteur suspend réellement la lecture")
	service.set_context("desktop")
	check(service._paused, "Une réussite ne réactive pas la musique mise en pause")
	service.toggle_pause()
	service.seek(service.playback_length()-0.5)
	await create_timer(0.25).timeout
	check(service.current_track != playing and changes.size()==1,"Le morceau suivant démarre automatiquement avant la fin")
	await create_timer(2.75).timeout
	check(not service._music[1-service._current].playing,"L’ancien lecteur s’arrête après le fondu de playlist")
	service.seek(12)
	var saved_track: String = service.current_track
	service.set_context("menu")
	service.set_context("desktop")
	check(service.current_track==saved_track and service.playback_position()>=11.5,"Le retour du menu reprend le morceau de jeu à sa position")
	service._silent = true
	for player: AudioStreamPlayer in service._music: player.stop()
	service.set_selection("desktop")
	service.set_context("menu")
	check(service.current_track == "desktop", "Le choix manuel garde son ambiance entre les scènes")
	service.set_selection("auto")
	check(service.current_track == service._menu_track, "Le menu retrouve son morceau dédié")
	var folder: String = "/tmp/darknet-audio-%s-%s" % [OS.get_process_id(), Time.get_ticks_usec()]
	DirAccess.make_dir_recursive_absolute(folder)
	var path: String = folder.path_join("audio.cfg")
	var first: Node = AudioService.new()
	first.settings_path = path
	first.persist_in_tests = true
	root.add_child(first)
	first.set_volume("master", 0.4)
	first.set_volume("music", 0.12)
	first.set_volume("effects", 0.8)
	first.set_muted(true)
	first.set_selection("mission")
	first._save_settings()
	first.queue_free()
	await process_frame
	var second: Node = AudioService.new()
	second.settings_path = path
	second.persist_in_tests = true
	root.add_child(second)
	check(is_equal_approx(float(second.preferences.music), 0.12) and second.preferences.muted and second.preferences.selection == "mission", "Préférences sonores restaurées après fermeture")
	second.queue_free()
	await process_frame
	DirAccess.remove_absolute(path)
	DirAccess.remove_absolute(folder)
	var album_folder: String = folder + "-album"
	DirAccess.make_dir_recursive_absolute(album_folder)
	var album: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(AudioService.ALBUM))
	for entry: Dictionary in album.tracks:
		DirAccess.copy_absolute(ProjectSettings.globalize_path("res://assets/audio/neon-dreams.ogg"),album_folder.path_join(entry.file))
	var manifest: FileAccess = FileAccess.open(album_folder.path_join("manifest.json"),FileAccess.WRITE)
	manifest.store_string(JSON.stringify(album))
	manifest.close()
	var album_service: Node = AudioService.new()
	album_service.album_path = album_folder.path_join("manifest.json")
	root.add_child(album_service)
	check(album_service.album_available and album_service._game_order.size()==11,"L’album complet charge onze morceaux de jeu")
	check(album_service.TITLES[album_service.current_track]=="Wake Sequence","Wake Sequence est réservé au menu")
	album_service.set_context("desktop")
	check(album_service.TITLES[album_service.current_track]=="Pulse Reconnected","La playlist de jeu commence par Pulse Reconnected")
	album_service.next_track()
	check(album_service.TITLES[album_service.current_track]=="Lost Frequency","La playlist saute Wake Sequence réservé au menu")
	var album_changes: Array[String] = []
	album_service.track_changed.connect(func(kind: String) -> void: album_changes.append(kind))
	album_service.set_context("mission")
	album_service.set_context("desktop")
	check(album_changes.is_empty(),"L’album téléchargé conserve lui aussi la continuité entre missions")
	album_service.queue_free()
	await process_frame
	for entry: Dictionary in album.tracks: DirAccess.remove_absolute(album_folder.path_join(entry.file))
	DirAccess.remove_absolute(album_folder.path_join("manifest.json"))
	DirAccess.remove_absolute(album_folder)
	service.preferences = original
	service._apply_volumes()
	var menu: Control = load("res://scenes/main_menu.tscn").instantiate()
	root.add_child(menu)
	await process_frame
	menu._settings()
	await process_frame
	var dialog: AcceptDialog = menu.get_child(menu.get_child_count()-1)
	var controls: Array[Node] = dialog.find_children("*", "HSlider", true, false)
	check(dialog.visible and controls.size() == 3 and dialog.size.y >= 350 and dialog.size.y <= 500, "Volumes accessibles depuis le menu dans une fenêtre compacte")
	var scroll: ScrollContainer = dialog.find_children("*", "ScrollContainer", true, false)[0]
	var visible_sliders: bool = true
	for slider: Control in controls:
		if not scroll.get_global_rect().grow(1).encloses(slider.get_global_rect()): visible_sliders = false
	check(visible_sliders, "Les trois curseurs sont visibles sans découpage dans le menu")
	dialog.queue_free()
	menu.queue_free()
	await process_frame
	print("Audio : %s contrôles, %s échec(s)" % [checks, failures])
	quit(1 if failures else 0)
