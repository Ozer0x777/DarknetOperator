extends Node
## Service audio unique, compositions locales et préférences hors sauvegarde de carrière.
signal settings_changed
signal effect_requested(kind: String)
signal track_changed(kind: String)
var TRACKS: Dictionary = {"menu":"res://assets/audio/neon-dreams.ogg", "desktop":"res://assets/audio/afterhours-grid.ogg", "mission":"res://assets/audio/night-runner.ogg"}
var TITLES: Dictionary = {"menu":"Neon Dreams", "desktop":"Afterhours Grid", "mission":"Night Runner"}
var STYLES: Dictionary = {"menu":"Dreamwave / Retrowave", "desktop":"Chillwave / Vaporwave", "mission":"Synthwave / Cyberpunk"}
const CROSSFADE: float = 2.5
const ALBUM: String = "res://assets/audio/chapter-album/manifest.json"
var album_path: String = ALBUM
var album_available: bool = false
var _menu_track: String = "menu"
var _game_order: Array[String] = ["desktop", "mission", "menu"]
var _game_track: String = ""
var _game_position: float = 0
var _paused: bool = false
signal playback_changed
const EFFECTS: Array[String] = ["click", "open", "close", "notify", "chordly", "telegrid", "sessyon", "sent", "confirm", "error", "success", "failure"]
var settings_path: String = "user://audio.cfg"
var persist_in_tests: bool = false
var preferences: Dictionary = {"master": 0.75, "music": 0.26, "effects": 0.65, "muted": false, "selection": "auto"}
var context: String = "menu"
var current_track: String = ""
var _silent: bool = false
var _music: Array[AudioStreamPlayer] = []
var _effects: Array[AudioStreamPlayer] = []
var _streams: Dictionary = {}
var _current: int = 0
var _effect_cursor: int = 0
var _last_effect: Dictionary = {}
var _fade: Tween
var _save_timer: Timer
var _dirty: bool = false

func _ready() -> void:
	_silent = DisplayServer.get_name() == "headless" or "--offline-test" in OS.get_cmdline_user_args()
	_load_album()
	_load_settings()
	for bus_name: String in ["Music", "Effects"]:
		if AudioServer.get_bus_index(bus_name) < 0:
			AudioServer.add_bus()
			var index: int = AudioServer.bus_count - 1
			AudioServer.set_bus_name(index, bus_name)
			AudioServer.set_bus_send(index, "Master")
	var limited: bool = false
	for index: int in range(AudioServer.get_bus_effect_count(0)):
		if AudioServer.get_bus_effect(0, index) is AudioEffectLimiter: limited = true
	if not limited:
		var limiter: AudioEffectLimiter = AudioEffectLimiter.new()
		limiter.ceiling_db = -1.0
		AudioServer.add_bus_effect(0, limiter)
	for index: int in range(2):
		var player: AudioStreamPlayer = AudioStreamPlayer.new()
		player.bus = "Music"
		player.volume_db = -60
		add_child(player)
		_music.append(player)
		player.finished.connect(func() -> void: _music_finished(index))
	for index: int in range(6):
		var player: AudioStreamPlayer = AudioStreamPlayer.new()
		player.bus = "Effects"
		add_child(player)
		_effects.append(player)
	for kind: String in TRACKS:
		var stream: AudioStream = AudioStreamOggVorbis.load_from_file(TRACKS[kind]) if kind.begins_with("chapter_") else load(TRACKS[kind])
		if stream is AudioStreamOggVorbis: stream.loop = preferences.selection != "auto" or (context == "menu" and kind == _menu_track)
		_streams[kind] = stream
	for kind: String in EFFECTS: _streams["fx:" + kind] = load("res://assets/audio/" + kind + ".wav")
	_save_timer = Timer.new()
	_save_timer.one_shot = true
	_save_timer.wait_time = 0.35
	_save_timer.timeout.connect(_save_settings)
	add_child(_save_timer)
	_apply_volumes()
	get_tree().node_added.connect(_wire_button)
	set_context("menu")

func _wire_button(node: Node) -> void:
	if node is BaseButton and not node.has_meta("audio_wired"):
		node.set_meta("audio_wired", true)
		node.pressed.connect(func() -> void: play_effect("click"))

func _load_album() -> void:
	if not FileAccess.file_exists(album_path): return
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(album_path))
	if not data is Dictionary or not data.get("tracks") is Array: return
	var available: Array[Dictionary] = []
	for entry: Variant in data.tracks:
		if not entry is Dictionary: return
		var file: String = str(entry.get("file", ""))
		if file.get_file() != file or not file.ends_with(".ogg"): return
		var path: String = album_path.get_base_dir().path_join(file)
		# Un album incomplet ne remplace pas la bibliothèque disponible.
		if not FileAccess.file_exists(path): return
		available.append(entry)
	if available.size() != 12: return
	_game_order.clear()
	for entry: Dictionary in available:
		var key: String = str(entry.id)
		TRACKS[key] = album_path.get_base_dir().path_join(str(entry.file))
		TITLES[key] = str(entry.title)
		STYLES[key] = "Synthwave / Dreamwave"
		if entry.get("menu", false): _menu_track = key
		else: _game_order.append(key)
	album_available = true

func set_context(kind: String) -> void:
	if kind not in ["menu", "desktop", "mission"]: return
	var previous: String = context
	if kind == "menu" and previous != "menu" and preferences.selection == "auto" and current_track in _game_order:
		_game_track = current_track
		_game_position = playback_position()
	context = kind
	if preferences.selection != "auto":
		_play_track(str(preferences.selection))
	elif kind == "menu":
		_play_track(_menu_track)
	elif previous == "menu" or current_track.is_empty():
		_play_track(_game_track if not _game_track.is_empty() else _game_order[0], _game_position)
	elif not current_track.is_empty():
		_play_track(current_track)

func _adjacent_track(step: int) -> String:
	var index: int = _game_order.find(current_track)
	return _game_order[posmod(index + step, _game_order.size())]

func next_track() -> void:
	if context == "menu": return
	play_from_playlist(_adjacent_track(1))

func previous_track() -> void:
	if context == "menu": return
	if playback_position() > 3:
		seek(0)
	else:
		play_from_playlist(_adjacent_track(-1))

func play_from_playlist(kind: String) -> void:
	if kind not in _game_order: return
	preferences.selection = "auto"
	_play_track(kind)
	_changed()

func playback_position() -> float:
	return _music[_current].get_playback_position() if not _music.is_empty() else 0

func playback_length() -> float:
	return _streams[current_track].get_length() if _streams.has(current_track) else 0

func toggle_pause() -> void:
	_paused = not _paused
	for player: AudioStreamPlayer in _music: player.stream_paused = _paused
	playback_changed.emit()

func seek(position: float) -> void:
	if _music.is_empty() or _silent: return
	_music[_current].seek(clampf(position, 0, maxf(0, playback_length()-0.05)))

func _process(_delta: float) -> void:
	if _silent or _paused or context == "menu" or preferences.selection != "auto" or _music.is_empty(): return
	var player: AudioStreamPlayer = _music[_current]
	if player.playing and player.stream != null and playback_position() >= playback_length() - CROSSFADE:
		next_track()

func _music_finished(index: int) -> void:
	if index == _current and context != "menu" and preferences.selection == "auto": next_track()

func _play_track(selected: String, position: float = 0) -> void:
	if not TRACKS.has(selected): return
	var stream: AudioStream = _streams[selected]
	if stream is AudioStreamOggVorbis: stream.loop = preferences.selection != "auto" or context == "menu"
	if selected == current_track and (_silent or (not _music.is_empty() and _music[_current].playing)): return
	var changed: bool = selected != current_track
	current_track = selected
	if changed: track_changed.emit(selected)
	if _music.is_empty() or _silent: return
	if _fade != null and _fade.is_valid(): _fade.kill()
	var previous: AudioStreamPlayer = _music[_current]
	_current = 1 - _current
	var next: AudioStreamPlayer = _music[_current]
	next.stop()
	next.stream = stream
	next.volume_db = -60
	next.play(position)
	next.stream_paused = _paused
	_fade = create_tween().set_parallel(true)
	_fade.tween_property(previous, "volume_db", -60.0, CROSSFADE)
	_fade.tween_property(next, "volume_db", 0.0, CROSSFADE)
	_fade.chain().tween_callback(previous.stop)

func play_effect(kind: String) -> void:
	if not EFFECTS.has(kind) or preferences.muted or float(preferences.effects) <= 0 or float(preferences.master) <= 0: return
	var family: String = "notification" if kind in ["notify", "chordly", "telegrid", "sessyon"] else kind
	var now: int = Time.get_ticks_msec()
	var delay: int = 350 if family == "notification" else 65
	if now - int(_last_effect.get(family, -100000)) < delay: return
	_last_effect[family] = now
	effect_requested.emit(kind)
	if _silent or _effects.is_empty(): return
	var player: AudioStreamPlayer = _effects[_effect_cursor]
	_effect_cursor = (_effect_cursor + 1) % _effects.size()
	player.stream = _streams["fx:" + kind]
	player.play()

func set_volume(kind: String, value: float) -> void:
	if kind not in ["master", "music", "effects"]: return
	preferences[kind] = clampf(value, 0, 1)
	_changed()

func set_muted(value: bool) -> void:
	preferences.muted = value
	_changed()

func toggle_mute() -> void:
	set_muted(not preferences.muted)

func set_selection(kind: String) -> void:
	if kind != "auto" and not TRACKS.has(kind): return
	if preferences.selection == kind: return
	preferences.selection = kind
	set_context(context)
	_changed()

func _changed() -> void:
	_apply_volumes()
	settings_changed.emit()
	_dirty = true
	if is_instance_valid(_save_timer): _save_timer.start()

func _apply_volumes() -> void:
	for kind: String in ["master", "music", "effects"]:
		var index: int = AudioServer.get_bus_index({"master":"Master", "music":"Music", "effects":"Effects"}[kind])
		if index < 0: continue
		var value: float = float(preferences[kind])
		AudioServer.set_bus_volume_db(index, linear_to_db(maxf(value, 0.0001)))
		AudioServer.set_bus_mute(index, value <= 0 or (kind == "master" and preferences.muted))

func _can_persist() -> bool:
	return persist_in_tests or "--offline-test" not in OS.get_cmdline_user_args()

func _load_settings() -> void:
	if not _can_persist(): return
	var config: ConfigFile = ConfigFile.new()
	if config.load(settings_path) != OK: return
	for kind: String in ["master", "music", "effects"]:
		var value: Variant = config.get_value("audio", kind, preferences[kind])
		if value is float or value is int: preferences[kind] = clampf(float(value), 0, 1)
	preferences.muted = bool(config.get_value("audio", "muted", false))
	var selection: String = str(config.get_value("audio", "selection", "auto"))
	if selection == "auto" or TRACKS.has(selection): preferences.selection = selection

func _save_settings() -> void:
	if not _dirty or not _can_persist(): return
	var config: ConfigFile = ConfigFile.new()
	for key: String in preferences: config.set_value("audio", key, preferences[key])
	if config.save(settings_path) == OK: _dirty = false

func _exit_tree() -> void:
	_save_settings()
