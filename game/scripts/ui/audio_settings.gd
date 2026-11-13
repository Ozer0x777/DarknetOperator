extends VBoxContainer
const UI = preload("res://scripts/ui/style.gd")
var _audio: Node
var _sliders: Dictionary = {}
var _values: Dictionary = {}
var _mute: CheckButton
var _selection: OptionButton
var _track: Label
var _keys: Array[String] = ["auto"]
var _next: Button

func _ready() -> void:
	_audio = get_node_or_null("/root/Audio")
	add_theme_constant_override("separation", 8)
	add_child(UI.label("Son et musique", 20))
	if _audio == null:
		add_child(UI.label("Service audio indisponible.", 12))
		return
	_mute = CheckButton.new()
	_mute.text = "Couper tous les sons"
	_mute.toggled.connect(_audio.set_muted)
	add_child(_mute)
	for entry: Array in [["master", "Volume général"], ["music", "Musique"], ["effects", "Effets sonores"]]:
		var kind: String = entry[0]
		var row: HBoxContainer = HBoxContainer.new()
		add_child(row)
		var caption: Label = UI.label(entry[1], 13)
		caption.custom_minimum_size.x = 120
		row.add_child(caption)
		var slider: HSlider = HSlider.new()
		slider.min_value = 0
		slider.max_value = 100
		slider.step = 1
		slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		slider.custom_minimum_size.x = 120
		slider.value_changed.connect(func(value: float) -> void: _audio.set_volume(kind, value / 100.0))
		row.add_child(slider)
		_sliders[kind] = slider
		var value: Label = UI.label("", 12)
		value.custom_minimum_size.x = 40
		row.add_child(value)
		_values[kind] = value
	_selection = OptionButton.new()
	_selection.add_item("Playlist continue")
	for kind: String in _audio.TRACKS:
		_keys.append(kind)
		_selection.add_item(str(_audio.TITLES[kind])+" · "+str(_audio.STYLES[kind]))
	_selection.item_selected.connect(func(index: int) -> void: _audio.set_selection(_keys[index]))
	add_child(_selection)
	_track = UI.wrapped("", 11, Color("a7b2c1"))
	add_child(_track)
	_next = UI.button("Morceau suivant", func() -> void: _audio.next_track())
	add_child(_next)
	add_child(UI.button("Écouter une notification", func() -> void: _audio.play_effect("notify")))
	_audio.settings_changed.connect(_sync)
	_audio.track_changed.connect(func(_kind: String) -> void: _sync())
	_sync()

func _sync() -> void:
	if _audio == null: return
	_mute.set_pressed_no_signal(_audio.preferences.muted)
	for kind: String in _sliders:
		var value: int = roundi(float(_audio.preferences[kind]) * 100)
		_sliders[kind].set_value_no_signal(value)
		_values[kind].text = "%s %%" % value
	_selection.select(_keys.find(_audio.preferences.selection))
	_track.text = "Lecture : " + str(_audio.TITLES.get(_audio.current_track, "en attente"))
	_next.disabled = _audio.context == "menu"
	_next.tooltip_text = "Passer au prochain morceau de la playlist" if not _next.disabled else "Le morceau du menu reste en boucle"
