"""
Generates a text file of shopping list items based
on the sheets created on google drive for Food.
"""
import copy
import logging
import math
import os
import sys

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

from elements import ChosenItem, Food, Recipe

def load_food_plan(worksheet, used_days):
    """
    Creates data frames by days for a worksheet.

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
    use_all = any(used_days)
    for sheet in worksheet:
        name = sheet.title.lower()
        if name in week_days:
            if used_days.get(name) or use_all:
                data = sheet.get_all_values()
                days[name] = pd.DataFrame(data)
    return days

def build_food_from_days(day_dicts):
    """
    Retrieves data for each chosen item by day.

    Parameters
    ----------
    day_dicts : tuple
        Any number of Dictionary of days by
        dataframes from a food plan.

    Returns
    -------
    dict
        Dictionary by days of extracted data.
    """
    logger = logging.getLogger(__name__)
    ignored_rows = (
        'Breakfast',
        'Lunch',
        'Snack',
        'Dinner',
        'Desert',
        'Stick To',
        'Totals',
        'Differences'
        )
    items = {}
    for day_dict in day_dicts:
        for day, food_sheet in day_dict.items():
            for _, food_row in food_sheet.iterrows():
                if food_row[0] == '' or food_row[1] == '':
                    continue
                try:
                    name = food_row[0]
                    qty = float(food_row[1])
                    unit_type = food_row[2]
                    gram_weight = food_row[12]
                except Exception as exc:
                    logger.warning(f'Failed to retrive values {exc}')
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
                        except Exception:
                            logger.warning(f'Failed to convert {name} gram_weight {gram_weight}')
                            continue
                        print(qty, gram_weight)
                        item.add_grams(qty, gram_weight)
                    elif unit_type == 'servings':
                        item.add_servings(qty)
                    else:
                        logger.warning(f'Unrecognized unit_type {unit_type} for {name}')
                        continue
    return items

def load_recipes(recipe_df, raw_df):
    """
    Loads recipes for the shopping list.

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
    logger = logging.getLogger(__name__)
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
            servs_per_rec = float(recipe_series[6])
            cur_recipe = Recipe(recipe_name, servs_per_rec)
        if start_track:
            if first_col:
                raw_ing_series = raw_df.loc[first_col]
                ing_name = raw_ing_series['Name']
                try:
                    serv_qty = float(raw_ing_series['Serving Qty'])
                    #Grab the qty from the recipe.
                    serv_amt = float(series[8])
                except Exception as exc:
                    logger.warning(f'Failed on {ing_name} {exc}')
                    continue
                serv_unit = raw_ing_series['Serving Unit']
                ingredient = Food(ing_name, serv_qty, serv_unit)
                ingredient *= serv_amt
                cur_recipe.append(ingredient)
        #So the next time in the loop we will look for ingredient names.
        if cur_recipe and first_col == 'Ingredients':
            start_track = True
    return recipes

def load_food_list(wks):
    """
    Loads the active items and recipes
    and returns their information as a dictionary.

    Parameters
    ----------
    wks : gspread.models.Spreadsheet
        Worksheet to read data from.

    Returns
    dict, dict
        Other and recipes organized.
    """
    logger = logging.getLogger(__name__)
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
        msg = 'Missing a data frame to load food'
        msg += f'{type(master_df)}, {type(recipe_df)}, {type(raw_df)}'
        logger.warning(msg)
        return None, {}
    recipes = load_recipes(recipe_df, raw_df)
    return master_df, recipes

def create_shopping_list(items, master_df, recipes):
    """
    Builds the shopping list based on the items provided.

    Parameters
    ----------
    items : dict
        The input items of food and recipes.
    master_df : pd.DataFrame
        Dataframe containing additional recipe and food info.
    recipes : dict
        Dictionary of recipes.
    """
    logger = logging.getLogger(__name__)
    shopping_list = {}
    for name, chosen_item in items.items():
        #Get the item to add to the shopping list if in recipes.
        recipe = recipes.get(name)
        total_s = chosen_item.total_servings()
        total_g = chosen_item.total_grams()
        if recipe:
            #The total servings need to be reduced by
            #the recipe ratio.
            total_recipes = math.ceil(total_s*recipe.servs_per_rec)
            for recipe_item in recipe.ingredients:
                new_food = copy.copy(recipe_item)
                new_food *= total_recipes
                if recipe_item.name not in shopping_list:
                    shopping_list[recipe_item.name] = new_food
                else:
                    shopping_list[recipe_item.name] += recipe_item
        else:
            master_series = master_df.loc[name]
            new_food_name = master_series[0]
            new_food_unit = master_series[5]
            try:
                new_food_qty = float(master_series[4])
            except Exception as exc1:
                msg = f'Failed to convert {name} {master_series[4]} qty {exc1}'
                if total_g is None:
                    logger.warning(msg)
                    continue
                try:
                    new_food_grams = float(master_series[6])
                    new_food_qty = new_food_grams/total_g
                except Exception as exc2:
                    logger.warning(f'{msg} {exc2}')
                    continue
            new_food = Food(new_food_name, new_food_qty, new_food_unit)
            new_food *= total_s
            if name not in shopping_list:
                shopping_list[name] = new_food
            else:
                shopping_list[name] += new_food
    return shopping_list

def main(used_days, output_file='shopping_list.txt', string_io=None):
    """
    Retrieves data from a google spreadsheet and
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
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    if string_io and not logger.hasHandlers():
        stream_handle = logging.StreamHandler(string_io)
        stream_handle.flush()
        stream_handle.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        stream_handle.setFormatter(formatter)
        logger.addHandler(stream_handle)
    logger.info(f'Building sheet with {[day for day, used in used_days.items() if used]}')
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
            'pers_key.json', scope) # Your json file here
    google_sheets = gspread.authorize(credentials)
    logger.info('Grabbing Chris food')
    try:
        chris_plan = google_sheets.open('Chris Food Plan')
    except gspread.exceptions.APIError:
        logger.exception('Unable to open Chris sheet!')
        return
    try:
        melia_plan = google_sheets.open("Melia's Food Plan")
    except gspread.exceptions.APIError:
        logger.exception('Unable to open Melias sheet!')
        return
    chris_days = load_food_plan(chris_plan, used_days)
    logger.info('Grabbing Melia food')
    mel_days = load_food_plan(melia_plan, used_days)
    logger.info('Grabbing master food list')
    master_df, recipes = load_food_list(google_sheets.open('Food List'))
    logger.info('Combining chris and melia food')
    food_by_day = build_food_from_days((chris_days, mel_days))
    logger.info('Creating the food list')
    shopping_list = create_shopping_list(food_by_day, master_df, recipes)
    shopping_list = list(shopping_list.values())
    shopping_list.sort()
    with open(output_file, 'w+', encoding='utf-8') as s_file:
        for item in shopping_list:
            s_file.write(f'{item}\n')
    logger.info(f'File Created {output_file}')

if __name__ == '__main__':
    F_NAME = 'shopping_list.txt'
    if len(sys.argv) > 1:
        F_NAME, _ = os.path.splitext(sys.argv[1])
        F_NAME += '.txt'
    print('Creating file', F_NAME)
    main({}, F_NAME)
