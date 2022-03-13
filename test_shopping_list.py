"""
Evaluates the methods in shopping_list
"""
import unittest

import pandas as pd

import shopping_list

#pylint: disable=missing-class-docstring,missing-function-docstring
class TestRoutines(unittest.TestCase):

    def test_build_food_from_days(self):
        chris_sheet = [
            ['Test', 'This', 'Is', 'a', 'row'],
        ]
        mel_sheet = [
            ['What', 'is', 'this'],
            ['Another', 'row', 'of'],
        ]
        chris_days = {'sunday':pd.DataFrame(chris_sheet)}
        mel_days = {'monday':pd.DataFrame(mel_sheet)}
        user_days = {'chris':chris_days, 'melia':mel_days}
        shopping_list.build_food_from_days(user_days)
