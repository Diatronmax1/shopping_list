"""
Generates a text file of shopping list items based
on the sheets created on google drive for Food.
"""
import copy
import datetime as dt
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
    used_days : tuple
        Desired days from the sheet.

    Returns
    -------
    dict
        Dictionary by day of pandas data frames.
    """
    str_days = {day.strftime('%A').lower():day for day in used_days}
    days = {}
    if worksheet is None:
        return days
    for sheet in worksheet:
        sheet_name = sheet.title.lower()
        sheet_day = str_days.get(sheet_name.lower())
        if sheet_day:
            data = sheet.get_all_values()
            days[sheet_day] = pd.DataFrame(data)
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
    for sheet_name, days in user_days.items():
        for day, food_sheet in days.items():
            for row, food_row in food_sheet.iterrows():
                log_msg = f'{sheet_name} - {day} - row {row} -'
                name = food_row[0]
                qty_str = food_row[1]
                if name == '' or qty_str == '':
                    continue
                if name in ignored_rows:
                    continue
                try:
                    qty = float(qty_str)
                    unit_type = food_row[2]
                    serv_weight_as_grams = food_row[11]
                except KeyError as key_exc:
                    msg = f'{log_msg} Failed to retrieve values {key_exc}'
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
                    item.sheets.add(sheet_name)
                    item.days.add(day)
                    if unit_type == 'grams':
                        if serv_weight_as_grams == '':
                            continue
                        try:
                            serv_weight_as_grams = float(serv_weight_as_grams)
                        except ValueError:
                            msg = f'Failed to convert {name} serv_weight (g) {serv_weight_as_grams}'
                            logger.exception(item.exc_str(msg))
                            continue
                        item.add_grams(qty, serv_weight_as_grams)
                    elif unit_type == 'servings':
                        item.add_servings(qty)
                    else:
                        msg = f'Unrecognized unit_type {unit_type} for {name}'
                        logger.warning(item.exc_str(msg))
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
    already_have : set
        If provided, will skip items that we know we have.

    Returns
    -------
    dict
        A collection of foods with proper servings and
        units appended to them.
    """
    logger = logging.getLogger(__name__)
    shopping_list = {}
    #Grab a list of food names to build a list of needed recipes.
    food_names = list(items.keys())
    ignored = {}
    for name in food_names:
        #Dont look for it later in master
        if name in recipes:
            recipe = recipes[name]
            chosen_item = items.pop(name)
            total_s = chosen_item.total_servings()
            #Gurantees we always create whole numbers of recipes.
            total_s = math.ceil(total_s*recipe.rec_per_serv)
            for rec_ing in recipe.ingredients:
                new_food = copy.copy(rec_ing)
                new_food.days |= chosen_item.days
                #Update the food item to the max of needed recipes.
                new_food *= total_s
                if new_food.name.lower() in already_have:
                    if new_food.name in ignored:
                        ignored[new_food.name] += new_food.amount
                    else:
                        ignored[new_food.name] = new_food.amount
                    continue
                if new_food.name in shopping_list:
                    shopping_list[new_food.name] += new_food
                else:
                    shopping_list[new_food.name] = new_food
    #Now grab all remaining food items from the master df. Report any missing items
    #to the user.
    for chosen_name, chosen_item in items.items():
        if chosen_name not in master_df.index:
            msg = f'{chosen_name} cant be found in master list!'
            logger.exception(chosen_item.exc_str(msg))
            continue
        master_series = master_df.loc[chosen_name]
        total_g = chosen_item.total_grams()
        total_s = chosen_item.total_servings()
        try:
            new_food = Food.from_masterlist(master_series, total_g, UREG)
        except ValueError:
            msg = f'Failed to convert {chosen_name} from master list'
            logger.exception(chosen_item.exc_str(msg))
        #Update the days this food is needed.
        new_food.days |= chosen_item.days
        new_food *= total_s
        if new_food.name.lower() in already_have:
            if new_food.name in ignored:
                ignored[new_food.name] += new_food.amount
            else:
                ignored[new_food.name] = new_food.amount
                continue
        if new_food.name in shopping_list:
            shopping_list[new_food.name] += new_food
        else:
            shopping_list[new_food.name] = new_food
    #Alert the user that we are ignoring these items.
    for food_name, amount in ignored.items():
        msg = f'Assuming already have {amount:.2f} of {food_name}'
        logger.info(msg)
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

def main(sheet_data, output_file='shopping_list.txt', string_io=None, already_have=None):
    """
    Retrieves data from a google spreadsheet and
    creates a shopping list from it.

    Parameters
    ----------
    sheet_data : dict
        Names of the sheets to open from google and the
        days as datetimes to use from those sheets.
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
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
            'pers_key.json', scope) # Your json file here
    google_sheets = gspread.authorize(credentials)
    days = {}
    for name, used_days in sheet_data.items():
        msg = f'Grabbing food from {name}'
        logger.info(msg)
        try:
            sheet = google_sheets.open(name)
        except gspread.exceptions.APIError:
            msg = f'Unable to open {name}!'
            logger.exception(msg)
            return
        days[name] = load_food_plan(sheet, used_days)
    logger.info('Grabbing master food list')
    master_df, recipes = load_food_list(google_sheets.open('Food List'))
    logger.info('Combining food sheets')
    food_by_day = build_food_from_days(days)
    logger.info('Creating the food list')
    shopping_list = create_shopping_list(food_by_day, master_df, recipes, already_have)
    shopping_list = list(shopping_list.values())
    shopping_list.sort()
    shopping_groups = build_groups(shopping_list)
    today = dt.date.today()
    with open(output_file, 'w+', encoding='utf-8') as s_file:
        first_line = ''
        second_line = ''
        for day_num in range(7):
            day = today + dt.timedelta(days=day_num)
            end = ' '
            if day_num == 6:
                end = ''
            day_block = f"{day.strftime('%A')}{end}"
            first_line += day_block
            date_block = day.strftime('%m/%d')
            add_len = len(day_block) - len(date_block)
            date_block += ' '*add_len
            second_line += date_block
        s_file.write(first_line + '\n')
        s_file.write(second_line + '\n\n')
        for group_name, food_list in shopping_groups.items():
            s_file.write(group_name + '\n')
            s_file.write('-'*len(group_name) + '\n')
            for food_item in food_list:
                s_file.write(f'{food_item}\n')
            s_file.write('\n')
    msg = f'File Created {output_file}'
    logger.info(msg)
