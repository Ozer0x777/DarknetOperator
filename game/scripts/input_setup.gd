extends Node
## Le jeu se pilote au clavier et à la souris. Par défaut, Godot relie aussi les
## actions d'interface (ui_left, ui_accept…) aux manettes : une manette branchée,
## un stick qui dérive ou un bouton pressé déplaçait le focus hors du terminal ou
## « cliquait » un bouton du bureau. Ces liaisons sont retirées au démarrage.

func _enter_tree() -> void:
	for action: StringName in InputMap.get_actions():
		if not str(action).begins_with("ui_"): continue
		for event: InputEvent in InputMap.action_get_events(action):
			if event is InputEventJoypadButton or event is InputEventJoypadMotion:
				InputMap.action_erase_event(action, event)
