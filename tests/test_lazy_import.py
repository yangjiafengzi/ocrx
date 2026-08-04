# -- coding: utf-8 --
"""验证 import ocrx 不会提前加载 PyMuPDF（惰性导入）。"""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_import_ocrx_does_not_load_pymupdf():
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "import ocrx\n"
        "assert 'fitz' not in sys.modules, 'fitz 不应在 import ocrx 时被加载'\n"
        "assert 'ocrx.pdf_processor' not in sys.modules\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
