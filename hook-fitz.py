# PyInstaller hook for fitz (PyMuPDF)
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all fitz/PyMuPDF data
datas, binaries, hiddenimports = collect_all('fitz')

# Also collect PyMuPDF
datas2, binaries2, hiddenimports2 = collect_all('PyMuPDF')

datas += datas2
binaries += binaries2
hiddenimports += hiddenimports2

# Add specific hidden imports
hiddenimports += [
    'fitz',
    'fitz.fitz',
    'fitz.utils',
    'PyMuPDF',
    'PyMuPDF.fitz',
]