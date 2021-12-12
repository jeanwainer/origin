import enum
import logging
from datetime import datetime

from fastapi import FastAPI
from typing import List, Optional
from pydantic import BaseModel, Field
from simpleeval import simple_eval

app = FastAPI()
logger = logging.getLogger(__name__)


class Vehicle(BaseModel):
    year: Optional[int]


class HouseOwnershipStatus(str, enum.Enum):
    owned = "owned"
    mortgaged = "mortgaged"


class House(BaseModel):
    ownership_status = HouseOwnershipStatus


class MaritalStatus(str, enum.Enum):
    single = "single"
    married = "married"


class RiskScore(str, enum.Enum):
    ineligible = "ineligible"
    economic = "economic"
    regular = "regular"
    responsible = "responsible"

    @classmethod
    def from_rating(cls, rating: int) -> "RiskScore":
        if rating is None:
            return cls.ineligible
        if rating < 0:
            return cls.economic
        if rating < 3:
            return cls.regular
        return cls.responsible


class CalculatedRiskResponse(BaseModel):
    auto: RiskScore
    disability: RiskScore
    home: RiskScore
    life: RiskScore


class UserDataInput(BaseModel):
    age: int
    dependents: int
    income: int
    marital_status: MaritalStatus
    risk_questions: List[bool] = Field(max_items=3, min_items=3)
    vehicle: Optional[Vehicle]
    house: Optional[House]


SCORE_RULES = [
    # If the user doesn’t have income, vehicles or houses, she is ineligible for disability, auto, and home insurance, respectively.
    ("income < 1", "disability", "set", "ineligible"),
    ("not vehicle", "auto", "set", "ineligible"),
    ("not house", "home", "set", "ineligible"),
    # If the user is over 60 years old, she is ineligible for disability and life insurance.
    ("age > 60", "disability,life", "set", "ineligible"),
    # ("age > 60", "life", "set", "ineligible"),
    # If the user is under 30 years old, deduct 2 risk points from all lines of insurance. If she is between 30 and 40 years old, deduct 1.
    ("age < 30", "*", "subtract", 2),
    ("30 < age < 40", "*", "subtract", 1),
    # If her income is above $200k, deduct 1 risk point from all lines of insurance.
    ("income > 200000", "*", "subtract", 1),
    # If the user's house is mortgaged, add 1 risk point to her home score and add 1 risk point to her disability score.
    ("house.ownership_status == 'mortgaged'", "home,disability", "add", 1),
    # ("house.ownership_status == 'mortgaged'", "disability", "add", 1),
    # If the user has dependents, add 1 risk point to both the disability and life scores.
    ("dependents > 0", "disability,life", "add", 1),
    # ("dependents > 0", "life", "add", 1),
    # If the user is married, add 1 risk point to the life score and remove 1 risk point from disability.
    ("marital_status == 'married'", "disability", "subtract", 1),
    ("marital_status == 'married'", "life", "add", 1),
    # If the user's vehicle was produced in the last 5 years, add 1 risk point to that vehicle’s score.
    ("vehicle['year'] > current_year - 5", "auto", "add", 1),
]


class ApplyRiskCalculation:
    actions = {"add": "+", "subtract": "-"}

    def __init__(self, data: dict, rules: list):
        self.data = data
        self.data["current_year"] = datetime.now().year
        self.rules = [
            {"condition": r[0], "field": r[1], "action": r[2], "value": r[3]}
            for r in rules
        ]
        base_score = self.calculate_base_score()
        logger.info(f"Base score: {base_score}")
        self.fields = {
            "auto": base_score,
            "disability": base_score,
            "home": base_score,
            "life": base_score,
        }

    def calculate_base_score(self):
        return sum(int(x) for x in self.data["risk_questions"])

    def evaluate_rule(self, condition: str) -> bool:
        return bool(simple_eval(condition, names=self.data))

    def apply_action(self, field: str, action: str, value: int):
        # Lets work with the hypothesis that we only have add, subtract and reject actions
        if action == "add":
            self.fields[field] += value
        elif action == "subtract":
            self.fields[field] -= value
        else:
            self.fields[field] = None
        print(f"Applied: {action} to {field}")

    def calculate(self):
        for rule in self.rules:
            print(rule["field"])
            target_fields = rule["field"].split(",")
            if target_fields == ["*"]:
                target_fields = [f for f in self.fields.keys()]
            for field in target_fields:
                print(f"rule: {field}")
                if self.fields.get(field) is not None and self.evaluate_rule(
                    rule["condition"]
                ):
                    print("Matched: " + rule["condition"])

                    self.apply_action(field, rule["action"], rule["value"])

    def get_result(self):
        translated_dict = {k: RiskScore.from_rating(v) for k, v in self.fields.items()}
        return translated_dict


@app.post("/", response_model=CalculatedRiskResponse)
def home(data: UserDataInput):
    calculated_risk = ApplyRiskCalculation(data=data.dict(), rules=SCORE_RULES)
    calculated_risk.calculate()
    return calculated_risk.get_result()
