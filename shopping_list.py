import copy
import gspread
import os
import pandas as pd
import sys
from oauth2client.service_account import ServiceAccountCredentials

def build_frames(worksheet):
    """Creates data frames by days for a worksheet.
    
    Parameters
    ----------
    worksheet : gspread.models.Spreadsheet
        The worksheet to read the days from.
        
    Returns
    -------
    dict
        Dictionary by day of pandas data frames.
    """
    week_days = ('sunday',
        'monday',
        'tuesday',
        'wednesday',
        'thursday',
        'friday',
        'saturday',
    )
    days = {}
    for sheet in worksheet:
        name = sheet.title.lower()
        if name in week_days:
            data = sheet.get_all_values()
            days[name] = pd.DataFrame(data)
    return days

class ChosenItem():
    """Container class for items chosen by the sheet user.

    Parameters
    ----------
    name : str
        Name of the chosen item.
    servings, float, optional, default=0
        Number of servings of this item.
    grams, float, optional, default=0
        Number of grams of this item.

    """

    def __init__(self, name):
        self.name = name
        self.servings = 0
        self.grams = 0
        self.gram_per_serv = None
        self.days = set()

    def __str__(self):
        return f'{self.name} {self.total_servings()} servings'

    def add_servings(self, servings):
        """Updates servings
        
        Parameters
        ----------
        servings : float
            Number of servings to add to this item.
        """
        self.servings += servings

    def add_grams(self, grams, gram_weight):
        """Updates grams.
        
        Parameters
        ----------
        grams : float
            Number of grams to add to this item.
        """
        self.grams += grams
        self.gram_per_serv = gram_weight

    def total_servings(self):
        """Compiles the total number of servings for
        this item.

        Returns
        -------
        float
            Number of servings for this item.
        """
        start_serv = self.servings
        if self.gram_per_serv:
            start_serv += self.grams/self.gram_per_serv
        return start_serv

    def total_grams(self):
        """Compiles the total number of grams for this item.
        
        Returns
        -------
        float
            Number of grams for this item.
        """
        start_grams = self.grams
        if self.servings and self.gram_per_serv:
            start_grams += self.serving * self.gram_per_serv
        return start_grams

def extract_list(day_dicts):
    """Retrieves data for each chosen item
    by day.

    Parameters
    ----------
    day_dicts : tuple
        Any number of Dictionary of days by dataframes from a food plan.

    Returns
    -------
    dict
        Dictionary by days of extracted data.
    """
    ignored_rows = ('Breakfast', 'Lunch', 'Snack', 'Dinner', 'Desert', 'Stick To', 'Totals', 'Differences')
    items = {}
    for plan in day_dicts:
        for day, df in plan.items():
            for _, series in df.iterrows():
                if series[0] == '' or series[1] == '':
                    continue
                try:
                    name = series[0]
                    qty = float(series[1])
                    unit_type = series[2]
                    gram_weight = series[12]
                except Exception as e:
                    print(e)
                    continue
                if name in ignored_rows:
                    continue
                if name and qty:
                    #Gurantees Item is available.
                    item = items.get(name)
                    if item is None:
                        item = ChosenItem(name)
                        items[name] = item
                    item.days.add(day)
                    if unit_type == 'grams':
                        if gram_weight == '':
                            continue
                        try:
                            gram_weight = float(gram_weight)
                        except Exception as e:
                            print(e)
                            continue
                        print(qty, gram_weight)
                        item.add_grams(qty, gram_weight)
                    elif unit_type == 'servings':
                        item.add_servings(qty)
                    else:
                        print('Unrecognized unit_type', unit_type)
                        continue
    return items

class Food():
    def __init__(self, name, serving_qty, serving_unit):
        self.name = name
        self.serving_qty = serving_qty
        self.serving_unit = serving_unit

    def __str__(self):
        return '{0},\t {1} {2}'.format(self.name, self.serving_qty, self.serving_unit)

    def __lt__(self, other):
        return self.name < other.name

    def __copy__(self):
        return type(self)(self.name, self.serving_qty, self.serving_unit)

    def __iadd__(self, other):
        self.serving_qty += other.serving_qty
        return self

    def __imul__(self, other):
        self.serving_qty *= other
        return self

class Recipe():
    """Recipe is comprised of one unit
    of itself, with many ingredients building
    up that one unit.
    
    Parameters
    ----------
    name : str
        Name of the recipe.
    ingredients : list
        List of food objects.
    
    """

    def __init__(self, name, ingredients=None):
        self.name = name
        self.ingredients = []
        if ingredients:
            self.ingredients = ingredients

    def __str__(self):
        return '{0} with {1} ingredients.'.format(self.name, len(self.ingredients))

    def append(self, item):
        self.ingredients.append(item)

def load_recipes(recipe_df, raw_df):
    """Loads recipes for the shopping list.

    Parameters
    ----------
    recipe_df : pd.DataFrame
        Dataframe to load the recipes from.
    raw_df : pd.DataFrame
        Raw ingredients within the recipes.

    Returns
    -------
    dict
        Recipe objects containing their shopping lists.
    """
    cur_recipe = None
    start_track = False
    recipes = {}
    for idx, series in recipe_df.iterrows():
        first_col = series[0]
        if first_col == 'Name':
            #Stop tracking if you encounter name again.
            start_track = False
            #If there was a previous recipe load it into recipes.
            if cur_recipe:
                recipes[recipe_name] = cur_recipe
            recipe_series = recipe_df.iloc[idx+1]
            recipe_name = recipe_series[0]
            cur_recipe = Recipe(recipe_name)
        if start_track:
            if first_col:
                raw_ing_series = raw_df.loc[first_col]
                ing_name = raw_ing_series['Name']
                serv_qty = float(raw_ing_series['Serving Qty'])
                serv_unit = raw_ing_series['Serving Unit']
                ingredient = Food(ing_name, serv_qty, serv_unit)
                cur_recipe.append(ingredient)
        #So the next time in the loop we will look for ingredient names.
        if cur_recipe and first_col == 'Ingredients':
            start_track = True
    return recipes

def load_food(wks):
    """Loads the active items and recipes 
    and returns their information as a dictionary.
    
    Parameters
    ----------
    wks : gspread.models.Spreadsheet
        Worksheet to read data from.
    
    Returns
    dict, dict
        Other and recipes organized.
    """
    master_df = None
    recipe_df = None
    raw_df = None
    for sheet in wks:
        title = sheet.title.lower()
        if title == 'master':
            data = sheet.get_all_values()
            master_df = pd.DataFrame(data)
            master_df = master_df.set_index(master_df[0])
        elif title == 'recipes':
            data = sheet.get_all_values()
            recipe_df = pd.DataFrame(data)
        elif title == 'raw ingredients':
            data = sheet.get_all_values()
            header = data.pop(0)
            raw_df = pd.DataFrame(data, columns=header)
            raw_df = raw_df.set_index(raw_df['Name'])
    if master_df is None or recipe_df is None or raw_df is None:
        print('Missing a data frame to load food', type(master_df), type(recipe_df), type(raw_df))
        return None, {}
    recipes = load_recipes(recipe_df, raw_df)
    return master_df, recipes

def create_shopping_list(items, master_df, recipes):
    shopping_list = {}
    for name, chosen_item in items.items():
        #Get the item to add to the shopping list if in recipes.
        recipe = recipes.get(name)
        ts = chosen_item.total_servings()
        if recipe:
            for recipe_item in recipe.ingredients:
                new_food = copy.copy(recipe_item)
                new_food *= ts
                if recipe_item.name not in shopping_list:
                    shopping_list[recipe_item.name] = new_food
                else:
                    shopping_list[recipe_item.name] += recipe_item
        else:
            master_series = master_df.loc[name]
            new_food_name = master_series[0]
            new_food_qty = float(master_series[4])
            new_food_unit = master_series[5]
            new_food = Food(new_food_name, new_food_qty, new_food_unit)
            new_food *= ts
            if name not in shopping_list:
                shopping_list[name] = new_food
            else:
                shopping_list[name] += new_food
    return shopping_list

def main(output_file='test.txt'):
    """Retrieves data from a google spreadsheet and 
    creates a shopping list from it.

    Parameters
    ----------
    user : str
        User name for the sheet.
    output_file : str, optional, default='test.txt'
        Output file to put the shopping list.

    Returns
    -------
    bool
        Whether or not the operation succeeded.
    """
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
            'x-pulsar-314603-93596a655165.json', scope) # Your json file here
    gc = gspread.authorize(credentials)
    c_plan = gc.open("Chris Food Plan")
    m_plan = gc.open("Melia's Food Plan")
    master = gc.open('Food List')
    c_dict = build_frames(c_plan)
    m_dict = build_frames(m_plan)
    items = extract_list((c_dict, m_dict))
    master_df, recipes = load_food(master)
    shopping_list = create_shopping_list(items, master_df, recipes)
    shopping_list = list(shopping_list.values())
    shopping_list.sort()
    with open(output_file, 'w+') as s_file:
        for item in shopping_list:
            s_file.write(str(item) + '\n')

if __name__ == '__main__':
    f_name = 'shopping_list.txt'
    if len(sys.argv) > 1:
        f_name, _ = os.path.splitext(sys.argv[1])
        f_name += '.txt'
    main(f_name)
