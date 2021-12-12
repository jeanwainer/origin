from copy import deepcopy
from freezegun import freeze_time

from fastapi.testclient import TestClient
from unittest import TestCase

from parameterized import parameterized

from main import app, ApplyRiskCalculation, RiskScore

client = TestClient(app)


class ApplyRiskCalculationTest(TestCase):
    def setUp(self) -> None:
        example_rules = [
            ("income < 1", "disability", "set", "ineligible"),
            ("not vehicle", "auto", "set", "ineligible"),
            ("not house", "home", "set", "ineligible"),
            ("age > 60", "disability,life", "set", "ineligible"),
            ("age < 30", "*", "subtract", 2),
            ("marital_status == 'married'", "life", "add", 1),
            ("vehicle['year'] > date.year - 5", "auto", "add", 1),
        ]
        example_payload = {
            "age": 35,
            "dependents": 2,
            "house": {"ownership_status": "owned"},
            "income": 0,
            "marital_status": "married",
            "risk_questions": [0, 1, 0],
            "vehicle": {"year": 2018},
        }
        self.obj = ApplyRiskCalculation(data=example_payload, rules=example_rules)

    @parameterized.expand(
        [([True, True, False], 2), ([True, True, True], 3), ([False, False, False], 0)]
    )
    def test_calculate_base_score(self, risk_questions, expected_score):
        self.obj.data["risk_questions"] = risk_questions
        result = self.obj.calculate_base_score()
        self.assertEqual(result, expected_score)

    @parameterized.expand(
        [
            ("1 == True", True),
            ("1+2", True),
            ("0", False),
            ("date.year == 1992", False),
        ]
    )
    def test_evaluate_rule_and_year(self, expression, result):
        self.assertEqual(self.obj.evaluate_rule(expression), result)

    @freeze_time("1992-01-01")
    def test_evaluate_current_year(self):
        obj = ApplyRiskCalculation(
            data={"risk_questions": [True, True, True]}, rules=[]
        )
        self.assertEqual(obj.evaluate_rule("date.year == 1992"), True)
        self.assertEqual(obj.evaluate_rule("date.year == 2021"), False)

    @parameterized.expand(
        [
            ("add", 5, 8),
            ("subtract", 1, 2),
            ("reject", "anythingreally", None),
            ("invalidstring", 123, None),
            # Not ideal, just making sure it does what's expected
        ]
    )
    def test_apply_action(self, operation, value, result_expected):
        # Risk questions below should return an initial result of 3
        obj = ApplyRiskCalculation(
            data={"risk_questions": [True, True, True]}, rules=[]
        )
        obj.apply_action("disability", operation, value)
        self.assertEqual(obj.fields["disability"], result_expected)

    def test_get_result(self):
        obj = ApplyRiskCalculation(
            data={"risk_questions": [True, True, True]}, rules=[]
        )
        obj.fields = {"disability": 5, "life": -1, "auto": None, "home": 2}
        result = obj.get_result()
        self.assertEqual(result["disability"], RiskScore.responsible)
        self.assertEqual(result["life"], RiskScore.economic)
        self.assertEqual(result["auto"], RiskScore.ineligible)
        self.assertEqual(result["home"], RiskScore.regular)

    @parameterized.expand(
        [
            (("age > 30", "disability", "set", "ineligible"), "disability", None),
            (("age < 30", "disability", "set", "ineligible"), "disability", 3),
            (("age == 35", "auto,home", "add", 1), "disability", 3),
            (("age == 35", "auto,disability", "add", 1), "disability", 4),
            (("age == 42", "disability", "add", 1), "disability", 3),
            (("age is None", "disability,life", "subtract", 1), "disability", 3),
            (("age is not None", "*", "subtract", 45), "disability", -42),
        ]
    )
    def test_calculate(self, rule, field, result):
        payload = {"age": 35, "risk_questions": [True, True, True]}
        self.obj = ApplyRiskCalculation(data=payload, rules=[rule])
        self.obj.calculate()
        self.assertEqual(self.obj.fields[field], result)


class DataValidationTest(TestCase):
    def setUp(self) -> None:
        self.payload = {
            "age": 35,
            "dependents": 2,
            "house": {"ownership_status": "owned"},
            "income": 0,
            "marital_status": "married",
            "risk_questions": [0, 1, 0],
            "vehicle": {"year": 2018},
        }

    def test_example_payload_is_successful(self):
        response = client.post("/", json=self.payload)
        self.assertEqual(response.status_code, 200)

    @parameterized.expand(
        [
            ("age"),
            ("dependents"),
            ("marital_status"),
            ("risk_questions"),
        ]
    )
    def test_missing_required_field(self, field):
        payload = {k: v for k, v in self.payload.items() if k != field}
        response = client.post("/", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"][0]["msg"], "field required")

    def test_invalid_data_fails(self):
        payload = deepcopy(self.payload)
        payload["age"] = "invalid"
        response = client.post("/", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"][0]["msg"], "value is not a valid integer"
        )


class DataInegibilityTest(TestCase):
    def setUp(self) -> None:
        self.payload = {
            "age": 35,
            "dependents": 2,
            "house": {"ownership_status": "owned"},
            "income": 0,
            "marital_status": "married",
            "risk_questions": [0, 1, 0],
            "vehicle": {"year": 2018},
        }

    def test_no_vehicle_provided(self):
        payload = deepcopy(self.payload)
        del payload["vehicle"]
        response = client.post("/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["auto"], "ineligible")

    def test_no_income(self):
        response = client.post("/", json=self.payload | {"income": 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["disability"], "ineligible")

    def test_no_house(self):
        payload = deepcopy(self.payload)
        del payload["house"]
        response = client.post("/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["home"], "ineligible")
