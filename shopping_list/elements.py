"""
Defines the portions of the online google
with items that we want for the sheet.
"""

from pint import DimensionalityError

def day_shortstr(days, fmt='%a'):
    """
    Retrieves a modified short string version of the
    days this food is required.

    Returns
    =======
    str
    """
    days = sorted(days)
    return f"({','.join([day.strftime(fmt) for day in days])})"

class Food():
    """
    An element of the list with a name and serving amt.

    Parameters
    ----------
    name : str
        Name of the food.
    amount : pint.Unit
        Unit from pint.
    rec_unit : str
        The unit if this came from a recipe. If
        just created will be the string that
        the amount was made from.
    food_type : str
        The type of food this is, used for categorizing
        the shopping_list

    """

    def __init__(self, name, amount, rec_unit, food_type):
        self.name = name
        self.amount = amount
        self.rec_unit = rec_unit
        self.food_type = food_type.lower()
        self.days = set()

    @classmethod
    def from_masterlist(cls, series, total_g, ureg):
        """
        Builds the food item from the master list
        pandas dataframe.

        Parameters
        ----------
        series : pd.Series
            Series for the new Food item from Master.
        total_g : float
            The total number of grams for the food from
            the chosen item if units are in grams.
        ureg : UnitRegistry
            Provided to keep one instance of the units
            registry alive.

        Returns
        -------
        Food
            The created food item.
        """
        name = series[0]
        qty_str = series[4]
        food_unit = series[5]
        grams_str = series[6]
        food_type = series[11]
        try:
            food_qty = float(qty_str)
        except ValueError as exc1:
            msg = f'Failed to convert {name} {qty_str} qty {exc1}'
            if total_g is None or total_g == 0:
                raise ValueError(msg) from exc1
            food_grams = float(grams_str)
            food_qty = food_grams/total_g
        amount = food_qty * ureg(food_unit)
        return cls(name, amount, food_unit, food_type)

    def day_shortstr(self):
        """
        Retrieves a modified short string version of the
        days this food is required.

        Returns
        =======
        str
        """
        if self.food_type == 'Meat':
            return day_shortstr(self.days, '%m/%d')
        return day_shortstr(self.days)

    def __str__(self):
        unit = self.amount
        try:
            unit = self.amount.to(self.rec_unit)
        except DimensionalityError:
            pass
        return f'{unit:.2f} {self.name} {self.day_shortstr()}'

    def __lt__(self, other):
        return self.name < other.name

    def __copy__(self):
        return type(self)(self.name, self.amount, self.rec_unit, self.food_type)

    def __iadd__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError(f'Can only add food items to each other not {other}')
        self.amount += other.amount
        self.days |= other.days
        return self

    def __imul__(self, other):
        self.amount *= other
        return self

class Recipe():
    """
    Recipe is comprised of one unit
    of itself, with many ingredients building
    up that one unit.

    Parameters
    ----------
    name : str
        Name of the recipe.
    rec_per_serv : float
        How much of a recipe is in a serving, used
        to determine full portions.
    ingredients : list, optional, default=None
        List of food objects.

    """

    def __init__(self, name, rec_per_serv, ingredients=None):
        self.name = name
        self.rec_per_serv = rec_per_serv
        self.days = set()
        self.ingredients = []
        if ingredients:
            self.ingredients = ingredients

    def __str__(self):
        return f'{self.name} with {len(self.ingredients)} ingredients.'

    def append(self, item):
        """
        Adds an item to ingredients.

        Parameters
        ----------
        item : Ingredient
            New ingredient for the Recipe.
        """
        self.ingredients.append(item)

class ChosenItem():
    """
    Container class for items chosen by the sheet user.

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
        self.sheets = set()
        self.servings = 0
        self.grams = 0
        self.serv_weight_as_grams = None
        self.days = set()

    def __str__(self):
        return f'{self.name} {self.total_servings()} servings'

    def exc_str(self, msg=''):
        """
        Returns a formatted info string for exceptions.
        """
        return msg + f" {self.sheets} {[day.strftime('%a') for day in self.days]}"

    def add_servings(self, servings):
        """
        Updates servings.

        Parameters
        ----------
        servings : float
            Number of servings to add to this item.
        """
        self.servings += servings

    def add_grams(self, grams, serv_weight_as_grams):
        """
        Updates grams.

        Parameters
        ----------
        grams : float
            Number of grams to add to this item.
        """
        self.grams += grams
        self.serv_weight_as_grams = serv_weight_as_grams

    def total_servings(self):
        """
        Compiles the total number of servings for
        this item.

        Returns
        -------
        float
            Number of servings for this item.
        """
        start_serv = self.servings
        if self.serv_weight_as_grams:
            start_serv += self.grams/self.serv_weight_as_grams
        return start_serv

    def total_grams(self):
        """
        Compiles the total number of grams for this item.

        Returns
        -------
        float
            Number of grams for this item.
        """
        if self.serv_weight_as_grams is None:
            return
        start_grams = self.grams
        if self.servings and self.serv_weight_as_grams:
            start_grams += self.servings * self.serv_weight_as_grams
        return start_grams
