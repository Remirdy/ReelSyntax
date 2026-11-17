import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STAGES = {"plan", "ingest", "build", "edit", "render", "review", "export", "operate"}
STATUSES = {"guidance", "production-guidance", "implemented", "validated", "deprecated", "blocked"}
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MAX_SKILL_BYTES = 256_000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path, max_bytes=8_000_000):
    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise ValueError(f"JSON file exceeds {max_bytes} bytes: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def contained_path(root, relative, must_exist=True):
    root = Path(root).resolve()
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("Expected a nonempty portable relative path")
    parts = Path(relative).parts
    if Path(relative).is_absolute() or any(x in {"..", "."} for x in parts) or ":" in relative:
        raise ValueError("Path must stay inside its authorized root")
    current = root
    for part in parts:
        current /= part
        if current.is_symlink():
            raise ValueError("Symbolic links are not allowed in managed paths")
    if not current.resolve().is_relative_to(root):
        raise ValueError("Path escapes its authorized root")
    if must_exist and not current.is_file():
        raise ValueError(f"Missing file: {relative}")
    return current


def skill_path(row, root=ROOT):
    path = contained_path(root, row["path"])
    expected = Path("library") / row["category"] / row["id"] / "SKILL.md"
    if Path(row["path"]) != expected:
        raise ValueError(f"Invalid skill path: {row['id']}")
    return path


def string_list(value, label):
    if not isinstance(value, list) or len(value) > 128 or any(not isinstance(x, str) or not x or len(x) > 256 for x in value):
        raise ValueError(f"Invalid string list: {label}")
    if len(value) != len(set(value)):
        raise ValueError(f"Duplicate values: {label}")


def validate_rows(rows, root=ROOT, verify_files=True):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100_000:
        raise ValueError("Registry must contain 1–100000 skills")
    known = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid registry row")
        for key in ("id", "category", "stage", "description", "path", "status", "version"):
            if not isinstance(row.get(key), str) or not row[key]:
                raise ValueError(f"Missing/invalid registry field: {key}")
        if not ID.fullmatch(row["id"]) or len(row["id"]) > 64 or not ID.fullmatch(row["category"]):
            raise ValueError("Invalid registry identifier")
        if row["id"] in known:
            raise ValueError(f"Duplicate skill ID: {row['id']}")
        if row["stage"] not in STAGES or row["status"] not in STATUSES or len(row["description"]) > 1024:
            raise ValueError(f"Invalid metadata: {row['id']}")
        if type(row.get("estimated_words")) is not int or not 1 <= row["estimated_words"] <= MAX_SKILL_BYTES:
            raise ValueError("Invalid word estimate")
        for key in ("aliases", "requires", "dependencies", "conflicts", "asset_types", "recommended_next", "resources"):
            string_list(row.get(key, []), key)
        if "sha256" in row and (not isinstance(row['sha256'], str) or not re.fullmatch(r"[a-f0-9]{64}", row["sha256"])):
            raise ValueError("Invalid skill digest")
        if 'resource_sha256' in row:
            hashes = row['resource_sha256']
            if not isinstance(hashes, dict) or set(hashes) != set(row.get('resources', [])) or any(not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value) for value in hashes.values()):
                raise ValueError('Invalid resource digest map')
        if "estimated_tokens" in row and (type(row["estimated_tokens"]) is not int or row["estimated_tokens"] < 1):
            raise ValueError("Invalid token estimate")
        if verify_files:
            base = skill_path(row, root).parent
            for relative in row.get("resources", []):
                resource = contained_path(root, relative)
                if base not in resource.parents:
                    raise ValueError("Resource must belong to its skill directory")
        known[row["id"]] = row
    visiting, visited = set(), set()

    def visit(sid):
        if len(visiting) >= 64:
            raise ValueError('Skill dependency depth exceeds the 64-skill safety limit')
        if sid in visiting:
            raise ValueError(f"Skill dependency cycle: {sid}")
        if sid in visited:
            return
        visiting.add(sid)
        row = known[sid]
        for key in ("dependencies", "conflicts", "recommended_next"):
            for target in row.get(key, []):
                if target not in known or target == sid:
                    raise ValueError(f"Invalid {key} target for {sid}: {target}")
        for target in row.get("dependencies", []):
            visit(target)
        visiting.remove(sid)
        visited.add(sid)

    for sid in known:
        visit(sid)
    hashes = {}
    for row in rows:
        if row.get("body_sha256"):
            previous = hashes.setdefault(row["body_sha256"], row["id"])
            if previous != row["id"]:
                raise ValueError(f"Duplicate instruction bodies: {previous}, {row['id']}")
    return rows


def frontmatter(text):
    parts = re.split(r"(?m)^---\r?\n", text, maxsplit=2)
    if len(parts) != 3 or parts[0] != "":
        raise ValueError("Expected scalar YAML frontmatter")
    fields = {}
    for line in parts[1].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.strip().partition(":")
        if not separator or key in fields:
            raise ValueError("Invalid or duplicate frontmatter key")
        value = value.strip()
        fields[key] = json.loads(value) if value.startswith('"') else value
        if not isinstance(fields[key], str):
            raise ValueError("Only scalar string metadata is supported")
    return fields, parts[2]


def inventory(root=ROOT):
    root = Path(root)
    files = sorted((root / "library").glob("*/*/SKILL.md"))
    for folder in ['references', 'scripts', 'assets']:
        files.extend(sorted(p for p in (root / 'library').glob(f'*/*/{folder}/**/*') if p.is_file() or p.is_symlink()))
    relations = root / "registry/relations.json"
    if relations.exists():
        files.append(relations)
    result = []
    for file in files:
        relative = file.relative_to(root).as_posix()
        checked = contained_path(root, relative)
        stat = checked.stat()
        result.append([relative, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns])
    return result


def rebuild(root=ROOT):
    root = Path(root)
    snapshot = inventory(root)
    relations_path = root / "registry/relations.json"
    relations = read_json(relations_path) if relations_path.exists() else {}
    if not isinstance(relations, dict):
        raise ValueError("Relations must be an object keyed by skill ID")
    rows = []
    for relative, *_ in snapshot:
        if len(Path(relative).parts) != 4 or not relative.startswith("library/") or not relative.endswith('/SKILL.md'):
            continue
        path = contained_path(root, relative)
        raw = path.read_bytes()
        if len(raw) > MAX_SKILL_BYTES:
            raise ValueError(f"Skill exceeds size limit: {relative}")
        fields, body = frontmatter(raw.decode("utf-8"))
        if fields.get("name") != path.parent.name or fields.get("category") != path.parent.parent.name:
            raise ValueError(f"Skill metadata does not match directory: {relative}")
        split = lambda value: [x.strip() for x in value.split(",") if x.strip()]
        row = {"id": fields["name"], "description": fields["description"], "category": fields["category"],
               "stage": fields["stage"], "status": fields["status"], "version": fields["version"],
               "aliases": split(fields.get("aliases", "")), "requires": split(fields.get("requires", "")),
               "path": relative, "estimated_words": len(raw.decode().split()),
               "estimated_tokens": (len(raw) + 2) // 3, "sha256": digest(raw),
               "body_sha256": digest(" ".join(body.split()).encode())}
        extra = relations.get(row["id"], {})
        if not isinstance(extra, dict) or set(extra) - {"dependencies", "conflicts", "asset_types", "recommended_next", "resources", "requires", "status"}:
            raise ValueError(f"Unknown relation fields: {row['id']}")
        row.update(extra)
        row['resource_sha256'] = {relative: digest(contained_path(root, relative).read_bytes()) for relative in row.get('resources', [])}
        rows.append(row)
    unknown = set(relations) - {row["id"] for row in rows}
    if unknown:
        raise ValueError(f"Relations reference unknown skills: {sorted(unknown)}")
    validate_rows(rows, root)
    document = {"schema_version": 2, "digest": digest(canonical(rows)), "skills": rows}
    index_path = root / 'registry/index.json'
    if not index_path.exists() or canonical(read_json(index_path)) != canonical(document):
        atomic_json(index_path, document)
    try:
        atomic_json(contained_path(root, '.reelsyntax/registry-inventory.json', must_exist=False), {'digest': document['digest'], 'files': snapshot})
    except PermissionError:
        document['maintenance_warning'] = 'Freshness cache is not writable; subsequent queries may rebuild metadata.'
    document['maintenance_body_reads'] = len(rows)
    return document


def load_index(root=ROOT, auto_update=True):
    root = Path(root)
    path = contained_path(root, "registry/index.json")
    document = read_json(path)
    if document.get("schema_version") not in {1, 2}:
        raise ValueError("Unsupported skill registry schema")
    cache_path = contained_path(root, '.reelsyntax/registry-inventory.json', must_exist=False)
    cached = read_json(cache_path) if cache_path.exists() else {}
    if auto_update and (document.get("schema_version") != 2 or cached.get('digest') != document.get('digest') or cached.get('files') != inventory(root)):
        document = rebuild(root)
    rows = validate_rows(document.get("skills"), root)
    expected = digest(canonical(rows))
    if document.get("schema_version") == 2 and document.get("digest") != expected:
        raise ValueError("Registry digest mismatch; review changes and run skills reindex")
    document["digest"] = expected
    document.setdefault('maintenance_body_reads', 0)
    return document


def load_skill(row, root=ROOT, token_budget=6000):
    raw = skill_path(row, root).read_bytes()
    if len(raw) > MAX_SKILL_BYTES or (len(raw) + 2) // 3 > token_budget:
        raise ValueError("Skill instruction body exceeds context budget")
    if "sha256" not in row or digest(raw) != row["sha256"]:
        raise ValueError("Skill content changed; validate and reindex before loading")
    return raw.decode("utf-8")
