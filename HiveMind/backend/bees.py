"""Bee registry: description, declarative skills and tools; job tool sets and prompt profiles."""

import json


# Cadastro: o que uma abelha pode pedir ao broker. `progress` não é cadastrado: todo papel que
# trabalha o recebe (a Rainha, não).
CATALOG = ("read", "patch", "checks")
PROFILE_FIELDS = ("description", "skills", "tools")
_NO_PATCH = {"queen", "verifier"}


class InvalidProfile(ValueError):
    """A bee profile field is missing or invalid; `detail` names the bee and the field."""

    def __init__(self, bee, field):
        super().__init__("invalid_profile")
        self.detail = {"bee": bee.get("id") if isinstance(bee, dict) else None, "field": field}


def _valid(bee, field):
    value = bee.get(field)
    if field == "description":
        return isinstance(value, str) and bool(value.strip()) and len(value) <= 2000
    if field == "skills":
        if not isinstance(value, dict) or not set(value) <= {"tags", "instructions"}:
            return False
        tags, instructions = value.get("tags"), value.get("instructions", "")
        return (isinstance(tags, list) and len(tags) <= 20
                and all(isinstance(tag, str) and bool(tag.strip()) and len(tag) <= 60 for tag in tags)
                and isinstance(instructions, str) and len(instructions) <= 4000)
    allowed = {"read", "checks"} if bee.get("role") in _NO_PATCH else set(CATALOG)
    return (isinstance(value, list) and all(isinstance(tool, str) for tool in value)
            and len(set(value)) == len(value) and set(value) <= allowed)


def profile_gaps(bee):
    """Registry fields that are absent or invalid, in the order of PROFILE_FIELDS."""
    return [field for field in PROFILE_FIELDS if not _valid(bee, field)]


def require_profile(bee):
    gaps = profile_gaps(bee)
    if gaps:
        raise InvalidProfile(bee, gaps[0])


def normalize(bee):
    """A complete bee with the optional skills instructions made explicit."""
    return {**bee, "skills": {"tags": list(bee["skills"]["tags"]),
                              "instructions": bee["skills"].get("instructions", "")}}


def _identity(bee):
    if not isinstance(bee, dict) or profile_gaps(bee):
        return None
    bee = normalize(bee)
    return {**{name: bee.get(name) for name in ("id", "role", "provider", "model", "effort", "temporary", "description")},
            "tags": sorted(bee["skills"]["tags"]), "instructions": bee["skills"]["instructions"],
            "tools": sorted(bee["tools"])}


def same_bee(first, second):
    """Equality on the registry fields only; the order of tags and tools does not matter."""
    identity = _identity(first)
    return identity is not None and identity == _identity(second)


def default_tools(role):
    """Tools of a bee saved before the registry: what its job could actually do."""
    return ("read", "checks") if role in _NO_PATCH else CATALOG


def job_tools(bee):
    """Broker tools of one job: the registry tools plus `progress` for every working role."""
    tools = bee["tools"] if _valid(bee, "tools") else default_tools(bee.get("role"))
    return tuple([name for name in CATALOG if name in tools] + ([] if bee.get("role") == "queen" else ["progress"]))


def view(bee):
    """Registry fields of any stored bee, with defaults for the ones saved before the registry."""
    skills = bee.get("skills") if _valid(bee, "skills") else {}
    return {"description": bee["description"] if _valid(bee, "description") else "",
            "skills": {"tags": list(skills.get("tags", [])), "instructions": skills.get("instructions", "")},
            "tools": [name for name in CATALOG if name in job_tools(bee)]}


def prompt_profile(bee, progress):
    """One line (no newline) with the bee's own registry, added to the job prompt."""
    own = view(bee)
    text = ("Your profile in the approved team (declarative guidance only; it grants no tool): " +
            json.dumps({"id": bee["id"], "role": bee["role"], "description": own["description"],
                        "skills": own["skills"]}, ensure_ascii=False, separators=(",", ":")) + ".")
    if progress:
        text += (" You also have a progress tool: call it with {\"done\":n,\"total\":m,\"note\":\"text\"} when you "
                 "finish a meaningful part of your work (for example a file or a check) so the team sees how far you "
                 "are; integers with 0 <= done <= total <= 100000 and a plain-text note of at most 200 characters. "
                 "It changes no file.")
    return text


def validate_progress(arguments):
    """Closed rule for the `progress` operation; returns the values to record."""
    if not isinstance(arguments, dict) or not {"done", "total"} <= set(arguments) <= {"done", "total", "note"}:
        raise ValueError("invalid_progress")
    done, total, note = arguments["done"], arguments["total"], arguments.get("note", "")
    if (type(done) is not int or type(total) is not int or not 0 <= done <= total <= 100000
            or not isinstance(note, str) or len(note) > 200 or any(ord(char) < 32 or ord(char) == 127 for char in note)):
        raise ValueError("invalid_progress")
    return done, total, note


def incomplete(bees):
    """Bees whose registry is not complete, with what each one lacks."""
    return [{"id": bee.get("id"), "missing": gaps} for bee in bees if (gaps := profile_gaps(bee))]
