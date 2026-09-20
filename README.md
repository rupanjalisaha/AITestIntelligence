# AITestIntelligence

**AI-Powered Software Test Automation**

AITestIntelligence is an AI-powered software testing framework that helps generate, validate, and execute UI and API test cases from natural-language requirements.

The project combines **LLM-based test generation** with **Selenium-based UI automation** and **API test execution** to reduce the manual effort involved in creating and running software tests.

## Features

### AI Test Generation

* Generate structured test cases from natural-language software requirements.
* Generate multiple distinct test scenarios covering functional, negative, boundary, validation, security, and error-handling scenarios.
* Include test data and expected outcomes in generated test cases.

### UI Test Automation

* Generate Selenium automation from generated test cases.
* Inspect web applications to identify available page elements and locators.
* Execute generated UI automation.
* Execute all generated UI test cases in a single run.
* Capture execution results and failure analysis.
* Retry UI automation when locator-related failures are detected.

### API Test Automation

* Generate API test cases from a requirement and base URL.
* Execute generated API test cases automatically.
* Execute multiple generated API test cases in a single run.
* Report passed and failed test cases along with execution results and duration.

### Test Validation

* Validate generated test cases against the supplied requirement.
* Detect invalid or inconsistent test-case structures and data.
* Apply validation rules before test execution.

### Automated Testing Pipeline

The application supports an end-to-end workflow:

```text
Natural Language Requirement
            ↓
      AI Test Generation
            ↓
      Test Validation
            ↓
   ┌────────┴────────┐
   ↓                 ↓
UI Test            API Test
   ↓                 ↓
Application        API
Inspection        Execution
   ↓
Selenium Code
Generation
   ↓
UI Execution
   ↓
Test Results
```

## Technology Stack

* **Python**
* **FastAPI**
* **Pydantic**
* **Ollama / Local LLM**
* **Selenium**
* **Pytest**
* **Requests**
* **GitHub Actions**

## Project Structure

```text
AITestIntelligence/
│
├── app/
│   ├── main.py
│   ├── models.py
│   │
│   └── services/
│       ├── test_generator.py
│       ├── test_quality_evaluator.py
│       ├── ui_test_validator.py
│       ├── automation_generator.py
│       ├── page_inspector.py
│       ├── test_executor.py
│       ├── api_test_generator.py
│       └── api_test_executor.py
│
├── tests/
│   ├── __init__.py
│   ├── test_test_executor.py
│   └── test_ui_test_validator.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

## Core API Endpoints

### Health Check

```http
GET /health
```

Returns the application health status.

### Generate Test Cases

```http
POST /api/v1/tests/generate
```

Generates test cases from a natural-language requirement.

### Validate Tests

```http
POST /api/v1/tests/validate
```

Evaluates generated test cases against the supplied requirement.

### Run UI Tests

```http
POST /api/v1/automation/run
```

Runs the UI automation workflow:

```text
Requirement
    ↓
Generate Test Cases
    ↓
Select Test Cases
    ↓
Inspect Application
    ↓
Generate Selenium Automation
    ↓
Execute Test Cases
    ↓
Return Results
```

If no specific test case ID is provided, the generated UI test cases are executed sequentially.

### Run API Tests

```http
POST /api/v1/api-tests/run
```

Generates API test cases and executes all generated API tests in a single request.

## Running the Project Locally

### 1. Clone the repository

```bash
git clone https://github.com/rupanjalisaha/AITestIntelligence.git
cd AITestIntelligence
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv venv
```

Activate it:

```powershell
venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Start the application

```powershell
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## Running Tests

Run the automated test suite with:

```powershell
python -m pytest -v
```

The project also includes a GitHub Actions CI workflow that runs the test suite automatically on pushes and pull requests to the main development branches.

## Example Workflow

A typical UI testing workflow looks like:

```text
1. Provide a software requirement
        ↓
2. AI generates test cases
        ↓
3. Generated tests are validated
        ↓
4. Application is inspected
        ↓
5. Selenium automation is generated
        ↓
6. Automation is executed
        ↓
7. Execution results are returned
```

For API testing:

```text
1. Provide API requirement + base URL
        ↓
2. AI generates API test cases
        ↓
3. Generated API tests are executed
        ↓
4. Results are collected
        ↓
5. Passed / failed tests are reported
```

## Current Project Status

AITestIntelligence is currently an **MVP/prototype focused on AI-assisted UI and API test automation**.

The current implementation focuses on:

* AI-based test generation
* Test validation
* UI application inspection
* Selenium automation generation
* UI test execution
* Locator-related retry handling
* API test generation
* API test execution
* Automated testing with Pytest
* Continuous integration with GitHub Actions

The project is actively evolving toward a more robust production-ready test automation platform.

## Future Improvements

Potential areas for future development include:

* Improved self-healing automation
* More robust locator recovery
* Better failure classification
* Test execution history
* Test result dashboards
* Parallel test execution
* Browser and environment management
* Richer API assertions
* Test reporting and evidence management
* Integration with CI/CD platforms
* Support for additional testing frameworks

## License

This project is currently intended as a development/MVP project. Licensing information will be added as the project is prepared for broader distribution.
