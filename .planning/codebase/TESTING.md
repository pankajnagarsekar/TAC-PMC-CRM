# Testing Practices

## Backend Testing
- **Framework**: `pytest`
- **Location**: `apps/api/tests/`
- **Key Test Files**:
  - `test_financials.py`: Validates monetary logic.
  - `test_rate_limiting.py`: Verifies resilience middleware.
  - `test_ocr_mobile.py`: Tests mobile-specific OCR processing.
- **Practice**:
  - Integration tests use a real MongoDB (test environment).
  - Mocking is reserved for external APIs (OpenAI, AWS).
  - Use `conftest.py` for shared fixtures.

## Frontend Testing
- **Framework**: Not yet configured centrally (Standard practice: Jest + React Testing Library).
- **Practice**:
  - Type checking via `tsc --noEmit`.
  - Component validation through manual UI review against "Luxury Industrial" aesthetic.

## Automation
- CI/CD pipelines expected to run `turbo lint` and `turbo test`.
- All financial mutations must have verified coverage.
