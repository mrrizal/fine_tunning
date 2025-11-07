from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class CodeBlock(BaseModel):
    start_line: int
    end_line: int
    code: str
    line_count: int


class CodeReviewPromptGenerator:
    def __init__(self):
        pass

    def _clean_code(self, code: str) -> str:
        """Clean code while preserving indentation."""
        if not code:
            return code

        lines = code.strip().splitlines()
        if not lines:
            return ""

        # Remove common leading whitespace
        non_empty_lines = [line for line in lines if line.strip()]
        if not non_empty_lines:
            return ""

        min_indent = min(len(line) - len(line.lstrip()) for line in non_empty_lines)

        cleaned_lines = []
        for line in lines:
            if line.strip():
                cleaned_lines.append(line[min_indent:])
            else:
                cleaned_lines.append("")

        return '\n'.join(cleaned_lines)

    def generate_style_review_prompt(
        self,
        added_code: List[Dict[str, Any]],
        deleted_code: List[Dict[str, Any]],
        full_function_code: str = "",
        function_name: str = ""
    ) -> str:
        """Generate a concise code review prompt with strict format enforcement."""

        # Format added code
        added_blocks = []
        for i, chunk in enumerate(added_code, 1):
            if isinstance(chunk, CodeBlock):
                code = chunk.code
            else:
                code = chunk.get('code', '')

            clean_code = self._clean_code(code)
            if clean_code:
                added_blocks.append(f"```python\n{clean_code}\n```")

        # Format deleted code
        deleted_blocks = []
        for i, chunk in enumerate(deleted_code, 1):
            if isinstance(chunk, CodeBlock):
                code = chunk.code
            else:
                code = chunk.get('code', '')

            clean_code = self._clean_code(code)
            if clean_code:
                deleted_blocks.append(f"```python\n{clean_code}\n```")

        # Determine context strategy based on change types
        has_additions = bool(added_blocks)
        has_deletions = bool(deleted_blocks)

        # Format context section
        context_section = ""
        if full_function_code:
            clean_full = self._clean_code(full_function_code)

            if has_deletions and not has_additions:
                # For deletions only, show it as "current state after removal"
                context_section = f"Current function `{function_name}` (after removal):\n```python\n{clean_full}\n```\n"
            elif has_additions or (has_additions and has_deletions):
                # For additions or mixed changes, show as current state
                context_section = f"Full function `{function_name}`:\n```python\n{clean_full}\n```\n"

        # Build the prompt with very clear instructions
        changes_section = ""
        if added_blocks:
            changes_section += f"### ADDED:\n{chr(10).join(added_blocks)}\n"
        if deleted_blocks:
            if has_deletions and not has_additions:
                changes_section += f"### REMOVED (these lines were deleted from the function above):\n{chr(10).join(deleted_blocks)}\n"
            else:
                changes_section += f"### REMOVED:\n{chr(10).join(deleted_blocks)}\n"

        if not changes_section:
            changes_section = "No code changes detected.\n"

        # Adjust instruction based on change type
        instruction_context = ""
        if has_deletions and not has_additions:
            instruction_context = " The function shown above is the current state after the removal."

        prompt = f"""### Instruction:
You are a code reviewer. Analyze this Python code change and respond EXACTLY in the format below.{instruction_context}

{context_section}{changes_section}
### Response:
SUMMARY: [One sentence describing what changed]
ISSUES: [List specific bugs/problems, or write "None found"]
IMPROVEMENTS: [Suggest specific improvements, or write "None needed"]
DECISION: [Yes/No] - [One sentence reason]"""

        return prompt.strip()

    def generate_duplication_check_prompt(
        self,
        code_snippet: str,
        similar_codes: List[Dict[str, Any]],
        function_name: str = ""
    ) -> str:
        """Generate a focused duplication check prompt."""

        if not code_snippet.strip() or not similar_codes:
            return ""

        clean_snippet = self._clean_code(code_snippet)

        # Only use the most similar code to avoid confusion
        most_similar = similar_codes[0]
        file_path = most_similar.get('file', 'unknown_file')
        similar_code = most_similar.get('code', '')
        similarity_score = most_similar.get('similarity', 'N/A')

        clean_similar = self._clean_code(similar_code)

        prompt = f"""Check for code duplication. Respond EXACTLY in the format below.

Current code from `{function_name}`:
```python
{clean_snippet}
```

Similar code from `{file_path}` ({similarity_score}% similar):
```python
{clean_similar}
```

You MUST respond in this EXACT format:

DUPLICATION LEVEL: [None/Low/Medium/High]

ANALYSIS: [Are these actual duplicates? One sentence.]

RECOMMENDATION: [What action to take? One sentence.]

Do not add extra text."""

        return prompt.strip()

    def generate_summary_prompt(
        self,
        style_result: str,
        duplication_result: str,
        function_name: str = ""
    ) -> str:
        """Generate a very focused summary prompt."""

        # Extract key info from previous results
        def extract_key_info(result: str, keyword: str) -> str:
            if not result or "sorry" in result.lower():
                return "No issues"

            # Look for the specific information we need
            lines = result.split('\n')
            for line in lines:
                if keyword.upper() in line.upper():
                    # Extract just the content after the colon
                    if ':' in line:
                        return line.split(':', 1)[1].strip()
            return "No issues"

        # Extract actual findings, not the review format
        style_issues = extract_key_info(style_result, "ISSUES")
        style_decision = extract_key_info(style_result, "DECISION")
        dup_level = extract_key_info(duplication_result, "DUPLICATION LEVEL")

        prompt = f"""Based on these code review results for function `{function_name}`, make a final decision:

STYLE REVIEW FOUND: {style_issues}
STYLE DECISION: {style_decision}
DUPLICATION LEVEL: {dup_level}

Your job: Decide if this code change should be approved based on the findings above.

Response format:
ISSUES FOUND: [Summarize actual problems found, or "None"]

PRIORITY: [High/Medium/Low]

RECOMMENDATION: [Approve/Request Changes/Needs Discussion]

REASON: [Why you made this recommendation]

Focus on the CODE QUALITY, not the review format."""

        return prompt.strip()

    def generate_contextual_review_prompt(self, payload_data: Dict[str, Any]) -> str:
        """Generate a comprehensive but concise review prompt."""

        added_code = payload_data.get('added_code', [])
        deleted_code = payload_data.get('deleted_code', [])
        full_function_code = payload_data.get('full_function_code', '')
        function_name = payload_data.get('function_name', '')

        return self.generate_style_review_prompt(
            added_code=added_code,
            deleted_code=deleted_code,
            full_function_code=full_function_code,
            function_name=function_name
        )


# Even more minimal version for better model compliance
class MinimalCodeReviewPrompts:
    def __init__(self):
        pass

    def _clean_code(self, code: str) -> str:
        """Basic code cleaning."""
        return code.strip()[:400] if code else ""  # Limit length

    def generate_review_prompt(
        self,
        added_code: List[Dict[str, Any]],
        deleted_code: List[Dict[str, Any]],
        function_name: str = ""
    ) -> str:
        """Ultra-focused review prompt."""

        # Get the main code blocks
        added_text = ""
        if added_code:
            first_added = added_code[0]
            if isinstance(first_added, CodeBlock):
                added_text = first_added.code
            else:
                added_text = first_added.get('code', '')

        deleted_text = ""
        if deleted_code:
            first_deleted = deleted_code[0]
            if isinstance(first_deleted, CodeBlock):
                deleted_text = first_deleted.code
            else:
                deleted_text = first_deleted.get('code', '')

        prompt = f"""Code review for function `{function_name}`. Answer in EXACT format below.

"""

        if added_text:
            prompt += f"NEW CODE:\n```python\n{self._clean_code(added_text)}\n```\n"

        if deleted_text:
            prompt += f"REMOVED CODE:\n```python\n{self._clean_code(deleted_text)}\n```\n"

        prompt += """
Format your response EXACTLY like this:

ISSUES: [List problems or "None"]
APPROVE: [Yes/No]
REASON: [One sentence]

No other text allowed."""

        return prompt

    def generate_duplication_prompt(
        self,
        code_snippet: str,
        similar_codes: List[Dict[str, Any]]
    ) -> str:
        """Ultra-simple duplication check."""

        if not similar_codes:
            return "No similar code found.\n\nDUPLICATE: No\nACTION: None needed"

        similar_code = similar_codes[0].get('code', '') if similar_codes else ''

        return f"""Compare these code blocks:

CODE A:
```python
{self._clean_code(code_snippet)}
```

CODE B:
```python
{self._clean_code(similar_code)}
```

Response format:
DUPLICATE: [Yes/No]
ACTION: [Combine/Keep separate/Review needed]"""

    def generate_summary_prompt(self, style_result: str, duplication_result: str) -> str:
        """Ultra-simple summary."""

        # Extract actual findings from the reviews
        style_clean = style_result.replace("ISSUES:", "").replace("APPROVE:", "").replace("REASON:", "")[:80]
        dup_clean = duplication_result.replace("DUPLICATE:", "").replace("ACTION:", "")[:50]

        return f"""Make final decision about this code change:

What the style review found: {style_clean}
What the duplication check found: {dup_clean}

Should this code change be merged?

DECISION: [APPROVE/REJECT]
REASON: [One sentence about the CODE QUALITY]

Do not comment on the review process itself."""


# Factory function to choose the right prompt generator
def get_prompt_generator(model_name: str = ""):
    """Select appropriate prompt generator based on model."""
    if "deepseek" in model_name.lower() or "coder" in model_name.lower():
        return MinimalCodeReviewPrompts()
    else:
        return CodeReviewPromptGenerator()
