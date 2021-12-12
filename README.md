# Origin Backend Take-Home Assignment
This is my submission for the [Origin Backend Take-Home Assignment](https://github.com/OriginFinancial/origin-backend-take-home-assignment/edit/master/README.md)

## How to run (Linux)
Just clone the repo, install dependencies in a virtual environment and run uvicorn:

```bash
$ git clone git@github.com:jeanwainer/origin.git
$ cd origin
$ virtualenv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
$ uvicorn main:app --reload
```

### To run tests:
```bash
$ pytest
```


The root path [localhost:8000/](http://localhost:8000/) (POST requests only) is the only API endpoint available, and it only accepts POST requests.
The OpenAPI documentation is at the [/docs](http://localhost:8000/docs) path.

## Discussions

As someone who has always worked with Django, I went to try a different approach this time. FastAPI was a great fit for this project, specially for such task of input, process, output without any need for persistent data storage.
As this is my first time using this framework, I still lack the experience for best practices and how to organize the code - should the models be in a different file, should we need a service layer? For simplicity sake, I left all code in one single file, and tests in another.

### Rules evaluation

The rules are set in a list tuples of 4 elements. This makes it very flexible to decouple the business rules from the code and have it set by product people in another API, for example.
This is their current structure:

- **A python expression** to be evaluated. All variables from the input are available in the context, as well as `now` which is a representation of `datetime.now()` for purposes of calculating the age of the vehicle. Example: `40 < age < 60` or `vehicle['year'] > date.year - 5`
- **A list of insurance types** represented by strings separated by a comma, or a wildcard `*` representing all 4 of them. These are the insurance calculations that will be affected by the rule.
- **An action** which can be either `add`, `subtract`, or `reject`. When adding or subtracting, the `value` (see below) is the number that will be added or subtracted from the insurance score. When using `reject` (and in this implementation, any other term), value will be ignored and the corresponding insurance types will be set as `ineligible`.
- **A value** which is the number that will be added or subtracted from the insurance score.

### Criteria for writing tests

For tests, I made the priority to cover every class method created individually, and then some other validations. Since pretty much all the validation is done by Pydantic and FastAPI, most of that logic is already tested, but in a "real life scenario" I would probably cover those as well.

### What's next to improve / known issues
This is just a first revision, and there is space to improve:
- Refactor the `ApplyRiskCalculation` class and perhaps move it to a service layer of the application.
- Remove score processing rules that are hardcoded in the code, and make them more flexible to set up externally.
- Rethink variables names, I recon that "field" was not the best choice for a name.
- This implementation might not validate correctly some nested data from the such as house.ownership_status.
- As the original instructions say, the endpoint is ready to accept 0 or 1 house. In this implementation, I'm considering that 0 houses is no "house" keyword, and 1 house is a `house` keyword with `ownership_status`. A next iteration of this implementation should also consider house with an empty array "0" houses.
- We should provide the context variables in a better formatted way - ```house['ownership_status']``` is not ideal in the rules writing context, a better syntax such as `house.ownership_status` would be much better.



## Final thoughts
I had a very short time to do this project, and I had a lot of fun with it and learning a new framework I had never used before. I'll be glad to discuss it with you if you have any questions.



=====================================

Original README.md:

# Origin Backend Take-Home Assignment
Origin offers its users an insurance package personalized to their specific needs without requiring the user to understand anything about insurance. This allows Origin to act as their *de facto* insurance advisor.

Origin determines the user’s insurance needs by asking personal & risk-related questions and gathering information about the user’s vehicle and house. Using this data, Origin determines their risk profile for **each** line of insurance and then suggests an insurance plan (`"economic"`, `"regular"`, `"responsible"`) corresponding to her risk profile.

For this assignment, you will create a simple version of that application by coding a simple API endpoint that receives a JSON payload with the user information and returns her risk profile (JSON again) – you don’t have to worry about the frontend of the application.

## The input
First, the would-be frontend of this application asks the user for her **personal information**. Then, it lets her add her **house** and **vehicle**. Finally, it asks her to answer 3 binary **risk questions**. The result produces a JSON payload, posted to the application’s API endpoint, like this example:

```JSON
{
  "age": 35,
  "dependents": 2,
  "house": {"ownership_status": "owned"},
  "income": 0,
  "marital_status": "married",
  "risk_questions": [0, 1, 0],
  "vehicle": {"year": 2018}
}
```

### User attributes
All user attributes are required:

- Age (an integer equal or greater than 0).
- The number of dependents (an integer equal or greater than 0).
- Income (an integer equal or greater than 0).
- Marital status (`"single"` or `"married"`).
- Risk answers (an array with 3 booleans).

### House
Users can have 0 or 1 house. When they do, it has just one attribute: `ownership_status`, which can be `"owned"` or `"mortgaged"`.

### Vehicle
Users can have 0 or 1 vehicle. When they do, it has just one attribute: a positive integer corresponding to the `year` it was manufactured.

## The risk algorithm
The application receives the JSON payload through the API endpoint and transforms it into a *risk profile* by calculating a *risk score* for each line of insurance (life, disability, home & auto) based on the information provided by the user.

First, it calculates the *base score* by summing the answers from the risk questions, resulting in a number ranging from 0 to 3. Then, it applies the following rules to determine a *risk score* for each line of insurance.

1. If the user doesn’t have income, vehicles or houses, she is ineligible for disability, auto, and home insurance, respectively.
2. If the user is over 60 years old, she is ineligible for disability and life insurance.
3. If the user is under 30 years old, deduct 2 risk points from all lines of insurance. If she is between 30 and 40 years old, deduct 1.
4. If her income is above $200k, deduct 1 risk point from all lines of insurance. 
5. If the user's house is mortgaged, add 1 risk point to her home score and add 1 risk point to her disability score. 
6. If the user has dependents, add 1 risk point to both the disability and life scores. 
7. If the user is married, add 1 risk point to the life score and remove 1 risk point from disability. 
8. If the user's vehicle was produced in the last 5 years, add 1 risk point to that vehicle’s score.

This algorithm results in a final score for each line of insurance, which should be processed using the following ranges:

- **0 and below** maps to **“economic”**.
- **1 and 2** maps to **“regular”**.
- **3 and above** maps to **“responsible”**.


## The output
Considering the data provided above, the application should return the following JSON payload:

```JSON
{
    "auto": "regular",
    "disability": "ineligible",
    "home": "economic",
    "life": "regular"
}
```

## Criteria
You may use any language and framework provided that you build a solid system with an emphasis on code quality, simplicity, readability, maintainability, and reliability, particularly regarding architecture and testing. We'd prefer it if you used Python, but it's just that – a preference.

Be aware that Origin will mainly take into consideration the following evaluation criteria:
* How clean and organized your code is;
* If you implemented the business rules correctly;
* How good your automated tests are (qualitative over quantitative).

Other important notes:
* Develop a extensible score calculation engine
* Add to the README file: (1) instructions to run the code; (2) what were the main technical decisions you made; (3) relevant comments about your project 
* You must use English in your code and also in your docs

This assignment should be doable in less than one day. We expect you to learn fast, **communicate with us**, and make decisions regarding its implementation & scope to achieve the expected results on time.

It is not necessary to build the screens a user would interact with, however, as the API is intended to power a user-facing application, we expect the implementation to be as close as possible to what would be necessary in real-life. Consider another developer would get your project/repository to evolve and implement new features from exactly where you stopped. 


