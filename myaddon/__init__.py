from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *
import os

from PyQt6.QtWebEngineWidgets import QWebEngineView

from anki.collection import Collection
from aqt.operations import QueryOp


def on_success(data: dict, web_view: QWebEngineView):
    def _inject_data():
        js_code = ""
        for key, value in data.items():
            js_code += f"document.getElementById('{key}').innerText = '{value}';"
        web_view.page().runJavaScript(js_code)

    # Ensure JavaScript is executed after page load
    web_view.loadFinished.connect(_inject_data)

def statFunction() -> None:
    dialog = QDialog(mw)
    dialog.setWindowTitle("WaniKani Stats")
    dialog.resize(550, 550)

    web_view = QWebEngineView(dialog)
    layout = QVBoxLayout(dialog)
    layout.addWidget(web_view)

    html_file_path = os.path.join(os.path.dirname(__file__), "stats.html")
    web_view.load(QUrl.fromLocalFile(html_file_path))

    op = QueryOp(
        parent=mw,
        op=lambda col: fetch_stats_op(col),
        success=lambda stat: on_success(stat, web_view)
    )
    op.with_progress().run_in_background()

    dialog.exec()


# Add menu item
if mw is None:
    raise RuntimeError("The 'mw' (main window) object is None. This addon cannot function without it.")
else:
    action = QAction("WaniKani Stats", mw)
    qconnect(action.triggered, statFunction)
    mw.form.menuTools.addAction(action)


def fetch_stats_op(col: Collection) -> dict:
    stats_dict = {"user_level": get_user_level(col),
                  "radicals_learned": "6969"}

    return stats_dict


def get_user_level(col: Collection) -> int:
    deck_name = "Wanikani Ultimate 3: Tokyo Drift"

    # Use Anki's search functionality to find new cards in the specified deck, sorted by due order
    query = f'deck:"{deck_name}" is:new'
    new_card_ids = col.find_cards(query, order="due")

    # Check if there are any new cards
    if not new_card_ids:
        return 60

    # Get the first new card from the sorted list
    card = col.get_card(new_card_ids[0])

    # Extract the tags from the card
    tags = card.note().tags

    # Find the tag that starts with "Lesson_" and extract the number
    for tag in tags:
        if tag.startswith("Lesson_"):
            lesson_number = tag.split("_")[1]
            try:
                return int(lesson_number)
            except ValueError:
                # Handle the case where the number is not valid
                pass

    # Return None if no relevant tag is found
    return None