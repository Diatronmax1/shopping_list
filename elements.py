"""
Defines the portions of the online google
with items that we want for the sheet.
"""

class Food():
    """
    An element of the list with a name and serving amt.

    Parameters
    ----------
    name : str
        Name of the food.
    serving_qty : float
        Amount in a serving.
    serving_unit : str
        The units of the serving.
    """
    def __init__(self, name, serving_qty, serving_unit):
        self.name = name
        self.serving_qty = serving_qty
        self.serving_unit = serving_unit

    def __str__(self):
        return f'{self.serving_qty} {self.serving_unit} {self.name}'

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
    """
    Recipe is comprised of one unit
    of itself, with many ingredients building
    up that one unit.

    Parameters
    ----------
    name : str
        Name of the recipe.
    servs_per_rec : float
        How much a single serving constitues a recipe. I.e
        0.125 means 8 servings is a full recipe.
    ingredients : list, optional, default=None
        List of food objects.

    """

    def __init__(self, name, servs_per_rec, ingredients=None):
        self.name = name
        self.servs_per_rec = servs_per_rec
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
        self.servings = 0
        self.grams = 0
        self.gram_per_serv = None
        self.days = set()

    def __str__(self):
        return f'{self.name} {self.total_servings()} servings'

    def add_servings(self, servings):
        """
        Updates servings.

        Parameters
        ----------
        servings : float
            Number of servings to add to this item.
        """
        self.servings += servings

    def add_grams(self, grams, gram_weight):
        """
        Updates grams.

        Parameters
        ----------
        grams : float
            Number of grams to add to this item.
        """
        self.grams += grams
        self.gram_per_serv = gram_weight

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
        if self.gram_per_serv:
            start_serv += self.grams/self.gram_per_serv
        return start_serv

    def total_grams(self):
        """
        Compiles the total number of grams for this item.

        Returns
        -------
        float
            Number of grams for this item.
        """
        if self.gram_per_serv is None:
            return
        start_grams = self.grams
        if self.servings and self.gram_per_serv:
            start_grams += self.servings * self.gram_per_serv
        return start_grams
