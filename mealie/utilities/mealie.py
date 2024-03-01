import requests
from slugify import slugify
from logging import Logger
from mealie.libraries.mealie import MealieRecipe
from mealie.libraries.ica import Ica
from mealie.libraries.mathem import Mathem

LIBRARIES = {"ica": Ica, "mathem": Mathem}
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb25nX3Rva2VuIjp0cnVlLCJpZCI6IjQwMGM3NTBiLTZjMWYtNDI3Ni05NTU2LWZiYjMyMzFlMTNiNSIsIm5hbWUiOiJJbXBvcnRlciIsImludGVncmF0aW9uX2lkIjoiZ2VuZXJpYyIsImV4cCI6MTg2MDY5MTk0M30.iXvhHVmvVONsMNyZxs0OXdN0ArkYUW5_OkALzals7to"

def headers():
    return {'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'}

def group_id():
    return "d0177319-6907-46fc-82d1-687d4d8b7fc5"


class Mealie:

    def __init__(self, logger: Logger):
        self.logger = logger
        self.api = "https://mealie.tp-softworks.se/api"

    def get_all(self, url: str, headers=headers()) -> None:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        items = response_json.get("items")
        for page in range(response_json.get("page")+1, response_json.get("total_pages")+1):
            response = requests.get(f"{url}?page={page}", headers=headers)
            response.raise_for_status()
            items += response.json().get("items")
        return items

    def update_categories(self, recipe: dict) -> None:
        categories = []
        for category in recipe.get("recipeCategory", []):
            slug = slugify(category)
            response = requests.get(f"{self.api}/organizers/categories/slug/{slug}", headers=headers())
            if not response.ok:
                self.logger.info(f"Category {category} does not exist, creating it.") 
                response = requests.post(f"{self.api}/organizers/categories?group_id={group_id()}", headers=headers(), json={"name": category})
                response.raise_for_status()
            categories.append({
                "name": category,
                "slug": slug,
                "id": response.json().get("id"),
            })
            self.logger.info(f"Category {category} has been added with id {response.json().get('id')}.") 
        recipe["recipeCategory"] = categories

    def add_foods(self, recipe: dict) -> None:
        all_foods = self.get_all(f"{self.api}/foods")
        food_dict = {food["name"]: food for food in all_foods}
        for ingredient in recipe.get("recipeIngredient", []):
            remote_ingredient = food_dict.get(ingredient["food"])
            if ingredient["food"] not in food_dict.keys():
                self.logger.info(f"Food {ingredient['food']} does not exist, creating it.")
                response = requests.post("https://mealie.tp-softworks.se/api/foods", headers=headers(), json={"name": ingredient["food"]})
                response.raise_for_status()
                remote_ingredient = response.json()
            ingredient["food"] = {
                "name": remote_ingredient["name"],
                "id": remote_ingredient["id"],
            }
            food_dict[remote_ingredient["name"]] = remote_ingredient
            self.logger.info(f"Food {remote_ingredient['name']} has been added with id {remote_ingredient['id']}.")

    def add_units(self, recipe: dict) -> None:
        all_units = self.get_all(f"{self.api}/units")
        unit_dict = {unit["abbreviation"]: unit for unit in all_units}
        for ingredient in recipe.get("recipeIngredient", []):
            if ingredient["unit"] is None:
                continue
            if ingredient["unit"] not in unit_dict.keys():
                raise Exception(f"Unit not found {ingredient['unit']}, please add manually")
            ingredient["unit"] = {
                "name": unit_dict[ingredient["unit"]]["name"],
                "id": unit_dict[ingredient["unit"]]["id"],
            }

    def add_image(self, slug: str, image: str):
        self.logger.info(f"Adding image from {image} to recipe.")
        response = requests.post(f"https://mealie.tp-softworks.se/api/recipes/{slug}/image", headers=headers(), json={"url": image, "includeTags": True})
        response.raise_for_status()
        self.logger.info(f"{image} added successfully.")

    def import_recipe(self, recipe: MealieRecipe):
        self.logger.info(f"Creating recipe with name {recipe.name}")
        try:
            response = requests.post(
                f"{self.api}/recipes?group_id={group_id()}",
                json={"name": recipe.name},
                headers=headers()
            )
            response.raise_for_status()
        except Exception as exception:
            self.logger.error(f"Failed to created recipe: {exception!s}")
            raise
        slug = response.json()
        self.logger.info(f"Slug for new recipe: {slug}")
        try:
            data = recipe.model_dump()
            self.update_categories(data)
            self.add_foods(data)
            self.add_units(data)

            self.logger.info(f"Patching in recipe information to {recipe.name}")
            response = requests.patch(
                f"{self.api}/recipes/{slug}?group_id={group_id()}",
                json=data,
                headers=headers()
            )
            response.raise_for_status()
            if data.get("image") is not None:
                self.add_image(slug, data["image"])
        except Exception as exception:
            self.logger.error(str(exception), exc_info=True)
            self.logger.info(f"Attempting to clean up recipe {recipe.name} due to errors.")
            response = requests.delete(f"{self.api}/recipes/{slug}?group_id={group_id()}", headers=headers())
            try:
                response.raise_for_status()
            except:
                self.logger.error(f"Error deleting recipe with slug {slug}, delete manually")
            raise

    def run(self, api: str, recipe: str):
        if api.lower() not in LIBRARIES.keys():
            self.logger.error(f"{api} does not exist as an importer yet")
            return
        import_library = LIBRARIES[api.lower()]
        try:
            mealie_recipe = import_library(recipe, self.logger).load()
        except ValueError as exception:
            self.logger.error(str(exception))
            return
        try:
            self.logger.info("Start the import to mealie")
            self.import_recipe(mealie_recipe)
            self.logger.info("Mealie import completed successfully!")
        except:
            pass
