from math import floor, ceil
from datetime import datetime, timedelta
import json

from aqt import mw
from aqt.qt import *
import os

from PyQt6.QtWebEngineWidgets import QWebEngineView

from anki.collection import Collection
from aqt.operations import QueryOp

config = mw.addonManager.getConfig(__name__)
deck_name = config.get("deckName")


def on_success(data: dict, web_view: QWebEngineView):
    def _inject_data():
        js_code = ""
        for key, value in data.items():
            safe_value = json.dumps(value)  # Serialize the string for safe JavaScript injection
            js_code += f"document.getElementById('{key}').innerText = {safe_value};"
        web_view.page().runJavaScript(js_code)

    # Ensure JavaScript is executed after page load
    web_view.loadFinished.connect(_inject_data)


def stat_function() -> None:
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
    qconnect(action.triggered, stat_function)
    mw.form.menuTools.addAction(action)


def fetch_stats_op(col: Collection) -> dict:
    user_level = get_user_level(col)

    stats_dict = {
        "user_level": user_level,
        "time_on_level": get_time_on_level(col, user_level),
        "typical_levelup": get_time_on_level(col, 15),
        "radicals_learned": get_radicals_learned(col),
        "kanji_learned": get_kanji_learned(col),
        "vocabulary_learned": get_vocabulary_learned(col),
        "start_date": get_start_date(col),
        "end_date": get_end_date(col),
    }

    return stats_dict


def get_user_level(col: Collection) -> int:
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

    # Return 60 if no relevant tag is found
    return 60


def get_time_on_level(col: Collection, level: int) -> str:
    tag = f"Lesson_{level}"
    query_all_cards = f'deck:"{deck_name}" tag:{tag}'
    card_ids = col.find_cards(query_all_cards)

    if not card_ids:
        return "No cards found for this level."

    # Get the earliest review date for these cards
    earliest_review_query = f"select min(id) from revlog where cid in ({','.join(map(str, card_ids))})"
    earliest_review_timestamp = col.db.scalar(earliest_review_query)

    if not earliest_review_timestamp:
        return "No reviews found for this level."

    # Convert the timestamp to a datetime object for the first review
    earliest_review_date = datetime.utcfromtimestamp(earliest_review_timestamp / 1000)
    print(f"lvl {level}", earliest_review_date)

    if level == 1:
        manual_start_date_str = config.get("manualStartDate")
        if manual_start_date_str:
            # Convert the manual start date string to a datetime object with default time
            manual_start_date = datetime.strptime(manual_start_date_str, '%Y-%m-%d')
            earliest_review_date = manual_start_date

    # Determine the end date based on whether the level is completed
    query_new_cards = f'deck:"{deck_name}" tag:{tag} is:new'
    new_card_ids = col.find_cards(query_new_cards)

    if not new_card_ids:
        # SQL query to find the earliest review timestamp for each card
        earliest_review_query_for_each_card = f"""
        SELECT cid, MIN(id) as earliest_review_timestamp
        FROM revlog
        WHERE cid IN ({','.join(map(str, card_ids))})
        GROUP BY cid
        """

        # Execute the query and fetch all results
        earliest_reviews = col.db.all(earliest_review_query_for_each_card)

        # Sort the results by timestamp and get the last one
        if earliest_reviews:
            last_earliest_review = sorted(earliest_reviews, key=lambda x: x[1])[-1]
            last_earliest_review_timestamp = last_earliest_review[1]

            # Convert timestamp to datetime
            end_date = datetime.utcfromtimestamp(last_earliest_review_timestamp / 1000)
        else:
            return "Query returned something bad"
    else:
        print(f"used current date for end date on level {level}")
        end_date = datetime.utcnow()

    print(f"lvl {level}", end_date)
    # Calculate the time difference
    time_diff = end_date - earliest_review_date

    # Extract days, hours, and minutes
    days = time_diff.days
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes = remainder // 60

    return f"{days} days, {hours} hours, {minutes} minutes"


def get_typical_levelup(col: Collection, current_level: int) -> str:
    def parse_time(time_string: str) -> int:
        if "No" in time_str:
            return -1
        parts = time_string.split(', ')
        days = int(parts[0].split(' ')[0])
        hours = int(parts[1].split(' ')[0])
        minutes = int(parts[2].split(' ')[0])
        return days * 24 * 60 + hours * 60 + minutes

    total_minutes = 0
    valid_levels_count = 0

    for level in range(1, current_level):
        time_str = get_time_on_level(col, level)
        parsed_time = parse_time(time_str)
        if parsed_time == -1:
            return f"Parsing failed on level {level}"
        total_minutes += parsed_time
        valid_levels_count += 1

    if valid_levels_count == 0:
        return "No valid data available for averaging."

    avg_minutes = total_minutes // valid_levels_count

    avg_days = avg_minutes // (24 * 60)
    avg_minutes %= (24 * 60)
    avg_hours = avg_minutes // 60
    avg_minutes %= 60

    return f"{avg_days} days, {avg_hours} hours, {avg_minutes} minutes"


def get_radicals_learned(col: Collection) -> int:
    query = f'deck:"{deck_name}" -is:new ("tag:radical" or "Card_Type:Radical")'
    learned_radical_card_ids = col.find_cards(query)

    return len(learned_radical_card_ids)


def get_kanji_learned(col: Collection) -> int:
    query = f'deck:"{deck_name}" -is:new ("tag:kanji" or "Card_Type:Kanji")'
    learned_kanji_card_ids = col.find_cards(query)

    return floor(len(learned_kanji_card_ids) / 2)


def get_vocabulary_learned(col: Collection) -> int:
    query = f'deck:"{deck_name}" -is:new ("tag:vocabulary" or "Card_Type:Vocabulary")'
    learned_vocabulary_card_ids = col.find_cards(query)

    return floor(len(learned_vocabulary_card_ids) / 2)


def get_start_date(col: Collection) -> str:
    manual_start_date = config.get("manualStartDate")

    # If a manual start date is set, use it
    if manual_start_date:
        try:
            # Validate and format the manual start date
            manual_date = datetime.strptime(manual_start_date, '%Y-%m-%d')
            days_ago = (datetime.utcnow() - manual_date).days + 1
            return f"{manual_start_date} ({days_ago} days ago)"
        except ValueError:
            return "Invalid manual start date format. Please use YYYY-MM-DD."

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


def get_end_date(col: Collection) -> str:
    # Get deck ID
    deck_id = col.decks.id(deck_name)

    # Number of new cards remaining
    new_card_query = f'deck:"{deck_name}" is:new'
    new_cards_remaining = len(col.find_cards(new_card_query))

    # Daily new card limit
    daily_new_limit = col.decks.config_dict_for_deck_id(deck_id)["new"]["perDay"]

    # Calculate days remaining
    days_remaining = ceil(new_cards_remaining / daily_new_limit)

    # Calculate estimated end date
    estimated_end_date = datetime.utcnow().date() + timedelta(days=days_remaining)
    end_date_str = estimated_end_date.strftime('%Y-%m-%d')

    return f"{end_date_str} ({days_remaining} days)"
