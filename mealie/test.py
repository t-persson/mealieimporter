import sys
import logging
import json
import requests
from slugify import slugify
from urllib.parse import urlparse
from mealie.libraries.ica import Ica
from mealie.libraries.mealie import MealieRecipe
from mealie.utilities.logging import SSEHandler

LIBRARIES = {"ica": Ica}
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb25nX3Rva2VuIjp0cnVlLCJpZCI6IjQwMGM3NTBiLTZjMWYtNDI3Ni05NTU2LWZiYjMyMzFlMTNiNSIsIm5hbWUiOiJJbXBvcnRlciIsImludGVncmF0aW9uX2lkIjoiZ2VuZXJpYyIsImV4cCI6MTg2MDY5MTk0M30.iXvhHVmvVONsMNyZxs0OXdN0ArkYUW5_OkALzals7to"

def headers():
    return {'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'}

def group_id():
    return "d0177319-6907-46fc-82d1-687d4d8b7fc5"

def update_categories(recipe: dict) -> None:
    categories = []
    for category in recipe.get("recipeCategory", []):
        slug = slugify(category)
        response = requests.get(f"https://mealie.tp-softworks.se/api/organizers/categories/slug/{slug}", headers=headers())
        if not response.ok:
            response = requests.post(f"https://mealie.tp-softworks.se/api/organizers/categories?group_id={group_id()}", headers=headers(), json={"name": category})
            response.raise_for_status()
        categories.append({
            "name": category,
            "slug": slug,
            "id": response.json().get("id"),
        })
    recipe["recipeCategory"] = categories


def get_all(url):
    response = requests.get(url, headers=headers())
    response.raise_for_status()
    response_json = response.json()
    items = response_json.get("items")
    for page in range(response_json.get("page")+1, response_json.get("total_pages")+1):
        response = requests.get(f"{url}?page={page}", headers=headers())
        response.raise_for_status()
        items += response.json().get("items")
    return items


def add_foods(recipe: dict) -> None:
    all_foods = get_all("https://mealie.tp-softworks.se/api/foods")
    food_dict = {food["name"]: food for food in all_foods}
    for ingredient in recipe.get("recipeIngredient", []):
        remote_ingredient = food_dict.get(ingredient["food"])
        if ingredient["food"] not in food_dict.keys():
            response = requests.post("https://mealie.tp-softworks.se/api/foods", headers=headers(), json={"name": ingredient["food"]})
            response.raise_for_status()
            remote_ingredient = response.json()
        ingredient["food"] = {
            "name": remote_ingredient["name"],
            "id": remote_ingredient["id"],
        }

def add_units(recipe: dict) -> None:
    all_units = get_all("https://mealie.tp-softworks.se/api/units")
    unit_dict = {unit["abbreviation"]: unit for unit in all_units}
    for ingredient in recipe.get("recipeIngredient", []):
        if ingredient["unit"] is None:
            continue
        if ingredient["unit"] not in unit_dict.keys():
            raise SystemExit(f"Unit not found {ingredient['unit']}, please add manually")
        ingredient["unit"] = {
            "name": unit_dict[ingredient["unit"]]["name"],
            "id": unit_dict[ingredient["unit"]]["id"],
        }

def add_image(slug: str, image: str):
    response = requests.post(f"https://mealie.tp-softworks.se/api/recipes/{slug}/image", headers=headers(), json={"url": image, "includeTags": True})
    response.raise_for_status()

def mealie_import(recipe: MealieRecipe):
    response = requests.post(
        f"https://mealie.tp-softworks.se/api/recipes?group_id={group_id()}",
        json={"name": recipe.name},
        headers=headers()
    )
    response.raise_for_status()
    slug = response.json()
    try:
        data = recipe.model_dump()
        update_categories(data)
        add_foods(data)
        add_units(data)
        # # print(json.dumps(data, indent=4))

        response = requests.patch(
            f"https://mealie.tp-softworks.se/api/recipes/{slug}?group_id={group_id()}",
            json=data,
            headers=headers()
        )
        response.raise_for_status()
        if data.get("image") is not None:
            add_image(slug, data["image"])
    except:
        response = requests.delete(f"https://mealie.tp-softworks.se/api/recipes/{slug}?group_id={group_id()}")
        try:
            response.raise_for_status()
        except:
            print("Error deleting recipe with slug {slug}, delete manually")
        raise

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout
    )
    logger.setLevel(logging.DEBUG)
    from queue import Queue
    q = Queue()
    logger.addHandler(SSEHandler(q))
    logger.info("Gooday")
    print(q.get_nowait())
    # API = sys.argv[1]
    # IDS = sys.argv[2:]
    # assert API.lower() in LIBRARIES.keys()
    # IMPORT_LIBRARY = LIBRARIES[API.lower()]
    # for ID in IDS:
    #     print(f"Importing {ID}")
    #     mealie_import(IMPORT_LIBRARY(ID).load())
    #     print(f"{ID} imported")
