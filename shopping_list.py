"""
Generates a text file of shopping list items based
on the sheets created on google drive for Food.
"""
import copy
import os
from pathlib import Path
import logging
import math

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from pint import UnitRegistry

from elements import ChosenItem, Food, Recipe

os.chdir(Path(__file__).parent)

UREG = UnitRegistry()
UREG.load_definitions('unit_def.txt')

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
    if worksheet is None:
        return days
    use_all = not any(used_days)
    for sheet in worksheet:
        name = sheet.title.lower()
        if name in week_days:
            if used_days.get(name) or use_all:
                data = sheet.get_all_values()
                days[name] = pd.DataFrame(data)
    return days

def build_food_from_days(user_days):
    """
    Retrieves data for each chosen item by day.

    Parameters
    ----------
    days : tuple
        Named dictionaries containing days for each user.

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
    for user_name, days in user_days.items():
        for day, food_sheet in days.items():
            for row, food_row in food_sheet.iterrows():
                log_msg = f'{user_name} - {day} - row {row} -'
                name = food_row[0]
                qty_str = food_row[1]
                if name == '' or qty_str == '':
                    continue
                if name in ignored_rows:
                    continue
                try:
                    qty = float(qty_str)
                    unit_type = food_row[2]
                    gram_weight = food_row[12]
                except KeyError as key_exc:
                    msg = f'{log_msg} Failed to retreive values {key_exc}'
                    logger.warning(msg)
                    continue
                except ValueError:
                    msg = f'{log_msg} Unable to convert qty {food_row[1]}'
                    logger.warning(msg)
                    continue
                #Gurantees Item is available.
                if name and qty:
                    new_item = False
                    item = items.get(name)
                    if item is None:
                        item = ChosenItem(name)
                        new_item = True
                    item.days.add(day)
                    if unit_type == 'grams':
                        if gram_weight == '':
                            continue
                        try:
                            gram_weight = float(gram_weight)
                        except ValueError:
                            msg = f'Failed to convert {name} gram_weight {gram_weight}'
                            logger.warning(msg)
                            continue
                        item.add_grams(qty, gram_weight)
                    elif unit_type == 'servings':
                        item.add_servings(qty)
                    else:
                        msg = f'Unrecognized unit_type {unit_type} for {name}'
                        logger.warning(msg)
                        continue
                    if new_item:
                        items[name] = item
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
            rec_per_serv = float(recipe_series[6])
            cur_recipe = Recipe(recipe_name, rec_per_serv)
        if start_track:
            if first_col:
                raw_ing_series = raw_df.loc[first_col]
                ing_name = raw_ing_series['Name']
                serv_str = raw_ing_series['Serving Qty']
                amt_str = series[8]
                try:
                    serv_qty = float(serv_str)
                    #Grab the qty from the recipe.
                    serv_amt = float(amt_str)
                except ValueError:
                    msg = f'Failed to convert {serv_str} or {amt_str} on {ing_name}'
                    logger.warning(msg)
                    continue
                serv_unit = raw_ing_series['Serving Unit']
                amount = serv_qty * UREG(serv_unit)
                #Grab the preferred unit from the recipe.
                rec_unit = series[2]
                food_type = raw_ing_series['Food Type']
                new_food = Food(ing_name, amount, rec_unit, food_type)
                new_food *= serv_amt
                cur_recipe.append(new_food)
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
    if master_df is None:
        logger.exception('Missing master dataframe from food list')
        return None, {}
    if recipe_df is None:
        logger.exception('Missing recipe dataframe')
        return None, {}
    if raw_df is None:
        logger.exception('Missing Raw Ingredient dataframe.')
        return None, {}
    recipes = load_recipes(recipe_df, raw_df)
    return master_df, recipes

def create_shopping_list(items, master_df, recipes, already_have):
    """
    Builds the shopping list based on the items provided.

    Parameters
    ----------
    items : dict
        Chosen items from Food Sheets.
    master_df : pd.DataFrame
        Contains all of the food information.
    recipes : dict
        Dictionary of recipes.
    already_have : set, optional, default=None
        If provided, will skip items that we know we have.

    Returns
    -------
    dict
        A collection of foods with proper servings and
        units appended to them.
    """
    if already_have is None:
        already_have = set()
    logger = logging.getLogger(__name__)
    shopping_list = {}
    for chosen_name, chosen_item in items.items():
        total_s = chosen_item.total_servings()
        total_g = chosen_item.total_grams()
        #Get the item to add to the shopping list if in recipes.
        recipe = recipes.get(chosen_name)
        if recipe:
            #If the number of items requested exceeds 1 recipe
            #round up so that 2 recipe amounts are ordered.
            total_recipes = math.ceil(total_s*recipe.rec_per_serv)
            for ing in recipe.ingredients:
                new_food = copy.copy(ing)
                new_food.days |= chosen_item.days
                new_food *= total_recipes
                ing_name = new_food.name.lower()
                if ing_name in already_have:
                    msg = f'Assuming already have {new_food.amount:.2f} of {ing_name}'
                    logger.info(msg)
                    continue
                if ing.name not in shopping_list:
                    shopping_list[ing.name] = new_food
                else:
                    shopping_list[ing.name] += new_food
            continue
        #Find the item in the master list.
        master_series = master_df.loc[chosen_name]
        new_food_name = master_series[0]
        new_qty_str = master_series[4]
        new_food_unit = master_series[5]
        new_grams_str = master_series[6]
        new_food_type = master_series[11]
        try:
            new_food_qty = float(new_qty_str)
        except ValueError as exc1:
            msg = f'Failed to convert {new_food_name} {new_qty_str} qty {exc1}'
            if total_g is None or total_g == 0:
                logger.warning(msg)
                continue
            try:
                new_food_grams = float(new_grams_str)
                new_food_qty = new_food_grams/total_g
            except ValueError as exc2:
                msg = f'{msg} {exc2}'
                logger.warning(msg)
                continue
        amount = new_food_qty * UREG(new_food_unit)
        new_food = Food(new_food_name, amount, new_food_unit, new_food_type)
        #Update the days this food is needed.
        new_food.days |= chosen_item.days
        new_food *= total_s
        if new_food.name.lower() in already_have:
            msg = f'Assuming already have {new_food.amount:.2f} of {new_food.name}'
            logger.info(msg)
            continue
        if new_food.name not in shopping_list:
            shopping_list[new_food.name] = new_food
        else:
            shopping_list[new_food.name] += new_food
    return shopping_list

def build_groups(shopping_list):
    """
    Takes a list of Food items and creates a dictionary
    organized by food_type. Blank food types will be appended
    to the end as a No Category.

    Parameters
    ----------
    shopping_list : list
        Input list of Food items.

    Returns
    -------
    dict
        Organized by group name (food type), and the food
        items in that group.
    """
    groups = {}
    no_group = []
    for food_item in shopping_list:
        if food_item.food_type == '':
            no_group.append(food_item)
            continue
        if food_item.food_type not in groups:
            groups[food_item.food_type] = []
        groups[food_item.food_type].append(food_item)
    groups['No Category'] = no_group
    return groups

def main(used_days, output_file='shopping_list.txt', string_io=None, already_have=None):
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
    if not any(used_days):
        logger.info('Building sheet for all days')
    else:
        msg = f'Building sheet with {[day for day, used in used_days.items() if used]}'
        logger.info(msg)
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
            'pers_key.json', scope) # Your json file here
    google_sheets = gspread.authorize(credentials)
    logger.info('Grabbing Chris food')
    sheets = {}
    try:
        chris_plan = google_sheets.open('Chris Food Plan')
        sheets['chris'] = chris_plan
    except gspread.exceptions.APIError:
        logger.exception('Unable to open Chris sheet!')
        return
    logger.info('Grabbing Melia food')
    try:
        melia_plan = google_sheets.open("Melia's Food Plan")
        sheets['melia'] = melia_plan
    except gspread.exceptions.APIError:
        logger.exception('Unable to open Melias sheet!')
        return
    days = {}
    chris_days = load_food_plan(sheets.get('chris'), used_days)
    if chris_days:
        days['chris'] = chris_days
    mel_days = load_food_plan(sheets.get('melia'), used_days)
    if mel_days:
        days['melia'] = mel_days
    logger.info('Grabbing master food list')
    master_df, recipes = load_food_list(google_sheets.open('Food List'))
    logger.info('Combining chris and melia food')
    food_by_day = build_food_from_days(days)
    logger.info('Creating the food list')
    shopping_list = create_shopping_list(food_by_day, master_df, recipes, already_have)
    shopping_list = list(shopping_list.values())
    shopping_list.sort()
    shopping_groups = build_groups(shopping_list)
    with open(output_file, 'w+', encoding='utf-8') as s_file:
        for group_name, food_list in shopping_groups.items():
            s_file.write(group_name + '\n')
            s_file.write('-'*len(group_name) + '\n')
            for food_item in food_list:
                s_file.write(f'{food_item}\n')
            s_file.write('\n')
    msg = f'File Created {output_file}'
    logger.info(msg)

if __name__ == '__main__':
    F_NAME = 'shopping_list.txt'
    main({}, F_NAME, already_have=set(['cumin']))
