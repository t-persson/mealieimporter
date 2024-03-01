import requests
from logging import Logger
from .mealie import MealieRecipe, Ingredient, Instruction, Nutrition


class Ica:
    pattern = "handla.api.ica.se"
    api = "https://handla.api.ica.se/api/recipes/recipe"

    def __init__(self, recipe: str, logger: Logger):
        self.logger = logger
        recipe = recipe.rstrip("/")
        if recipe.startswith("https://handla.api.ica.se/api/recipes/recipe"):
            id = recipe.rsplit("/", maxsplit=1)[1]
        elif recipe.startswith("https://www.ica.se/recept"):
            partial = recipe.rsplit("/", maxsplit=1)[1]
            id = partial.rsplit("-", maxsplit=1)[1]
        elif recipe.isdigit():
            id = recipe
        else:
            raise ValueError(f"{recipe!r} is in a format that cannot be handled by the ICA importer")
        self.url = f"{self.api}/{id}"

    def ingredients(self, ingredient_groups: list[dict]) -> list[Ingredient]:
        self.logger.info("Loading ingredients from recipe")
        ingredients = []
        for ingredient_group in ingredient_groups:
            for ingredient in ingredient_group.get("Ingredients", []):
                ingredients.append(Ingredient(
                    unit = ingredient.get("Unit"),
                    quantity = ingredient.get("Quantity"),
                    food = ingredient.get("Ingredient"),
                ))
        return ingredients

    def instructions(self, steps: list[str]) -> list[Instruction]:
        self.logger.info("Loading step by step instructions from recipe")
        instructions = []
        for step in steps:
            instructions.append(Instruction(text=step))
        return instructions

    def nutritions(self, per_portion: dict) -> Nutrition:
        if per_portion is None:
            return None
        # TODO: Should these be calculated to be for full recipe
        self.logger.info("Loading nutrition information from recipe")
        return Nutrition(
            calories = per_portion.get("KCalories"),
            fatContent = per_portion.get("Fat"),
            proteinContent = per_portion.get("Protein"),
            carbohydrateContent = per_portion.get("Carbohydrate"),
            sodiumContent = per_portion.get("Salt"),
        )

    def load(self) -> MealieRecipe:
        self.logger.info(f"Loading recipe from {self.url!r}")
        response = requests.get(self.url)
        response.raise_for_status()
        recipe = response.json()
        self.logger.info(f"Recipe name {recipe.get('Title')!r}")
        mealie_recipe = MealieRecipe(
            name = recipe.get("Title"),
            image = recipe.get("ImageUrl"),
            description = recipe.get("PreambleHTML"),
            recipeCategory = recipe.get("MdsaCategories") + recipe.get("Categories"),
            tags = [],
            rating = 0,
            recipeYield = str(recipe.get("Portions")),
            recipeIngredient = self.ingredients(recipe.get("IngredientGroups")),
            recipeInstructions = self.instructions(recipe.get("CookingSteps")),
            nutrition = self.nutritions(recipe.get("NutritionPerPortion")),
            totalTime = recipe.get("CookingTime"),
            notes = [],
        )
        self.logger.info(f"Recipe has been successfully loaded from {self.url!r}")
        return mealie_recipe


if __name__ == "__main__":
    ICA = Ica("https://www.ica.se/recept/scones-690203/")
    print(ICA.url)
    ICA = Ica("https://handla.api.ica.se/api/recipes/recipe/715613")
    print(ICA.url)
    ICA = Ica("12345")
    print(ICA.url)
