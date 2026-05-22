import re


REGEX_AS_PREFIX_FULL = re.compile(r'^%AS(?::([^%]*))?%(.+)$', re.IGNORECASE)
REGEX_BLENDER_SUFFIX = re.compile(r'\.\d{3}$')


def normalize_shapekey_name(name):
    result = name.split("$")[0]
    return REGEX_BLENDER_SUFFIX.sub("", result)


def parse_shapekey_name_for_base(name):
    if '@BASE:' in name:
        parts = name.split('@BASE:')
        if len(parts) == 2:
            return parts[0]
    return name


def get_modifier_prediction_target(modifier):
    if modifier.type == 'MESH_DEFORM':
        return modifier.object
    if modifier.type == 'SURFACE_DEFORM':
        return modifier.target
    return None


def get_as_modifier_display_name(modifier_name):
    match = REGEX_AS_PREFIX_FULL.match(modifier_name)
    if not match:
        return None
    return normalize_shapekey_name(match.group(2))


def is_all_mode_modifier(modifier):
    target_object = get_modifier_prediction_target(modifier)
    if not target_object or not getattr(modifier, "is_bound", False):
        return False

    target_data = target_object.data
    if (target_data.shape_keys
        and len(target_data.shape_keys.key_blocks) > 1
        and target_data.shape_keys.key_blocks[0].name.lower() == "all"):
        return True

    match = REGEX_AS_PREFIX_FULL.match(modifier.name)
    if not match or not match.group(1):
        return False
    tag_upper = match.group(1).upper()
    return tag_upper == "ALL" or tag_upper.startswith("ALL:")


def iter_predicted_shapekey_names(obj):
    for modifier in obj.modifiers:
        if not modifier.name.upper().startswith("%AS"):
            continue

        if is_all_mode_modifier(modifier):
            target_object = get_modifier_prediction_target(modifier)
            if not target_object or not target_object.data.shape_keys:
                continue
            for key_block in target_object.data.shape_keys.key_blocks[1:]:
                clean_name = parse_shapekey_name_for_base(key_block.name)
                if clean_name:
                    yield clean_name
            continue

        display_name = get_as_modifier_display_name(modifier.name)
        if display_name:
            yield display_name


def get_shapekey_candidates(obj):
    candidates = []
    seen = set()

    if obj.data.shape_keys:
        for key_block in obj.data.shape_keys.key_blocks:
            clean_name = parse_shapekey_name_for_base(key_block.name)
            if clean_name and clean_name not in seen:
                candidates.append(clean_name)
                seen.add(clean_name)

    for name in iter_predicted_shapekey_names(obj):
        if name not in seen:
            candidates.append(name)
            seen.add(name)

    return candidates
