# Test Coverage Documentation

This document provides information about the test coverage setup for the Vulipay API project.

## Overview

Test coverage is a measure of how much of your code is executed during your tests. It helps identify areas of code that are not being tested, which could potentially contain bugs or issues.

## Tools Used

- **coverage.py**: A tool for measuring code coverage of Python programs
- **Django's test runner**: Used to run the tests

## Configuration

The test coverage configuration is defined in the `.coveragerc` file in the project root. This file specifies:

- Which source files to measure
- Which files to exclude from measurement
- Which lines to exclude from coverage reporting
- Output formats and locations

## Running Test Coverage

There are several commands available in the Makefile to run tests with coverage:

### Basic Coverage Run

```bash
make test-coverage
```

This command runs the tests and collects coverage data but doesn't display a report.

### Coverage Report in Terminal

```bash
make test-coverage-report
```

This command displays a coverage report in the terminal, showing the percentage of code covered for each module and highlighting missing lines.

### HTML Coverage Report

```bash
make test-coverage-html
```

This command generates an HTML coverage report in the `htmlcov` directory. Open `htmlcov/index.html` in a browser to view a detailed, interactive coverage report.

## Interpreting Coverage Reports

The coverage report shows:

- **Coverage percentage**: The percentage of code that was executed during tests
- **Missing lines**: Lines of code that were not executed during tests
- **Excluded lines**: Lines that are excluded from coverage calculation (as defined in `.coveragerc`)

## Improving Test Coverage

To improve test coverage:

1. Focus on writing tests for modules with low coverage
2. Prioritize testing complex logic and edge cases
3. Use the HTML report to identify specific uncovered lines
4. Add tests for error handling and exception paths

## Best Practices

- Aim for high coverage, but don't obsess over 100% coverage
- Focus on testing business logic and critical paths
- Use meaningful assertions in tests, not just code execution
- Regularly review coverage reports to identify gaps

## Continuous Integration

Consider adding test coverage checks to your CI pipeline to ensure coverage doesn't decrease over time. You can set minimum coverage thresholds for the overall project or for specific modules.