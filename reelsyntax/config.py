from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
import os
from pathlib import Path
import re
import sys
import tomllib
from typing import Any, Iterator

ACTIVE_CONFIG_FILE: ContextVar[Path | None] = ContextVar("active_config_file", default=None)
ACTIVE_PROJECT_DIR: ContextVar[Path | None] = ContextVar("active_project_dir", default=None)

CONFIG_FILENAME = "reelsyntax.toml"
USER_CONFIG_FILENAME = "config.toml"
PROVIDER_NAMES = frozenset({"offline_rules", "ollama", "openai_compat", "mcp_host"})
PROFILE_NAMES = frozenset({"draft", "production", "hero"})
LANG_TAG_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
ENDPOINT_RE = re.compile(r"^https?://[^\s\x00-\x1f]+$")
MAX_CONFIG_BYTES = 131_072


@dataclass(frozen=True)
class GeneralConfig:
    ui_lang: str = "auto"
    video_lang: str = "auto"
    allow_network: bool = False
    attribution: bool = False


@dataclass(frozen=True)
class ProviderConfig:
    name: str = "offline_rules"
    model: str = ""
    endpoint: str = ""
    timeout_sec: int = 60
    max_repairs: int = 3


@dataclass(frozen=True)
class PathsConfig:
    ffmpeg: str = ""
    ffprobe: str = ""
    blender: str = ""


@dataclass(frozen=True)
class RenderConfig:
    default_profile: str = "draft"
    cache_budget_mib: int = 0
    reduced_motion: bool = False
    timeout_sec: int = 180


@dataclass(frozen=True)
class ResolvedConfig:
    config_version: int
    general: GeneralConfig
    provider: ProviderConfig
    paths: PathsConfig
    render: RenderConfig
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sources"] = list(self.sources)
        return payload


def _check_keys(mapping: Any, allowed: set[str], label: str) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        raise ValueError(f"{label}: expected a TOML table")
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ValueError(f"{label}: unknown configuration keys {unknown}")
    return mapping


def _check_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label}: expected boolean")
    return value


def _check_int(value: Any, low: int, high: int, label: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label}: expected integer in [{low}, {high}]")
    return value


def _check_lang(value: Any, label: str) -> str:
    if not isinstance(value, str) or (value != "auto" and not LANG_TAG_RE.fullmatch(value)):
        raise ValueError(f"{label}: expected 'auto' or a BCP-47 language tag")
    return value


def _check_executable_path(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label}: expected string path")
    if value == "":
        return ""
    candidate = Path(value).expanduser()
    if not candidate.is_absolute() or not candidate.is_file():
        raise ValueError(f"{label}: must be an existing absolute file path")
    if os.name != "nt" and not os.access(candidate, os.X_OK):
        raise ValueError(f"{label}: file is not executable")
    return str(candidate)


def validate_config_data(raw: dict[str, Any], source_label: str = CONFIG_FILENAME) -> dict[str, Any]:
    top = _check_keys(raw, {"config_version", "general", "provider", "paths", "render"}, source_label)
    version = top.get("config_version", 1)
    if type(version) is not int or version != 1:
        raise ValueError(f"{source_label}.config_version: only version 1 is supported")

    normalized: dict[str, Any] = {"config_version": 1}

    if "general" in top:
        sec = _check_keys(top["general"], {"ui_lang", "video_lang", "allow_network", "attribution"}, f"{source_label}.general")
        gen: dict[str, Any] = {}
        if "ui_lang" in sec:
            gen["ui_lang"] = _check_lang(sec["ui_lang"], f"{source_label}.general.ui_lang")
        if "video_lang" in sec:
            gen["video_lang"] = _check_lang(sec["video_lang"], f"{source_label}.general.video_lang")
        if "allow_network" in sec:
            gen["allow_network"] = _check_bool(sec["allow_network"], f"{source_label}.general.allow_network")
        if "attribution" in sec:
            gen["attribution"] = _check_bool(sec["attribution"], f"{source_label}.general.attribution")
        normalized["general"] = gen

    if "provider" in top:
        sec = _check_keys(
            top["provider"],
            {"name", "model", "endpoint", "timeout_sec", "max_repairs"},
            f"{source_label}.provider",
        )
        prov: dict[str, Any] = {}
        if "name" in sec:
            if not isinstance(sec["name"], str) or sec["name"] not in PROVIDER_NAMES:
                raise ValueError(f"{source_label}.provider.name: unsupported provider")
            prov["name"] = sec["name"]
        if "model" in sec:
            if not isinstance(sec["model"], str) or len(sec["model"]) > 128 or any(ord(c) < 32 for c in sec["model"]):
                raise ValueError(f"{source_label}.provider.model: invalid model identifier")
            prov["model"] = sec["model"]
        if "endpoint" in sec:
            ep = sec["endpoint"]
            if not isinstance(ep, str) or len(ep) > 512 or (ep != "" and not ENDPOINT_RE.fullmatch(ep)):
                raise ValueError(f"{source_label}.provider.endpoint: expected http(s) URL or empty string")
            prov["endpoint"] = ep
        if "timeout_sec" in sec:
            prov["timeout_sec"] = _check_int(sec["timeout_sec"], 1, 600, f"{source_label}.provider.timeout_sec")
        if "max_repairs" in sec:
            prov["max_repairs"] = _check_int(sec["max_repairs"], 0, 3, f"{source_label}.provider.max_repairs")
        normalized["provider"] = prov

    if "paths" in top:
        sec = _check_keys(top["paths"], {"ffmpeg", "ffprobe", "blender"}, f"{source_label}.paths")
        paths_out: dict[str, Any] = {}
        for key in ("ffmpeg", "ffprobe", "blender"):
            if key in sec:
                paths_out[key] = _check_executable_path(sec[key], f"{source_label}.paths.{key}")
        normalized["paths"] = paths_out

    if "render" in top:
        sec = _check_keys(
            top["render"],
            {"default_profile", "cache_budget_mib", "reduced_motion", "timeout_sec"},
            f"{source_label}.render",
        )
        rend: dict[str, Any] = {}
        if "default_profile" in sec:
            if not isinstance(sec["default_profile"], str) or sec["default_profile"] not in PROFILE_NAMES:
                raise ValueError(f"{source_label}.render.default_profile: expected draft, production, or hero")
            rend["default_profile"] = sec["default_profile"]
        if "cache_budget_mib" in sec:
            rend["cache_budget_mib"] = _check_int(sec["cache_budget_mib"], 0, 1_048_576, f"{source_label}.render.cache_budget_mib")
        if "reduced_motion" in sec:
            rend["reduced_motion"] = _check_bool(sec["reduced_motion"], f"{source_label}.render.reduced_motion")
        if "timeout_sec" in sec:
            rend["timeout_sec"] = _check_int(sec["timeout_sec"], 1, 3600, f"{source_label}.render.timeout_sec")
        normalized["render"] = rend

    return normalized


def read_toml_file(path: Path) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink():
        raise ValueError(f"Configuration file cannot be a symbolic link: {target}")
    if not target.is_file():
        raise ValueError(f"Configuration file does not exist: {target}")
    if target.stat().st_size > MAX_CONFIG_BYTES:
        raise ValueError(f"Configuration file exceeds {MAX_CONFIG_BYTES} bytes: {target}")
    try:
        raw = tomllib.loads(target.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Invalid TOML in {target}: {error}") from error
    return validate_config_data(raw, str(target))


def user_config_path(environ: dict[str, str] | None = None, platform_name: str | None = None) -> Path:
    env = os.environ if environ is None else environ
    plat = sys.platform if platform_name is None else platform_name
    explicit = env.get("REELSYNTAX_USER_CONFIG")
    if explicit:
        return Path(explicit).expanduser()
    if plat == "win32":
        appdata = env.get("APPDATA")
        base = Path(appdata) if appdata else (Path.home() / "AppData/Roaming")
        return base / "reelsyntax" / USER_CONFIG_FILENAME
    xdg = env.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / "reelsyntax" / USER_CONFIG_FILENAME
    if plat == "darwin":
        posix_candidate = Path.home() / ".config/reelsyntax" / USER_CONFIG_FILENAME
        if posix_candidate.is_file():
            return posix_candidate
        return Path.home() / "Library/Application Support/reelsyntax" / USER_CONFIG_FILENAME
    return Path.home() / ".config/reelsyntax" / USER_CONFIG_FILENAME


def discover_project_config(project: Path | str | None = None, cwd: Path | None = None) -> Path | None:
    target_project = Path(project) if project is not None else ACTIVE_PROJECT_DIR.get()
    if target_project is not None:
        p = target_project if target_project.is_dir() else target_project.parent
        candidate = p / CONFIG_FILENAME
        if candidate.is_file():
            return candidate.resolve()
    work = Path.cwd() if cwd is None else cwd
    local = work / CONFIG_FILENAME
    if local.is_file():
        return local.resolve()
    return None


def _parse_env_bool(raw: str, name: str) -> bool:
    low = raw.strip().lower()
    if low in {"1", "true", "yes", "on"}:
        return True
    if low in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name}: expected boolean value (1/0, true/false)")


def _apply_env_overrides(merged: dict[str, dict[str, Any]], env: dict[str, str]) -> bool:
    applied = False
    str_mappings = (
        ("REELSYNTAX_UI_LANG", "general", "ui_lang", lambda v: _check_lang(v, "REELSYNTAX_UI_LANG")),
        ("REELSYNTAX_VIDEO_LANG", "general", "video_lang", lambda v: _check_lang(v, "REELSYNTAX_VIDEO_LANG")),
        ("REELSYNTAX_PROVIDER", "provider", "name", lambda v: v if v in PROVIDER_NAMES else (_ for _ in ()).throw(ValueError("REELSYNTAX_PROVIDER: unsupported provider"))),
        ("REELSYNTAX_MODEL", "provider", "model", lambda v: v),
        ("REELSYNTAX_ENDPOINT", "provider", "endpoint", lambda v: v if (v == "" or ENDPOINT_RE.fullmatch(v)) else (_ for _ in ()).throw(ValueError("REELSYNTAX_ENDPOINT: expected http(s) URL"))),
        ("REELSYNTAX_FFMPEG", "paths", "ffmpeg", lambda v: _check_executable_path(v, "REELSYNTAX_FFMPEG")),
        ("REELSYNTAX_FFPROBE", "paths", "ffprobe", lambda v: _check_executable_path(v, "REELSYNTAX_FFPROBE")),
        ("REELSYNTAX_BLENDER", "paths", "blender", lambda v: _check_executable_path(v, "REELSYNTAX_BLENDER")),
        ("REELSYNTAX_DEFAULT_PROFILE", "render", "default_profile", lambda v: v if v in PROFILE_NAMES else (_ for _ in ()).throw(ValueError("REELSYNTAX_DEFAULT_PROFILE: invalid profile"))),
    )
    for env_key, section, field, validator in str_mappings:
        raw_val = env.get(env_key)
        if raw_val is not None and raw_val != "":
            merged[section][field] = validator(raw_val)
            applied = True

    bool_mappings = (
        ("REELSYNTAX_ALLOW_NETWORK", "general", "allow_network"),
        ("REELSYNTAX_ATTRIBUTION", "general", "attribution"),
        ("REELSYNTAX_REDUCED_MOTION", "render", "reduced_motion"),
    )
    for env_key, section, field in bool_mappings:
        raw_val = env.get(env_key)
        if raw_val is not None and raw_val != "":
            merged[section][field] = _parse_env_bool(raw_val, env_key)
            applied = True

    int_mappings = (
        ("REELSYNTAX_PROVIDER_TIMEOUT", "provider", "timeout_sec", 1, 600),
        ("REELSYNTAX_MAX_REPAIRS", "provider", "max_repairs", 0, 3),
        ("REELSYNTAX_CACHE_BUDGET_MIB", "render", "cache_budget_mib", 0, 1_048_576),
        ("REELSYNTAX_RENDER_TIMEOUT", "render", "timeout_sec", 1, 3600),
    )
    for env_key, section, field, low, high in int_mappings:
        raw_val = env.get(env_key)
        if raw_val is not None and raw_val != "":
            try:
                parsed = int(raw_val)
            except ValueError as error:
                raise ValueError(f"{env_key}: expected integer") from error
            merged[section][field] = _check_int(parsed, low, high, env_key)
            applied = True
    return applied


def load_config(
    config_file: Path | str | None = None,
    project: Path | str | None = None,
    environ: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> ResolvedConfig:
    env = os.environ if environ is None else environ
    merged: dict[str, dict[str, Any]] = {
        "general": asdict(GeneralConfig()),
        "provider": asdict(ProviderConfig()),
        "paths": asdict(PathsConfig()),
        "render": asdict(RenderConfig()),
    }
    sources: list[str] = []

    u_path = user_config_path(env)
    if u_path.is_file():
        u_data = read_toml_file(u_path)
        for sec in ("general", "provider", "paths", "render"):
            merged[sec].update(u_data.get(sec, {}))
        sources.append(str(u_path))

    explicit = Path(config_file) if config_file is not None else ACTIVE_CONFIG_FILE.get()
    if explicit is None and env.get("REELSYNTAX_CONFIG"):
        explicit = Path(env["REELSYNTAX_CONFIG"]).expanduser()

    if explicit is not None:
        exp_data = read_toml_file(explicit)
        for sec in ("general", "provider", "paths", "render"):
            merged[sec].update(exp_data.get(sec, {}))
        sources.append(str(explicit.resolve()))
    else:
        p_path = discover_project_config(project=project, cwd=cwd)
        if p_path is not None and str(p_path) not in sources:
            p_data = read_toml_file(p_path)
            for sec in ("general", "provider", "paths", "render"):
                merged[sec].update(p_data.get(sec, {}))
            sources.append(str(p_path))

    if _apply_env_overrides(merged, env):
        sources.append("env")

    return ResolvedConfig(
        config_version=1,
        general=GeneralConfig(**merged["general"]),
        provider=ProviderConfig(**merged["provider"]),
        paths=PathsConfig(**merged["paths"]),
        render=RenderConfig(**merged["render"]),
        sources=tuple(sources),
    )


@contextmanager
def config_context(config_file: Path | str | None = None, project: Path | str | None = None) -> Iterator[None]:
    tok_cfg = ACTIVE_CONFIG_FILE.set(Path(config_file).expanduser() if config_file is not None else None)
    tok_proj = ACTIVE_PROJECT_DIR.set(Path(project) if project is not None else None)
    try:
        yield
    finally:
        ACTIVE_PROJECT_DIR.reset(tok_proj)
        ACTIVE_CONFIG_FILE.reset(tok_cfg)


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    raise TypeError(f"Unsupported TOML scalar: {type(value)!r}")


def render_starter_toml() -> str:
    cfg = ResolvedConfig(
        config_version=1,
        general=GeneralConfig(),
        provider=ProviderConfig(),
        paths=PathsConfig(),
        render=RenderConfig(),
        sources=(),
    )
    lines = [f"config_version = {cfg.config_version}", ""]
    for section_name, section_obj in (
        ("general", cfg.general),
        ("provider", cfg.provider),
        ("paths", cfg.paths),
        ("render", cfg.render),
    ):
        lines.append(f"[{section_name}]")
        for key, value in asdict(section_obj).items():
            lines.append(f"{key} = {_toml_scalar(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_starter_config(target: Path | None = None, *, user_scope: bool = False, force: bool = False) -> Path:
    if user_scope:
        dest = user_config_path()
    elif target is None:
        dest = Path.cwd() / CONFIG_FILENAME
    elif target.suffix == ".toml":
        dest = target
    else:
        dest = target / CONFIG_FILENAME
    dest = dest.expanduser().absolute()
    if dest.is_symlink():
        raise ValueError("Refusing to write configuration through a symbolic link")
    if dest.exists() and not force:
        raise ValueError(f"Configuration file already exists: {dest} (pass --force to overwrite)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = render_starter_toml()
    validate_config_data(tomllib.loads(content), str(dest))
    dest.write_text(content, encoding="utf-8")
    return dest
