import pandas as pd
import shopping_list as sl
from gspread.models import Spreadsheet
import unittest

class TestRoutines(unittest.TestCase):

    def test00_build_frames(self):
        """Validates the return of a dictionary."""
        pass

    def test01_extract_list(self):
        """Verifies removing the list of items
        properly from a day_dictionary."""
        sunday = pd.DataFrame()
        day_dict = {'sunday':sunday}


class TestChosenItem(unittest.TestCase):

    def test00_create(self):
        item = sl.ChosenItem('test')
        self.assertEqual(item.name, 'test')
        self.assertEqual(item.servings, 0)
        self.assertEqual(item.grams, 0)
        self.assertIsNone(item.gram_per_serv)

    def test01_add_servings(self):
        item = sl.ChosenItem('test')
        item.add_servings(2.3)
        self.assertEqual(item.servings, 2.3)

    def test02_add_grams(self):
        item = sl.ChosenItem('test')
        item.add_grams(44.4, 11.1)
        self.assertEqual(item.grams, 44.4)
        self.assertEqual(item.gram_per_serv, 11.1)

    def test03_total_servings(self):
        item = sl.ChosenItem('test')
        item.add_servings(2.0)
        ts = item.total_servings()
        self.assertEqual(ts, 2.0)
        item.add_grams(44.4, 11.1)
        ts = item.total_servings()
        self.assertEqual(ts, 6.0)

        
if __name__ == '__main__':
    unittest.main()