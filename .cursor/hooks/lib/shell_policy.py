"""Deterministic shell command segmentation and policy evaluation.

Exports:

- ShellPolicyDecision       — frozen dataclass with: allowed, reason,
                              segments, trace
- REASON_*                  — stable string constants for decision reasons
- segment_shell_command()   — split a command on &&, ||, ;, |, and newlines
                              (quote-aware)
- extract_shell_c_payload() — extract the inner command string from
                              sh/bash/zsh -c '...' invocations
- unwrap_wrappers()         — strip leading wrappers (sudo, doas, env,
                              command, nice, nohup, timeout)
- evaluate_shell_policy()   — evaluate a command against a shell policy
                              mapping; returns ShellPolicyDecision
- analyze_command_segments() — expose segmentation only (test helper)

Evaluation Flow (evaluate_shell_policy):

1. Read policy booleans: deny_rm_recursive_force, deny_git_push_main
2. Segment the command at &&, ||, ;, |, and newlines
3. For each segment:
   a. Tokenize via shlex (deny on parse error)
   b. Unwrap leading wrappers (sudo, env, etc.)
   c. Check for rm with both recursive and force flags
   d. Check for git push targeting the main branch
   e. If the segment is sh/bash/zsh -c '...', recurse into the inner
      command (up to max_nest depth, default 32)
4. Return ShellPolicyDecision with allowed, reason, and trace

Deny Reasons:

- deny_rm_recursive_force — rm with both -r/-R and -f flags
- deny_git_push_main      — git push targeting the main branch
- deny_nested_shell_depth  — sh -c nesting exceeds max_nest limit
- deny_shell_parse_error   — shlex could not tokenize a segment
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any, Iterable, Mapping, Sequence

# Reason codes emitted on deny (stable strings for auditing / tests).
REASON_ALLOW = "allow"
REASON_DENY_RM_RECURSIVE_FORCE = "deny_rm_recursive_force"
REASON_DENY_GIT_PUSH_MAIN = "deny_git_push_main"
REASON_DENY_NESTED_SHELL_DEPTH = "deny_nested_shell_depth"
REASON_DENY_SHELL_PARSE_ERROR = "deny_shell_parse_error"

_DEFAULT_MAX_NEST = 32
_DEFAULT_MAX_UNWRAP = 64


@dataclass(frozen=True)
class ShellPolicyDecision:
    """
    Result of evaluating one logical command line for shell policy.

    Fields:
    - ``allowed``: whether the shell command should be permitted.
    - ``reason``: stable machine-readable outcome (see ``REASON_*`` constants).
    - ``segments``: top-level split of the original *command* at ``&&``, ``||``, ``;``,
      newline, and ``|`` (quote-aware); unchanged when denial comes from a nested ``-c`` body.
    - ``trace``: ordered diagnostic tags (reason-specific tail, truncation markers, etc.).
    """

    allowed: bool
    reason: str
    segments: tuple[str, ...]
    trace: tuple[str, ...]


def segment_shell_command(cmd: str) -> list[str]:
    """
    Split *cmd* on ``&&``, ``||``, ``;``, newlines, and ``|`` outside quotes.

    Quotes: ``'...'``, ``"..."`` (with ``\\`` escapes only recognized inside double quotes).

    Example: ``"echo hello && rm -rf /"`` → ``["echo hello", "rm -rf /"]``
    """
    if not cmd:
        return []
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(cmd)
    in_single = False
    in_double = False
    escape = False

    def flush() -> None:
        nonlocal buf
        piece = "".join(buf).strip()
        buf = []
        if piece:
            parts.append(piece)

    while i < n:
        ch = cmd[i]
        if escape:
            buf.append(ch)
            escape = False
            i += 1
            continue
        if in_single:
            buf.append(ch)
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            if ch == "\\":
                escape = True
                buf.append(ch)
                i += 1
                continue
            buf.append(ch)
            if ch == '"':
                in_double = False
            i += 1
            continue

        if ch == "\\":
            escape = True
            buf.append(ch)
            i += 1
            continue
        if ch == "'":
            in_single = True
            buf.append(ch)
            i += 1
            continue
        if ch == '"':
            in_double = True
            buf.append(ch)
            i += 1
            continue

        if cmd.startswith("&&", i):
            flush()
            i += 2
            continue
        if cmd.startswith("||", i):
            flush()
            i += 2
            continue
        if ch == ";":
            flush()
            i += 1
            continue
        if ch == "|":
            flush()
            i += 1
            continue
        if ch in "\r\n":
            flush()
            if ch == "\r" and i + 1 < n and cmd[i + 1] == "\n":
                i += 2
            else:
                i += 1
            continue

        buf.append(ch)
        i += 1

    flush()
    return parts


def _basename(pathish: str) -> str:
    return PurePath(pathish).name


def _shell_grouped_command_basename(token: str) -> str:
    """
    Basename of *token* after stripping only **outer** grouping punctuation ``(``, ``)``, ``{``, ``}``.

    Covers shlex tokens like ``(rm`` or ``rm)`` from subshell/grouping syntax without altering
    interior spelling (deterministic, bounded).
    """
    t = token.strip()
    limit = max(len(t), 1) + 8
    for _ in range(limit):
        before = t
        while t and t[0] in "({":
            t = t[1:].lstrip()
        while t and t[-1] in ")}":
            t = t[:-1].rstrip()
        if t == before:
            break
    return _basename(t) if t else ""


def _shell_names() -> frozenset[str]:
    return frozenset({"sh", "bash", "zsh"})


def extract_shell_c_payload(tokens: Sequence[str]) -> str | None:
    """
    If *tokens* is a ``sh``/``bash``/``zsh`` invocation with ``-c`` / ``--command``, return inner command string.

    Handles merged short options like ``bash -lc 'cmd'``.
    """
    if len(tokens) < 2:
        return None
    if _basename(tokens[0]) not in _shell_names():
        return None
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t == "-c":
            if i + 1 < len(tokens):
                return tokens[i + 1]
            return None
        if t == "--command":
            if i + 1 < len(tokens):
                return tokens[i + 1]
            return None
        if t.startswith("--command="):
            return t.split("=", 1)[1]
        if t.startswith("-") and t != "--":
            body = t[1:]
            if "c" in body:
                if i + 1 < len(tokens):
                    return tokens[i + 1]
                return None
        i += 1
    return None


def unwrap_wrappers(
    tokens: list[str],
    wrappers: Iterable[str],
    *,
    max_steps: int = _DEFAULT_MAX_UNWRAP,
) -> list[str]:
    """
    Strip leading wrappers from *tokens* (``sudo``, ``doas``, ``env``, ``command``, ``nice``, ``nohup``, ``timeout``).

    Wrapper set is typically ``policy['shell']['deny_wrappers']`` — the same keys are used for unwrapping
    so policy edits stay coherent.

    If the leading executable basename is listed in *wrappers* but is not a built-in strip rule
    (e.g. a future/typo name), it is left in place: the command is treated as opaque rather than guessed.
    """
    wrapper_set = {w.strip() for w in wrappers if isinstance(w, str) and w.strip()}
    cur = list(tokens)
    for _ in range(max_steps):
        if not cur:
            return cur
        base = _basename(cur[0])
        if base not in wrapper_set:
            return cur
        if base in ("sudo", "doas"):
            nxt = _strip_sudo_like(cur)
        elif base == "env":
            nxt = _strip_env(cur)
        elif base == "command":
            nxt = cur[1:] if len(cur) > 1 else []
        elif base == "nice":
            nxt = _strip_nice(cur)
        elif base == "nohup":
            nxt = cur[1:] if len(cur) > 1 else []
        elif base == "timeout":
            nxt = _strip_timeout(cur)
        else:
            # Listed in policy but no dedicated unwrapper — do not strip unknown executables.
            return cur
        if nxt == cur:
            return cur
        cur = nxt
    return cur


def _strip_sudo_like(tokens: Sequence[str]) -> list[str]:
    j = 1
    n = len(tokens)
    while j < n:
        t = tokens[j]
        if not t.startswith("-") or t == "-":
            break
        if t in ("-u", "-g", "-p", "-U", "-D", "-h", "-R") and j + 1 < n:
            j += 2
            continue
        j += 1
    return list(tokens[j:])


def _strip_env(tokens: Sequence[str]) -> list[str]:
    j = 1
    n = len(tokens)
    assign = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")
    while j < n:
        t = tokens[j]
        if t == "-":
            j += 1
            continue
        if t.startswith("-") and t != "-":
            j += 1
            continue
        if assign.match(t):
            j += 1
            continue
        break
    return list(tokens[j:])


def _strip_nice(tokens: Sequence[str]) -> list[str]:
    j = 1
    n = len(tokens)
    while j < n:
        t = tokens[j]
        if not t.startswith("-") or t == "-":
            break
        if t in ("-n", "--adjustment") and j + 1 < n:
            j += 2
            continue
        if re.fullmatch(r"-\d+", t):
            j += 1
            continue
        j += 1
    return list(tokens[j:])


def _strip_timeout(tokens: Sequence[str]) -> list[str]:
    """GNU ``timeout``-style option skipping + one duration token."""
    _TIMEOUT_BOOL_FLAGS = frozenset({"--foreground", "--preserve-status"})
    _TIMEOUT_ARG_FLAGS = frozenset({"-k", "--kill-after"})
    j = 1
    n = len(tokens)
    while j < n:
        t = tokens[j]
        if not t.startswith("-") or t == "-":
            break
        if t in _TIMEOUT_BOOL_FLAGS:
            j += 1
            continue
        if t in _TIMEOUT_ARG_FLAGS:
            if "=" in t:
                j += 1
            elif j + 1 < n:
                j += 2
            else:
                j += 1
            continue
        j += 1
    if j < n and re.fullmatch(r"[\d.]+[smhd]?", tokens[j]):
        j += 1
    return list(tokens[j:])


def _split_shlex(line: str) -> list[str]:
    """Tokenize one shell segment; raises ``ValueError`` on unterminated quotes / invalid escapes."""
    return shlex.split(line, posix=True)


def _shlex_error_snippet(seg: str, *, max_len: int = 120) -> str:
    s = seg.strip().replace("\n", "\\n")
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def _token_has_rm_recursive_and_force(tok: str) -> bool:
    if not tok.startswith("-") or tok.startswith("--"):
        return False
    flags = tok[1:]
    has_r = any(c in flags for c in "rR")
    has_f = "f" in flags
    return has_r and has_f


def _rm_argv_slice(tokens: Sequence[str], rm_index: int) -> Sequence[str]:
    """Arguments belonging to the ``rm`` at *rm_index* only (split before a subsequent ``rm`` token)."""
    end = len(tokens)
    for k in range(rm_index + 1, len(tokens)):
        if _shell_grouped_command_basename(tokens[k]) == "rm":
            end = k
            break
    return tokens[rm_index + 1 : end]


def _argv_has_recursive_and_force(argv: Sequence[str]) -> bool:
    """True if *argv* (one command's tokens after the executable) includes both recursive and force rm flags."""
    recursive = False
    force = False
    for arg in argv:
        if arg in ("--recursive", "-r", "-R"):
            recursive = True
        elif arg == "--force" or arg == "-f":
            force = True
        elif arg.startswith("--recursive="):
            recursive = True
        elif arg.startswith("--force="):
            force = True
        elif arg.startswith("-") and not arg.startswith("--"):
            body = arg[1:]
            if any(c in body for c in "rR"):
                recursive = True
            if "f" in body:
                force = True
            if _token_has_rm_recursive_and_force(arg):
                recursive = True
                force = True
    return recursive and force


def _scan_rm_rf(tokens: Sequence[str]) -> bool:
    """Detect any ``rm`` invocation whose own argv (scoped per ``rm`` word) has recursive + force."""
    for i, tok in enumerate(tokens):
        if _shell_grouped_command_basename(tok) != "rm":
            continue
        argv = _rm_argv_slice(tokens, i)
        if _argv_has_recursive_and_force(argv):
            return True
    return False


def _arg_targets_main(arg: str, patterns: Sequence[str]) -> bool:
    """Conservative match for ``main`` ref / refspec without ``mains``-style substring false positives."""
    if arg == "main":
        return True
    for pat in patterns:
        if not pat or pat == "main":
            continue
        if arg == pat:
            return True
    if ":" in arg:
        for seg in arg.split(":"):
            if seg == "main":
                return True
            for pat in patterns:
                if pat and pat != "main" and seg == pat:
                    return True
    if arg.endswith("/main") and len(arg) > len("/main"):
        return True
    return False


def _git_push_targets_main(tokens: Sequence[str], patterns: Sequence[str]) -> bool:
    """True if this token stream is ``git push`` with args referencing ``main`` per *patterns*."""
    if len(tokens) < 3:
        return False
    if _basename(tokens[0]) != "git" or tokens[1] != "push":
        return False
    pats = [p.strip() for p in patterns if isinstance(p, str) and p.strip()]
    for arg in tokens[2:]:
        if _arg_targets_main(arg, pats):
            return True
    return False


def _shell_policy_bool(mapping: Mapping[str, Any], key: str, *, default: bool) -> bool:
    """Return *default* if *key* is absent; if present, only ``bool`` values are honored (no truthiness coercion)."""
    if key not in mapping:
        return default
    v = mapping[key]
    if isinstance(v, bool):
        return v
    return default


def _evaluate_tokens(
    tokens: list[str],
    *,
    deny_rm: bool,
    deny_git_main: bool,
    wrappers: Sequence[str],
    main_patterns: Sequence[str],
) -> tuple[str, tuple[str, ...]] | None:
    """Return ``(reason, trace)`` when denied, else ``None``."""
    eff = unwrap_wrappers(list(tokens), wrappers)
    if deny_rm and _scan_rm_rf(eff):
        return REASON_DENY_RM_RECURSIVE_FORCE, ("rm_recursive_force",)
    if deny_git_main and _git_push_targets_main(eff, main_patterns):
        return REASON_DENY_GIT_PUSH_MAIN, ("git_push_main",)
    return None


def evaluate_shell_policy(
    command: str,
    shell_policy: Mapping[str, Any],
    *,
    max_nest: int = _DEFAULT_MAX_NEST,
) -> ShellPolicyDecision:
    """
    Evaluate *command* using validated ``policy['shell']`` mapping.

    *shell_policy* should supply strict ``bool`` values for ``deny_rm_recursive_force`` and
    ``deny_git_push_main`` (non-bool values fall back to ``True``); plus lists ``deny_wrappers``
    and ``main_ref_patterns``.
    """
    deny_rm = _shell_policy_bool(shell_policy, "deny_rm_recursive_force", default=True)
    deny_git_main = _shell_policy_bool(shell_policy, "deny_git_push_main", default=True)
    wrappers_raw = shell_policy.get("deny_wrappers", [])
    wrappers = [w for w in wrappers_raw if isinstance(w, str)]
    main_raw = shell_policy.get("main_ref_patterns", [])
    main_patterns = [m for m in main_raw if isinstance(m, str)]

    top_segments = tuple(segment_shell_command(command))

    if not command.strip():
        return ShellPolicyDecision(True, REASON_ALLOW, top_segments, ("empty_input",))

    def scan_block(line: str, depth: int) -> tuple[str, tuple[str, ...]] | None:
        if depth > max_nest:
            return REASON_DENY_NESTED_SHELL_DEPTH, ("nest_limit",)
        prefix: tuple[str, ...] = (f"shell_c_depth={depth}",) if depth else ()
        for seg in segment_shell_command(line):
            seg_st = seg.strip()
            try:
                toks = _split_shlex(seg_st)
            except ValueError:
                snip = _shlex_error_snippet(seg_st)
                return REASON_DENY_SHELL_PARSE_ERROR, prefix + (
                    "shlex_error",
                    f"segment={snip!r}",
                )
            if not toks:
                continue
            hit = _evaluate_tokens(
                toks,
                deny_rm=deny_rm,
                deny_git_main=deny_git_main,
                wrappers=wrappers,
                main_patterns=main_patterns,
            )
            if hit is not None:
                reason, local_trace = hit
                return reason, prefix + local_trace
            inner = extract_shell_c_payload(toks)
            if inner:
                sub = scan_block(inner, depth + 1)
                if sub is not None:
                    reason, sub_trace = sub
                    return reason, prefix + ("nested_shell_c",) + sub_trace
        return None

    denied = scan_block(command, 0)
    if denied is not None:
        reason, tr = denied
        return ShellPolicyDecision(
            allowed=False,
            reason=reason,
            segments=top_segments,
            trace=tr,
        )
    return ShellPolicyDecision(True, REASON_ALLOW, top_segments, ("ok",))


def analyze_command_segments(command: str) -> tuple[str, ...]:
    """Expose segmentation only (handy for table-driven tests)."""
    return tuple(segment_shell_command(command))
