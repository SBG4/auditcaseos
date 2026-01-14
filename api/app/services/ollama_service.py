"""Ollama service for AI-powered case analysis."""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OllamaService:
    """Service for interacting with Ollama API for case analysis."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ):
        """
        Initialize the OllamaService.

        Args:
            host: Ollama API host URL (default from env: OLLAMA_HOST)
            model: Default model to use (default from env: OLLAMA_MODEL or 'llama3.2')
            timeout: Request timeout in seconds (default: 120)
        """
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = timeout

        # Remove trailing slash if present
        self.host = self.host.rstrip("/")

        logger.info(f"OllamaService initialized: {self.host} (model: {self.model})")

    async def _generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate a response from Ollama.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Model to use (defaults to instance model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response

        Raises:
            httpx.HTTPError: If API request fails
        """
        url = f"{self.host}/api/generate"

        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                data = response.json()
                return data.get("response", "")

        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    async def _chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Chat with Ollama using message format.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to instance model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        url = f"{self.host}/api/chat"

        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                data = response.json()
                return data.get("message", {}).get("content", "")

        except httpx.TimeoutException:
            logger.error("Ollama chat request timed out")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama chat HTTP error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Ollama chat request failed: {e}")
            raise

    def _format_case_context(self, case_data: dict[str, Any]) -> str:
        """Format case data into a readable context string."""
        parts = []

        if case_data.get("case_id"):
            parts.append(f"Case ID: {case_data['case_id']}")

        if case_data.get("case_type"):
            parts.append(f"Type: {case_data['case_type']}")

        if case_data.get("severity"):
            parts.append(f"Severity: {case_data['severity']}")

        if case_data.get("title"):
            parts.append(f"Title: {case_data['title']}")

        if case_data.get("description"):
            parts.append(f"Description: {case_data['description']}")

        if case_data.get("subject_user"):
            parts.append(f"Subject User: {case_data['subject_user']}")

        if case_data.get("subject_computer"):
            parts.append(f"Subject Computer: {case_data['subject_computer']}")

        if case_data.get("subject_devices"):
            devices = ", ".join(case_data["subject_devices"])
            parts.append(f"Devices: {devices}")

        if case_data.get("findings"):
            findings_text = "\n".join(
                f"- {f.get('title', 'Untitled')}: {f.get('description', '')}"
                for f in case_data["findings"]
            )
            parts.append(f"Findings:\n{findings_text}")

        if case_data.get("timeline_events"):
            timeline_text = "\n".join(
                f"- [{e.get('event_time', '')}] {e.get('description', '')}"
                for e in case_data["timeline_events"]
            )
            parts.append(f"Timeline:\n{timeline_text}")

        return "\n\n".join(parts)

    async def summarize_case(
        self,
        case_data: dict[str, Any],
        max_length: int = 500,
    ) -> str:
        """
        Generate a summary of an audit case.

        Args:
            case_data: Case data dictionary
            max_length: Maximum summary length (approximate)

        Returns:
            Generated summary text

        Raises:
            Exception: If summary generation fails
        """
        context = self._format_case_context(case_data)

        system_prompt = """You are an expert audit analyst assistant. Your task is to summarize
audit cases clearly and concisely. Focus on:
- Key facts and timeline
- Involved parties and systems
- Potential policy violations or security concerns
- Current status and severity

Be objective and factual. Do not make assumptions beyond the provided information."""

        prompt = f"""Please provide a concise summary of the following audit case.
The summary should be approximately {max_length} characters or less.

{context}

Summary:"""

        try:
            summary = await self._generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=max_length // 2,  # Rough token estimate
            )

            logger.info(f"Generated summary for case: {case_data.get('case_id', 'unknown')}")
            return summary.strip()

        except Exception as e:
            logger.error(f"Failed to generate case summary: {e}")
            raise

    async def suggest_findings(
        self,
        case_data: dict[str, Any],
        max_suggestions: int = 5,
    ) -> list[str]:
        """
        Suggest potential findings based on case data.

        Args:
            case_data: Case data dictionary
            max_suggestions: Maximum number of suggestions

        Returns:
            List of suggested finding descriptions

        Raises:
            Exception: If suggestion generation fails
        """
        context = self._format_case_context(case_data)
        case_type = case_data.get("case_type", "POLICY")

        system_prompt = f"""You are an expert audit analyst specializing in {case_type} investigations.
Based on the case information provided, suggest potential findings or areas of concern that
should be investigated further. Consider:
- Policy violations
- Security implications
- Patterns of behavior
- Data protection concerns
- Compliance issues

Provide specific, actionable findings."""

        prompt = f"""Based on the following audit case, suggest up to {max_suggestions} potential
findings or concerns that warrant further investigation. Format each finding on a separate line,
starting with a dash (-).

{context}

Potential Findings:"""

        try:
            response = await self._generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.6,
                max_tokens=1024,
            )

            # Parse response into list
            findings = []
            for line in response.strip().split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    finding = line[1:].strip()
                    if finding:
                        findings.append(finding)

            # Limit to max_suggestions
            findings = findings[:max_suggestions]

            logger.info(
                f"Generated {len(findings)} finding suggestions for case: "
                f"{case_data.get('case_id', 'unknown')}"
            )
            return findings

        except Exception as e:
            logger.error(f"Failed to generate finding suggestions: {e}")
            raise

    async def generate_report_section(
        self,
        case_data: dict[str, Any],
        section_type: str,
    ) -> str:
        """
        Generate a specific section of an audit report.

        Args:
            case_data: Case data dictionary
            section_type: Type of section (e.g., 'executive_summary', 'findings',
                         'timeline', 'recommendations', 'conclusion')

        Returns:
            Generated section text

        Raises:
            Exception: If generation fails
        """
        context = self._format_case_context(case_data)

        section_prompts = {
            "executive_summary": {
                "instruction": """Write an executive summary for this audit case. Include:
- Brief overview of the incident
- Key findings and their impact
- Current status
- Recommended actions
Keep it concise and suitable for senior management.""",
                "max_tokens": 1024,
            },
            "findings": {
                "instruction": """Write a detailed findings section for this audit case. Include:
- Each finding with evidence references
- Severity assessment
- Affected systems or users
- Policy/compliance implications
Be thorough and factual.""",
                "max_tokens": 2048,
            },
            "timeline": {
                "instruction": """Write a chronological timeline section for this audit case. Include:
- Key events in order
- Relevant timestamps
- Actions taken
- Evidence collected
Present events in a clear, sequential format.""",
                "max_tokens": 1024,
            },
            "recommendations": {
                "instruction": """Write recommendations for this audit case. Include:
- Immediate actions required
- Long-term preventive measures
- Policy improvements
- Training or awareness needs
Be specific and actionable.""",
                "max_tokens": 1024,
            },
            "conclusion": {
                "instruction": """Write a conclusion for this audit case report. Include:
- Summary of key points
- Overall assessment
- Final determination
- Next steps
Be clear and definitive.""",
                "max_tokens": 512,
            },
        }

        if section_type not in section_prompts:
            available = ", ".join(section_prompts.keys())
            raise ValueError(
                f"Unknown section type: {section_type}. Available: {available}"
            )

        section_config = section_prompts[section_type]

        system_prompt = """You are an expert audit analyst writing a formal audit report.
Your writing should be:
- Professional and objective
- Clear and well-structured
- Factual with evidence-based conclusions
- Compliant with audit documentation standards"""

        prompt = f"""{section_config['instruction']}

Case Information:
{context}

{section_type.replace('_', ' ').title()}:"""

        try:
            section = await self._generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=section_config["max_tokens"],
            )

            logger.info(
                f"Generated '{section_type}' section for case: "
                f"{case_data.get('case_id', 'unknown')}"
            )
            return section.strip()

        except Exception as e:
            logger.error(f"Failed to generate report section '{section_type}': {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if Ollama service is available.

        Returns:
            True if Ollama is responding, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.host}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
ollama_service = OllamaService()
