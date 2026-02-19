"""
=============================================================================
 Utilitaire de capture de sortie console → Image PNG (style terminal)
=============================================================================
 Génère des images PNG au look "terminal sombre" à partir de texte,
 idéal pour illustrer un rapport technique.
=============================================================================
"""

import io
import os
import sys
import textwrap
from contextlib import contextmanager
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Backend non-interactif (pas besoin d'affichage)
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


# ═══════════════════════════════════════════════════════════════════════════
# Configuration du style terminal
# ═══════════════════════════════════════════════════════════════════════════

TERMINAL_BG = "#1e1e2e"       # Fond sombre (style Catppuccin Mocha)
TERMINAL_FG = "#cdd6f4"       # Texte clair
TERMINAL_GREEN = "#a6e3a1"    # Vert pour le titre
TERMINAL_BORDER = "#45475a"   # Bordure
FONT_SIZE = 9                 # Taille de police
MAX_LINE_WIDTH = 100          # Largeur max d'une ligne
OUTPUT_DIR = Path(__file__).parent / "outputs"


def ensure_output_dir() -> Path:
    """Crée le dossier outputs/ s'il n'existe pas."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR


def find_monospace_font() -> str:
    """Trouve une police monospace disponible sur le système."""
    preferred = [
        "Menlo", "Monaco", "Courier New", "Consolas",
        "DejaVu Sans Mono", "Liberation Mono", "monospace",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in preferred:
        if font in available:
            return font
    return "monospace"


# ═══════════════════════════════════════════════════════════════════════════
# Capture de stdout
# ═══════════════════════════════════════════════════════════════════════════

class OutputCapture:
    """Capture stdout tout en continuant à l'afficher dans le terminal."""

    def __init__(self):
        self.buffer = io.StringIO()
        self._original_stdout = None

    def start(self):
        """Commence la capture."""
        self._original_stdout = sys.stdout
        sys.stdout = self

    def stop(self) -> str:
        """Arrête la capture et retourne le texte capturé."""
        sys.stdout = self._original_stdout
        return self.buffer.getvalue()

    def write(self, text):
        """Écrit dans le buffer ET dans le terminal original."""
        self.buffer.write(text)
        if self._original_stdout:
            self._original_stdout.write(text)

    def flush(self):
        self.buffer.flush()
        if self._original_stdout:
            self._original_stdout.flush()


@contextmanager
def capture_output():
    """
    Context manager pour capturer la sortie console.

    Usage:
        with capture_output() as capture:
            print("Hello")
        text = capture.stop()  # NON — on utilise capture.buffer.getvalue()

    Ou plus simplement via save_output_as_image().
    """
    cap = OutputCapture()
    cap.start()
    try:
        yield cap
    finally:
        pass  # Le stop sera fait manuellement


# ═══════════════════════════════════════════════════════════════════════════
# Rendu texte → Image PNG
# ═══════════════════════════════════════════════════════════════════════════

def text_to_image(
    text: str,
    filename: str,
    title: str = "",
    max_lines: int = 80,
) -> str:
    """
    Convertit du texte en image PNG au style terminal sombre.

    Args:
        text: Le texte à rendre en image.
        filename: Nom du fichier (sans extension, ex: 'migration').
        title: Titre affiché en haut de l'image (en vert).
        max_lines: Nombre max de lignes à afficher.

    Returns:
        Chemin absolu du fichier PNG créé.
    """
    ensure_output_dir()
    font_name = find_monospace_font()

    # Préparer les lignes
    lines = text.strip().split("\n")

    # Tronquer les lignes trop longues
    wrapped_lines = []
    for line in lines:
        if len(line) > MAX_LINE_WIDTH:
            wrapped_lines.extend(textwrap.wrap(line, MAX_LINE_WIDTH, subsequent_indent="    "))
        else:
            wrapped_lines.append(line)

    if len(wrapped_lines) > max_lines:
        wrapped_lines = wrapped_lines[:max_lines]
        wrapped_lines.append(f"  ... ({len(lines) - max_lines} lignes tronquées)")

    nb_lines = len(wrapped_lines) + (3 if title else 1)

    # Dimensions dynamiques
    fig_width = min(max(10, MAX_LINE_WIDTH * 0.085), 16)
    fig_height = max(2, nb_lines * 0.22 + 0.8)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    fig.patch.set_facecolor(TERMINAL_BG)
    ax.set_facecolor(TERMINAL_BG)
    ax.axis("off")

    # Titre
    y_start = 0.97
    if title:
        # Barre de titre style terminal
        ax.text(
            0.01, y_start, f"  ● ● ●  {title}",
            transform=ax.transAxes,
            fontsize=FONT_SIZE + 1,
            fontfamily=font_name,
            color=TERMINAL_GREEN,
            fontweight="bold",
            verticalalignment="top",
        )
        y_start -= 0.02
        # Ligne séparatrice
        ax.plot(
            [0.01, 0.99], [y_start, y_start],
            color=TERMINAL_BORDER,
            linewidth=0.5,
            transform=ax.transAxes,
        )
        y_start -= 0.02

    # Corps du texte
    line_height = 1.0 / (nb_lines + 2)
    for i, line in enumerate(wrapped_lines):
        y = y_start - i * line_height
        if y < 0.01:
            break
        ax.text(
            0.015, y, line,
            transform=ax.transAxes,
            fontsize=FONT_SIZE,
            fontfamily=font_name,
            color=TERMINAL_FG,
            verticalalignment="top",
        )

    # Bordure arrondie
    from matplotlib.patches import FancyBboxPatch
    border = FancyBboxPatch(
        (0.003, 0.003), 0.994, 0.994,
        boxstyle="round,pad=0.01",
        transform=ax.transAxes,
        facecolor="none",
        edgecolor=TERMINAL_BORDER,
        linewidth=1.5,
    )
    ax.add_patch(border)

    # Sauvegarder
    filepath = OUTPUT_DIR / f"{filename}.png"
    plt.savefig(
        filepath,
        dpi=150,
        bbox_inches="tight",
        pad_inches=0.1,
        facecolor=TERMINAL_BG,
        edgecolor="none",
    )
    plt.close(fig)

    return str(filepath)


# ═══════════════════════════════════════════════════════════════════════════
# Fonction tout-en-un
# ═══════════════════════════════════════════════════════════════════════════

def save_output_as_image(text: str, filename: str, title: str = "") -> str:
    """
    Sauvegarde un texte capturé en image PNG.

    Args:
        text: Texte à sauvegarder.
        filename: Nom du fichier (sans .png).
        title: Titre optionnel en haut de l'image.

    Returns:
        Chemin du fichier image créé.
    """
    path = text_to_image(text, filename, title)
    print(f"\n  📸 Image sauvegardée : {path}")
    return path
