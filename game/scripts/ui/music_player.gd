extends VBoxContainer
const UI = preload("res://scripts/ui/style.gd")
var audio: Node
var title: Label
var status: Label
var timeline: HSlider
var elapsed: Label
var playlist: ItemList
var pause: Button
var volume: HSlider
var _keys: Array[String] = []
var _dragging: bool = false

func _ready() -> void:
	audio = get_node("/root/Audio")
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 6)
	title = UI.wrapped("", 20, Color("8ac6f0"))
	add_child(title)
	status = UI.wrapped("", 12, Color("a7b2c1"))
	add_child(status)
	timeline = HSlider.new()
	timeline.step = 0.1
	timeline.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	timeline.drag_started.connect(func() -> void: _dragging = true)
	timeline.drag_ended.connect(func(changed: bool) -> void:
		if changed: audio.seek(timeline.value)
		_dragging = false)
	timeline.value_changed.connect(func(value: float) -> void:
		if not _dragging: audio.seek(value))
	add_child(timeline)
	elapsed = UI.label("", 12, Color("a7b2c1"))
	add_child(elapsed)
	var row: HBoxContainer = HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	add_child(row)
	row.add_child(UI.button("Précédent", audio.previous_track))
	pause = UI.button("Pause", audio.toggle_pause)
	row.add_child(pause)
	row.add_child(UI.button("Suivant", audio.next_track))
	var mix: HBoxContainer = HBoxContainer.new()
	mix.add_child(UI.label("Volume musique",12))
	volume = HSlider.new()
	volume.min_value = 0
	volume.max_value = 100
	volume.step = 1
	volume.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	volume.value_changed.connect(func(value: float) -> void: audio.set_volume("music", value / 100.0))
	mix.add_child(volume)
	add_child(mix)
	playlist = ItemList.new()
	playlist.size_flags_vertical = Control.SIZE_EXPAND_FILL
	playlist.custom_minimum_size.y = 84
	playlist.item_activated.connect(func(index: int) -> void: audio.play_from_playlist(_keys[index]))
	add_child(playlist)
	_keys.assign(audio._game_order)
	for key: String in _keys: playlist.add_item(str(audio.TITLES[key]))
	playlist.tooltip_text = "Double-clique pour écouter un morceau et poursuivre la playlist"
	var tip: Label = UI.wrapped("Wake Sequence au menu · les 11 autres morceaux s’enchaînent en jeu." if audio.album_available else "Album demandé en attente du fichier source. Les trois compositions originales restent disponibles.", 12, Color("a7b2c1"))
	add_child(tip)
	audio.track_changed.connect(func(_key: String) -> void: _sync())
	audio.playback_changed.connect(_sync)
	audio.settings_changed.connect(_sync)
	_sync()

func _sync() -> void:
	title.text = str(audio.TITLES.get(audio.current_track, "En attente"))
	status.text = ("En pause" if audio._paused else "Lecture continue") + " · " + str(audio.STYLES.get(audio.current_track, ""))
	pause.text = "Reprendre" if audio._paused else "Pause"
	volume.set_value_no_signal(float(audio.preferences.music)*100)
	var index: int = _keys.find(audio.current_track)
	playlist.deselect_all()
	if index >= 0: playlist.select(index)

func _process(_delta: float) -> void:
	if audio == null: return
	var duration: float = audio.playback_length()
	var position: float = audio.playback_position()
	if not _dragging:
		timeline.max_value = maxf(1, duration)
		timeline.set_value_no_signal(position)
	elapsed.text = _clock(position) + " / " + _clock(duration)

func _clock(seconds: float) -> String:
	var total: int = maxi(0, int(seconds))
	return "%02d:%02d" % [total / 60, total % 60]
