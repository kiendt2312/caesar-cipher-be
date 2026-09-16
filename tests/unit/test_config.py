import ast
from pathlib import Path

from app import config

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_application_constants_match_approved_structure() -> None:
    assert config.MAX_FILE_BYTES == 5 * 1024 * 1024
    assert config.MAX_REQUEST_BYTES == 64 * 1024 * 1024
    assert config.ALLOWED_EXTENSION == ".txt"
    assert config.CHUNK_SIZE == 64 * 1024
    assert config.PORT == 8000


def test_file_size_threshold_literal_has_one_implementation_source() -> None:
    occurrences: list[Path] = []

    for source_root in (PROJECT_ROOT / "app", PROJECT_ROOT / "tests"):
        for path in source_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if any(
                isinstance(node, ast.Constant) and node.value == config.MAX_FILE_BYTES
                for node in ast.walk(tree)
            ):
                occurrences.append(path.relative_to(PROJECT_ROOT))

    assert occurrences == [Path("app/config.py")]


def test_file_limit_comment_states_the_exact_binary_size() -> None:
    source = (PROJECT_ROOT / "app/config.py").read_text(encoding="utf-8")
    assert "5242880 byte = 5 MiB" in source
