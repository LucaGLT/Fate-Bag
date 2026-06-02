from pathlib import Path

from src.tools.test_console_app import run_console_demo


def _debug_case(title, given, expected, actual):
    print(f"\n[CASE] {title}")
    print(f"  GIVEN    : {given}")
    print(f"  EXPECTED : {expected}")
    print(f"  ACTUAL   : {actual}")


def test_console_app_runs_end_to_end(tmp_path):
    base_dir = Path(tmp_path) / "console-demo"
    summary = run_console_demo(base_dir)

    _debug_case(
        "Console app end-to-end flow",
        {"base_dir": str(base_dir)},
        {
            "token_count": 3,
            "drawn_count": 2,
            "revealed_count": 3,
            "loaded_draw_history_size": 2,
            "json_files_created": ["tokens.json", "sessions.json"],
        },
        {
            "token_count": summary["token_count"],
            "drawn_count": len(summary["drawn"]),
            "revealed_count": summary["revealed_count"],
            "loaded_draw_history_size": summary["loaded_draw_history_size"],
            "events_count": len(summary["events"]),
            "json_files_created": sorted([p.name for p in base_dir.glob("*.json")]),
        },
    )

    assert summary["token_count"] == 3
    assert len(summary["drawn"]) == 2
    assert summary["revealed_count"] == 3
    assert summary["loaded_draw_history_size"] == 2
    assert (base_dir / "tokens.json").exists()
    assert (base_dir / "sessions.json").exists()
    assert len(summary["events"]) > 0
