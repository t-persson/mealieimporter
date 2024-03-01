import requests
import shutil
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from logging import Logger
from .mealie import MealieRecipe, Ingredient, Instruction, Nutrition


STATIC = Path(__file__).parent.parent.joinpath("static")

class Mathem:
    api = "https://api.mathem.io/ecom-recipe/noauth/recipes/detail"

    def __init__(self, recipe: str, logger: Logger):
        self.logger = logger
        recipe = recipe.rstrip("/")
        if recipe.startswith("https://api.mathem.io"):
            url = urlparse(recipe)
            slug = parse_qs(url.query).get("url")[0]
        elif recipe.startswith("https://www.mathem.se/recept"):
            slug = recipe.rsplit("/", maxsplit=1)[1]
        else:
            raise ValueError(f"{recipe!r} is in a format that cannot be handled by the Mathem importer")
        self.url = f"{self.api}/?url={slug}"

    def categories(self, recipe: dict) -> list[str]:
        categories = (
            recipe.get("courseType") + \
            recipe.get("mealType") + \
            recipe.get("occasion") + \
            recipe.get("origin") + \
            recipe.get("diet")
        )
        return [category["name"] for category in categories]

    def ingredients(self, ingredient_groups: list[dict]) -> list[Ingredient]:
        self.logger.info("Loading ingredients from recipe")
        ingredients = []
        for group in ingredient_groups:
            for ingredient in group.get("ingredients", []):
                ingredients.append(Ingredient(
                    unit = ingredient.get("unit").lower(),
                    quantity = ingredient.get("amount"),
                    food = ingredient.get("name").lower(),
                ))
        return ingredients

    def instructions(self, steps: list[str]) -> list[Instruction]:
        self.logger.info("Loading step by step instructions from recipe")
        instructions = []
        for step in steps:
            if step[0].isdigit():
                # Mathem recipes start with "\d+. "
                step = step.split(".", maxsplit=1)[1].strip()
            if step.startswith("Recept:") or step.startswith("Foto:"):
                # Mathem credits in the instructions, for some reason
                continue
            instructions.append(Instruction(text=step))
        return instructions

    def nutritions(self, nutrition_info: str) -> Nutrition:
        if not nutrition_info:
            return None
        nutritions = {}
        print(nutrition_info)
        for nutrition in nutrition_info.split(","):
            if nutrition is None:
                continue
            split = nutrition.strip().split(" ")
            if split[-1].startswith("kcal"):
                nutritions["calories"] = split[0]
            elif split[-1].startswith("protein"):
                nutritions["proteinContent"] = split[0]
            elif split[-1].startswith("fett"):
                nutritions["fatContent"] = split[0]
            elif split[-1].startswith("kolhydrater"):
                nutritions["carbohydrateContent"] = split[0]
        print(nutritions)

    def download_image(self, image: str) -> str:
        if not image.startswith("https:"):
            image = f"https:{image}"
        response = requests.get(image, stream=True)
        response.raise_for_status()
        parsed = urlparse(image)
        filename = parsed.path.rsplit("/", maxsplit=1)[-1]
        with STATIC.joinpath(filename).open("wb") as imagefile:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, imagefile)
        return f"http://192.168.1.136:8000/static/{filename}"

    def load(self) -> MealieRecipe:
        self.logger.info(f"Loading recipe from {self.url!r}")
        response = requests.get(self.url)
        response.raise_for_status()
        recipe = response.json()
        self.logger.info(f"Recipe name {recipe.get('heading')!r}")
        imageUrl = self.download_image(recipe.get("imageUrl"))
        mealie_recipe = MealieRecipe(
            name = recipe.get("heading"),
            image = imageUrl,
            description = recipe.get("title"),
            recipeCategory = self.categories(recipe),
            tags = [],
            rating = 0,
            recipeYield = str(recipe.get("originalPortions")),
            recipeIngredient = self.ingredients(recipe.get("ingredients")),
            recipeInstructions = self.instructions(recipe.get("instructions")),
            nutrition = self.nutritions(recipe.get("nutritionInfo")),
            totalTime = recipe.get("cookingTimeString"),
            notes = [],
        )
        self.logger.info(f"Recipe has been successfully loaded from {self.url!r}")
        return mealie_recipe

if __name__ == "__main__":
    import logging
    LOGGER = logging.getLogger("Hello")
    # API = Mathem("https://api.mathem.io/ecom-recipe/noauth/recipes/detail?url=pizza-bianco-med-serrano--fetaost-och-kramigt-agg&portions=0", LOGGER)
    # print(API.url)
    API = Mathem("https://www.mathem.se/recept/pizza-bianco-med-serrano--fetaost-och-kramigt-agg", LOGGER)
    print(API.load())
    API = Mathem("https://api.mathem.io/ecom-recipe/noauth/recipes/detail?url=jordartskockssoppa-med-timjan", LOGGER)
    print(API.load())
