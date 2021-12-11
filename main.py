import enum
from datetime import datetime

from fastapi import FastAPI
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError, validator
from simpleeval import simple_eval

app = FastAPI()

year = datetime.now().year


class Vehicle(BaseModel):
    year: int


class HouseOwnershipStatus(str, enum.Enum):
    owned = "owned"
    mortgaged = "mortgaged"


class House(BaseModel):
    ownership_status = HouseOwnershipStatus


class MaritalStatus(str, enum.Enum):
    single = "single"
    married = "married"


class CalculatedRiskResponse(BaseModel):
    """Example output:
    {
    "auto": "regular",
    "disability": "ineligible",
    "home": "economic",
    "life": "regular"
    }
    """

    auto: str
    disability: str
    home: str
    life: str


class UserDataInput(BaseModel):
    age: int
    dependents: int
    income: int
    marital_status: MaritalStatus
    risk_questions: List[int] = Field(max_items=3, min_items=3)
    vehicle: Optional[Vehicle]
    house: Optional[House]

    # @validator("risk_questions")
    # def validate_number_of_elements(cls, value):
    #     if len(value) != 3:
    #         raise ValueError("risk_questions must be a list of 3 integers")
    #     return value


rules = [
    # If the user doesn’t have income, vehicles or houses, she is ineligible for disability, auto, and home insurance, respectively.
    #   "income < 1", "disability", "set", "ineligible"
    #   "not vehicle", "auto", "set", "ineligible"
    #   "not house", "home", "set", "ineligible"
    # If the user is over 60 years old, she is ineligible for disability and life insurance.
    #   "age > 60", "disability", "set", "ineligible"
    #   "age > 60", "life", "set", "ineligible"
    # If the user is under 30 years old, deduct 2 risk points from all lines of insurance. If she is between 30 and 40 years old, deduct 1.
    #   "age < 30", "*", "subtract", 2
    #   "30 < age < 40", "*", "subtract", 1
    # If her income is above $200k, deduct 1 risk point from all lines of insurance.
    #   "income > 200000", "*", "subtract", 1
    # If the user's house is mortgaged, add 1 risk point to her home score and add 1 risk point to her disability score.
    #   "house.ownership_status == 'mortgaged'", "home", "add", 1
    #   "house.ownership_status == 'mortgaged'", "disability", "add", 1
    # If the user has dependents, add 1 risk point to both the disability and life scores.
    #   "dependents > 0", "disability", "add", 1
    #   "dependents > 0", "life", "add", 1
    # If the user is married, add 1 risk point to the life score and remove 1 risk point from disability.
    #   "marital_status == 'married'", "disability", "subtract", 1
    #   "marital_status == 'married'", "life", "add", 1
    # If the user's vehicle was produced in the last 5 years, add 1 risk point to that vehicle’s score.
    #     "vehicle.year > year - 5", "auto", "add", 1
    {
        "field": "",
        "condition": "",
        "action": "",
        "value": "",
    },
]


class ApplyRiskCalculation:
    def __init__(self, data: dict, rules: list):
        self.data = data
        self.data = []
        self.rules = rules
        self.base_score = self.calculate_base_score()

    def calculate_base_score(self):
        return sum(int(x) for x in self.data["risk_questions"])

    def calculate(self):
        for rule in self.rules:
            if self.evaluate_rule(rule["condition"]):
                self.apply_action(rule)
        simple_eval("'equal' if x == y else 'not equal'", names=self.data)


@app.post("/", response_model=CalculatedRiskResponse)
def home(data: UserDataInput):
    calculated_risk = ApplyRiskCalculation(data=data.dict(), rules=rules)
    return {
        "auto": "regular",
        "disability": "ineligible",
        "home": "economic",
        "life": "regular",
    }
