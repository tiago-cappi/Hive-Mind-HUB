# Os testes moram em tests/ mas importam módulos da raiz do repo
# (`import server`) — este conftest põe a raiz no sys.path antes da coleta.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
