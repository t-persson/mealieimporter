from uuid import uuid4
from typing import Optional
from pydantic import BaseModel, Field


def uuidstr():
    return str(uuid4())


class Ingredient(BaseModel):
    referenceId: str = Field(default_factory=uuidstr)
    title: Optional[str] = ""
    note: Optional[str] = ""
    unit: Optional[str]
    food: Optional[str] = None
    disableAmount: bool = False
    quantity: float


class Instruction(BaseModel):
    id: str = Field(default_factory=uuidstr)
    title: Optional[str] = ""
    text: str
    ingredientReferences: list[str] = []


class Nutrition(BaseModel):
    calories: Optional[float] = None
    fatContent: Optional[float] = None
    proteinContent: Optional[float] = None
    carbohydrateContent: Optional[float] = None
    fiberContent: Optional[float] = None
    sodiumContent: Optional[float] = None
    sugarContent: Optional[float] = None


class Settings(BaseModel):
    public: bool = True
    showNutrition: bool = True
    showAssets: bool = True
    landscapeView: bool = True
    disableComments: bool = False
    disableAmount: bool = False


class Note(BaseModel):
    title: Optional[str]
    text: str


class MealieRecipe(BaseModel):
    name: str
    image: Optional[str]
    description: str
    recipeCategory: list[str]
    tags: list[str]
    rating: int
    recipeYield: str
    recipeIngredient: list[Ingredient]
    recipeInstructions: list[Instruction]
    nutrition: Optional[Nutrition]
    totalTime: str
    prepTime: str = ""
    performTime: str = ""
    settings: Settings = Settings()
    assets: list = []
    notes: list[Note]
    orgURL: Optional[str] = None
    extras: Optional[dict] = {}
    comments: Optional[list] = []


