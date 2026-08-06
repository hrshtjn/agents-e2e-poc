# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Model Armor Guard — ADK callback hooks for input/output safety screening.

Verified against google-cloud-modelarmor==0.7.1.

Usage in agent.py:
    from app.security.model_armor_guard import screen_input, screen_output

    root_agent = Agent(
        ...
        before_model_callback=screen_input,
        after_model_callback=screen_output,
    )
"""

import logging
import os
import re
from typing import Optional

import google.cloud.modelarmor_v1 as modelarmor_v1
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.api_core.client_options import ClientOptions
from google.genai import types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Set MODEL_ARMOR_TEMPLATE in your environment or Secret Manager.
# Format: projects/<PROJECT_ID>/locations/<REGION>/templates/<TEMPLATE_ID>
TEMPLATE_NAME: str = os.environ.get("MODEL_ARMOR_TEMPLATE", "")

# Fail-open (True) → log the error and allow the request through if Model
# Armor is unreachable. Set to False in production to fail closed (block).
FAIL_OPEN: bool = os.environ.get("MODEL_ARMOR_FAIL_OPEN", "true").lower() == "true"

_PLACEHOLDER = "YOUR_PROJECT_ID"


def _is_configured() -> bool:
    """Returns True only when a real template name has been set.

    Returns False (and skips all Model Armor calls) when:
    - MODEL_ARMOR_TEMPLATE is empty / not set in the environment
    - The value still contains the placeholder 'YOUR_PROJECT_ID'
    """
    return bool(TEMPLATE_NAME) and _PLACEHOLDER not in TEMPLATE_NAME

# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_client: Optional[modelarmor_v1.ModelArmorClient] = None


def _get_client() -> modelarmor_v1.ModelArmorClient:
    """Returns a lazily-initialised, reused ModelArmorClient with correct regional routing."""
    global _client
    if _client is None:
        # Extract region from format: projects/*/locations/<region>/templates/*
        match = re.search(r"/locations/([^/]+)/", TEMPLATE_NAME)
        if match and match.group(1) != "global":
            region = match.group(1)
            endpoint = f"modelarmor.{region}.rep.googleapis.com"
            client_options = ClientOptions(api_endpoint=endpoint)
            _client = modelarmor_v1.ModelArmorClient(client_options=client_options)
        else:
            _client = modelarmor_v1.ModelArmorClient()
    return _client


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _extract_matched_filter_names(
    sanitization_result: modelarmor_v1.SanitizationResult,
) -> list[str]:
    """
    Returns the string names of filters that matched (e.g. ["rai", "pi_and_jailbreak"]).

    filter_results is a MutableMapping[str, FilterResult] where keys are:
        "csam", "malicious_uris", "rai", "pi_and_jailbreak", "sdp"
    """
    matched = []
    for filter_name, filter_result in sanitization_result.filter_results.items():
        state = None

        if "rai_filter_result" in filter_result:
            state = filter_result.rai_filter_result.match_state
        elif "pi_and_jailbreak_filter_result" in filter_result:
            state = filter_result.pi_and_jailbreak_filter_result.match_state
        elif "sdp_filter_result" in filter_result:
            sdp = filter_result.sdp_filter_result
            # Check the nested oneof inside SdpFilterResult
            if "inspect_result" in sdp:
                state = sdp.inspect_result.match_state
            elif "deidentify_result" in sdp:
                state = sdp.deidentify_result.match_state
            elif "redact_result" in sdp:
                state = sdp.redact_result.match_state
        elif "malicious_uri_filter_result" in filter_result:
            state = filter_result.malicious_uri_filter_result.match_state
        elif "csam_filter_filter_result" in filter_result:
            state = filter_result.csam_filter_filter_result.match_state
        elif "virus_scan_filter_result" in filter_result:
            state = filter_result.virus_scan_filter_result.match_state

        if state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
            matched.append(filter_name)

    return matched


def _extract_deidentified_text(
    sanitization_result: modelarmor_v1.SanitizationResult,
) -> Optional[str]:
    """
    If the SDP filter ran deidentification, returns the redacted text.
    Otherwise returns None.
    """
    sdp_result = sanitization_result.filter_results.get("sdp")
    if sdp_result and "sdp_filter_result" in sdp_result:
        sdp = sdp_result.sdp_filter_result
        if "deidentify_result" in sdp and sdp.deidentify_result.data.text:
            return sdp.deidentify_result.data.text
    return None


def _blocked_response(reason: str) -> LlmResponse:
    """Returns a standardised blocked-request LlmResponse."""
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text=(
                        "I'm sorry, but your request was flagged by our security policy "
                        f"({reason}) and cannot be processed. Please rephrase your query "
                        "or contact your administrator if you believe this is an error."
                    )
                )
            ],
        )
    )


# ---------------------------------------------------------------------------
# ADK Callbacks
# ---------------------------------------------------------------------------

def screen_input(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """
    before_model_callback — screens the user's prompt through Model Armor
    before it reaches Gemini.

    Returns:
        A blocked LlmResponse if the prompt is unsafe.
        None to allow the request to proceed normally.
    """
    if not _is_configured():
        logger.warning(
            "Model Armor: NOT active — MODEL_ARMOR_TEMPLATE is not configured. "
            "Prompts are reaching Gemini unscreened. "
            "Set MODEL_ARMOR_TEMPLATE in app/.env to enable."
        )
        return None

    if not llm_request.contents:
        return None

    # Extract the latest user-role message text
    user_text = ""
    for content in reversed(llm_request.contents):
        if content.role == "user" and content.parts:
            user_text = " ".join(
                part.text for part in content.parts if hasattr(part, "text") and part.text
            )
            break

    if not user_text.strip():
        return None

    session_id = getattr(callback_context.state, "session_id", "unknown")

    try:
        client = _get_client()
        request = modelarmor_v1.SanitizeUserPromptRequest(
            name=TEMPLATE_NAME,
            user_prompt_data=modelarmor_v1.DataItem(text=user_text),
        )
        response = client.sanitize_user_prompt(request)
        sanitization = response.sanitization_result

        if sanitization.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
            matched_filters = _extract_matched_filter_names(sanitization)
            logger.warning(
                "Model Armor BLOCKED input | session=%s | filters=%s | preview=%.80r",
                session_id,
                matched_filters,
                user_text,
            )
            return _blocked_response(", ".join(matched_filters) or "policy violation")

        logger.debug("Model Armor: input allowed | session=%s", session_id)

    except Exception:
        logger.exception("Model Armor input screening error | session=%s", session_id)
        if not FAIL_OPEN:
            return _blocked_response("security check unavailable")

    return None  # Safe — proceed normally


def screen_output(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """
    after_model_callback — screens the model's response through Model Armor
    before it is returned to the user.

    Returns:
        A redacted/blocked LlmResponse if the response is unsafe.
        None to return the original response as-is.
    """
    if not _is_configured():
        logger.warning(
            "Model Armor: NOT active — MODEL_ARMOR_TEMPLATE is not configured. "
            "Model responses are returned unscreened. "
            "Set MODEL_ARMOR_TEMPLATE in app/.env to enable."
        )
        return None

    if not llm_response.content or not llm_response.content.parts:
        return None

    response_text = " ".join(
        part.text
        for part in llm_response.content.parts
        if hasattr(part, "text") and part.text
    )

    if not response_text.strip():
        return None

    session_id = getattr(callback_context.state, "session_id", "unknown")

    try:
        client = _get_client()
        request = modelarmor_v1.SanitizeModelResponseRequest(
            name=TEMPLATE_NAME,
            model_response_data=modelarmor_v1.DataItem(text=response_text),
        )
        response = client.sanitize_model_response(request)
        sanitization = response.sanitization_result

        if sanitization.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
            matched_filters = _extract_matched_filter_names(sanitization)

            # If SDP ran de-identification, prefer the redacted version over a full block
            deidentified_text = _extract_deidentified_text(sanitization)
            if deidentified_text:
                logger.warning(
                    "Model Armor REDACTED output (SDP) | session=%s | filters=%s",
                    session_id,
                    matched_filters,
                )
                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=deidentified_text)],
                    )
                )

            # Otherwise block the response entirely
            logger.warning(
                "Model Armor BLOCKED output | session=%s | filters=%s",
                session_id,
                matched_filters,
            )
            return _blocked_response(", ".join(matched_filters) or "policy violation")

        logger.debug("Model Armor: output allowed | session=%s", session_id)

    except Exception:
        logger.exception("Model Armor output screening error | session=%s", session_id)
        if not FAIL_OPEN:
            return _blocked_response("security check unavailable")

    return None  # Safe — return original response
