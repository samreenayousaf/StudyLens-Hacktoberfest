import json
import re
from typing import Any, Dict, List, Optional
from app.ai.ollama_client import OllamaClient
from app.ai.prompts import ANALYSIS_SYSTEM_PROMPT, build_analysis_prompt


class AnswerAnalyzer:
    """Analyzer for student written answers using local Gemma 3:1B through Ollama."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.client = ollama_client or OllamaClient()

    def analyze(
        self,
        question_text: str,
        target_concept_name: str,
        target_concept_description: str,
        student_answer: str,
        known_concepts: List[str],
    ) -> Dict[str, Any]:
        """Perform concept-aware analysis of a student answer."""
        prompt = build_analysis_prompt(
            question_text=question_text,
            target_concept_name=target_concept_name,
            target_concept_description=target_concept_description,
            student_answer=student_answer,
            known_concepts=known_concepts,
        )

        raw_response = self.client.generate(
            prompt=prompt,
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
        )

        return self.parse_and_normalize_response(
            raw_response=raw_response,
            target_concept_name=target_concept_name,
            student_answer=student_answer,
            known_concepts=known_concepts,
        )

    def parse_and_normalize_response(
        self,
        raw_response: str,
        target_concept_name: str,
        student_answer: str,
        known_concepts: List[str],
    ) -> Dict[str, Any]:
        """Parse raw JSON output from model and apply safety/normalization rules."""
        parsed_data = self._extract_json(raw_response)

        # 1. Normalize understanding_score
        raw_score = parsed_data.get("understanding_score", 50)
        try:
            score = float(raw_score)
        except (ValueError, TypeError):
            score = 50.0
        clamped_score = max(0.0, min(100.0, score))

        # 2. Normalize detected_concepts against known active concepts & prevent concept explosion
        raw_detected = parsed_data.get("detected_concepts", [])
        valid_detected = self._filter_detected_concepts(
            raw_detected=raw_detected,
            target_concept_name=target_concept_name,
            student_answer=student_answer,
            known_concepts=known_concepts,
        )

        # 3. Normalize misconceptions & apply False-Positive Protection filters
        raw_misconceptions = parsed_data.get("misconceptions", [])
        if not isinstance(raw_misconceptions, list):
            raw_misconceptions = []

        valid_misconceptions = [str(m).strip() for m in raw_misconceptions if m and str(m).strip()]

        # 4. Normalize evidence
        evidence = parsed_data.get("evidence", "")
        if not isinstance(evidence, str) or not evidence.strip():
            evidence = f"Analysis of answer regarding '{target_concept_name}'."
        else:
            evidence = evidence.strip()

        # Apply False-Positive Misconception Protection & Contradiction Filters
        valid_misconceptions = self._filter_false_positive_misconceptions(
            target_concept_name=target_concept_name,
            student_answer=student_answer,
            misconceptions=valid_misconceptions,
            understanding_score=clamped_score,
            evidence=evidence,
        )

        # Apply Score, Contradiction, and Evidence Validation
        clamped_score, valid_misconceptions, evidence = self._validate_score_and_contradictions(
            target_concept_name=target_concept_name,
            student_answer=student_answer,
            score=clamped_score,
            misconceptions=valid_misconceptions,
            evidence=evidence,
        )

        return {
            "understanding_score": clamped_score,
            "detected_concepts": valid_detected,
            "misconceptions": valid_misconceptions,
            "evidence": evidence,
        }

    def _filter_detected_concepts(
        self,
        raw_detected: Any,
        target_concept_name: str,
        student_answer: str,
        known_concepts: List[str],
    ) -> List[str]:
        """Ensure detected concepts are grounded in the question and student answer.
        Filters out any secondary concepts from known_concepts that are NOT mentioned in the student's answer."""
        if not isinstance(raw_detected, list):
            raw_detected = [target_concept_name]

        known_map = {c.lower().strip(): c for c in known_concepts}
        valid_detected = []

        # Always include target_concept_name if valid
        target_clean = target_concept_name.lower().strip()
        if target_clean in known_map:
            valid_detected.append(known_map[target_clean])

        answer_lower = student_answer.lower()

        # Keyword mapping for active curriculum concepts to verify explicit presence in answer text
        concept_keywords = {
            "waterfall": ["waterfall"],
            "agile": ["agile"],
            "scrum": ["scrum"],
            "coupling": ["coupling"],
            "cohesion": ["cohesion"],
            "requirements engineering": ["requirements engineering"],
            "functional vs non-functional requirements": ["functional requirement", "non-functional requirement", "non-functional"],
            "software testing": ["software testing"],
            "unit testing": ["unit test", "unit testing"],
            "integration testing": ["integration test", "integration testing"],
            "version control": ["version control", "git"],
        }

        for item in raw_detected:
            if not isinstance(item, str):
                continue
            item_clean = item.lower().strip()
            if item_clean in known_map:
                canonical_name = known_map[item_clean]
                if canonical_name in valid_detected:
                    continue

                # Secondary concepts MUST be explicitly mentioned in student answer
                keywords = concept_keywords.get(canonical_name.lower(), [canonical_name.lower()])
                if any(kw in answer_lower for kw in keywords):
                    valid_detected.append(canonical_name)

        return valid_detected if valid_detected else [target_concept_name]

    def _validate_score_and_contradictions(
        self,
        target_concept_name: str,
        student_answer: str,
        score: float,
        misconceptions: List[str],
        evidence: str,
    ) -> tuple[float, List[str], str]:
        """Validate score against conceptual contradictions, misconceptions, and evidence alignment."""
        answer_lower = student_answer.lower()
        concept_lower = target_concept_name.lower()

        # 1. Waterfall Reversal Check:
        # If student claims Waterfall is for changing requirements, frequent changes, or continuous Agile-style modifications
        if "waterfall" in concept_lower or "waterfall" in answer_lower:
            has_stable_affirmation = any(
                st in answer_lower
                for st in ["unlikely to change", "stable", "well-defined", "predictable", "specified upfront"]
            )
            is_waterfall_reversal = (
                any(
                    phrase in answer_lower
                    for phrase in [
                        "change frequently",
                        "frequently change",
                        "modify requirements easily",
                        "continuous involvement",
                        "frequently changing",
                    ]
                )
                and not has_stable_affirmation
                and not any(neg in answer_lower for neg in ["not for", "does not allow", "avoids", "unsuited"])
            )

            if is_waterfall_reversal:
                score = min(score, 35.0)
                misc_text = "Waterfall is suitable for projects with constantly changing requirements."
                if not any("changing requirements" in m.lower() or "frequently" in m.lower() for m in misconceptions):
                    misconceptions.append(misc_text)
                if any(praise in evidence.lower() for praise in ["correctly", "aligns", "accurately", "good understanding"]):
                    evidence = "The student incorrectly claims Waterfall is suited for frequently changing requirements and continuous modifications, whereas Waterfall is designed for stable, predictable requirements and sequential stages."

        # 2. Coupling Reversal Check:
        if "coupling" in concept_lower or "coupling" in answer_lower:
            is_coupling_reversal = (
                ("high coupling" in answer_lower or ("high" in answer_lower and "coupling" in answer_lower))
                and any(
                    phrase in answer_lower
                    for phrase in [
                        "very few dependencies",
                        "mostly independent",
                        "few dependencies",
                    ]
                )
                and not ("low coupling" in answer_lower and "desirable" in answer_lower)
            )

            if is_coupling_reversal:
                score = min(score, 30.0)
                misc_text = "Reverses definition of high coupling by claiming high coupled modules have very few dependencies."
                if not any("few dependencies" in m.lower() or "reverses" in m.lower() for m in misconceptions):
                    misconceptions.append(misc_text)
                if any(praise in evidence.lower() for praise in ["correctly", "aligns", "accurately", "good understanding"]):
                    evidence = "The student incorrectly claims high coupling means modules have very few dependencies, reversing the true definition where high coupling indicates strong interdependence."

        # 3. Functional vs Non-Functional Requirements Reversal Check:
        if "functional" in concept_lower or "requirement" in concept_lower:
            func_def_reversal = bool(
                re.search(r'(?<!non-)(?<!non\s)\bfunctional\s+requirements?\s+(?:describe|are|specify|define|include)\s+(?:how|performance|speed|reliability|quality)', answer_lower)
                or (re.search(r'(?<!non-)(?<!non\s)\bfunctional\s+requirements?\b', answer_lower) and any(phrase in answer_lower for phrase in ["describe how well", "how the system performs", "how well a system"]))
            )
            nonfunc_def_reversal = bool(
                re.search(r'\bnon-?functional\s+requirements?\s+(?:describe|are|specify|define|include)\s+(?:the\s+)?(?:specific\s+)?(?:features|actions|what|user registration)', answer_lower)
                or (re.search(r'\bnon-?functional\s+requirements?\b', answer_lower) and any(phrase in answer_lower for phrase in ["features and actions", "specific features", "actions the system must provide"]))
            )
            is_func_reversal = func_def_reversal or nonfunc_def_reversal

            if is_func_reversal:
                score = min(score, 35.0)
                misc_text = "Reverses definitions of functional and non-functional requirements by claiming functional requirements describe performance and non-functional requirements describe features/actions."
                if not any("revers" in m.lower() or "functional" in m.lower() for m in misconceptions):
                    misconceptions.append(misc_text)
                if any(praise in evidence.lower() for praise in ["correctly", "aligns", "accurately", "good understanding"]):
                    evidence = "The student incorrectly reverses the definitions of functional and non-functional requirements, claiming functional requirements describe system performance and non-functional requirements describe features."

        # 4. Misconception presence score clamping:
        # If valid misconceptions are present, score should not be unjustifiably high (> 50.0)
        if misconceptions and score > 50.0:
            score = 50.0

        # 5. Evidence-score alignment:
        # If score is low (< 50.0), evidence should not claim the answer is correct
        if score < 50.0 and any(praise in evidence.lower() for praise in ["correctly describes", "correctly states", "accurately explains", "aligns with", "good understanding"]):
            evidence = f"The student's answer contains conceptual errors regarding {target_concept_name}."

        return score, misconceptions, evidence

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Safely extract JSON dict from text, stripping markdown codeblocks if present."""
        if not text:
            return {}

        cleaned = text.strip()
        # Remove markdown fences ```json ... ```
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)
            else:
                cleaned = re.sub(r"```(?:json)?|```", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback regex search for JSON dict object
            dict_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if dict_match:
                try:
                    return json.loads(dict_match.group(1))
                except json.JSONDecodeError:
                    pass
            return {}

    def _filter_false_positive_misconceptions(
        self,
        target_concept_name: str,
        student_answer: str,
        misconceptions: List[str],
        understanding_score: float,
        evidence: str,
    ) -> List[str]:
        """Filter out false positive misconceptions caused by omissions, meta-judgments, or direct contradictions of student statements."""
        if not misconceptions:
            return []

        answer_lower = student_answer.lower()

        # Omission & Meta-judgment patterns (omission != misconception)
        omission_patterns = [
            "does not explicitly",
            "doesn't explicitly",
            "fails to mention",
            "fail to mention",
            "did not mention",
            "didn't mention",
            "does not mention",
            "doesn't mention",
            "omitted",
            "omits",
            "lacks detail",
            "lacks a broader",
            "lacks a deeper",
            "lacks connection",
            "lacks understanding of why",
            "does not fully articulate",
            "doesn't fully articulate",
            "does not explain",
            "doesn't explain",
            "neglecting technical",
            "focuses solely on",
            "focus solely on",
            "does not address",
            "doesn't address",
            "has not demonstrated",
            "is not explicitly",
            "without considering",
            "does not specify",
            "doesn't specify",
        ]

        filtered = []
        for misc in misconceptions:
            misc_lower = misc.lower()

            # 1. Reject meta-judgments / completeness comments about missing details
            if any(pat in misc_lower for pat in omission_patterns):
                continue

            # 2. Agile False-Positive Protection:
            has_agile_values = (
                "collaboration" in answer_lower
                or "working software" in answer_lower
                or "adapt" in answer_lower
                or "responding to change" in answer_lower
                or "response to change" in answer_lower
                or "incremental" in answer_lower
                or "flexible" in answer_lower
            )
            advocates_fixed_plan = (
                ("fixed plan" in answer_lower or "waterfall" in answer_lower or "sequential" in answer_lower)
                and not any(neg in answer_lower for neg in ["instead of", "rather than", "not ", "no "])
            )
            if ("agile" in target_concept_name.lower() or "agile" in answer_lower) and not advocates_fixed_plan:
                if has_agile_values and any(
                    bad in misc_lower
                    for bad in [
                        "rigid",
                        "sequential",
                        "waterfall",
                        "fixed plan",
                        "ignores working software",
                        "neglecting technical",
                        "focuses solely on",
                        "solely on customer",
                        "without considering",
                    ]
                ):
                    continue

            # 3. Waterfall False-Positive Protection:
            # If student answer affirms Waterfall suitability for stable requirements,
            # reject false misconceptions claiming Waterfall is for changing requirements.
            has_waterfall_stable = (
                "stable" in answer_lower
                or "unlikely to change" in answer_lower
                or "well-defined" in answer_lower
                or "predictable" in answer_lower
                or "specified upfront" in answer_lower
                or "sequential" in answer_lower
            )
            if ("waterfall" in target_concept_name.lower() or "waterfall" in answer_lower) and has_waterfall_stable:
                if any(
                    bad in misc_lower
                    for bad in [
                        "changing requirements",
                        "frequently changing",
                        "evolving requirements",
                        "continuous involvement",
                        "modify requirements easily",
                        "unsuited for stable",
                    ]
                ):
                    continue

            # 4. Scrum Roles False-Positive Protection:
            has_scrum_roles = (
                "product owner" in answer_lower
                and "scrum master" in answer_lower
                and ("developer" in answer_lower or "development team" in answer_lower)
            )
            if "scrum" in target_concept_name.lower() or "scrum" in answer_lower:
                if has_scrum_roles and any(
                    bad in misc_lower
                    for bad in [
                        "interchangeable",
                        "solely responsible",
                        "only responsible",
                        "roles are distinct and have separate responsibilities",
                        "roles are distinct",
                    ]
                ):
                    continue

            # 5. Functional vs Non-Functional Requirements Protection:
            has_req_distinction = (
                ("functional" in answer_lower and "non-functional" in answer_lower)
                and ("what" in answer_lower or "behavior" in answer_lower)
                and ("how" in answer_lower or "quality" in answer_lower or "constraint" in answer_lower)
            )
            if "requirement" in target_concept_name.lower() or "functional" in answer_lower:
                if has_req_distinction and any(
                    bad in misc_lower
                    for bad in [
                        "just about what",
                        "doesn't understand the difference",
                        "does not understand the difference",
                        "lack of functionality",
                    ]
                ):
                    continue

            # 6. Coupling False-Positive Protection
            supports_low_coupling = (
                "low coupling" in answer_lower
                or "undesirable" in answer_lower
                or "strong dependencies" in answer_lower
                or "easier to maintain" in answer_lower
                or "reduce coupling" in answer_lower
                or "few dependencies" in answer_lower
            )
            if "coupling" in target_concept_name.lower() or "coupling" in answer_lower:
                if supports_low_coupling and not ("high coupling is desirable" in answer_lower or ("high coupling" in answer_lower and "few dependencies" in answer_lower)):
                    if any(
                        bad in misc_lower
                        for bad in [
                            "high coupling preference",
                            "prefers high coupling",
                            "desirable",
                            "always bad",
                            "tightly dependent",
                            "confuses high and low",
                            "confuses low and high",
                            "reverses definition",
                            "tightly dependent on each other",
                            "lack of dependencies",
                            "core definition",
                            "implies a lack",
                            "few dependencies",
                        ]
                    ):
                        continue

            filtered.append(misc)

        return filtered
