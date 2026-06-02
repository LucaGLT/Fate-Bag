from pathlib import Path

from src.gui_pyqt.views.main_window import main


if __name__ == "__main__":
    raise SystemExit(main(base_dir=Path(".runtime/gui")))
