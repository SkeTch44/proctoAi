# Requirements Document

## Introduction

This feature integrates MiniMax 2.5 as the primary LLM provider for all AI generation tasks in the ProctoAI platform, with Ollama demoted to a fallback role. Currently, the platform uses Ollama as the primary LLM (with Gemini as fallback) for question generation, RAG-based question generation, grading assistance, and other AI tasks. This change introduces a new `MiniMaxClient` into the existing `LLMFactory` abstraction, reorders the provider priority to MiniMax → Ollama, and ensures all AI-dependent subsystems (question generation, RAG, grading, LLMRunner) route through the updated factory without breaking existing functionality.

## Glossary

- **LLM_Factory**: The `LLMFactory` class in `backend/utils/llm_client.py` responsible for creating and returning the active LLM client based on availability and priority.
- **MiniMax_Client**: A new implementation of the `LLMClient` abstract class that communicates with the MiniMax 2.5 API over HTTPS.
- **Ollama_Client**: The existing `OllamaClient` class that communicates with a local Ollama instance for LLM inference.
- **LLM_Provider**: The `llm_provider.py` module that manages the singleton LLM client instance with health-check and auto-reset logic.
- **LLM_Runner**: The `LLMRunner` class in `backend/llm_runner.py` that executes skill-compiled prompts directly against Ollama.
- **Question_Generation_Service**: The unified service (`question_generation_service.py`) that orchestrates pure AI, RAG, and PDF scan question generation modes.
- **Grading_Engine**: The `GradingEngine` class that evaluates student answers using semantic similarity.
- **RAG_Engine**: The retrieval-augmented generation engine that indexes documents and retrieves relevant chunks for context-grounded generation.
- **Health_Check**: A lightweight probe to determine whether an LLM provider is reachable and operational.
- **Fallback**: The mechanism by which the system automatically switches to the next-priority LLM provider when the higher-priority provider is unavailable.

## Requirements

### Requirement 1: MiniMax Client Implementation

**User Story:** As a platform operator, I want a MiniMax 2.5 API client that conforms to the existing LLMClient interface, so that MiniMax can be used interchangeably with other LLM providers.

#### Acceptance Criteria

1. THE MiniMax_Client SHALL implement the `LLMClient` abstract interface including `generate_content` and `health_check` methods.
2. WHEN `generate_content` is called with a prompt string, THE MiniMax_Client SHALL send an HTTPS POST request to the MiniMax 2.5 chat completions API endpoint and return a response wrapper object with a `text` attribute containing the generated content.
3. WHEN `health_check` is called, THE MiniMax_Client SHALL return `True` if the `MINIMAX_API_KEY` environment variable is set to a non-empty string and a test request to the MiniMax API returns an HTTP 200 response within 5 seconds, and `False` otherwise.
4. IF the MiniMax API returns an HTTP error status (4xx or 5xx), THEN THE MiniMax_Client SHALL log the error details including the HTTP status code and return `None` from `generate_content`.
5. IF the MiniMax API request times out after 60 seconds, THEN THE MiniMax_Client SHALL log a timeout warning and return `None`.
6. IF the `MINIMAX_API_KEY` environment variable is not set or is empty, THEN THE MiniMax_Client SHALL log an error indicating the missing configuration and `health_check` SHALL return `False`.
7. THE MiniMax_Client SHALL read the model name from the `MINIMAX_MODEL` environment variable, defaulting to `MiniMax-M1` if not set.

### Requirement 2: LLM Factory Priority Reordering

**User Story:** As a platform operator, I want MiniMax 2.5 to be the first-choice LLM provider with Ollama as fallback, so that the platform uses the higher-quality cloud model when available and degrades gracefully to local inference.

#### Acceptance Criteria

1. WHEN `LLM_Factory.create_client()` is called, THE LLM_Factory SHALL attempt to create providers in this order: MiniMax_Client first, Ollama_Client second.
2. WHEN the MiniMax_Client health check succeeds within 5 seconds, THE LLM_Factory SHALL return the MiniMax_Client instance and log at INFO level that MiniMax is the active provider.
3. WHEN the MiniMax_Client health check fails or times out and the Ollama_Client health check succeeds within 5 seconds, THE LLM_Factory SHALL return the Ollama_Client instance and log at INFO level that Ollama is the fallback provider.
4. IF both MiniMax_Client and Ollama_Client health checks fail or time out, THEN THE LLM_Factory SHALL log an error at ERROR level indicating both providers are unavailable and return `None`.
5. THE LLM_Factory SHALL remove Gemini from the provider chain (replaced by MiniMax).
6. IF a provider health check raises any exception (network error, authentication failure, or unexpected error), THEN THE LLM_Factory SHALL treat that provider as unavailable and proceed to the next provider in the priority order.

### Requirement 3: LLM Runner Migration to Factory

**User Story:** As a developer, I want the LLMRunner to use the LLM_Factory abstraction instead of directly calling Ollama, so that all AI generation paths benefit from the MiniMax-first priority and automatic fallback.

#### Acceptance Criteria

1. WHEN `LLMRunner.run_batch` is called, THE LLM_Runner SHALL obtain the active LLM client from LLM_Provider (which uses LLM_Factory) instead of making direct HTTP requests to Ollama, and SHALL pass the constructed prompt string to the client's `generate_content` method.
2. WHEN `LLMRunner.execute` is called with a SkillPacket, THE LLM_Runner SHALL route the request through the active LLM client obtained from LLM_Provider, passing the compiled prompt to the client's `generate_content` method.
3. THE LLM_Runner SHALL preserve existing behavior for prompt truncation (truncating prompts exceeding 8000 characters), JSON parsing of the client response text, JSON extraction fallback via regex in `execute`, and timeout management (120-second request timeout) regardless of which provider is active.
4. IF the active LLM client's `generate_content` returns `None`, THEN THE LLM_Runner SHALL log the failure including the batch ID or skill ID and return `None` to the caller without raising an exception.
5. WHEN `LLMRunner.run_batch` or `LLMRunner.execute` is called with skill-specific LLM parameters (temperature, max_tokens), THE LLM_Runner SHALL pass those parameters to the active LLM client so that per-call configuration is preserved across providers.
6. IF LLM_Provider raises a RuntimeError because no LLM client could be initialized, THEN THE LLM_Runner SHALL catch the exception, log the error, and return `None`.

### Requirement 4: Environment Configuration

**User Story:** As a platform operator, I want to configure the MiniMax API key and model via environment variables, so that credentials are managed securely and the model can be changed without code modifications.

#### Acceptance Criteria

1. THE Config class SHALL expose `MINIMAX_API_KEY` read from the `MINIMAX_API_KEY` environment variable, defaulting to an empty string.
2. THE Config class SHALL expose `MINIMAX_MODEL` read from the `MINIMAX_MODEL` environment variable, defaulting to `MiniMax-M1`.
3. THE `.env.example` file SHALL document the `MINIMAX_API_KEY` and `MINIMAX_MODEL` variables in the AI/LLM section.
4. THE MiniMax_Client SHALL include the configured API key in an `Authorization: Bearer <key>` header for all API requests.
5. IF `MINIMAX_API_KEY` is empty or unset when the MiniMax_Client attempts a request, THEN THE MiniMax_Client SHALL raise an error indicating that the API key is not configured, without sending the request.

### Requirement 5: Fallback Resilience in LLM Provider

**User Story:** As a platform operator, I want the LLM provider to automatically retry with the fallback provider when the primary provider becomes unhealthy at runtime, so that AI features remain available during MiniMax outages.

#### Acceptance Criteria

1. WHEN the LLM_Provider invokes health_check() on the current client and the check returns false or raises an exception, THE LLM_Provider SHALL reset the cached instance and invoke LLM_Factory to obtain a new client (which will try MiniMax first, then Ollama).
2. WHEN the MiniMax_Client health_check() returns false or the connection times out within 5 seconds after initial selection, THE LLM_Provider SHALL fall back to Ollama_Client on the next invocation of get_llm_client().
3. WHEN a fallback transition occurs, THE LLM_Provider SHALL log a warning that includes the provider name that failed and the exception message or health-check failure status that caused the transition.
4. IF both MiniMax_Client and Ollama_Client fail their health checks during a single get_llm_client() invocation, THEN THE LLM_Provider SHALL raise a runtime error indicating that no LLM provider is available.
5. WHEN the LLM_Provider is currently using the fallback Ollama_Client and a subsequent get_llm_client() call is made, THE LLM_Provider SHALL re-attempt MiniMax_Client via LLM_Factory before returning the Ollama_Client, allowing automatic recovery to the primary provider.

### Requirement 6: Question Generation Service Compatibility

**User Story:** As an educator, I want all three question generation modes (pure AI, RAG, PDF scan) to work seamlessly with MiniMax as the primary provider, so that question quality improves without changing my workflow.

#### Acceptance Criteria

1. WHEN the Question_Generation_Service calls `LLMRunner.execute` and MiniMax_Client is the active provider, THE Question_Generation_Service SHALL receive a parsed JSON object containing at minimum the fields `question_text` (string, 1–2000 characters), `question_type` (string), and `question_data` (object with `options` and/or `correct_answer`), identical in structure to responses produced by Ollama_Client.
2. THE Question_Generation_Service SHALL require no code changes to its public interface or internal logic beyond what LLM_Runner provides.
3. WHEN MiniMax is the active provider and the pure AI or RAG generation mode is invoked, THE Question_Generation_Service SHALL return a response within 30 seconds per question batch, matching the same JSON schema currently produced when Ollama is the active provider.
4. IF MiniMax_Client returns a non-JSON or malformed response, THEN THE LLM_Runner SHALL return None to the Question_Generation_Service, and the Question_Generation_Service SHALL set the result `success` field to false and include an error message indicating the provider returned an unparseable response.
5. WHEN the PDF scan mode is invoked, THE Question_Generation_Service SHALL produce results independent of which LLM provider is active, since PDF scan relies on text extraction and parsing rather than LLM generation.

### Requirement 7: RAG-Based Generation Compatibility

**User Story:** As an educator, I want RAG-based question generation to work with MiniMax as the primary LLM, so that document-grounded questions benefit from the higher-quality model.

#### Acceptance Criteria

1. WHEN the QuestionGenerator invokes `self.llm_client` (obtained via LLM_Provider), THE QuestionGenerator SHALL delegate prompt execution to whichever provider LLM_Factory selected, without referencing a specific provider name in its RAG retrieval, document processing, or prompt construction logic.
2. WHEN the QuestionGenerator performs RAG-based generation, THE QuestionGenerator SHALL pass the assembled prompt to the active LLM client's `generate_content(prompt: str)` method and accept the response through the same `LLMClient` interface used by all providers.
3. IF `self.llm_client` resolves to `None` (no provider available) during RAG generation, THEN THE QuestionGenerator SHALL invoke `_generate_fallback_questions`, returning template-based MCQ questions derived from extracted document sentences.
4. IF `self.llm_client.generate_content()` returns `None` (generation failure) during RAG generation, THEN THE QuestionGenerator SHALL invoke `_generate_fallback_questions`, returning template-based MCQ questions derived from extracted document sentences.

### Requirement 8: MiniMax Request Format Compliance

**User Story:** As a developer, I want the MiniMax client to format requests according to the MiniMax 2.5 API specification, so that prompts are correctly interpreted and responses are properly parsed.

#### Acceptance Criteria

1. THE MiniMax_Client SHALL send requests to the MiniMax chat completions endpoint as an HTTPS POST with a JSON body containing the `model` field set to the configured model name, a `messages` array, and a `response_format` field set to `{"type": "json_object"}`.
2. WHEN `generate_content` is called with a prompt string, THE MiniMax_Client SHALL construct the `messages` array with a single object having `role` set to `"user"` and `content` set to the prompt string.
3. WHEN the API response is received successfully, THE MiniMax_Client SHALL extract the text content from the first choice's assistant message in the response body and return it as the `text` attribute of the response wrapper.
4. IF the API response body does not contain the expected message structure, THEN THE MiniMax_Client SHALL log an error indicating the unexpected response format and return `None`.
5. THE MiniMax_Client SHALL include the `Content-Type: application/json` header and the `Authorization` header with the configured API key in every request.
