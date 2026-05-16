# Implementation Plan: MiniMax LLM Integration

## Overview

Integrate MiniMax 2.5 as the primary LLM provider for ProctoAI, replacing the Ollama-first/Gemini-fallback chain with MiniMax-first/Ollama-fallback. Implementation touches the client layer, factory, runner, provider, and configuration, while preserving all downstream consumer interfaces.

## Tasks

- [x] 1. Add MiniMax configuration and environment setup
  - [x] 1.1 Add MINIMAX_API_KEY and MINIMAX_MODEL to Config class
    - Add `MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")` to `backend/config.py`
    - Add `MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M1")` to `backend/config.py`
    - _Requirements: 4.1, 4.2_

  - [x] 1.2 Update .env.example with MiniMax variables
    - Add `MINIMAX_API_KEY=` and `MINIMAX_MODEL=MiniMax-M1` entries in the AI/LLM section of `.env.example`
    - _Requirements: 4.3_

- [x] 2. Implement MiniMaxClient class
  - [x] 2.1 Create MiniMaxClient in backend/utils/llm_client.py
    - Implement `MiniMaxClient(LLMClient)` with `__init__`, `health_check`, and `generate_content` methods
    - Use `https://api.minimax.io/v1/chat/completions` endpoint
    - `health_check()`: return `True` if `MINIMAX_API_KEY` is non-empty and a test request returns HTTP 200 within 5 seconds; `False` otherwise
    - `generate_content(prompt, **kwargs)`: construct messages array with `role: "user"`, `content: prompt`; include `Authorization: Bearer <key>` and `Content-Type: application/json` headers; extract `choices[0].message.content` from response; return `response_wrapper(text)` or `None` on failure
    - Handle HTTP errors (4xx/5xx) by logging status code and returning `None`
    - Handle timeout (60s) by logging warning and returning `None`
    - Handle missing/empty API key by logging error and returning `None` without sending request
    - Handle malformed response body (missing `choices` structure) by logging and returning `None`
    - Read model from `MINIMAX_MODEL` env var, defaulting to `MiniMax-M1`
    - Accept optional `temperature` and `max_completion_tokens` kwargs and include in request body
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 4.4, 4.5, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 2.2 Write property test: Response Parsing Round-Trip
    - **Property 1: Response Parsing Round-Trip**
    - **Validates: Requirements 1.2, 8.3**
    - Use Hypothesis to generate arbitrary content strings; mock the HTTP response with `choices[0].message.content` set to the generated string; assert `generate_content().text` equals the generated string exactly

  - [ ]* 2.3 Write property test: Request Construction Correctness
    - **Property 2: Request Construction Correctness**
    - **Validates: Requirements 8.1, 8.2, 8.5, 4.4**
    - Use Hypothesis to generate non-empty prompt strings; capture the outgoing request body and headers; assert `model` matches configured model, `messages[0].role == "user"`, `messages[0].content == prompt`, `Authorization` header contains the API key, `Content-Type` is `application/json`

  - [ ]* 2.4 Write property test: Error Responses Yield None
    - **Property 4: Error Responses Yield None**
    - **Validates: Requirements 1.4, 8.4**
    - Use Hypothesis to generate HTTP status codes in range 400–599 and malformed response bodies; assert `generate_content()` returns `None` for all cases

  - [ ]* 2.5 Write unit tests for MiniMaxClient
    - Test health check with valid key + 200 response → True
    - Test health check with empty key → False
    - Test health check with timeout → False
    - Test generate_content with empty API key → None (no request sent)
    - Test generate_content with HTTP 500 → None
    - Test generate_content with timeout → None
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 1.6_

- [x] 3. Modify LLMFactory priority ordering
  - [x] 3.1 Reorder LLMFactory.create_client() to MiniMax-first, Ollama-second
    - Change `LLMFactory.create_client()` in `backend/utils/llm_client.py` to try MiniMaxClient first (with 5s health check timeout), then OllamaClient second
    - Remove Gemini from the provider chain (keep `GeminiClient` class in file for future use)
    - Wrap each provider's health check in try/except to handle unexpected exceptions gracefully
    - Log at INFO level which provider is selected; log at ERROR level if both unavailable
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 3.2 Write property test: Factory Priority Ordering
    - **Property 3: Factory Priority Ordering**
    - **Validates: Requirements 2.1, 2.6**
    - Use Hypothesis to generate all combinations of provider health states (healthy/unhealthy/exception for MiniMax and Ollama); mock health_check methods; assert factory returns highest-priority healthy provider or None, and never raises an unhandled exception

  - [ ]* 3.3 Write unit tests for LLMFactory
    - Test returns MiniMaxClient when MiniMax healthy
    - Test returns OllamaClient when MiniMax unhealthy, Ollama healthy
    - Test returns None when both unhealthy
    - Test does not instantiate GeminiClient
    - Test handles exception from health_check gracefully
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Migrate LLMRunner to use LLM Factory abstraction
  - [x] 5.1 Refactor LLMRunner.run_batch() to use get_llm_client()
    - Remove direct `requests.post` to Ollama in `run_batch()`
    - Import and call `get_llm_client()` from `backend.providers.llm_provider`
    - Pass constructed prompt to `client.generate_content(prompt, temperature=temperature, max_tokens=max_tokens)`
    - Preserve prompt truncation at 8000 chars with truncation suffix
    - Preserve JSON parsing of response.text
    - Handle `RuntimeError` from provider (no client available) → log and return None
    - Handle `generate_content()` returning None → log with batch_id and return None
    - _Requirements: 3.1, 3.3, 3.4, 3.5, 3.6_

  - [x] 5.2 Refactor LLMRunner.execute() to use get_llm_client()
    - Remove direct `requests.post` to Ollama in `execute()`
    - Import and call `get_llm_client()` from `backend.providers.llm_provider`
    - Pass compiled prompt to `client.generate_content(prompt, temperature=temperature, max_tokens=max_tokens)`
    - Preserve JSON parsing with regex fallback for extraction
    - Handle `RuntimeError` from provider → log and return None
    - Handle `generate_content()` returning None → log with skill_id and return None
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 5.3 Write property test: Prompt Truncation Invariant
    - **Property 5: Prompt Truncation Invariant**
    - **Validates: Requirements 3.3**
    - Use Hypothesis to generate prompt strings of varying lengths; mock get_llm_client; assert that prompts ≤ 8000 chars are passed unchanged, and prompts > 8000 chars are truncated to ≤ 8000 + len(truncation suffix)

  - [ ]* 5.4 Write property test: Parameter Forwarding
    - **Property 6: Parameter Forwarding**
    - **Validates: Requirements 3.5**
    - Use Hypothesis to generate valid temperature (0 < t ≤ 1) and max_tokens (≥ 1) values in skill_metadata; mock get_llm_client and capture kwargs passed to generate_content; assert temperature and max_tokens match the input values exactly

  - [ ]* 5.5 Write unit tests for LLMRunner
    - Test run_batch returns None when get_llm_client raises RuntimeError
    - Test run_batch returns None when generate_content returns None
    - Test execute returns None when get_llm_client raises RuntimeError
    - Test execute returns None when generate_content returns None
    - Test JSON regex fallback extraction in execute
    - Test prompt truncation at 8000 chars
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

- [x] 6. Verify LLM Provider fallback resilience
  - [x] 6.1 Confirm llm_provider.py health-check-and-reset logic works with new factory order
    - Verify that `get_llm_client()` resets cached instance when health check fails
    - Verify that after reset, `LLMFactory.create_client()` re-attempts MiniMax first, enabling recovery to primary
    - Add logging for fallback transitions including failed provider name and reason
    - _Requirements: 5.1, 5.2, 5.3, 5.5_

  - [ ]* 6.2 Write integration tests for LLM Provider fallback
    - Test health-check-and-reset cycle with mocked providers
    - Test raises RuntimeError when both providers fail
    - Test recovery to MiniMax after temporary outage
    - Test fallback warning log includes provider name and failure reason
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Verify downstream consumer compatibility
  - [x] 8.1 Verify QuestionGenerationService works with MiniMax responses
    - Confirm no code changes needed in `question_generation_service.py`
    - Verify JSON schema compatibility (question_text, question_type, question_data fields)
    - Confirm PDF scan mode is independent of LLM provider
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

  - [x] 8.2 Verify QuestionGenerator RAG path uses LLMClient interface
    - Confirm `QuestionGenerator` delegates to `self.llm_client.generate_content()` without provider-specific references
    - Confirm fallback to `_generate_fallback_questions()` when `self.llm_client` is None
    - Confirm fallback when `generate_content()` returns None
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 8.3 Write integration tests for downstream consumers
    - Test QuestionGenerationService end-to-end with mocked MiniMax responses
    - Test QuestionGenerator RAG path with mocked LLM client
    - Test QuestionGenerator fallback when llm_client is None
    - Test QuestionGenerator fallback when generate_content returns None
    - _Requirements: 6.1, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document using Hypothesis
- Unit tests validate specific examples and edge cases
- The `GeminiClient` class is kept in the codebase but removed from the factory chain
- All downstream consumers (QuestionGenerationService, QuestionGenerator, GradingEngine) require no interface changes
- The `response_wrapper` pattern is preserved for backward compatibility

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "2.5", "3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3"] },
    { "id": 4, "tasks": ["5.1", "5.2"] },
    { "id": 5, "tasks": ["5.3", "5.4", "5.5", "6.1"] },
    { "id": 6, "tasks": ["6.2"] },
    { "id": 7, "tasks": ["8.1", "8.2"] },
    { "id": 8, "tasks": ["8.3"] }
  ]
}
```
