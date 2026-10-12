# /// script
# requires-python = ">=3.12"
#
# [tool.orcaslicer.plugin]
# name = "Helix Calibration Context"
# description = "Shows active Orca context and qualifies a read-only Helix companion panel."
# author = "Helix-Orca Calibration contributors"
# version = "0.3.0"
# type = "script"
# ///
"""Read-only OrcaSlicer context inspector and nightly qualification probe.

The only filesystem operation is an explicit export into this plugin's
host-provided storage directory. There is no networking, slicing, G-code
execution, preset/project mutation, or external profile-file access.
"""

import datetime
import html
import json
import math
import pathlib
import re

import orca


PLUGIN_NAME = "Helix Calibration"
EXPORT_ACTION_NAME = "Export Orca Context JSON"
QUALIFICATION_ACTION_NAME = "Helix Calibration Nightly Qualification"
EXPORTER_VERSION = "0.3.0"
TARGET_BUILD = {
    "platform": "Windows x64",
    "version": "OrcaSlicer 2.5.0-dev",
    "build": "210bc927",
    "source_commit": "210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3",
    "workflow_run": 38106132250,
    "artifact_id": 11690627983,
    "artifact_name": "OrcaSlicer_Windows_V2.5.0-dev_x64_portable",
    "artifact_digest": "sha256:080b00bc001256fd521a663e2939004d09a14f9bdef08c351167580e0d505d13",
    "orca_slicer_exe_sha256": "8d9db0bec8b8a8e0ad0a70485daaf7ee9fa1c88d5f1395f92eabf0430ce0339b",
    "orca_slicer_dll_sha256": "5b71e5dbf2f6b3319d6d69f597e3aa3dbf9403f9ea63f93c3c72dc294efba0a4",
    "metadata_source": "verified upstream scheduled run, artifact API digest, and downloaded payload hashes",
}

READ_SUCCEEDED = "runtime_read_succeeded"
DATA_ABSENT = "api_exists_but_data_absent_in_this_context"
AWAITING_RUNTIME = "source_verified_capability_awaiting_runtime_verification"
DIFFERENT_PHASE = "capability_requires_a_different_execution_phase"
NO_ACCESSOR = "no_supported_accessor_found_in_inspected_binding_surface"
READ_FAILED = "read_failed"
REDACTED = "intentionally_omitted_or_redacted"
READ_STATUSES = (
    READ_SUCCEEDED,
    DATA_ABSENT,
    AWAITING_RUNTIME,
    DIFFERENT_PHASE,
    NO_ACCESSOR,
    READ_FAILED,
    REDACTED,
)

EXPLICIT_GCODE_FIELDS = (
    "machine_start_gcode",
    "machine_end_gcode",
    "filament_start_gcode",
    "filament_end_gcode",
    "before_layer_change_gcode",
    "layer_change_gcode",
    "change_filament_gcode",
)

# These names are filtered after key enumeration, so coverage remains visible.
# The list is intentionally conservative and only covers known secrets and
# path-bearing values in Orca's configuration surface.
SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "api_key",
    "apikey",
    "token",
    "secret",
    "access_token",
    "auth_token",
    "refresh_token",
    "credential",
    "client_secret",
    "printhost_user",
)
PERSONAL_PATH_KEYS = {
    "bed_custom_model",
    "bed_custom_texture",
    "post_process",
    "printhost_cafile",
}


def _call(obj, *names):
    """Call the first supported zero-argument method from ``names``."""
    for name in names:
        candidate = getattr(obj, name, None)
        if callable(candidate):
            return candidate()
    raise AttributeError(f"None of these methods are available: {', '.join(names)}")


def _bool_attr(obj, name):
    value = getattr(obj, name, None)
    if callable(value):
        value = value()
    return value if isinstance(value, bool) else None


def _source_classification(preset):
    """Return a user-facing source without inventing missing provenance."""
    if preset is None:
        return {"label": "Unavailable", "reason": "Preset was not resolved by Orca."}

    checks = (
        ("is_project_embedded", "Project embedded"),
        ("is_external", "External"),
        ("is_default", "Default"),
        ("is_system", "System"),
        ("is_from_bundle", "Bundled"),
        ("is_user", "User"),
    )
    supported = False
    for attr, label in checks:
        value = _bool_attr(preset, attr)
        if value is not None:
            supported = True
        if value:
            return {"label": label, "reason": None}
    if supported:
        return {"label": "Unclassified", "reason": "Orca exposed no matching source flag."}
    return {"label": "Unavailable", "reason": "This Orca build exposes no preset source flags."}


def _preset_view(preset):
    if preset is None:
        return {
            "name": "Unavailable",
            "source": _source_classification(None),
            "dirty": None,
            "reason": "Preset was not resolved by Orca.",
        }
    name = getattr(preset, "name", None) or "Unavailable"
    dirty = _bool_attr(preset, "is_dirty")
    return {
        "name": str(name),
        "source": _source_classification(preset),
        "dirty": dirty,
        "reason": None if name != "Unavailable" else "Preset name is unavailable.",
    }


def _profile_context(collection):
    """Keep saved selection and Orca's edited copy visibly separate."""
    try:
        selected = _call(collection, "selected_preset", "get_selected_preset")
        selected_view = _preset_view(selected)
    except Exception as exc:
        selected_view = _preset_view(None)
        selected_view["reason"] = f"Saved selection unavailable: {exc}"

    try:
        edited = _call(collection, "edited_preset", "get_edited_preset")
        edited_view = _preset_view(edited)
    except Exception as exc:
        edited_view = _preset_view(None)
        edited_view["reason"] = f"Edited preset unavailable: {exc}"

    return {
        "selected": selected_view,
        "edited": edited_view,
        "same_name": (
            selected_view["name"] != "Unavailable"
            and selected_view["name"] == edited_view["name"]
        ),
    }


def _parse_number_vector(serialized, setting_name):
    if serialized is None:
        return [], f"{setting_name} is absent from Orca's current effective configuration."
    text = str(serialized).strip()
    if not text:
        return [], f"{setting_name} is empty in Orca's current effective configuration."

    values = []
    for index, token in enumerate(text.split(";")):
        token = token.strip()
        try:
            value = float(token)
        except (TypeError, ValueError):
            return [], f"{setting_name} contains an unsupported value at index {index}: {token!r}."
        if not math.isfinite(value):
            return [], f"{setting_name} contains a non-finite value at index {index}."
        values.append(value)
    return values, None


def _setting_value(values, index, error, setting_name, unit, integer=False):
    if error:
        return {"available": False, "display": "Unavailable", "reason": error}
    if index >= len(values):
        return {
            "available": False,
            "display": "Unavailable",
            "reason": f"{setting_name} has {len(values)} value(s), but index {index} was requested.",
        }
    value = values[index]
    if integer:
        if not value.is_integer():
            return {
                "available": False,
                "display": "Unavailable",
                "reason": f"{setting_name} at index {index} is not a whole-number temperature.",
            }
        normalized = int(value)
    else:
        normalized = value
    return {
        "available": True,
        "value": normalized,
        "display": f"{normalized:g} {unit}" if not integer else f"{normalized} {unit}",
        "reason": None,
    }


def _safe_full_config_value(bundle, key):
    try:
        return bundle.full_config_value(key), None
    except Exception as exc:
        return None, f"Orca could not read {key}: {exc}"


def _technology(bundle):
    value, error = _safe_full_config_value(bundle, "printer_technology")
    if error:
        return {"value": None, "display": "Unavailable", "reason": error}
    if value is None or not str(value).strip():
        return {
            "value": None,
            "display": "Unavailable",
            "reason": "printer_technology is absent from Orca's current effective configuration.",
        }
    text = str(value).strip()
    return {"value": text, "display": text, "reason": None}


def build_context(host):
    """Build a JSON-compatible snapshot without allowing one missing field to crash it."""
    try:
        bundle = host.preset_bundle()
    except Exception as exc:
        return {
            "status": "error",
            "message": f"The Orca preset host API is unavailable: {exc}",
            "warnings": [],
        }

    warnings = []
    profiles = {}
    for key, attr in (("printer", "printers"), ("process", "prints")):
        collection = getattr(bundle, attr, None)
        if collection is None:
            profiles[key] = None
            warnings.append(f"Orca did not expose the {key} preset collection.")
        else:
            profiles[key] = _profile_context(collection)

    technology = _technology(bundle)
    technology_key = (technology["value"] or "").upper()
    status = "unsupported" if technology_key and technology_key not in {"FFF", "FDM"} else "ok"
    message = None
    if status == "unsupported":
        message = f"Printer technology {technology['display']} is not supported by this FFF-only milestone."
    elif technology["value"] is None:
        warnings.append(technology["reason"])

    nozzle_raw, nozzle_read_error = _safe_full_config_value(bundle, "nozzle_diameter")
    temp_raw, temp_read_error = _safe_full_config_value(bundle, "nozzle_temperature")
    nozzle_values, nozzle_parse_error = _parse_number_vector(nozzle_raw, "nozzle_diameter")
    temp_values, temp_parse_error = _parse_number_vector(temp_raw, "nozzle_temperature")
    nozzle_error = nozzle_read_error or nozzle_parse_error
    temp_error = temp_read_error or temp_parse_error

    extruder_count = len(nozzle_values) if not nozzle_error else 1
    extruders = [
        {
            "index": index,
            "nozzle_diameter": _setting_value(
                nozzle_values, index, nozzle_error, "nozzle_diameter", "mm"
            ),
        }
        for index in range(max(1, extruder_count))
    ]

    try:
        selected_filament_names = list(bundle.current_filament_preset_names())
    except Exception as exc:
        selected_filament_names = []
        warnings.append(f"Selected filament names are unavailable: {exc}")
    try:
        current_filament_presets = list(bundle.current_filament_presets())
    except Exception as exc:
        current_filament_presets = []
        warnings.append(f"Current filament presets are unavailable: {exc}")

    filament_count = max(len(selected_filament_names), len(current_filament_presets), 1)
    if not selected_filament_names:
        warnings.append("Orca returned no selected filament profile names.")
    filaments = []
    for index in range(filament_count):
        selected_name = (
            str(selected_filament_names[index])
            if index < len(selected_filament_names) and selected_filament_names[index]
            else "Unavailable"
        )
        preset = current_filament_presets[index] if index < len(current_filament_presets) else None
        current_view = _preset_view(preset)
        filaments.append(
            {
                "index": index,
                "selected_name": selected_name,
                "current": current_view,
                "normal_nozzle_temperature": _setting_value(
                    temp_values,
                    index,
                    temp_error,
                    "nozzle_temperature",
                    "°C",
                    integer=True,
                ),
            }
        )

    if selected_filament_names and len(current_filament_presets) != len(selected_filament_names):
        warnings.append(
            "Orca returned different counts for selected filament names and resolved filament presets; "
            "unmatched entries are shown as unavailable."
        )
    if not temp_error and len(temp_values) != len(selected_filament_names):
        warnings.append(
            f"Orca returned {len(temp_values)} effective nozzle temperature value(s) for "
            f"{len(selected_filament_names)} selected filament slot(s)."
        )

    return {
        "status": status,
        "message": message,
        "technology": technology,
        "profiles": profiles,
        "extruders": extruders,
        "filaments": filaments,
        "warnings": warnings,
        "provenance": {
            "profile_identity": "Saved selections come from PresetCollection.selected_preset().",
            "edited_identity": "Current edited copies come from PresetCollection.edited_preset().",
            "settings": (
                "Nozzle values come from PresetBundle.full_config_value(), Orca's current effective "
                "merged configuration. They may include unsaved edits and are not claimed to be saved."
            ),
        },
    }


def _error_reason(exc):
    message = str(exc)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def _is_json_value(value):
    """The pinned config bindings return only str or None; reject surprises."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


def _is_sensitive_key(key):
    lowered = key.casefold()
    if lowered in PERSONAL_PATH_KEYS:
        return True, "Known path-bearing setting omitted to avoid exporting personal filesystem paths."
    if any(part in lowered for part in SENSITIVE_KEY_PARTS):
        return True, "Known credential or token setting redacted."
    return False, None


def _empty_counts():
    return {status: 0 for status in READ_STATUSES}


def _unavailable_config_source(namespace, association, status, reason):
    counts = _empty_counts()
    counts[status] = 1
    return {
        "namespace": namespace,
        "association": association,
        "source_read_status": status,
        "key_enumeration": {"read_status": status, "reason": reason},
        "enumerable_key_count": None,
        "read_outcome_counts": counts,
        "entries": [],
    }


def _capture_config_source(namespace, association, obj, keys_method="config_keys", value_method="config_value"):
    """Capture one supported ConfigBase binding without interpreting values."""
    if obj is None:
        return _unavailable_config_source(
            namespace,
            association,
            DATA_ABSENT,
            "The associated Orca object is absent in the current context.",
        )

    try:
        keys = list(getattr(obj, keys_method)())
    except Exception as exc:
        return _unavailable_config_source(
            namespace,
            association,
            READ_FAILED,
            f"Key enumeration failed: {_error_reason(exc)}",
        )

    entries = []
    counts = _empty_counts()
    for key in keys:
        if not isinstance(key, str):
            entries.append(
                {
                    "key": None,
                    "read_status": READ_FAILED,
                    "raw_value": None,
                    "reason": f"Orca returned a non-string configuration key of type {type(key).__name__}.",
                }
            )
            counts[READ_FAILED] += 1
            continue

        redact, reason = _is_sensitive_key(key)
        if redact:
            entries.append(
                {
                    "key": key,
                    "read_status": REDACTED,
                    "raw_value": None,
                    "reason": reason,
                }
            )
            counts[REDACTED] += 1
            continue

        try:
            value = getattr(obj, value_method)(key)
            if not _is_json_value(value):
                raise TypeError(
                    f"unsupported non-JSON value type {type(value).__name__}; raw value was not coerced"
                )
            status = READ_SUCCEEDED if value is not None else DATA_ABSENT
            entry = {"key": key, "read_status": status, "raw_value": value}
            if value is None:
                entry["reason"] = "The accessor returned null for this enumerated key."
            entries.append(entry)
            counts[status] += 1
        except Exception as exc:
            entries.append(
                {
                    "key": key,
                    "read_status": READ_FAILED,
                    "raw_value": None,
                    "reason": _error_reason(exc),
                }
            )
            counts[READ_FAILED] += 1

    return {
        "namespace": namespace,
        "association": association,
        "source_read_status": READ_SUCCEEDED,
        "key_enumeration": {"read_status": READ_SUCCEEDED, "reason": None},
        "enumerable_key_count": len(keys),
        "read_outcome_counts": counts,
        "entries": entries,
    }


def _read_known_field(obj, name, *, call=False):
    try:
        value = getattr(obj, name)
        if call:
            value = value()
        if not _is_json_value(value):
            raise TypeError(f"unsupported non-JSON value type {type(value).__name__}")
        return {"read_status": READ_SUCCEEDED, "raw_value": value}
    except Exception as exc:
        return {"read_status": READ_FAILED, "raw_value": None, "reason": _error_reason(exc)}


def _preset_metadata(preset):
    if preset is None:
        return {
            "read_status": DATA_ABSENT,
            "reason": "Preset was not resolved by Orca.",
            "fields": {},
            "omitted_fields": [
                {"field": "file", "read_status": REDACTED, "reason": "Preset filesystem paths are not exported."}
            ],
        }
    fields = {}
    for name in (
        "name",
        "alias",
        "bundle_id",
        "is_default",
        "is_external",
        "is_system",
        "is_visible",
        "is_dirty",
        "is_compatible",
        "is_project_embedded",
    ):
        fields[name] = _read_known_field(preset, name)
    fields["is_user"] = _read_known_field(preset, "is_user", call=True)
    fields["is_from_bundle"] = _read_known_field(preset, "is_from_bundle", call=True)
    return {
        "read_status": READ_SUCCEEDED,
        "fields": fields,
        "omitted_fields": [
            {"field": "file", "read_status": REDACTED, "reason": "Preset filesystem paths are not exported."}
        ],
    }


def _capture_collection_pair(sources, collection, namespace_prefix, association_prefix):
    result = {}
    for label, methods in (
        ("selected_saved", ("selected_preset", "get_selected_preset")),
        ("current_edited", ("edited_preset", "get_edited_preset")),
    ):
        association = f"{association_prefix}; {label.replace('_', ' ')}"
        try:
            preset = _call(collection, *methods)
            metadata = _preset_metadata(preset)
            source = _capture_config_source(f"{namespace_prefix}.{label}", association, preset)
        except Exception as exc:
            preset = None
            reason = _error_reason(exc)
            metadata = {"read_status": READ_FAILED, "reason": reason, "fields": {}, "omitted_fields": []}
            source = _unavailable_config_source(
                f"{namespace_prefix}.{label}", association, READ_FAILED, reason
            )
        sources.append(source)
        result[label] = {"preset": preset, "metadata": metadata, "config_source": source["namespace"]}
    return result


def _field_raw(metadata, name):
    field = (metadata or {}).get("fields", {}).get(name, {})
    return field.get("raw_value") if field.get("read_status") == READ_SUCCEEDED else None


def _capture_filaments(bundle, sources):
    collection = getattr(bundle, "filaments", None)
    if collection is None:
        editor = {
            "read_status": DATA_ABSENT,
            "reason": "PresetBundle.filaments is absent in this runtime context.",
        }
        edited_name = None
    else:
        pair = _capture_collection_pair(
            sources,
            collection,
            "filament_editor",
            "The single filament PresetCollection editor state exposed by Orca",
        )
        editor = {
            "read_status": READ_SUCCEEDED,
            "selected_saved": pair["selected_saved"]["metadata"],
            "current_edited": pair["current_edited"]["metadata"],
            "semantics": (
                "This is one collection-level editor state, not evidence that every filament slot has "
                "an independently edited preset object."
            ),
        }
        edited_name = _field_raw(pair["current_edited"]["metadata"], "name")

    try:
        names = list(bundle.current_filament_preset_names())
        names_status = READ_SUCCEEDED if names else DATA_ABSENT
        names_error = None
    except Exception as exc:
        names = []
        names_status = READ_FAILED
        names_error = _error_reason(exc)
    try:
        resolved = list(bundle.current_filament_presets())
        resolved_status = READ_SUCCEEDED if resolved else DATA_ABSENT
        resolved_error = None
    except Exception as exc:
        resolved = []
        resolved_status = READ_FAILED
        resolved_error = _error_reason(exc)

    matching_edited_slots = [index for index, name in enumerate(names) if name == edited_name]
    slots = []
    for index in range(max(len(names), len(resolved))):
        name = names[index] if index < len(names) else None
        preset = resolved[index] if index < len(resolved) else None
        association = {
            "slot_index_zero_based": index,
            "selected_name": name,
            "pairing_basis": (
                "Positional pairing of PresetBundle.current_filament_preset_names() and "
                "PresetBundle.current_filament_presets()."
            ),
        }
        if edited_name is None or name != edited_name:
            association["collection_edited_mapping"] = "not_established_for_this_slot"
        elif len(matching_edited_slots) == 1:
            association["collection_edited_mapping"] = "unique_name_match"
        else:
            association["collection_edited_mapping"] = "ambiguous_same_preset_selected_in_multiple_slots"

        source = _capture_config_source(
            f"filament_slots[{index}].resolved_current_preset",
            association,
            preset,
        )
        sources.append(source)
        slots.append(
            {
                "slot_index_zero_based": index,
                "selected_name": {"read_status": READ_SUCCEEDED if name is not None else DATA_ABSENT, "raw_value": name},
                "resolved_current_preset": _preset_metadata(preset),
                "config_source": source["namespace"],
                "association": association,
                "semantics": (
                    "The pinned binding resolves this name through PresetCollection.find_preset(). "
                    "For the collection's active preset this can be Orca's edited temporary copy; "
                    "it is not labeled as a raw saved leaf profile."
                ),
            }
        )

    return {
        "editor_state": editor,
        "slot_name_read": {"read_status": names_status, "reason": names_error, "count": len(names)},
        "resolved_preset_read": {
            "read_status": resolved_status,
            "reason": resolved_error,
            "count": len(resolved),
        },
        "count_mismatch": len(names) != len(resolved),
        "slots": slots,
    }


def _capture_model(host, sources):
    try:
        model = host.model()
    except Exception as exc:
        return {"read_status": READ_FAILED, "reason": _error_reason(exc), "objects": []}

    model_fields = {}
    for name, call in (
        ("id", True),
        ("object_count", True),
        ("material_count", True),
        ("current_plate_index", True),
        ("is_fdm_support_painted", True),
        ("is_seam_painted", True),
        ("is_mm_painted", True),
        ("is_fuzzy_skin_painted", True),
        ("designer", True),
        ("design_id", True),
    ):
        model_fields[name] = _read_known_field(model, name, call=call)

    try:
        objects = list(model.objects())
        objects_status = READ_SUCCEEDED
        objects_error = None
    except Exception as exc:
        objects = []
        objects_status = READ_FAILED
        objects_error = _error_reason(exc)

    object_records = []
    for object_index, obj in enumerate(objects):
        object_fields = {}
        for name, call in (
            ("id", True),
            ("name", False),
            ("module_name", False),
            ("printable", False),
            ("instance_count", True),
            ("volume_count", True),
            ("has_custom_layering", True),
            ("is_fdm_support_painted", True),
            ("is_seam_painted", True),
            ("is_mm_painted", True),
            ("is_fuzzy_skin_painted", True),
        ):
            object_fields[name] = _read_known_field(obj, name, call=call)

        object_source = _capture_config_source(
            f"model.objects[{object_index}].config",
            {"object_index_zero_based": object_index, "object_id": object_fields["id"].get("raw_value")},
            obj,
        )
        sources.append(object_source)

        try:
            instances = list(obj.instances())
            instance_records = [
                {
                    "index_zero_based": index,
                    "id": _read_known_field(instance, "id", call=True),
                    "printable": _read_known_field(instance, "printable"),
                    "effective_is_printable": {
                        "read_status": DIFFERENT_PHASE,
                        "raw_value": None,
                        "reason": "The source documents ModelInstance.is_printable() as set during slicing.",
                    },
                }
                for index, instance in enumerate(instances)
            ]
            instances_status = READ_SUCCEEDED
            instances_error = None
        except Exception as exc:
            instance_records = []
            instances_status = READ_FAILED
            instances_error = _error_reason(exc)

        try:
            volumes = list(obj.volumes())
            volumes_status = READ_SUCCEEDED
            volumes_error = None
        except Exception as exc:
            volumes = []
            volumes_status = READ_FAILED
            volumes_error = _error_reason(exc)

        volume_records = []
        for volume_index, volume in enumerate(volumes):
            volume_fields = {}
            for name, call in (
                ("id", True),
                ("name", False),
                ("extruder_id", True),
                ("is_model_part", True),
                ("is_modifier", True),
                ("is_negative_volume", True),
                ("is_support_enforcer", True),
                ("is_support_blocker", True),
            ):
                volume_fields[name] = _read_known_field(volume, name, call=call)
            volume_source = _capture_config_source(
                f"model.objects[{object_index}].volumes[{volume_index}].config",
                {
                    "object_index_zero_based": object_index,
                    "volume_index_zero_based": volume_index,
                    "volume_id": volume_fields["id"].get("raw_value"),
                    "extruder_id_one_based": volume_fields["extruder_id"].get("raw_value"),
                },
                volume,
            )
            sources.append(volume_source)
            volume_records.append(
                {
                    "index_zero_based": volume_index,
                    "fields": volume_fields,
                    "config_source": volume_source["namespace"],
                    "mesh_data": {
                        "read_status": REDACTED,
                        "reason": "Mesh arrays are intentionally outside this diagnostic snapshot.",
                    },
                }
            )

        object_records.append(
            {
                "index_zero_based": object_index,
                "fields": object_fields,
                "omitted_fields": [
                    {
                        "field": "input_file",
                        "read_status": REDACTED,
                        "reason": "Source model filesystem paths are not exported.",
                    }
                ],
                "config_source": object_source["namespace"],
                "instances": {
                    "read_status": instances_status,
                    "reason": instances_error,
                    "items": instance_records,
                },
                "volumes": {
                    "read_status": volumes_status,
                    "reason": volumes_error,
                    "items": volume_records,
                },
            }
        )

    return {
        "read_status": READ_SUCCEEDED,
        "fields": model_fields,
        "objects_read": {"read_status": objects_status, "reason": objects_error, "count": len(objects)},
        "objects": object_records,
    }


def _capture_application_context(host):
    result = {}
    try:
        result["app_info"] = {
            "read_status": READ_SUCCEEDED,
            "raw_value": dict(host.app_info()),
        }
    except Exception as exc:
        result["app_info"] = {
            "read_status": READ_FAILED,
            "raw_value": None,
            "reason": _error_reason(exc),
        }
    try:
        plater = host.plater()
        result["plater"] = {
            "read_status": READ_SUCCEEDED,
            "is_project_dirty": _read_known_field(plater, "is_project_dirty", call=True),
            "is_presets_dirty": _read_known_field(plater, "is_presets_dirty", call=True),
            "inside_snapshot_capture": _read_known_field(plater, "inside_snapshot_capture", call=True),
        }
    except Exception as exc:
        result["plater"] = {"read_status": READ_FAILED, "reason": _error_reason(exc)}
    try:
        result["app_language"] = {"read_status": READ_SUCCEEDED, "raw_value": host.app_language()}
    except Exception as exc:
        result["app_language"] = {
            "read_status": READ_FAILED,
            "raw_value": None,
            "reason": _error_reason(exc),
        }
    return result


def _source_summaries(sources):
    return [
        {
            "namespace": source["namespace"],
            "source_read_status": source["source_read_status"],
            "enumerable_key_count": source["enumerable_key_count"],
            "read_outcome_counts": source["read_outcome_counts"],
        }
        for source in sources
    ]


def _gcode_template_report(sources):
    occurrences = {}
    for source_index, source in enumerate(sources):
        for entry_index, entry in enumerate(source["entries"]):
            key = entry.get("key")
            if not key:
                continue
            lowered = key.casefold()
            if key in EXPLICIT_GCODE_FIELDS or "gcode" in lowered or "template" in lowered:
                occurrences.setdefault(key, []).append(
                    {
                        "source_namespace": source["namespace"],
                        "association": source["association"],
                        "read_status": entry["read_status"],
                        "raw_value_location": (
                            f"configuration_sources[{source_index}].entries[{entry_index}].raw_value"
                        ),
                    }
                )

    explicit = {}
    for key in EXPLICIT_GCODE_FIELDS:
        found = occurrences.get(key, [])
        if found:
            statuses = sorted({item["read_status"] for item in found})
            explicit[key] = {"exposure": statuses, "occurrences": found}
        else:
            enumeration_failures = [
                source["namespace"]
                for source in sources
                if source["key_enumeration"]["read_status"] == READ_FAILED
            ]
            if enumeration_failures:
                exposure = [READ_FAILED]
                reason = (
                    "No occurrence was found, but key enumeration failed for: "
                    + ", ".join(enumeration_failures)
                )
            else:
                exposure = [DATA_ABSENT]
                reason = "Not present in the successfully enumerated sources in this runtime snapshot."
            explicit[key] = {
                "exposure": exposure,
                "occurrences": [],
                "reason": reason,
            }

    interpretations = []
    for source in sources:
        for entry in source["entries"]:
            key = entry.get("key")
            value = entry.get("raw_value")
            if key not in occurrences or entry.get("read_status") != READ_SUCCEEDED or not isinstance(value, str):
                continue
            markers = re.findall(r"\{[^{}\r\n]+\}|\[[^\[\]\r\n]+\]", value)
            command_tokens = []
            for line in value.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith(";"):
                    continue
                token = stripped.split(None, 1)[0]
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token) and not re.fullmatch(
                    r"[GMTgmt]\d+(?:\.\d+)?", token
                ):
                    if token not in command_tokens:
                        command_tokens.append(token)
            interpretations.append(
                {
                    "source_namespace": source["namespace"],
                    "key": key,
                    "content_kind": "template_text_retrieved_from_orca",
                    "placeholder_or_expression_markers_present": bool(markers),
                    "placeholder_or_expression_markers": markers,
                    "line_leading_firmware_macro_candidates": command_tokens,
                    "macro_candidate_basis": (
                        "Line-leading identifier not shaped like G<number>, M<number>, or T<number>; "
                        "firmware configuration is required to confirm whether it is a macro."
                    ),
                }
            )

    return {
        "explicit_fields": explicit,
        "other_discovered_fields": sorted(key for key in occurrences if key not in EXPLICIT_GCODE_FIELDS),
        "template_interpretation_separate_from_raw_values": interpretations,
        "limitations": [
            "Expanded G-code output was not obtained because this action does not slice or export G-code.",
            "Firmware macro definitions were not obtained; candidate command names are not proof of macro behavior.",
            "Reading template text does not prove printer-start behavior or evaluate Orca placeholders.",
        ],
    }


def _combined_source_status(sources, namespace_prefixes):
    matching = [
        source["source_read_status"]
        for source in sources
        if any(source["namespace"].startswith(prefix) for prefix in namespace_prefixes)
    ]
    if not matching:
        return DATA_ABSENT
    if READ_FAILED in matching:
        return READ_FAILED
    if DATA_ABSENT in matching:
        return DATA_ABSENT
    return READ_SUCCEEDED


def _capability_coverage(sources, model, application):
    return [
        {
            "surface": "selected and edited printer/process presets",
            "read_status": _combined_source_status(sources, ("printer.", "process.")),
            "detail": "Source-verified PresetCollection selected_preset() and edited_preset(); runtime outcomes are in configuration_sources.",
        },
        {
            "surface": "selected filament slots and exposed filament editor state",
            "read_status": _combined_source_status(sources, ("filament_editor.", "filament_slots[")),
            "detail": "Source-verified ordered names/current preset views plus one collection-level selected/edited pair.",
        },
        {
            "surface": "PresetBundle merged configuration",
            "read_status": _combined_source_status(sources, ("preset_bundle.merged_full_config",)),
            "detail": "Source-verified full_config_keys()/full_config_value(); it is not labeled complete final sliced configuration.",
        },
        {
            "surface": "live model object and volume configuration overrides",
            "read_status": _combined_source_status(sources, ("model.objects[",)),
            "detail": "Source-verified ModelObject/ModelVolume config_keys()/config_value(); mesh arrays intentionally omitted.",
        },
        {
            "surface": "standalone project configuration namespace",
            "read_status": NO_ACCESSOR,
            "detail": "Project values contribute to PresetBundle.full_config(), but the inspected host bindings expose no separate project-config accessor.",
        },
        {
            "surface": "active plate index",
            "read_status": (model.get("fields", {}).get("current_plate_index", {}).get("read_status", model.get("read_status", READ_FAILED))),
            "detail": "Model.current_plate_index() is the only bound active-plate identity read and is captured under project_model_context.",
        },
        {
            "surface": "active plate object and plate settings",
            "read_status": NO_ACCESSOR,
            "detail": "No Plate object, plate preset collection, or plate config accessor is bound.",
        },
        {
            "surface": "tool/extruder associations",
            "read_status": _combined_source_status(sources, ("filament_slots[", "model.objects[")),
            "detail": "Volume.extruder_id() and ordered filament slots are captured, but no accessor establishes a broader authoritative tool mapping.",
        },
        {
            "surface": "selected physical-printer connection object",
            "read_status": NO_ACCESSOR,
            "detail": "PresetType includes PhysicalPrinter, but PresetBundle exposes no physical-printer collection or selected physical-printer accessor. Enumerable merged config keys may still include non-secret connection settings.",
        },
        {
            "surface": "calibration state",
            "read_status": NO_ACCESSOR,
            "detail": "No calibration-state accessor is present in the inspected preset, app, model, or script binding surface.",
        },
        {
            "surface": "resolved slice Print/PrintObject/PrintRegion configuration",
            "read_status": DIFFERENT_PHASE,
            "detail": "These bindings are only reachable through a slicing-pipeline execute(ctx); this diagnostic registers no hook and triggers no slicing.",
        },
        {
            "surface": "G-code export path/host/output name and export-time full config",
            "read_status": DIFFERENT_PHASE,
            "detail": (
                "The nightly's GCodeExportStarted/GCodeExportFinished lifecycle payload exposes the model id, "
                "model name, outcome, and output path. It does not expose an export-time full config; the "
                "qualification companion observes the event without initiating slicing or export."
            ),
        },
        {
            "surface": "Orca build metadata from running host",
            "read_status": application.get("app_info", {}).get("read_status", READ_FAILED),
            "detail": (
                "The qualified nightly exposes orca.host.app_info(); its version/build payload is captured "
                "under application_context and compared with the independently pinned artifact."
            ),
        },
    ]


def build_context_inventory(host, captured_at=None):
    """Capture only source-verified read-only host surfaces into a JSON-safe snapshot."""
    captured_at = captured_at or datetime.datetime.now(datetime.timezone.utc)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=datetime.timezone.utc)
    captured_at_text = captured_at.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    sources = []

    try:
        bundle = host.preset_bundle()
        bundle_status = READ_SUCCEEDED
        bundle_reason = None
    except Exception as exc:
        bundle = None
        bundle_status = READ_FAILED
        bundle_reason = _error_reason(exc)

    presets = {}
    filaments = {
        "read_status": READ_FAILED,
        "reason": "PresetBundle was unavailable.",
        "slots": [],
    }
    if bundle is not None:
        for name, attr in (("printer", "printers"), ("process", "prints")):
            collection = getattr(bundle, attr, None)
            if collection is None:
                presets[name] = {"read_status": DATA_ABSENT, "reason": f"PresetBundle.{attr} is absent."}
            else:
                pair = _capture_collection_pair(
                    sources,
                    collection,
                    name,
                    f"{name} PresetCollection",
                )
                presets[name] = {
                    "read_status": READ_SUCCEEDED,
                    "selected_saved": pair["selected_saved"]["metadata"],
                    "current_edited": pair["current_edited"]["metadata"],
                }
        filaments = _capture_filaments(bundle, sources)
        merged = _capture_config_source(
            "preset_bundle.merged_full_config",
            (
                "PresetBundle.full_config(); current merged Orca configuration, not claimed to be "
                "the complete final sliced configuration"
            ),
            bundle,
            keys_method="full_config_keys",
            value_method="full_config_value",
        )
        sources.append(merged)
    else:
        for namespace in (
            "printer.selected_saved",
            "printer.current_edited",
            "process.selected_saved",
            "process.current_edited",
            "filament_editor.selected_saved",
            "filament_editor.current_edited",
            "preset_bundle.merged_full_config",
        ):
            sources.append(
                _unavailable_config_source(
                    namespace,
                    "PresetBundle-dependent source",
                    READ_FAILED,
                    bundle_reason,
                )
            )

    model = _capture_model(host, sources)
    application = _capture_application_context(host)
    app_info = application.get("app_info", {})

    snapshot = {
        "schema": "helix-orca-context-inventory/v1",
        "diagnostic_only": True,
        "capture": {
            "captured_at_utc": captured_at_text,
            "exporter_version": EXPORTER_VERSION,
            "target_build": dict(TARGET_BUILD),
            "host_build_metadata_read_status": app_info.get("read_status", READ_FAILED),
            "host_build": app_info.get("raw_value"),
        },
        "preset_bundle": {
            "read_status": bundle_status,
            "reason": bundle_reason,
            "profiles": presets,
            "filaments": filaments,
        },
        "application_context": application,
        "project_model_context": model,
        "configuration_sources": sources,
        "coverage_report": {
            "status_definitions": {
                READ_SUCCEEDED: "The read succeeded during this capture.",
                DATA_ABSENT: "The supported API returned no data in this context.",
                AWAITING_RUNTIME: "The pinned source exposes the capability; this build still needs Windows runtime verification.",
                DIFFERENT_PHASE: "The capability is available only in a different host execution phase.",
                NO_ACCESSOR: "No supported accessor was found in the inspected pinned binding surface.",
                READ_FAILED: "The read raised or returned an unusable value; see its reason.",
                REDACTED: "The field was enumerated but intentionally omitted or redacted.",
            },
            "configuration_source_summaries": _source_summaries(sources),
            "capability_surfaces": _capability_coverage(sources, model, application),
            "privacy": {
                "read_status": REDACTED,
                "detail": (
                    "Known credentials/tokens and known path-bearing config values are recorded as redacted; "
                    "preset file paths, source-model input paths, mesh arrays, and inactive presets are omitted."
                ),
            },
        },
        "gcode_and_template_fields": _gcode_template_report(sources),
        "non_claims": [
            "Selected preset objects are not described as raw on-disk leaf JSON files.",
            "PresetBundle.full_config() is not described as the complete final sliced configuration.",
            "No missing value was inferred from profile files, G-code, filenames, or prior reports.",
            "No template was expanded and no G-code or firmware macro was executed.",
        ],
    }
    return snapshot


def write_context_export(snapshot, storage_root, captured_at=None):
    """Write one complete UTF-8 JSON document beneath host-provided storage."""
    captured_at = captured_at or datetime.datetime.now(datetime.timezone.utc)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=datetime.timezone.utc)
    stamp = captured_at.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    export_dir = pathlib.Path(storage_root) / "exports"
    export_path = export_dir / f"orca-context-{stamp}.json"
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    try:
        export_dir.mkdir(parents=True, exist_ok=True)
        with export_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except Exception:
        try:
            if export_path.exists():
                export_path.unlink()
        except Exception:
            pass
        raise
    return str(export_path)


INITIAL_CONTENT_MARKER = "__HELIX_INITIAL_CONTENT_HTML__"


PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root { --bg:var(--orca-bg,#fff); --fg:var(--orca-fg,#202124);
  --muted:var(--orca-muted,#687078); --border:var(--orca-border,#ccd0d5);
  --accent:var(--orca-accent,#00a67e); --accent-fg:var(--orca-accent-fg,#fff);
  --ui:var(--orca-font,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif); }
@media (prefers-color-scheme: dark) { :root { --bg:var(--orca-bg,#2b2d30); --fg:var(--orca-fg,#e4e6e8);
  --muted:var(--orca-muted,#9aa0a6); --border:var(--orca-border,#3d4043); } }
* { box-sizing: border-box; }
body { margin: 0; padding: 18px; font: 13px/1.45 var(--ui); color:var(--fg); background:var(--bg); }
header { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:14px; }
h1 { font-size:20px; margin:0; } h2 { font-size:14px; margin:0 0 10px; }
button { border:0; border-radius:6px; padding:8px 14px; font-weight:600; cursor:pointer;
  color:var(--accent-fg); background:var(--accent); }
button:disabled { opacity:.55; cursor:default; }
.card { padding:13px; margin:0 0 10px; border:1px solid var(--border); border-radius:8px; background:var(--bg); }
.grid { display:grid; grid-template-columns:minmax(130px,.8fr) minmax(180px,1.4fr); gap:5px 12px; }
.label { color:var(--muted); } .value { overflow-wrap:anywhere; }
.dirty { color:#b05a00; font-weight:600; } .clean { color:#27743b; } .unavailable { color:#a23a3a; }
.notice { border-left:4px solid #b78300; } .error { border-left-color:#b3261e; }
.small { font-size:12px; color:var(--muted); }
ul { margin:6px 0 0; padding-left:20px; }
</style></head>
<body>
<header><div><h1>Helix Calibration</h1><div class="small">Read-only Orca context</div></div>
<button id="refresh" type="button">Refresh</button></header>
<main id="content">__HELIX_INITIAL_CONTENT_HTML__</main>
<script>
(function () {
  const content = document.getElementById('content');
  const refresh = document.getElementById('refresh');
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const row = (label, value, cls='') => '<div class="label">'+esc(label)+'</div><div class="value '+cls+'">'+esc(value)+'</div>';
  function sourceText(view) {
    if (!view || !view.source) return 'Unavailable';
    return view.source.reason ? view.source.label + ' — ' + view.source.reason : view.source.label;
  }
  function nameText(view) {
    if (!view) return 'Unavailable';
    return (view.name || 'Unavailable') + (view.reason ? ' — ' + view.reason : '');
  }
  function profileCard(title, profile) {
    if (!profile) return '<section class="card"><h2>'+esc(title)+'</h2><div class="unavailable">Unavailable</div></section>';
    const selected = profile.selected || {};
    const edited = profile.edited || {};
    const state = edited.dirty === true ? ['Unsaved edits present','dirty'] :
      edited.dirty === false ? ['No unsaved edits reported','clean'] : ['Unavailable','unavailable'];
    return '<section class="card"><h2>'+esc(title)+'</h2><div class="grid">' +
      row('Saved selection', nameText(selected)) + row('Saved source', sourceText(selected)) +
      row('Current edited copy', nameText(edited)) + row('Current source', sourceText(edited)) +
      row('Edit state', state[0], state[1]) +
      '</div></section>';
  }
  function setting(setting) {
    if (!setting || !setting.available) return '<span class="unavailable">Unavailable' +
      (setting && setting.reason ? ' — '+esc(setting.reason) : '') + '</span>';
    return esc(setting.display);
  }
  function render(data) {
    refresh.disabled = false;
    if (!data || data.status === 'error') {
      content.innerHTML = '<section class="card notice error"><h2>Context unavailable</h2><div>'+esc(data && data.message || 'Unknown host error')+'</div></section>';
      return;
    }
    let html = '';
    if (data.status === 'unsupported') html += '<section class="card notice error"><h2>Unsupported context</h2><div>'+esc(data.message)+'</div></section>';
    html += profileCard('Printer profile', data.profiles && data.profiles.printer);
    html += profileCard('Process profile', data.profiles && data.profiles.process);
    html += '<section class="card"><h2>Extruders · current effective settings</h2><div class="grid">';
    (data.extruders || []).forEach(e => { html += '<div class="label">'+esc('Extruder '+(e.index+1)+' nozzle')+'</div><div class="value">'+setting(e.nozzle_diameter)+'</div>'; });
    html += '</div>';
    html += '</section>';
    (data.filaments || []).forEach(f => {
      const state = f.current && f.current.dirty === true ? ['Unsaved edits present','dirty'] :
        f.current && f.current.dirty === false ? ['No unsaved edits reported','clean'] : ['Unavailable','unavailable'];
      html += '<section class="card"><h2>Filament slot '+(f.index+1)+'</h2><div class="grid">' +
        row('Saved selection', f.selected_name || 'Unavailable') +
        row('Current preset view', nameText(f.current)) +
        row('Source', sourceText(f.current)) + row('Edit state', state[0], state[1]) +
        '</div><div style="margin-top:10px"><span class="label">Normal nozzle temperature · current effective value</span><br>'+setting(f.normal_nozzle_temperature)+'</div></section>';
    });
    if (data.warnings && data.warnings.length) html += '<section class="card notice"><h2>Unavailable or inconsistent information</h2><ul>'+data.warnings.map(w=>'<li>'+esc(w)+'</li>').join('')+'</ul></section>';
    html += '<section class="card small"><h2>What these values mean</h2><div>'+esc(data.provenance.profile_identity)+'</div><div>'+esc(data.provenance.edited_identity)+'</div><div>'+esc(data.provenance.settings)+'</div></section>';
    content.innerHTML = html;
  }
  refresh.addEventListener('click', function () {
    refresh.disabled = true;
    content.insertAdjacentHTML('afterbegin','<section class="card" id="loading">Refreshing current Orca context…</section>');
    window.orca.postMessage({command:'refresh'});
  });
  window.orca.onMessage(function (data) { const loading=document.getElementById('loading'); if (loading) loading.remove(); render(data); });
})();
</script></body></html>"""


def _html_text(value):
    return html.escape(str("" if value is None else value), quote=True)


def _html_row(label, value, css_class=""):
    return (
        f'<div class="label">{_html_text(label)}</div>'
        f'<div class="value {_html_text(css_class)}">{_html_text(value)}</div>'
    )


def _source_text(view):
    if not view or not view.get("source"):
        return "Unavailable"
    source = view["source"]
    if source.get("reason"):
        return f'{source.get("label", "Unavailable")} — {source["reason"]}'
    return source.get("label", "Unavailable")


def _name_text(view):
    if not view:
        return "Unavailable"
    name = view.get("name") or "Unavailable"
    return f'{name} — {view["reason"]}' if view.get("reason") else name


def _edit_state(view):
    if view and view.get("dirty") is True:
        return "Unsaved edits present", "dirty"
    if view and view.get("dirty") is False:
        return "No unsaved edits reported", "clean"
    return "Unavailable", "unavailable"


def _profile_card(title, profile):
    if not profile:
        return (
            f'<section class="card"><h2>{_html_text(title)}</h2>'
            '<div class="unavailable">Unavailable</div></section>'
        )
    selected = profile.get("selected") or {}
    edited = profile.get("edited") or {}
    state, state_class = _edit_state(edited)
    return (
        f'<section class="card"><h2>{_html_text(title)}</h2><div class="grid">'
        f'{_html_row("Saved selection", _name_text(selected))}'
        f'{_html_row("Saved source", _source_text(selected))}'
        f'{_html_row("Current edited copy", _name_text(edited))}'
        f'{_html_row("Current source", _source_text(edited))}'
        f'{_html_row("Edit state", state, state_class)}'
        '</div></section>'
    )


def _setting_html(setting):
    if not setting or not setting.get("available"):
        reason = f' — {_html_text(setting["reason"])}' if setting and setting.get("reason") else ""
        return f'<span class="unavailable">Unavailable{reason}</span>'
    return _html_text(setting.get("display", ""))


def _render_context_html(data):
    """Render the initial snapshot before the window and its WebView exist."""
    if not data or data.get("status") == "error":
        message = data.get("message") if data else "Unknown host error"
        return (
            '<section class="card notice error"><h2>Context unavailable</h2>'
            f'<div>{_html_text(message)}</div></section>'
        )

    sections = []
    if data.get("status") == "unsupported":
        sections.append(
            '<section class="card notice error"><h2>Unsupported context</h2>'
            f'<div>{_html_text(data.get("message", ""))}</div></section>'
        )

    profiles = data.get("profiles") or {}
    sections.append(_profile_card("Printer profile", profiles.get("printer")))
    sections.append(_profile_card("Process profile", profiles.get("process")))

    extruders = ['<section class="card"><h2>Extruders · current effective settings</h2><div class="grid">']
    for extruder in data.get("extruders") or []:
        extruder_label = f'Extruder {extruder.get("index", 0) + 1} nozzle'
        extruders.append(
            f'<div class="label">{_html_text(extruder_label)}</div>'
            f'<div class="value">{_setting_html(extruder.get("nozzle_diameter"))}</div>'
        )
    extruders.append("</div></section>")
    sections.append("".join(extruders))

    for filament in data.get("filaments") or []:
        current = filament.get("current") or {}
        state, state_class = _edit_state(current)
        sections.append(
            f'<section class="card"><h2>Filament slot {filament.get("index", 0) + 1}</h2><div class="grid">'
            f'{_html_row("Saved selection", filament.get("selected_name") or "Unavailable")}'
            f'{_html_row("Current preset view", _name_text(current))}'
            f'{_html_row("Source", _source_text(current))}'
            f'{_html_row("Edit state", state, state_class)}'
            '</div><div style="margin-top:10px"><span class="label">'
            'Normal nozzle temperature · current effective value</span><br>'
            f'{_setting_html(filament.get("normal_nozzle_temperature"))}</div></section>'
        )

    warnings = data.get("warnings") or []
    if warnings:
        items = "".join(f'<li>{_html_text(warning)}</li>' for warning in warnings)
        sections.append(
            '<section class="card notice"><h2>Unavailable or inconsistent information</h2>'
            f'<ul>{items}</ul></section>'
        )

    provenance = data.get("provenance") or {}
    sections.append(
        '<section class="card small"><h2>What these values mean</h2>'
        f'<div>{_html_text(provenance.get("profile_identity", ""))}</div>'
        f'<div>{_html_text(provenance.get("edited_identity", ""))}</div>'
        f'<div>{_html_text(provenance.get("settings", ""))}</div></section>'
    )
    return "".join(sections)


def _page_with_initial_context(context):
    return PAGE.replace(INITIAL_CONTENT_MARKER, _render_context_html(context), 1)


def _enum_name(value):
    name = getattr(value, "name", None)
    if isinstance(name, str) and name:
        return name
    text = str(value)
    return text.rsplit(".", 1)[-1] if text else "Unknown"


def lifecycle_event_payload(event, context, captured_at=None):
    """Normalize the source-verified lifecycle payload into JSON-safe values."""
    captured_at = captured_at or datetime.datetime.now(datetime.timezone.utc)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=datetime.timezone.utc)
    return {
        "captured_at_utc": captured_at.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": _enum_name(event),
        "name": str(getattr(context, "name", "") or ""),
        "code": _enum_name(getattr(context, "code", "Unknown")),
        "msg": str(getattr(context, "msg", "") or ""),
        "id": str(getattr(context, "id", "") or ""),
        "previous_name": str(getattr(context, "previous_name", "") or ""),
        "device_id": str(getattr(context, "device_id", "") or ""),
        "job_id": str(getattr(context, "job_id", "") or ""),
        "source": str(getattr(context, "source", "") or ""),
        "index": int(getattr(context, "index", -1)),
        "dirty": bool(getattr(context, "dirty", False)),
    }


def _runtime_build(host):
    try:
        info = dict(host.app_info())
    except Exception as exc:
        return {
            "read_status": READ_FAILED,
            "reason": _error_reason(exc),
            "info": {},
            "matches_target": False,
        }
    version = str(info.get("version") or "")
    build = str(info.get("build") or "")
    matches = version == TARGET_BUILD["version"].removeprefix("OrcaSlicer ") and build.startswith(TARGET_BUILD["build"])
    return {
        "read_status": READ_SUCCEEDED,
        "reason": None if matches else "Running Orca version/build does not match the pinned October 11 target.",
        "info": info,
        "matches_target": matches,
    }


def _qualification_snapshot(host, events, captured_at=None):
    captured_at = captured_at or datetime.datetime.now(datetime.timezone.utc)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=datetime.timezone.utc)
    context = build_context(host)
    event_names = {item.get("event") for item in events}
    required_events = (
        "PresetSelected",
        "ProjectDirtyChanged",
        "GCodeExportStarted",
        "GCodeExportFinished",
    )
    return {
        "schema": "helix-orca-nightly-qualification/v1",
        "diagnostic_only": True,
        "captured_at_utc": captured_at.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "target": dict(TARGET_BUILD),
        "runtime": _runtime_build(host),
        "context": context,
        "lifecycle": {
            "events": list(events),
            "required_observations": {
                name: name in event_names for name in required_events
            },
        },
        "non_claims": [
            "This probe does not start, upload, or monitor a print.",
            "This probe does not write, save, or apply an Orca preset value.",
            "The launch command and Windows process evidence, not this payload alone, prove isolated --datadir use.",
        ],
    }


def write_qualification_evidence(snapshot, storage_root, captured_at=None):
    captured_at = captured_at or datetime.datetime.now(datetime.timezone.utc)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=datetime.timezone.utc)
    stamp = captured_at.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    evidence_dir = pathlib.Path(storage_root) / "qualification"
    evidence_path = evidence_dir / f"nightly-qualification-{stamp}.json"
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    with evidence_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    return str(evidence_path)


QUALIFICATION_PANEL_PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
* { box-sizing:border-box; }
body { margin:0; padding:12px; font:13px/1.4 var(--orca-font,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif);
  color:var(--orca-fg,#e4e6e8); background:var(--orca-bg,#2b2d30); }
h1 { margin:0; font-size:16px; } h2 { margin:0 0 8px; font-size:13px; }
.muted { color:var(--orca-muted,#9aa0a6); font-size:12px; }
.card { border:1px solid var(--orca-border,#3d4043); border-radius:7px; padding:10px; margin-top:10px; }
.grid { display:grid; grid-template-columns:minmax(95px,.8fr) minmax(130px,1.3fr); gap:4px 8px; }
.label { color:var(--orca-muted,#9aa0a6); } .value { overflow-wrap:anywhere; }
.ok { color:#50b96b; font-weight:600; } .bad { color:#ee6b65; font-weight:600; }
.actions { display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }
button { border:1px solid var(--orca-border,#3d4043); border-radius:5px; padding:7px 10px; cursor:pointer;
  color:var(--orca-fg,#e4e6e8); background:var(--orca-accent,#008c6a); }
button.quiet { background:transparent; }
#events { max-height:210px; overflow:auto; margin:0; padding-left:20px; }
#events li { margin:0 0 7px; overflow-wrap:anywhere; }
#saved { margin-top:8px; overflow-wrap:anywhere; }
</style></head><body>
<h1>Helix Calibration</h1>
<div class="muted">October 11 nightly qualification · read-only · never starts a print</div>
<div class="actions">
  <button id="refresh" type="button">Refresh context</button>
  <button id="save" type="button">Save qualification evidence</button>
  <button id="clear" class="quiet" type="button">Clear events</button>
</div>
<section class="card"><h2>Runtime</h2><div id="runtime" class="grid"></div></section>
<section class="card"><h2>Current Orca context</h2><div id="context" class="grid"></div></section>
<section class="card"><h2>Manual exported file</h2>
<label>Select the actual exported G-code <input id="file" type="file" accept=".gcode"></label>
<div id="file-status" class="muted">No file selected</div></section>
<section class="card"><h2>Lifecycle events</h2><ol id="events"></ol></section>
<div id="saved" class="muted"></div>
<script>
(function () {
  var runtime = document.getElementById('runtime');
  var context = document.getElementById('context');
  var events = document.getElementById('events');
  var saved = document.getElementById('saved');
  function esc(value) { var span=document.createElement('span'); span.textContent=value == null ? '' : String(value); return span.innerHTML; }
  function row(label, value, cls) { return '<div class="label">'+esc(label)+'</div><div class="value '+(cls||'')+'">'+esc(value)+'</div>'; }
  function name(view) { return view && view.name ? view.name : 'Unavailable'; }
  function setting(value) { return value && value.available ? value.display : 'Unavailable'; }
  function addEvent(item) {
    var li=document.createElement('li');
    var detail=[item.name, item.msg, item.source].filter(Boolean).join(' · ');
    li.innerHTML='<strong>'+esc(item.event)+'</strong>'+(detail ? '<br><span class="muted">'+esc(detail)+'</span>' : '');
    events.insertBefore(li, events.firstChild);
  }
  function render(message) {
    var build=message.runtime || {}, info=build.info || {};
    runtime.innerHTML=row('Version',info.version||'Unavailable')+row('Build',info.build||'Unavailable')+
      row('Pinned target',message.target.build,build.matches_target?'ok':'bad')+
      row('Match',build.matches_target?'Yes':'No',build.matches_target?'ok':'bad');
    var data=message.context || {}, profiles=data.profiles || {}, filaments=data.filaments || [];
    var first=filaments[0] || {};
    context.innerHTML=row('Printer',name(profiles.printer && profiles.printer.edited))+
      row('Process',name(profiles.process && profiles.process.edited))+
      row('Filament',first.selected_name||'Unavailable')+
      row('Effective temp',setting(first.normal_nozzle_temperature))+
      row('Filament edited',first.current && first.current.dirty === true ? 'Unsaved edits present' : 'No/Unavailable',
          first.current && first.current.dirty === true ? 'ok' : '')+
      row('Status',data.status||'Unavailable',data.status==='ok'?'ok':'bad');
    events.innerHTML='';
    ((message.lifecycle && message.lifecycle.events)||[]).forEach(addEvent);
    saved.textContent=message.saved_path ? 'Saved: '+message.saved_path : (message.error||'');
  }
  window.orca.onMessage(function (message) {
    if (!message) return;
    if (message.command === 'state') render(message);
    else if (message.command === 'event') addEvent(message.event);
  });
  document.getElementById('refresh').addEventListener('click',function(){window.orca.postMessage({command:'refresh'});});
  document.getElementById('save').addEventListener('click',function(){window.orca.postMessage({command:'save'});});
  document.getElementById('clear').addEventListener('click',function(){window.orca.postMessage({command:'clear'});});
  // about:blank host documents lack crypto.subtle. Hash selected bytes locally.
  function sha256(bytes) {
    var k=[1116352408,1899447441,3049323471,3921009573,961987163,1508970993,2453635748,2870763221,
      3624381080,310598401,607225278,1426881987,1925078388,2162078206,2614888103,3248222580,
      3835390401,4022224774,264347078,604807628,770255983,1249150122,1555081692,1996064986,
      2554220882,2821834349,2952996808,3210313671,3336571891,3584528711,113926993,338241895,
      666307205,773529912,1294757372,1396182291,1695183700,1986661051,2177026350,2456956037,
      2730485921,2820302411,3259730800,3345764771,3516065817,3600352804,4094571909,275423344,
      430227734,506948616,659060556,883997877,958139571,1322822218,1537002063,1747873779,
      1955562222,2024104815,2227730452,2361852424,2428436474,2756734187,3204031479,3329325298];
    var h=[1779033703,3144134277,1013904242,2773480762,1359893119,2600822924,528734635,1541459225];
    var input=new Uint8Array(bytes), padded=new Uint8Array(Math.ceil((input.length+9)/64)*64);
    padded.set(input); padded[input.length]=128;
    var view=new DataView(padded.buffer); view.setUint32(padded.length-4,input.length*8,false);
    var w=new Uint32Array(64);
    function rotate(x,n){return (x>>>n)|(x<<(32-n));}
    for(var offset=0;offset<padded.length;offset+=64){
      for(var i=0;i<16;i++) w[i]=view.getUint32(offset+i*4,false);
      for(i=16;i<64;i++){
        var x=w[i-15],y=w[i-2];
        w[i]=(w[i-16]+(rotate(x,7)^rotate(x,18)^(x>>>3))+w[i-7]+(rotate(y,17)^rotate(y,19)^(y>>>10)))>>>0;
      }
      var a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],z=h[7];
      for(i=0;i<64;i++){
        var t1=(z+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+k[i]+w[i])>>>0;
        var t2=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))>>>0;
        z=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;
      }
      [a,b,c,d,e,f,g,z].forEach(function(value,i){h[i]=(h[i]+value)>>>0;});
    }
    return h.map(function(value){return value.toString(16).padStart(8,'0');}).join('');
  }
  document.getElementById('file').addEventListener('change',async function () {
    var status=document.getElementById('file-status'), file=this.files[0];
    if (!file) return;
    try {
      if (!/\.gcode$/i.test(file.name) || file.size>20000000 || file.size===0) throw Error('Select a nonempty G-code file below 20 MB.');
      var bytes=await file.arrayBuffer();
      var sha=sha256(bytes);
      var text=new TextDecoder('utf-8',{fatal:true}).decode(bytes), bands=[], match;
      var pattern=/^M10[49]\s+S(\d+)(?:\s|$)/gm;
      while ((match=pattern.exec(text))!==null) { var value=Number(match[1]); if(value>0 && bands.indexOf(value)<0) bands.push(value); }
      var expected=[230,225,220,215,210,205,200,195,190];
      if (JSON.stringify(bands)!==JSON.stringify(expected)) throw Error('Temperature choices do not match 230–190 °C in 5 °C steps.');
      window.orca.postMessage({command:'manual_file',file:{name:file.name,size:file.size,sha256:sha,bands:bands}});
      status.textContent=file.name+' · '+file.size+' bytes · SHA-256 '+sha+' · choices verified';
    } catch(error) { status.textContent='Rejected: '+error.message; window.orca.postMessage({command:'manual_file',file:null}); }
  });
  window.orca.postMessage({command:'ready'});
})();
</script></body></html>"""


class NightlyQualificationPanel(orca.script.ScriptPluginCapabilityBase):
    """Read-only target-runtime probe; product transport remains gated on its result."""

    MAX_EVENTS = 100

    def __init__(self):
        super().__init__()
        self.panel = None
        self.storage_root = None
        self.events = []
        self.manual_file = None

    def get_name(self):
        return QUALIFICATION_ACTION_NAME

    def execute(self):
        if self.panel is not None and self.panel.is_open():
            self.panel.show()
            return orca.ExecutionResult.success(f"{QUALIFICATION_ACTION_NAME} is already open.")
        self.storage_root = orca.host.plugin.storage()
        self.panel = orca.host.ui.create_dock_panel(
            html=QUALIFICATION_PANEL_PAGE,
            title="Helix Calibration",
            width=360,
            height=560,
            on_message=self.on_message,
            on_close=self.on_close,
            dock="right",
        )
        return orca.ExecutionResult.success(f"{QUALIFICATION_ACTION_NAME} opened.")

    def on_message(self, message):
        command = (message or {}).get("command") if isinstance(message, dict) else None
        if command in {"ready", "refresh"}:
            self._post_state()
        elif command == "clear":
            self.events.clear()
            self._post_state()
        elif command == "manual_file":
            candidate = message.get("file")
            self.manual_file = None
            if (isinstance(candidate, dict) and isinstance(candidate.get("name"), str)
                    and re.fullmatch(r"[^/\\]+\.gcode", candidate["name"], re.IGNORECASE)
                    and type(candidate.get("size")) is int and 0 < candidate["size"] <= 20000000
                    and isinstance(candidate.get("sha256"), str)
                    and re.fullmatch(r"[a-f0-9]{64}", candidate["sha256"])
                    and candidate.get("bands") == list(range(230, 189, -5))):
                self.manual_file = dict(candidate)
        elif command == "save":
            self._save_and_post()

    def on_close(self):
        self.panel = None

    def on_lifecycle_event(self, event, context):
        payload = lifecycle_event_payload(event, context)
        self.events.append(payload)
        del self.events[:-self.MAX_EVENTS]
        if self.panel is not None and self.panel.is_open():
            self.panel.post({"command": "event", "event": payload})

    def _post_state(self, **extra):
        if self.panel is None or not self.panel.is_open():
            return
        payload = _qualification_snapshot(orca.host, self.events)
        payload["command"] = "state"
        payload.update(extra)
        self.panel.post(payload)

    def _save_and_post(self):
        try:
            captured_at = datetime.datetime.now(datetime.timezone.utc)
            snapshot = _qualification_snapshot(orca.host, self.events, captured_at=captured_at)
            snapshot["manual_file_selection"] = self.manual_file
            saved_path = write_qualification_evidence(
                snapshot,
                self.storage_root,
                captured_at=captured_at,
            )
        except Exception as exc:
            self._post_state(error=f"Qualification evidence export failed: {_error_reason(exc)}")
            return
        self._post_state(saved_path=saved_path)


class HelixCalibrationContext(orca.script.ScriptPluginCapabilityBase):
    def __init__(self):
        super().__init__()
        self.window = None

    def get_name(self):
        return PLUGIN_NAME

    def execute(self):
        if self.window is not None and self.window.is_open():
            self.window.close()
        # PluginWebDialog loads a bootstrap document before SetPage installs this
        # HTML. Host posts made during that transition are not acknowledged and
        # were lost on the target WebView2 build, so initialize in-band instead.
        initial_context = build_context(orca.host)
        self.window = orca.host.ui.create_window(
            html=_page_with_initial_context(initial_context),
            title=PLUGIN_NAME,
            width=560,
            height=700,
            on_message=self.on_message,
        )
        return orca.ExecutionResult.success(f"{PLUGIN_NAME} opened.")

    def on_message(self, message):
        if isinstance(message, dict) and message.get("command") == "refresh":
            self._post_current_context()

    def _post_current_context(self):
        if self.window is None or not self.window.is_open():
            return
        self.window.post(build_context(orca.host))


class ExportOrcaContextJson(orca.script.ScriptPluginCapabilityBase):
    """Synchronous audited capture/write action; no deferred callback is used."""

    def get_name(self):
        return EXPORT_ACTION_NAME

    def execute(self):
        captured_at = datetime.datetime.now(datetime.timezone.utc)
        try:
            snapshot = build_context_inventory(orca.host, captured_at=captured_at)
            storage_root = orca.host.plugin.storage()
            export_path = write_context_export(snapshot, storage_root, captured_at=captured_at)
        except Exception as exc:
            return orca.ExecutionResult.failure(
                orca.PluginResult.RecoverableError,
                f"Orca context export failed: {_error_reason(exc)}",
            )
        return orca.ExecutionResult.success(
            f"Orca context exported to: {export_path}",
            export_path,
        )


@orca.plugin
class HelixCalibrationPlugin(orca.base):
    def register_capabilities(self):
        orca.register_capability(HelixCalibrationContext)
        orca.register_capability(ExportOrcaContextJson)
        orca.register_capability(NightlyQualificationPanel)
