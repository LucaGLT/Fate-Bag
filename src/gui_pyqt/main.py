import sys
from pathlib import Path

# Assicura che la root del progetto sia nel path quando si esegue direttamente il file.
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.gui_pyqt.views.main_window import main


if __name__ == "__main__":
    raise SystemExit(main(base_dir=Path(".runtime/gui")))
