# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions
# This is a simple example for a custom action which utters "Hello World!"

import sqlite3
from aifc import Error
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import AllSlotsReset
from rasa_sdk.executor import CollectingDispatcher
from fuzzywuzzy import process


##Ajouter un toTexte

class InfoPoleAction(Action):

    def name(self) -> Text:
        return "info_pole_action"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        c = create_connection(db_file="/home/tontonbal/PycharmProjects/ChatBot/db/lis_db")
        cur = c.cursor()
        cur.execute(f"SELECT Nom FROM table_pole")
        get_result = cur.fetchall()
        dispatcher.utter_message(text=str("Les différents pôles du LiS sont :" + get_result))

        return []


class InfoPoleParticulierAction(Action):

    def name(self) -> Text:
        return "info_pole_particulier_action"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        c = create_connection(db_file="/home/tontonbal/PycharmProjects/IA/db/lis_db")
        cur = c.cursor()
        slot_name = "Nom"
        if not tracker.get_slot('pole'):
            dispatcher.utter_message("Je suis désolé, je n'ai pas cette information.")
            return [AllSlotsReset()]
        slot_value = fusy_matching(c, slot_name, tracker.get_slot("pole"))

        cur.execute(f"SELECT * FROM table_pole WHERE {slot_name} = '{slot_value}'")
        rows = cur.fetchall()
        for row in rows:
            get_result = f"{row[1]} Le/la responsable du pôle est {row[2]} et le/la co-responsable est {row[3]}"
            dispatcher.utter_message(str(get_result))
        return [AllSlotsReset()]

class InfoComposantes(Action):

    def name(self) -> Text:
        return "info_composantes_action"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        c = create_connection(db_file="/home/tontonbal/PycharmProjects/IA/db/lis_db")
        cur = c.cursor()
        cur.execute(f"SELECT * FROM composantes")
        rows = cur.fetchall()
        get_result = ""
        for row in rows:
            get_result = get_result + row[0] + ", "
        get_result = f"Les composantes du LiS sont : {get_result}"
        dispatcher.utter_message(str(get_result))
        return []

# Entrée : prend les différentes valeur des colonnes de la DB, ainsi qu'une input.
# Retourne la valeur la de la colonne la plus proche lexicalement de l'input
def fusy_matching(c, slot_name, slot_value):

    cur = c.cursor()
    cur.execute(f"SELECT DISTINCT {slot_name} FROM table_pole")
    column_name = cur.fetchall()
    best_match = process.extractOne(slot_value, column_name)
    return best_match[0][0]


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn


def select_by_slot(conn, slot_name, slot_value):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM table_pole WHERE {slot_name}='{slot_value}'")
    rows = cur.fetchall()

    for row in rows:
        return f"{row[0]}";

# c = create_connection(db_file="/home/tontonbal/PycharmProjects/ChatBot/db/lis_db")
# cur = c.cursor()
# cur.execute(f"SELECT DISTINCT Nom FROM table_pole")
# column_name = cur.fetchall()
# best_match = process.extractOne("acb", column_name)
# print(best_match[0][0])