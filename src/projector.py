from typing import Dict, Any, List, Optional
from .models import CanonicalProfile
import re


class Projector:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def project(self, profiles: List[CanonicalProfile]) -> List[Dict[str, Any]]:
        output = []
        for profile in profiles:
            try:
                projected = self._project_single(profile)
                if projected is not None:
                    output.append(projected)
            except ValueError as e:
                print(f"Skipping profile {profile.candidate_id}: {e}")
        return output

    def _project_single(self, profile: CanonicalProfile) -> Dict[str, Any]:
        result = {}
        profile_dict = profile.model_dump()
        on_missing = self.config.get("on_missing", "null")
        include_confidence = self.config.get("include_confidence", True)

        for field_def in self.config.get("fields", []):
            path = field_def.get("path")
            source_path = field_def.get("from", path)
            is_required = field_def.get("required", False)
            normalize_type = field_def.get("normalize")

            val = self._extract_value(profile_dict, source_path)

            if val is not None and normalize_type:
                val = self._apply_normalization(val, normalize_type)

            if val is None or (isinstance(val, list) and len(val) == 0):
                if is_required and on_missing == "error":
                    raise ValueError(f"Required field '{source_path}' missing for '{profile.candidate_id}'")
                elif on_missing == "omit":
                    continue
                else:
                    val = None

            result[path] = val

        if include_confidence:
            result["provenance"] = profile_dict.get("provenance") or {}
            result["overall_confidence"] = profile_dict.get("overall_confidence")

        return result

    def _apply_normalization(self, val: Any, normalize_type: str) -> Any:
        from .normalizers import normalize_phone, normalize_skill
        if normalize_type == "E164":
            if isinstance(val, str):
                return normalize_phone(val) or val
        elif normalize_type == "canonical":
            if isinstance(val, list):
                result = []
                for item in val:
                    if isinstance(item, str):
                        result.append(normalize_skill(item) or item)
                    elif isinstance(item, dict) and "name" in item:
                        item["name"] = normalize_skill(item["name"]) or item["name"]
                        result.append(item)
                return result
            elif isinstance(val, str):
                return normalize_skill(val) or val
        return val

    def _extract_value(self, data: Any, path: str) -> Any:
        # Array wildcard: "skills[].name" or "skills[*].name"
        m = re.match(r'^(\w+)\[[\]*]\]?\.(.+)$', path)
        if not m:
            m = re.match(r'^(\w+)\[\]\.(.+)$', path)
        if not m:
            m = re.match(r'^(\w+)\[\*\]\.(.+)$', path)
        if m:
            array_key, sub_path = m.group(1), m.group(2)
            arr = data.get(array_key) if isinstance(data, dict) else None
            if isinstance(arr, list):
                results = [self._extract_value(item, sub_path) for item in arr]
                results = [r for r in results if r is not None]
                return results if results else None
            return None

        parts = re.split(r'\.|\[', path.replace(']', ''))
        curr = data
        for part in parts:
            if not part:
                continue
            if isinstance(curr, dict):
                curr = curr.get(part)
            elif isinstance(curr, list):
                try:
                    curr = curr[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
            if curr is None:
                return None
        return curr
