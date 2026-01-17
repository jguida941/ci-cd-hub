# ADR-0044: Archive Extraction Security Hardening

**Status:** Accepted  
**Date:** 2026-01-06  

## Context

The cihub CLI downloads and extracts archive files (ZIP, tarball) from external sources:
- GitHub artifact downloads (ZIP files from workflow runs)
- Tool installations (tarball files from GitHub releases)

Both Python's `zipfile.extractall()` and `tarfile.extractall()` are vulnerable to path traversal attacks (CVE-2007-4559 and variants) where malicious archives contain entries like `../../../etc/passwd` that extract outside the intended directory.

## Decision

### 1. ZIP Extraction Security

All ZIP extraction uses a `_safe_extractall()` helper that:
1. Iterates through all ZIP member paths before extraction
2. Resolves each path to absolute form
3. Uses `Path.relative_to()` to verify the path stays within the target directory
4. Raises `ValueError` if any path escapes (defense-in-depth)

```python
def _safe_extractall(zf: zipfile.ZipFile, target_dir: Path) -> None:
 resolved_target = target_dir.resolve()
 for member in zf.namelist():
 member_path = (target_dir / member).resolve()
 try:
 member_path.relative_to(resolved_target)
 except ValueError:
 raise ValueError(f"Path traversal detected in ZIP: {member}") from None
 zf.extractall(target_dir)
```

### 2. Tarball Extraction Security

Tarball extraction adds additional checks for symlinks:
1. Same path traversal protection as ZIP (using `relative_to()`)
2. Reject symbolic links (`issym()`)
3. Reject hard links (`islnk()`)

```python
def _extract_tarball_member(tar_path: Path, member_name: str, dest_dir: Path) -> Path:
 resolved_dest = dest_dir.resolve()
 with tarfile.open(tar_path) as tf:
 member = tf.getmember(member_name)
 # Reject symlinks and hardlinks
 if member.issym() or member.islnk():
 raise ValueError(f"Symlink/hardlink rejected: {member_name}")
 extracted = (dest_dir / member.name).resolve()
 try:
 extracted.relative_to(resolved_dest)
 except ValueError:
 raise ValueError(f"Path traversal detected: {member_name}") from None
 tf.extract(member, dest_dir)
 return extracted
```

### 3. Consistent Pattern

The same `Path.relative_to()` technique is used everywhere:
- ZIP extraction (`correlation.py`, `github_api.py`, `debug_orchestrator.py`)
- Tarball extraction (`hub_ci/__init__.py`)
- POM module validation (`java_pom.py`)
- Path validation utilities (`paths.py`)

## Consequences

### Positive
- Defense-in-depth against CVE-2007-4559 and variants
- `relative_to()` is immune to string prefix bypass attacks (unlike `str.startswith()`)
- Consistent pattern makes code review easier
- Clear error messages for debugging

### Negative
- Small performance overhead (iterating all members before extraction)
- Requires extra validation code

## Alternatives Considered

1. **Python 3.12+ `tarfile.data_filter`**: Only available in Python 3.12+; we support 3.11
2. **String prefix checking (`str.startswith()`)**: Vulnerable to bypass attacks like `/tmp/safe` vs `/tmp/safevil`
3. **Trust built-in sanitization**: Python's built-in protection is cautious, not absolute

## References

- [CVE-2007-4559](https://www.cvedetails.com/cve/CVE-2007-4559/) - Directory traversal in tarfile
- [Python zipfile docs](https://docs.python.org/3/library/zipfile.html) - "Never extract archives from untrusted sources"
- [Python tarfile discussion](https://discuss.python.org/t/policies-for-tarfile-extractall-a-k-a-fixing-cve-2007-4559/23149)
