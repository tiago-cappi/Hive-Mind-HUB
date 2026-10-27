"""Hooks de leitura/alteração: exclusão mútua e recusa de versões defasadas.

Entre ferramentas, a assinatura lida pertence à sessão; durante uma ferramenta,
um lock compartilhado protege o acervo. Shell/MCP observam o inventário inteiro,
pois seu destino não é inferível com segurança pelo texto do comando. É uma
guarda cooperativa de concorrência do Hub, não um sandbox do sistema operacional.
"""
import ctypes
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

FILE_TOOLS = {"Read", "Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell", "REPL"}
EXCLUDED = {".obsidian", ".trash", ".claude"}
MANAGED = {"_agentes/voice-hub.md", "_agentes/historico-mobile.json"}


def signature(file):
    try:
        return hashlib.sha256(file.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def atomic_json(file, data):
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_name(file.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, file)


def pid_alive(pid):
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x1000, False, int(pid))
        if not handle:
            # Acesso negado não prova processo morto.
            return ctypes.get_last_error() == 5
        code = ctypes.c_ulong()
        ok = kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))
        kernel.CloseHandle(ctypes.c_void_p(handle))
        return not ok or code.value == 259
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


@contextmanager
def control(state):
    """Serializa publicação/retirada de locks, inclusive recuperação concorrente."""
    state = Path(state)
    state.mkdir(parents=True, exist_ok=True)
    with open(state / "control.lock", "a+b") as fh:
        fh.seek(0, 2)
        if fh.tell() == 0:
            fh.write(b"0")
            fh.flush()
        deadline = time.monotonic() + 5
        while True:
            try:
                fh.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Não foi possível acessar a guarda do acervo")
                time.sleep(0.02)
        try:
            yield
        finally:
            fh.seek(0)
            if os.name == "nt":
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh, fcntl.LOCK_UN)


def remove_lock(lock):
    # Windows pode recusar temporariamente a retirada do diretório. Não esconder
    # falha definitiva nem abrir o acervo enquanto a retirada está incompleta.
    for attempt in range(5):
        try:
            shutil.rmtree(lock)
            return
        except FileNotFoundError:
            return
        except OSError:
            if attempt == 4:
                raise
            time.sleep(0.05)


def _release(state, owner, tool_id=None):
    lock = Path(state) / "active"
    try:
        data = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    if data["owner"] == owner and (tool_id is None or data["tool"] == tool_id):
        remove_lock(lock)


def release_owner(state, owner, tool_id=None):
    with control(state):
        _release(state, owner, tool_id)


def acquire(state, owner, pid, tool_id, timeout=20):
    state.mkdir(parents=True, exist_ok=True)
    lock = state / "active"
    deadline = time.monotonic() + timeout
    while True:
        with control(state):
            if lock.exists():
                try:
                    data = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
                except (FileNotFoundError, json.JSONDecodeError):
                    # Não há publicação em curso: todo publicador segura control.
                    # Recupera também uma retirada parcial da versão anterior.
                    remove_lock(lock)
                else:
                    if not pid_alive(data["pid"]):
                        _release(state, data["owner"])
            if not lock.exists():
                # Apenas pastas preparatórias abandonadas podem existir aqui;
                # uma publicação viva precisaria estar segurando control.
                for abandoned in state.glob(".claim-*"):
                    remove_lock(abandoned)
                prepared = state / (".claim-" + uuid.uuid4().hex)
                prepared.mkdir()
                try:
                    atomic_json(prepared / "owner.json", {"owner": owner, "pid": pid, "tool": tool_id})
                    prepared.replace(lock)
                finally:
                    if prepared.exists():
                        remove_lock(prepared)
                return
        if time.monotonic() >= deadline:
            raise RuntimeError("Outra ferramenta está usando o acervo. Tente novamente após ela terminar.")
        time.sleep(0.05)


def inventory(vault):
    result = {}
    for directory, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in EXCLUDED and not (Path(directory) / d).is_symlink()]
        for name in files:
            file = Path(directory) / name
            rel = file.relative_to(vault).as_posix()
            if rel in MANAGED or file.is_symlink():
                continue
            result[str(file.resolve())] = signature(file)
    return result


def handle(event, vault, state, owner, pid):
    if event.get("hook_event_name") == "PostToolBatch":
        # Permissões recusadas depois do PreToolUse e ferramentas canceladas
        # podem não produzir PostToolUseFailure. O batch termina sua posse sem
        # considerar como escrita concluída o que não foi executado.
        for call in event.get("tool_calls") or []:
            handle({**event, **call, "hook_event_name": "PostToolUseFailure"}, vault, state, owner, pid)
        return None
    tool = event.get("tool_name", "")
    inp = event.get("tool_input") or {}
    broad = tool in SHELL_TOOLS or tool in {"Grep", "Glob"} or tool.startswith("mcp__")
    file = Path(inp.get("file_path") or inp.get("notebook_path") or vault).resolve()
    file_in_vault = file == vault or vault in file.parents
    if not broad and (tool not in FILE_TOOLS or not file_in_vault):
        return None
    if file_in_vault and file.relative_to(vault).as_posix() in MANAGED:
        raise RuntimeError("Esse histórico é gravado pelo Hub; use notas pessoais separadas.")
    tool_id = event.get("tool_use_id") or ""
    session = event.get("session_id") or owner
    ledger = state / "sessions" / (hashlib.sha256(session.encode()).hexdigest() + ".json")
    pre = event.get("hook_event_name") == "PreToolUse"
    if pre:
        if inp.get("run_in_background"):
            raise RuntimeError("A guarda exige que a ferramenta termine suas escritas antes de liberar o acervo.")
        acquire(state, owner, pid, tool_id)
        with control(state):
            lock = state / "active"
            data = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
            if data["owner"] != owner or data["tool"] != tool_id:
                raise RuntimeError("A ferramenta perdeu a posse da guarda antes de iniciar.")
            try:
                seen = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else {}
                current = inventory(vault) if broad else {str(file): signature(file)}
                if tool != "Read":
                    stale = [p for p in (seen if broad else current)
                             if p in seen and signature(Path(p)) != seen[p]]
                    if stale:
                        raise RuntimeError("Outra sessão mudou arquivos que você leu. Releia com Read: " + ", ".join(stale[:5]))
                    if tool in {"Write", "Edit", "MultiEdit", "NotebookEdit"} and current[str(file)] is not None and str(file) not in seen:
                        raise RuntimeError("Leia a versão atual com Read antes de alterar esse arquivo.")
                atomic_json(lock / "pending.json", {"ledger": str(ledger), "current": current})
            except Exception:
                _release(state, owner, tool_id)
                raise
    else:
        with control(state):
            lock = state / "active"
            try:
                data = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
            except FileNotFoundError:
                return None
            if data["owner"] != owner or data["tool"] != tool_id:
                return None
            try:
                pending = json.loads((lock / "pending.json").read_text(encoding="utf-8"))
                if event.get("hook_event_name") == "PostToolUse":
                    seen = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else {}
                    current = inventory(vault) if broad else {str(file): signature(file)}
                    seen.update(current)
                    for p in pending["current"]:
                        seen[p] = signature(Path(p))
                    atomic_json(ledger, seen)
            except FileNotFoundError:
                pass
            finally:
                _release(state, owner, tool_id)

    return None


def main():
    event = json.load(sys.stdin)
    try:
        handle(event, Path(os.environ["HUB_VAULT"]).resolve(), Path(os.environ["HUB_GUARD_STATE"]),
               os.environ["HUB_GUARD_OWNER"], int(os.environ["HUB_GUARD_PID"]))
    except Exception as error:
        if event.get("hook_event_name") == "PreToolUse":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                  "permissionDecision": "deny", "permissionDecisionReason": str(error)}}, ensure_ascii=False))
        else:
            print(str(error), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
