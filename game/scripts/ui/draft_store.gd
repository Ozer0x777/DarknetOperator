extends RefCounted
## Brouillons locaux par pseudo et service ; les tests doivent fournir leur dossier.
var identity: String = ""
var scope: String = ""
var directory_override: String = ""
var values: Dictionary = {}
var _path: String = ""
var _recovered: bool = false

func configure(handle: String, service: String) -> void:
	identity = handle
	scope = service
	values = {}
	_path = ""
	_recovered = false
	if handle.is_empty(): return
	if "--offline-test" in OS.get_cmdline_user_args() and directory_override.is_empty(): return
	var directory: String = directory_override if not directory_override.is_empty() else "user://drafts"
	_path = ProjectSettings.globalize_path(directory).path_join((handle + "\n" + service).sha256_text() + ".json")
	for candidate: String in [_path, _path + ".previous"]:
		if not FileAccess.file_exists(candidate): continue
		var parser: JSON = JSON.new()
		if parser.parse(FileAccess.get_file_as_string(candidate)) != OK: continue
		var data: Variant = parser.data
		if not data is Dictionary or data.get("version") != 1 or not data.get("drafts") is Dictionary: continue
		_recovered = candidate != _path
		for key: Variant in data.drafts:
			if key is String and data.drafts[key] is String: values[key] = data.drafts[key]
		break

func save(drafts: Dictionary) -> Error:
	if drafts == values: return OK
	if _path.is_empty():
		values = drafts.duplicate(true)
		return OK
	var error: Error = DirAccess.make_dir_recursive_absolute(_path.get_base_dir())
	if error != OK: return error
	var file: FileAccess = FileAccess.open(_path + ".tmp", FileAccess.WRITE)
	if file == null: return FileAccess.get_open_error()
	file.store_string(JSON.stringify({"version": 1, "drafts": drafts}))
	file.flush()
	error = file.get_error()
	file.close()
	if error != OK: return error
	if FileAccess.file_exists(_path):
		if _recovered:
			error = DirAccess.remove_absolute(_path)
			if error != OK: return error
		else:
			if FileAccess.file_exists(_path + ".previous"):
				error = DirAccess.remove_absolute(_path + ".previous")
				if error != OK: return error
			error = DirAccess.rename_absolute(_path, _path + ".previous")
			if error != OK: return error
	error = DirAccess.rename_absolute(_path + ".tmp", _path)
	if error != OK:
		if FileAccess.file_exists(_path + ".previous"): DirAccess.rename_absolute(_path + ".previous", _path)
		return error
	_recovered = false
	values = drafts.duplicate(true)
	return OK
