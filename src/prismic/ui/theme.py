"""Application-wide visual theme.

A single dark QSS stylesheet plus the raw color tokens it's built from, so
custom-painted widgets (the result list's thumbnail delegate, in
particular) can match it exactly instead of guessing at colors. Applied
once, app-wide, via `QApplication.setStyleSheet()` in `bootstrap.py` --
individual widgets don't carry their own stylesheets, only the object
names / properties this file's selectors key off of.

Purely presentational: nothing here reads application or domain state.
"""

from __future__ import annotations

# -- Color tokens -------------------------------------------------------
# Referenced directly by ui/thumbnail_delegate.py so custom-painted rows
# use the exact same palette as everything QSS styles automatically.

BG_APP = "#1c1e22"
BG_PANEL = "#212327"
BG_PANEL_RAISED = "#26282d"
BG_CANVAS = "#131417"  # the media viewer's own backdrop -- deliberately
# darker than the surrounding chrome so photos/video read as the subject,
# not the panel they sit in.

BORDER = "#34373d"
BORDER_SUBTLE = "#2b2d32"

TEXT_PRIMARY = "#e8e9ec"
TEXT_SECONDARY = "#9a9ea6"
TEXT_MUTED = "#6b6f78"

ACCENT = "#557463"  # derived from assets/icon/prismic-icon.svg's own accent
# stroke (#6ee7a6), then muted 50% (half saturation, half brightness in
# HSB) on request -- the icon itself is untouched and stays at full
# brightness; only this in-UI accent is toned down.
ACCENT_HOVER = "#637669"  # the icon's next gradient step (#9febb8), muted
# the same way, so hover still reads as "the same accent, one step up."
# Qt's hex-with-alpha format is #AARRGGBB (alpha *first*) for both QColor and
# QSS -- not the CSS-web convention of alpha last. Get this backwards and the
# alpha nibbles get read as part of the RGB value instead, producing a wrong,
# fully-opaque color rather than an error (that's how a "20% blue" wash
# turned into solid yellow-green here the first time around).
ACCENT_MUTED = "#33557463"  # ~20% alpha; menu-item highlight, not selection
ACCENT_MUTED_STRONG = "#55557463"

# The tag-checked and current-item indicators are deliberately grayscale --
# neutral, not tinted with the brand accent -- so they read as "selection",
# a distinct concept from "accent". SELECTED_MARK reuses TEXT_PRIMARY rather
# than a new hex: it's already the palette's brightest neutral, so a filled
# checkbox or the current-item bar reads clearly against BG_APP without
# introducing a color that means nothing else in this file.
SELECTED_MARK = TEXT_PRIMARY
SELECTED_WASH = "#26ffffff"  # ~15% white -- stronger than HOVER_WASH so a
# selected row still reads as distinct from a merely-hovered one.

DANGER = "#e5697a"
DANGER_MUTED = "#26e5697a"

HOVER_WASH = "#0fffffff"
PRESSED_WASH = "#1cffffff"

THUMB_PLACEHOLDER = "#2d3036"
THUMB_VIDEO_BADGE = "#99000000"

_FONT_STACK = '"Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif'


STYLESHEET = f"""
* {{
    font-family: {_FONT_STACK};
    outline: none;
}}

QMainWindow, QWidget {{
    background: {BG_APP};
    color: {TEXT_PRIMARY};
}}

QWidget#emptyStateLabel {{
    color: {TEXT_MUTED};
    font-size: 14px;
}}

/* -- Menu bar / menus --------------------------------------------------- */

QMenuBar {{
    background: {BG_APP};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BORDER_SUBTLE};
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 4px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background: {HOVER_WASH};
}}
QMenu {{
    background: {BG_PANEL_RAISED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background: {ACCENT_MUTED_STRONG};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 6px;
}}

/* -- Status bar ----------------------------------------------------------- */

QStatusBar {{
    background: {BG_APP};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER_SUBTLE};
}}
QStatusBar::item {{
    border: none;
}}

/* Both sides of the status bar are pinned to the same fixed height,
   regardless of what they currently contain -- a keycap's border and
   padding make it taller than a plain text label, so without a floor
   here the whole bar visibly grows/shrinks by a couple of pixels
   every time a hovered control's hint (or the transient message) comes
   and goes. */
QWidget#hoverExplainerBar, QLabel#transientMessageBar {{
    min-height: 22px;
}}
QLabel#hoverExplainerText {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}
QLabel#keycap {{
    background: {BG_PANEL_RAISED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-bottom: 2px solid {BORDER};
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#transientMessageBar {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    padding-right: 4px;
}}

/* -- Panel titles ---------------------------------------------------------- */

QLabel#panelTitle {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    padding: 10px 10px 6px 10px;
    letter-spacing: 0.5px;
}}

/* -- Buttons ---------------------------------------------------------------- */

QPushButton {{
    background: {BG_PANEL_RAISED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
}}
QPushButton:hover {{
    background: {HOVER_WASH};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background: {PRESSED_WASH};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    border-color: {BORDER_SUBTLE};
}}
QPushButton#dangerButton:hover {{
    background: {DANGER_MUTED};
    border-color: {DANGER};
    color: {DANGER};
}}
QPushButton#playPauseButton {{
    background: {ACCENT};
    border: none;
    color: #0e1116;
    font-weight: 600;
    padding: 6px 16px;
}}
QPushButton#playPauseButton:hover {{
    background: {ACCENT_HOVER};
}}

/* -- Text inputs (rename/create dialogs, etc.) ------------------------------ */

QLineEdit {{
    background: {BG_PANEL_RAISED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}

QDialog {{
    background: {BG_PANEL};
}}

/* -- List views ---------------------------------------------------------
   Both the tag lists and the result list paint every pixel of a row
   themselves (TagRowDelegate / ThumbnailDelegate) -- checkbox, hover and
   selection washes included -- so Qt's own ::item styling is blanked out
   here rather than layered underneath it. */

QListView {{
    background: {BG_PANEL};
    border: none;
    outline: none;
    padding: 4px;
}}
QListView#tagList::item, QListView#resultList::item {{
    border: none;
    padding: 0;
}}
QListView#tagList::item:selected, QListView#resultList::item:selected {{
    background: transparent;
}}
QListView#tagList::item:hover, QListView#resultList::item:hover {{
    background: transparent;
}}

QLineEdit#tagSearchBox {{
    margin: 0 8px 8px 8px;
    font-size: 12px;
}}
QLineEdit#tagRenameEdit {{
    padding: 2px 6px;
}}

QListView#resultList {{
    padding: 6px;
}}
QListView#resultList::item {{
    border: none;
    padding: 0;
}}
QListView#resultList::item:selected {{
    background: transparent;
}}
QListView#resultList::item:hover {{
    background: transparent;
}}

/* -- Splitter --------------------------------------------------------------- */

QSplitter::handle {{
    background: {BORDER_SUBTLE};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:hover {{
    background: {ACCENT};
}}

/* -- Media viewer ------------------------------------------------------------ */

QWidget#mediaViewer {{
    background: {BG_CANVAS};
}}
QStackedWidget#viewerStack {{
    background: {BG_CANVAS};
    border-radius: 8px;
}}
QGraphicsView {{
    background: {BG_CANVAS};
    border: none;
}}
QVideoWidget {{
    background: {BG_CANVAS};
}}
QWidget#viewerControls {{
    background: {BG_PANEL};
    border-top: 1px solid {BORDER_SUBTLE};
    padding: 8px 10px;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 13px;
    height: 13px;
    margin: -5px 0;
    border-radius: 6px;
    background: {TEXT_PRIMARY};
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT_HOVER};
}}

/* -- Scrollbars --------------------------------------------------------------- */

QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 11px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {TEXT_MUTED};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QMessageBox {{
    background: {BG_PANEL};
}}

QToolTip {{
    background: {BG_PANEL_RAISED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    padding: 4px 6px;
    border-radius: 4px;
}}
"""
