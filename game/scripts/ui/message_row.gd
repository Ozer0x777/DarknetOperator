extends Container
## Le contenu d’une bulle ne doit jamais imposer la largeur minimale de la fenêtre.
var outgoing: bool = false
var natural_width: float = 200

func _get_minimum_size() -> Vector2:
	if get_child_count() == 0: return Vector2.ZERO
	return Vector2(0, get_child(0).get_combined_minimum_size().y)

func _notification(what: int) -> void:
	if what != NOTIFICATION_SORT_CHILDREN or get_child_count() == 0: return
	var bubble: Control = get_child(0)
	var width: float = minf(natural_width, minf(560, size.x * 0.86))
	var height: float = maxf(size.y, bubble.get_combined_minimum_size().y)
	fit_child_in_rect(bubble, Rect2(Vector2(size.x - width if outgoing else 0, 0), Vector2(width, height)))

func _init() -> void:
	child_entered_tree.connect(func(child: Node) -> void:
		if child is Control:
			child.minimum_size_changed.connect(func() -> void: update_minimum_size(); queue_sort()))
