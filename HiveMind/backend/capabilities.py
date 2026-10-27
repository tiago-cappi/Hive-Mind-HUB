"""Conservative selection and compatibility decisions for discovery-only P0."""

from dataclasses import dataclass
from contextlib import contextmanager
import threading
from types import MappingProxyType

from .adapters.base import Discovery


@dataclass(frozen=True)
class GateResult:
    catalog: str
    entitlement: str
    included_billing: str
    execution_allowed: bool
    reasons: tuple[str, ...]


class _EnforcementEvidence:
    """Internal capability bound to a live provider session and model selection."""

    def __init__(self, seal, provider, version, model, effort, validate):
        if seal is not _EVIDENCE_SEAL:
            raise TypeError("evidence is issued by the provider session")
        self._provider, self._version = provider, version
        self._model, self._effort, self._validate = model, effort, validate


_EVIDENCE_SEAL = object()


def _issue_evidence(provider, version, model, effort, validate):
    # Internal Python boundary only: never construct this from HTTP/UI input.
    return _EnforcementEvidence(_EVIDENCE_SEAL, provider, version, model, effort, validate)


class PauseRequested(Exception):
    """A new broker operation was refused after pause was requested."""


class ToolNotAllowed(Exception):
    """The requested operation is not one of the broker's allowed tools."""


class ToolAdmission:
    """Admission and drain for broker operations; it does not control CLI tools."""

    def __init__(self):
        self._lock = threading.Lock()
        self._pausing = False
        self._active = 0

    @contextmanager
    def admit(self):
        with self._lock:
            if self._pausing:
                raise PauseRequested()
            self._active += 1
        try:
            yield
        finally:
            with self._lock:
                self._active -= 1

    def accepting(self):
        with self._lock:
            return not self._pausing

    def request_pause(self):
        with self._lock:
            self._pausing = True
            return self._active == 0

    def drained(self):
        with self._lock:
            return self._pausing and self._active == 0


_TOOLS = ("read", "patch", "checks", "progress")


class ToolBroker:
    """Dispatch only trusted, explicitly supplied handlers through pause admission.

    Handlers remain responsible for filesystem and command authorization. This
    seam alone does not authorize a workspace or enable a provider session.
    """

    def __init__(self, handlers):
        if not handlers or not set(handlers) <= set(_TOOLS) or not all(
            callable(handler) for handler in handlers.values()
        ):
            raise ValueError("expected handlers among read, patch, checks and progress")
        self._handlers = MappingProxyType(dict(handlers))
        self.admission = ToolAdmission()

    @property
    def names(self):
        """The tools this job may use, in catalog order."""
        return tuple(name for name in _TOOLS if name in self._handlers)

    def dispatch(self, name, arguments):
        if name not in self._handlers:
            raise ToolNotAllowed()
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be an object")
        with self.admission.admit():
            return self._handlers[name](arguments)

    def dispatch_and_reply(self, name, arguments, reply):
        """Keep admission open until the tool result is sent to the provider."""
        if name not in _TOOLS:
            raise ToolNotAllowed()
        if not isinstance(arguments, dict) or not callable(reply):
            raise ValueError("invalid tool request")
        with self.admission.admit():
            if name not in self._handlers:
                # A real tool this job was not given: refuse it, but do not fail the job.
                reply(False, {"error": "tool_not_allowed"})
                return
            try:
                result = self._handlers[name](arguments)
            except Exception:
                reply(False, {"error": "tool_failed"})
            else:
                reply(True, result)


def evaluate(discovery: Discovery, model: str, effort: str,
             evidence=None) -> GateResult:
    """Evaluate verified facts; the returned gate does not dispatch a turn."""
    if discovery.models is None:
        catalog = "unknown"
    else:
        matches = [item for item in discovery.models if item.name == model]
        catalog = ("model_unlisted" if not matches else
                   "effort_unlisted" if effort not in matches[0].efforts else "listed")
    reasons = []
    if not discovery.installed:
        reasons.append("cli_unavailable")
    if not discovery.compatible:
        reasons.append("version_unverified")
    if not discovery.authenticated:
        reasons.append("subscription_unverified")
    if discovery.errors:
        reasons.append("discovery_incomplete")
    if catalog != "listed":
        reasons.append("selection_" + catalog)
    if discovery.ordinary_usage_allowed is False:
        reasons.append("ordinary_quota_unavailable")
    billing = ("ordinary_available" if discovery.provider == "codex"
               and discovery.authenticated and discovery.ordinary_usage_allowed is True
               and discovery.has_credits is False else
               "ordinary_available" if discovery.provider == "claude" and discovery.authenticated
               and discovery.ordinary_usage_allowed is True and discovery.extra_usage_enabled is False
               else "unknown")
    if billing == "unknown":
        reasons.append("billing_path_unverified")
    if discovery.provider == "claude" and discovery.policy_customizations_absent is not True:
        reasons.append("managed_policy_unverified")
    if type(evidence) is not _EnforcementEvidence or (
            evidence._provider, evidence._version, evidence._model, evidence._effort) != (
            discovery.provider, discovery.version, model, effort):
        reasons.append("enforcement_evidence_unverified")
    else:
        try:
            if evidence._validate() is not True:
                reasons.append("enforcement_evidence_unverified")
        except Exception:
            reasons.append("enforcement_evidence_unverified")
    return GateResult(catalog, "not_tested", billing, not reasons, tuple(reasons))
