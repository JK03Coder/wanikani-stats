from math import floor
from datetime import datetime

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
    stats_dict = {
        "user_level": get_user_level(col),
        "radicals_learned": get_radicals_learned(col),
        "kanji_learned": get_kanji_learned(col),
        "vocabulary_learned": get_vocabulary_learned(col),
        "start_date": get_start_date(col),
    }

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


def get_radicals_learned(col: Collection) -> int:
    deck_name = "Wanikani Ultimate 3: Tokyo Drift"

    query = f'deck:"{deck_name}" -is:new ("tag:radical" or "Card_Type:Radical")'
    learned_radical_card_ids = col.find_cards(query)

    return len(learned_radical_card_ids)


def get_kanji_learned(col: Collection) -> int:
    deck_name = "Wanikani Ultimate 3: Tokyo Drift"

    query = f'deck:"{deck_name}" -is:new ("tag:kanji" or "Card_Type:Kanji")'
    learned_kanji_card_ids = col.find_cards(query)

    return floor(len(learned_kanji_card_ids)/2)


def get_vocabulary_learned(col: Collection) -> int:
    deck_name = "Wanikani Ultimate 3: Tokyo Drift"

    query = f'deck:"{deck_name}" -is:new ("tag:vocabulary" or "Card_Type:Vocabulary")'
    learned_vocabulary_card_ids = col.find_cards(query)

    return floor(len(learned_vocabulary_card_ids)/2)


def get_start_date(col: Collection) -> str:
    deck_name = "Wanikani Ultimate 3: Tokyo Drift"

    query = """
        select min(id) from revlog 
        where cid in (
            select id from cards where did = (
                select id from decks where name = ?
            )
        )
    """
    first_review_id = col.db.scalar(query, deck_name)

    if first_review_id and first_review_id > 0:
        # Convert the timestamp from milliseconds to seconds
        first_review_date = datetime.utcfromtimestamp(first_review_id / 1000)
        date_str = first_review_date.strftime('%Y-%m-%d')

        # Calculate days ago
        days_ago = (datetime.utcnow() - first_review_date).days
        return f"{date_str} ({days_ago} days ago)"
    else:
        return "---"
