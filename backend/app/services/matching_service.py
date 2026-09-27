"""
Student Matching Service - Phase 2.
Implements the Student Matching + Confidence + Exception Engine.

Safety Principle:
NEVER silently assign an attendance record to the wrong student.
Ambiguous matches must be flagged as NEEDS_REVIEW.
Unmatched records must be flagged as UNMATCHED.
Missing ERP students are never automatically marked absent.
"""

import re
import difflib
from typing import List, Dict, Tuple, Optional, Set
from app.core.logging import logger
from app.schemas.attendance import AttendanceItem
from app.schemas.student import (
    StudentInfo,
    MatchCandidate,
    MatchingResultItem,
    MatchingSummary,
    MatchAttendanceRequest,
    MatchAttendanceResponse,
    MatchingExceptionItem,
    MatchMethod,
    ResolutionState,
)


class StudentMatchingService:
    """
    Deterministic matching engine linking AI attendance records to ERP student records.
    
    Matching Priority:
    1. Student ID (Primary unique identifier)
    2. Roll Number (Secondary numeric/code identifier)
    3. Enrollment Number (Official registration identifier)
    4. Exact Name (Case-sensitive exact match)
    5. Normalized Name (Case-insensitive, whitespace-collapsed)
    6. Fuzzy Name Matching (Safe Levenshtein-based similarity)
    7. Resolution: MATCHED, NEEDS_REVIEW, or UNMATCHED
    """

    # Configurable confidence ratings
    CONF_STUDENT_ID = 1.00
    CONF_ROLL_NUMBER = 0.98
    CONF_ENROLLMENT_NUMBER = 0.98
    CONF_EXACT_NAME = 0.95
    CONF_NORMALIZED_NAME = 0.90
    
    # Fuzzy matching thresholds
    FUZZY_HIGH_CONF_THRESHOLD = 0.88      # Minimum similarity to consider auto-matching
    FUZZY_AMBIGUITY_MARGIN = 0.12         # Margin required over 2nd best candidate to avoid ambiguity
    FUZZY_MIN_CANDIDATE_THRESHOLD = 0.60  # Minimum similarity to qualify as a candidate

    @staticmethod
    def normalize_name(name: Optional[str]) -> str:
        """
        Normalizes a name string for reliable comparison:
        - Converts to lowercase
        - Strips punctuation (dots, commas, hyphens)
        - Collapses multiple whitespace characters to a single space
        """
        if not name:
            return ""
        # Remove punctuation, keep alphanumeric and spaces
        cleaned = re.sub(r"[^\w\s]", " ", name.lower())
        # Collapse multiple whitespace
        return " ".join(cleaned.split())

    @staticmethod
    def extract_roll_digits(raw_val: Optional[str]) -> Optional[str]:
        """
        Extracts clean numeric roll digits from raw identifier (e.g. 'Roll 015' -> '015', '#02' -> '02').
        """
        if not raw_val:
            return None
        cleaned = raw_val.strip()
        match = re.search(r"\b(\d+)\b", cleaned)
        if match:
            return match.group(1)
        return None

    def match_attendance(self, request: MatchAttendanceRequest) -> MatchAttendanceResponse:
        """
        Executes deterministic matching of AI attendance items against the ERP student roster.
        """
        erp_students = request.erp_students
        ai_records = request.ai_records

        logger.info(
            f"Beginning Student Matching Engine: {len(ai_records)} AI records vs {len(erp_students)} ERP students"
        )

        # Index ERP students for efficient and deterministic lookup
        id_index: Dict[str, StudentInfo] = {}
        roll_exact_index: Dict[str, List[StudentInfo]] = {}
        roll_numeric_index: Dict[int, List[StudentInfo]] = {}
        enrollment_index: Dict[str, StudentInfo] = {}
        exact_name_index: Dict[str, List[StudentInfo]] = {}
        norm_name_index: Dict[str, List[StudentInfo]] = {}

        for student in erp_students:
            # Student ID (unique key)
            clean_id = student.student_id.strip().upper()
            id_index[clean_id] = student

            # Roll number
            if student.roll_number:
                rn_clean = student.roll_number.strip()
                roll_exact_index.setdefault(rn_clean.upper(), []).append(student)
                digits = self.extract_roll_digits(rn_clean)
                if digits is not None:
                    roll_numeric_index.setdefault(int(digits), []).append(student)

            # Enrollment number
            if student.enrollment_number:
                enrollment_index[student.enrollment_number.strip().upper()] = student

            # Exact Name
            exact_name_index.setdefault(student.name.strip(), []).append(student)

            # Normalized Name
            norm_name = self.normalize_name(student.name)
            if norm_name:
                norm_name_index.setdefault(norm_name, []).append(student)

        matched_results: List[MatchingResultItem] = []
        assigned_students_map: Dict[str, AttendanceStatus] = {}
        exceptions: List[MatchingExceptionItem] = []

        # Process each AI record in sequence
        for item in ai_records:
            match_res = self._match_single_record(
                item=item,
                erp_students=erp_students,
                id_index=id_index,
                roll_exact_index=roll_exact_index,
                roll_numeric_index=roll_numeric_index,
                enrollment_index=enrollment_index,
                exact_name_index=exact_name_index,
                norm_name_index=norm_name_index,
            )

            # Preserve raw_student_id from AI record
            if not match_res.raw_student_id and getattr(item, "raw_student_id", None):
                match_res.raw_student_id = item.raw_student_id

            # Safety Rule 1: Handle Low-Confidence physical mark detection
            # Low confidence must trigger teacher review without inventing a third status
            if item.confidence < 0.65 and match_res.resolution == ResolutionState.MATCHED:
                match_res.resolution = ResolutionState.NEEDS_REVIEW
                match_res.review_reason = (
                    f"Unclear physical attendance mark on sheet (AI confidence: {item.confidence:.2f}). "
                    f"Requires teacher review."
                )
                exceptions.append(
                    MatchingExceptionItem(
                        type="UNCLEAR_ATTENDANCE_MARK",
                        student_id=match_res.matched_student_id,
                        name=match_res.matched_name or item.raw_name,
                        message=match_res.review_reason,
                        details={
                            "ai_confidence": item.confidence,
                            "detected_status": item.status.value if hasattr(item.status, "value") else str(item.status),
                        },
                    )
                )

            # Safety Rule 2: Check for duplicate & conflicting AI detection of the same ERP student
            if match_res.matched_student_id:
                clean_id = match_res.matched_student_id.strip().upper()
                if clean_id in assigned_students_map:
                    prev_status = assigned_students_map[clean_id]
                    match_res.is_duplicate = True
                    match_res.resolution = ResolutionState.NEEDS_REVIEW

                    if prev_status != item.status:
                        match_res.review_reason = (
                            f"Conflicting attendance records detected for student ID '{match_res.matched_student_id}' "
                            f"({match_res.matched_name}): {prev_status} vs {item.status}. Requires teacher review."
                        )
                        exceptions.append(
                            MatchingExceptionItem(
                                type="CONFLICTING_ATTENDANCE_DETECTED",
                                student_id=match_res.matched_student_id,
                                name=match_res.matched_name,
                                message=match_res.review_reason,
                                details={
                                    "previous_status": prev_status.value if hasattr(prev_status, "value") else str(prev_status),
                                    "current_status": item.status.value if hasattr(item.status, "value") else str(item.status),
                                },
                            )
                        )
                    else:
                        match_res.review_reason = (
                            f"Duplicate AI record: Student ID '{match_res.matched_student_id}' "
                            f"({match_res.matched_name}) appeared more than once in AI results."
                        )
                        exceptions.append(
                            MatchingExceptionItem(
                                type="DUPLICATE_DETECTED",
                                student_id=match_res.matched_student_id,
                                name=match_res.matched_name,
                                message=match_res.review_reason,
                                details={
                                    "raw_name": item.raw_name,
                                    "raw_identifier": item.raw_identifier,
                                },
                            )
                        )
                else:
                    assigned_students_map[clean_id] = item.status

            # Record review exception if ambiguous
            if match_res.resolution == ResolutionState.NEEDS_REVIEW and not match_res.is_duplicate:
                exceptions.append(
                    MatchingExceptionItem(
                        type="AMBIGUOUS_MATCH",
                        student_id=match_res.matched_student_id,
                        name=match_res.matched_name or item.raw_name,
                        message=match_res.review_reason or "Ambiguous match requires teacher review.",
                        details={"candidates_count": len(match_res.candidates)},
                    )
                )
            elif match_res.resolution == ResolutionState.UNMATCHED:
                exceptions.append(
                    MatchingExceptionItem(
                        type="UNMATCHED_STUDENT",
                        name=item.raw_name,
                        message=f"No matching ERP student found for AI record: '{item.raw_name or item.raw_identifier}'",
                        details={
                            "raw_name": item.raw_name,
                            "raw_identifier": item.raw_identifier,
                        },
                    )
                )

            matched_results.append(match_res)

        # Detect ERP students not present in AI results
        # IMPORTANT: Missing students are NEVER marked absent automatically.
        missing_erp_students: List[StudentInfo] = []
        for student in erp_students:
            clean_id = student.student_id.strip().upper()
            if clean_id not in assigned_students_map:
                missing_erp_students.append(student)
                exceptions.append(
                    MatchingExceptionItem(
                        type="MISSING_ERP_STUDENT",
                        student_id=student.student_id,
                        name=student.name,
                        message=(
                            f"Student {student.student_id} ({student.name}) was not detected in AI results. "
                            f"Will NOT be marked absent automatically."
                        ),
                    )
                )

        # Sort missing students deterministically by roll number or student ID
        missing_erp_students.sort(key=lambda s: (s.roll_number or "", s.student_id))

        # Compute summary tallies
        matched_count = sum(1 for r in matched_results if r.resolution == ResolutionState.MATCHED)
        needs_review_count = sum(1 for r in matched_results if r.resolution == ResolutionState.NEEDS_REVIEW)
        unmatched_count = sum(1 for r in matched_results if r.resolution == ResolutionState.UNMATCHED)
        duplicates_count = sum(1 for r in matched_results if r.is_duplicate)

        summary = MatchingSummary(
            total_ai_records=len(ai_records),
            matched=matched_count,
            needs_review=needs_review_count,
            unmatched=unmatched_count,
            duplicates=duplicates_count,
            total_erp_students=len(erp_students),
            missing_erp_students_count=len(missing_erp_students),
        )

        logger.info(
            f"Student Matching complete: {matched_count} Matched, {needs_review_count} Needs Review "
            f"({duplicates_count} duplicates), {unmatched_count} Unmatched, {len(missing_erp_students)} Missing ERP students."
        )

        return MatchAttendanceResponse(
            success=True,
            results=matched_results,
            summary=summary,
            erp_students_not_detected=missing_erp_students,
            exceptions=exceptions,
        )

    @classmethod
    def compute_fuzzy_score(cls, norm_ai_name: str, norm_erp_name: str) -> float:
        """
        Computes a safe similarity score between AI detected name and ERP student name.
        Guards against false positives where common surnames (e.g. Patel, Sharma) match
        completely different students (e.g. Suresh Patel vs Sneha Patel).
        """
        overall_ratio = difflib.SequenceMatcher(None, norm_ai_name, norm_erp_name).ratio()

        ai_parts = norm_ai_name.split()
        erp_parts = norm_erp_name.split()

        # Multi-word names: guard against completely different first or last names
        if len(ai_parts) >= 2 and len(erp_parts) >= 2:
            first_ratio = difflib.SequenceMatcher(None, ai_parts[0], erp_parts[0]).ratio()
            # If first names are completely different (< 0.70), this is NOT a typo match
            if first_ratio < 0.70:
                return 0.0

            last_ratio = difflib.SequenceMatcher(None, ai_parts[-1], erp_parts[-1]).ratio()
            # If last names are completely different (< 0.60), this is NOT a match
            if last_ratio < 0.60:
                return 0.0

            return overall_ratio

        return overall_ratio

    def _match_single_record(
        self,
        item: AttendanceItem,
        erp_students: List[StudentInfo],
        id_index: Dict[str, StudentInfo],
        roll_exact_index: Dict[str, List[StudentInfo]],
        roll_numeric_index: Dict[int, List[StudentInfo]],
        enrollment_index: Dict[str, StudentInfo],
        exact_name_index: Dict[str, List[StudentInfo]],
        norm_name_index: Dict[str, List[StudentInfo]],
    ) -> MatchingResultItem:
        """
        Executes prioritized matching pipeline for a single AI attendance entry.
        """
        raw_id = item.raw_identifier.strip() if item.raw_identifier else ""
        raw_name = item.raw_name.strip() if item.raw_name else ""
        raw_mark = item.raw_attendance_mark
        ai_conf = round(item.confidence, 2)

        # -------------------------------------------------------------
        # 1. PRIORITY 1: Student ID Matching
        # -------------------------------------------------------------
        target_student_id = (getattr(item, "raw_student_id", None) or "").strip()
        if not target_student_id and raw_id:
            target_student_id = raw_id

        if target_student_id:
            clean_raw_id = target_student_id.upper()
            if clean_raw_id in id_index:
                matched_stu = id_index[clean_raw_id]
                return MatchingResultItem(
                    raw_name=item.raw_name,
                    raw_identifier=item.raw_identifier,
                    raw_student_id=getattr(item, "raw_student_id", None),
                    raw_attendance_mark=raw_mark,
                    status=item.status,
                    ai_confidence=ai_conf,
                    match_confidence=self.CONF_STUDENT_ID,
                    matched_student_id=matched_stu.student_id,
                    matched_roll_number=matched_stu.roll_number,
                    matched_name=matched_stu.name,
                    match_method=MatchMethod.STUDENT_ID,
                    resolution=ResolutionState.MATCHED,
                )

        # -------------------------------------------------------------
        # 2. PRIORITY 2: Roll Number Matching
        # -------------------------------------------------------------
        if raw_id:
            # Check exact roll string match first (e.g. "001" or "015")
            clean_rn = raw_id.upper()
            if clean_rn in roll_exact_index:
                candidates = roll_exact_index[clean_rn]
                if len(candidates) == 1:
                    matched_stu = candidates[0]
                    return MatchingResultItem(
                        raw_name=item.raw_name,
                        raw_identifier=item.raw_identifier,
                        raw_attendance_mark=raw_mark,
                        status=item.status,
                        ai_confidence=ai_conf,
                        match_confidence=self.CONF_ROLL_NUMBER,
                        matched_student_id=matched_stu.student_id,
                        matched_roll_number=matched_stu.roll_number,
                        matched_name=matched_stu.name,
                        match_method=MatchMethod.ROLL_NUMBER,
                        resolution=ResolutionState.MATCHED,
                    )
                else:
                    return MatchingResultItem(
                        raw_name=item.raw_name,
                        raw_identifier=item.raw_identifier,
                        raw_attendance_mark=raw_mark,
                        status=item.status,
                        ai_confidence=ai_conf,
                        match_confidence=0.50,
                        match_method=MatchMethod.ROLL_NUMBER,
                        resolution=ResolutionState.NEEDS_REVIEW,
                        review_reason=f"Multiple students share roll number '{clean_rn}'",
                        candidates=[
                            MatchCandidate(
                                student_id=s.student_id,
                                roll_number=s.roll_number,
                                name=s.name,
                            )
                            for s in candidates
                        ],
                    )

            # Check numeric roll integer extraction (e.g. "Roll 15" -> 15)
            digits = self.extract_roll_digits(raw_id)
            if digits is not None:
                int_rn = int(digits)
                if int_rn in roll_numeric_index:
                    candidates = roll_numeric_index[int_rn]
                    if len(candidates) == 1:
                        matched_stu = candidates[0]
                        return MatchingResultItem(
                            raw_name=item.raw_name,
                            raw_identifier=item.raw_identifier,
                            raw_attendance_mark=raw_mark,
                            status=item.status,
                            ai_confidence=ai_conf,
                            match_confidence=self.CONF_ROLL_NUMBER,
                            matched_student_id=matched_stu.student_id,
                            matched_roll_number=matched_stu.roll_number,
                            matched_name=matched_stu.name,
                            match_method=MatchMethod.ROLL_NUMBER,
                            resolution=ResolutionState.MATCHED,
                        )
                    else:
                        return MatchingResultItem(
                            raw_name=item.raw_name,
                            raw_identifier=item.raw_identifier,
                            raw_attendance_mark=raw_mark,
                            status=item.status,
                            ai_confidence=ai_conf,
                            match_confidence=0.50,
                            match_method=MatchMethod.ROLL_NUMBER,
                            resolution=ResolutionState.NEEDS_REVIEW,
                            review_reason=f"Multiple students match numeric roll number '{int_rn}'",
                            candidates=[
                                MatchCandidate(
                                    student_id=s.student_id,
                                    roll_number=s.roll_number,
                                    name=s.name,
                                )
                                for s in candidates
                            ],
                        )

        # -------------------------------------------------------------
        # 3. PRIORITY 3: Enrollment Number Matching
        # -------------------------------------------------------------
        if raw_id:
            clean_enroll = raw_id.upper()
            if clean_enroll in enrollment_index:
                matched_stu = enrollment_index[clean_enroll]
                return MatchingResultItem(
                    raw_name=item.raw_name,
                    raw_identifier=item.raw_identifier,
                    raw_attendance_mark=raw_mark,
                    status=item.status,
                    ai_confidence=ai_conf,
                    match_confidence=self.CONF_ENROLLMENT_NUMBER,
                    matched_student_id=matched_stu.student_id,
                    matched_roll_number=matched_stu.roll_number,
                    matched_name=matched_stu.name,
                    match_method=MatchMethod.ENROLLMENT_NUMBER,
                    resolution=ResolutionState.MATCHED,
                )

        # -------------------------------------------------------------
        # 4. PRIORITY 4: Exact Name Matching
        # -------------------------------------------------------------
        if raw_name and raw_name in exact_name_index:
            candidates = exact_name_index[raw_name]
            if len(candidates) == 1:
                matched_stu = candidates[0]
                return MatchingResultItem(
                    raw_name=item.raw_name,
                    raw_identifier=item.raw_identifier,
                    raw_attendance_mark=raw_mark,
                    status=item.status,
                    ai_confidence=ai_conf,
                    match_confidence=self.CONF_EXACT_NAME,
                    matched_student_id=matched_stu.student_id,
                    matched_roll_number=matched_stu.roll_number,
                    matched_name=matched_stu.name,
                    match_method=MatchMethod.EXACT_NAME,
                    resolution=ResolutionState.MATCHED,
                )
            else:
                # Multiple students have the exact same name -> AMBIGUOUS -> NEEDS_REVIEW
                return MatchingResultItem(
                    raw_name=item.raw_name,
                    raw_identifier=item.raw_identifier,
                    raw_attendance_mark=raw_mark,
                    status=item.status,
                    ai_confidence=ai_conf,
                    match_confidence=0.50,
                    match_method=MatchMethod.EXACT_NAME,
                    resolution=ResolutionState.NEEDS_REVIEW,
                    review_reason="Multiple students have the exact same name.",
                    candidates=[
                        MatchCandidate(
                            student_id=s.student_id,
                            roll_number=s.roll_number,
                            name=s.name,
                        )
                        for s in candidates
                    ],
                )

        # -------------------------------------------------------------
        # 5. PRIORITY 5: Normalized Name Matching
        # -------------------------------------------------------------
        norm_ai_name = self.normalize_name(raw_name)
        if norm_ai_name and norm_ai_name in norm_name_index:
            candidates = norm_name_index[norm_ai_name]
            if len(candidates) == 1:
                matched_stu = candidates[0]
                return MatchingResultItem(
                    raw_name=item.raw_name,
                    raw_identifier=item.raw_identifier,
                    raw_attendance_mark=raw_mark,
                    status=item.status,
                    ai_confidence=ai_conf,
                    match_confidence=self.CONF_NORMALIZED_NAME,
                    matched_student_id=matched_stu.student_id,
                    matched_roll_number=matched_stu.roll_number,
                    matched_name=matched_stu.name,
                    match_method=MatchMethod.NORMALIZED_NAME,
                    resolution=ResolutionState.MATCHED,
                )
            else:
                # Multiple students share this normalized name -> NEEDS_REVIEW
                return MatchingResultItem(
                    raw_name=item.raw_name,
                    raw_identifier=item.raw_identifier,
                    raw_attendance_mark=raw_mark,
                    status=item.status,
                    ai_confidence=ai_conf,
                    match_confidence=0.50,
                    match_method=MatchMethod.NORMALIZED_NAME,
                    resolution=ResolutionState.NEEDS_REVIEW,
                    review_reason="Multiple students match this normalized name.",
                    candidates=[
                        MatchCandidate(
                            student_id=s.student_id,
                            roll_number=s.roll_number,
                            name=s.name,
                        )
                        for s in candidates
                    ],
                )

        # -------------------------------------------------------------
        # 6. PRIORITY 6: Fuzzy Name Matching
        # -------------------------------------------------------------
        if norm_ai_name:
            fuzzy_candidates: List[Tuple[float, StudentInfo]] = []
            for student in erp_students:
                norm_erp_name = self.normalize_name(student.name)
                if not norm_erp_name:
                    continue

                score = self.compute_fuzzy_score(norm_ai_name, norm_erp_name)

                if score >= self.FUZZY_MIN_CANDIDATE_THRESHOLD:
                    fuzzy_candidates.append((score, student))

            # Deterministic sort: highest similarity first, tiebreak by student_id
            fuzzy_candidates.sort(key=lambda x: (-x[0], x[1].student_id))

            if fuzzy_candidates:
                best_score, best_student = fuzzy_candidates[0]
                second_score = fuzzy_candidates[1][0] if len(fuzzy_candidates) > 1 else 0.0
                score_margin = best_score - second_score

                # Candidate representations for review UI
                candidate_objs = [
                    MatchCandidate(
                        student_id=s.student_id,
                        roll_number=s.roll_number,
                        name=s.name,
                        similarity=round(sc, 2),
                    )
                    for sc, s in fuzzy_candidates[:5]
                ]

                # Check if ambiguous (close second candidate) or confidence is moderate
                is_ambiguous = len(fuzzy_candidates) > 1 and score_margin < self.FUZZY_AMBIGUITY_MARGIN

                if not is_ambiguous and best_score >= self.FUZZY_HIGH_CONF_THRESHOLD:
                    # High-confidence, non-ambiguous fuzzy match (e.g. minor typo "Rahul Kumr" -> "Rahul Kumar")
                    return MatchingResultItem(
                        raw_name=item.raw_name,
                        raw_identifier=item.raw_identifier,
                        raw_attendance_mark=raw_mark,
                        status=item.status,
                        ai_confidence=ai_conf,
                        match_confidence=round(best_score * 0.90, 2),
                        matched_student_id=best_student.student_id,
                        matched_roll_number=best_student.roll_number,
                        matched_name=best_student.name,
                        match_method=MatchMethod.FUZZY_NAME,
                        resolution=ResolutionState.MATCHED,
                        candidates=candidate_objs,
                    )
                else:
                    # Ambiguous fuzzy match or similarity below high-confidence threshold -> NEEDS_REVIEW
                    reason = (
                        "Ambiguous fuzzy match between multiple students."
                        if is_ambiguous
                        else f"Fuzzy match similarity ({round(best_score, 2)}) requires teacher review."
                    )
                    return MatchingResultItem(
                        raw_name=item.raw_name,
                        raw_identifier=item.raw_identifier,
                        raw_attendance_mark=raw_mark,
                        status=item.status,
                        ai_confidence=ai_conf,
                        match_confidence=round(best_score * 0.70, 2),
                        matched_student_id=best_student.student_id,
                        matched_roll_number=best_student.roll_number,
                        matched_name=best_student.name,
                        match_method=MatchMethod.FUZZY_NAME,
                        resolution=ResolutionState.NEEDS_REVIEW,
                        review_reason=reason,
                        candidates=candidate_objs,
                    )

        # -------------------------------------------------------------
        # 7. UNMATCHED (No reasonable match found)
        # -------------------------------------------------------------
        return MatchingResultItem(
            raw_name=item.raw_name,
            raw_identifier=item.raw_identifier,
            raw_attendance_mark=raw_mark,
            status=item.status,
            ai_confidence=ai_conf,
            match_confidence=0.0,
            matched_student_id=None,
            matched_roll_number=None,
            matched_name=None,
            match_method=MatchMethod.NONE,
            resolution=ResolutionState.UNMATCHED,
            review_reason="No matching student found in ERP roster.",
        )


matching_service = StudentMatchingService()
