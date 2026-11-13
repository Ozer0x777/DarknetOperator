extends TextEdit
## Entrée envoie ; Maj+Entrée conserve une nouvelle ligne, y compris après collage.
signal submitted
var enter_sends: bool = true

func _gui_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode in [KEY_ENTER, KEY_KP_ENTER] and not event.shift_pressed:
			if enter_sends or event.ctrl_pressed or event.meta_pressed:
				accept_event()
				if editable: submitted.emit()
