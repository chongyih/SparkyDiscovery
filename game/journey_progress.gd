extends RefCounted
## Older saves have no activity timestamp; their modification time preserves a useful fallback.
static func read(path: String, maximum_checkpoint: int) -> Dictionary:
	var config := ConfigFile.new()
	if config.load(path) != OK:
		return {}
	var checkpoint: Variant = config.get_value("progress", "task", -1)
	if not checkpoint is int or checkpoint < 0 or checkpoint > maximum_checkpoint:
		return {}
	var last_played: Variant = config.get_value("progress", "last_played", FileAccess.get_modified_time(path))
	if not (last_played is float or last_played is int):
		last_played = FileAccess.get_modified_time(path)
	return {"checkpoint": checkpoint, "last_played": float(last_played)}

static func latest(independence_path: String, wartime_path: String) -> String:
	var independence := read(independence_path, 3)
	var wartime := read(wartime_path, 4)
	if independence.is_empty():
		return "" if wartime.is_empty() else "1942"
	if wartime.is_empty():
		return "1965"
	return "1942" if wartime.last_played > independence.last_played else "1965"

static func finished(independence_path: String, wartime_path: String) -> bool:
	# A newer 1942 save means the player has already begun another journey.
	if latest(independence_path, wartime_path) != "1965":
		return false
	return read(independence_path, 3).checkpoint == 3
