from argparse import ArgumentParser
from pathlib import Path

from src.core.engine.draw_engine import DrawEngine
from src.core.engine.session_engine import SessionEngine
from src.core.engine.shuffle_engine import ShuffleEngine
from src.core.events.event_bus import EventBus
from src.core.events.event_types import EventType
from src.core.models.enums import TokenFrontType, TokenShape
from src.core.models.token import Token
from src.core.services.draw_service import DrawService
from src.core.services.session_service import SessionService
from src.core.services.token_service import TokenService
from src.infrastructure.json.json_session_repository import JsonSessionRepository
from src.infrastructure.json.json_token_repository import JsonTokenRepository


def _log_step(title: str, details: dict) -> None:
    print(f"\n[STEP] {title}")
    for key, value in details.items():
        print(f"  - {key}: {value}")


def _build_sample_tokens(base_dir: Path) -> list[Token]:
    assets_dir = base_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    back_image = assets_dir / "back.png"
    back_image.write_bytes(b"fake-image")

    return [
        Token(
            name="Blessing",
            shape=TokenShape.CIRCLE,
            front_type=TokenFrontType.TEXT,
            front_value="Blessing",
            back_value=str(back_image),
            categories=["holy"],
            tags=["light"],
            weight=3.0,
            rarity="common",
        ),
        Token(
            name="Curse",
            shape=TokenShape.HEXAGON,
            front_type=TokenFrontType.TEXT,
            front_value="Curse",
            back_value=str(back_image),
            categories=["shadow"],
            tags=["dark"],
            weight=1.0,
            rarity="rare",
        ),
        Token(
            name="Shield",
            shape=TokenShape.CIRCLE,
            front_type=TokenFrontType.TEXT,
            front_value="Shield",
            back_value=str(back_image),
            categories=["holy"],
            tags=["defense"],
            weight=2.0,
            rarity="common",
        ),
    ]


def run_console_demo(base_dir: Path) -> dict:
    base_dir.mkdir(parents=True, exist_ok=True)
    token_repo = JsonTokenRepository(base_dir / "tokens.json")
    session_repo = JsonSessionRepository(base_dir / "sessions.json")
    event_bus = EventBus()

    captured_events: list[str] = []

    def event_logger(event):
        captured_events.append(event.event_type)

    for event_type in EventType:
        event_bus.register(event_type, event_logger)

    token_service = TokenService(token_repo, event_bus)

    tokens = _build_sample_tokens(base_dir)
    for token in tokens:
        token_service.create_token(token)

    saved_tokens = token_service.list_tokens()
    _log_step(
        "crea token",
        {
            "count": len(saved_tokens),
            "token_ids": [str(token.id) for token in saved_tokens],
        },
    )

    session_engine = SessionEngine(saved_tokens)
    session_service = SessionService(
        session_engine=session_engine,
        shuffle_engine=ShuffleEngine(),
        repository=session_repo,
        event_bus=event_bus,
    )
    draw_service = DrawService(
        draw_engine=DrawEngine(saved_tokens),
        session_repository=session_repo,
        event_bus=event_bus,
    )

    session = session_service.start_session(seed=21)
    _log_step(
        "crea sessione",
        {
            "session_id": str(session.session_id),
            "table_size": len(session.table_tokens),
        },
    )

    session = session_service.shuffle_session(session, seed=99)
    _log_step(
        "shuffle",
        {
            "seed": session.seed,
            "order": [str(table_token.token_id) for table_token in session.table_tokens],
        },
    )

    drawn = draw_service.draw_uniform(session, count=2, with_replacement=False, seed=13)
    _log_step("draw", {"drawn_token_ids": drawn, "draw_history_size": len(session.draw_history)})

    revealed = draw_service.reveal_tokens(session)
    _log_step("reveal", {"revealed_count": len(revealed), "revealed_token_ids": revealed})

    loaded_session = session_service.load_session(session.session_id)
    _log_step(
        "load",
        {
            "loaded_session_id": str(loaded_session.session_id),
            "loaded_draw_history_size": len(loaded_session.draw_history),
        },
    )

    summary = {
        "token_count": len(saved_tokens),
        "session_id": str(session.session_id),
        "drawn": drawn,
        "revealed_count": len(revealed),
        "loaded_draw_history_size": len(loaded_session.draw_history),
        "events": captured_events,
    }

    _log_step("summary", summary)
    return summary


def main() -> None:
    parser = ArgumentParser(description="Fate-Bag Core console test app")
    parser.add_argument(
        "--base-dir",
        default=".runtime/console-demo",
        help="Directory for temporary JSON persistence files",
    )
    args = parser.parse_args()

    run_console_demo(Path(args.base_dir))


if __name__ == "__main__":
    main()
