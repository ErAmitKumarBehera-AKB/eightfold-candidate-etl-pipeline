from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import re

from .models import CanonicalProfile, ProvenanceRecord, Skill, Links


class Merger:
    SOURCE_CONFIDENCE = {
        'GitHub':       0.90,
        'LinkedIn':     0.90,
        'Resume':       0.85,
        'ATS':          0.70,
        'RecruiterCSV': 0.60,
    }
    DEFAULT_CONFIDENCE = 0.50

    def merge(self, profiles: List[Tuple[str, CanonicalProfile]]) -> List[CanonicalProfile]:
        email_to_id: Dict[str, str] = {}
        name_employer_to_id: Dict[str, str] = {}
        merged: Dict[str, CanonicalProfile] = {}

        for source_name, profile in profiles:
            canonical_id = self._resolve_identity(profile, email_to_id, name_employer_to_id)

            if canonical_id not in merged:
                merged[canonical_id] = CanonicalProfile(candidate_id=canonical_id)

            self._merge_into(merged[canonical_id], profile, source_name)

            for email in profile.emails:
                email_to_id[email.lower()] = canonical_id
            key = self._name_employer_key(profile)
            if key:
                name_employer_to_id[key] = canonical_id

        for profile in merged.values():
            profile.overall_confidence = self._compute_overall_confidence(profile)
            if profile.years_experience is None:
                profile.years_experience = self._compute_years_experience(profile)

        return list(merged.values())

    def _resolve_identity(
        self,
        profile: CanonicalProfile,
        email_to_id: Dict[str, str],
        name_employer_to_id: Dict[str, str],
    ) -> str:
        for email in profile.emails:
            if email.lower() in email_to_id:
                return email_to_id[email.lower()]

        key = self._name_employer_key(profile)
        if key and key in name_employer_to_id:
            return name_employer_to_id[key]

        if profile.emails:
            return profile.emails[0].lower()
        return profile.candidate_id

    def _name_employer_key(self, profile: CanonicalProfile) -> Optional[str]:
        if not profile.full_name:
            return None
        parts = self._normalize_name(profile.full_name).split()
        first_name = parts[0] if parts else None
        employer = None
        if profile.experience:
            employer = self._normalize_name(profile.experience[0].company or '')
        if first_name and employer:
            return f"{first_name}|{employer}"
        return None

    def _normalize_name(self, name: str) -> str:
        return re.sub(r'[^a-z0-9\s]', '', name.lower()).strip()

    def _merge_into(self, target: CanonicalProfile, source: CanonicalProfile, source_name: str):
        confidence = self.SOURCE_CONFIDENCE.get(source_name, self.DEFAULT_CONFIDENCE)

        if source.full_name:
            curr = target.provenance.get('full_name')
            if not curr or confidence > curr.confidence:
                target.full_name = source.full_name
                target.provenance['full_name'] = ProvenanceRecord(
                    source=source_name, method="highest_confidence", confidence=confidence
                )

        for email in source.emails:
            if email.lower() not in target.emails:
                target.emails.append(email.lower())

        from .normalizers import normalize_phone
        for phone in source.phones:
            norm = normalize_phone(phone)
            key = norm if norm else phone
            if key and key not in target.phones:
                target.phones.append(key)

        if source.location:
            from .normalizers import normalize_country
            curr = target.provenance.get('location')
            if not curr or confidence > curr.confidence:
                loc = source.location.model_copy(deep=True)
                if loc.country:
                    loc.country = normalize_country(loc.country)
                target.location = loc
                target.provenance['location'] = ProvenanceRecord(
                    source=source_name,
                    method="exact_match" if not curr else "override",
                    confidence=confidence
                )

        self._merge_links(target, source)

        if source.headline:
            curr = target.provenance.get('headline')
            if not curr or confidence > curr.confidence:
                target.headline = source.headline
                target.provenance['headline'] = ProvenanceRecord(
                    source=source_name, method="highest_confidence", confidence=confidence
                )

        self._merge_experience(target, source)
        self._merge_education(target, source)
        self._merge_skills(target, source, source_name)

    def _merge_links(self, target: CanonicalProfile, source: CanonicalProfile):
        if not source.links:
            return
        if not target.links:
            target.links = Links()
        if source.links.linkedin and not target.links.linkedin:
            target.links.linkedin = source.links.linkedin
        if source.links.github and not target.links.github:
            target.links.github = source.links.github
        if source.links.portfolio and not target.links.portfolio:
            target.links.portfolio = source.links.portfolio
        for url in (source.links.other or []):
            if url not in target.links.other:
                target.links.other.append(url)

    def _merge_experience(self, target: CanonicalProfile, source: CanonicalProfile):
        from .normalizers import normalize_date
        existing = {
            (self._normalize_name(e.company or ''), self._normalize_name(e.title or ''))
            for e in target.experience
        }
        for exp in source.experience:
            key = (self._normalize_name(exp.company or ''), self._normalize_name(exp.title or ''))
            if key not in existing:
                copy = exp.model_copy(deep=True)
                if copy.start:
                    copy.start = normalize_date(copy.start)
                if copy.end:
                    copy.end = normalize_date(copy.end)
                target.experience.append(copy)
                existing.add(key)

    def _merge_education(self, target: CanonicalProfile, source: CanonicalProfile):
        existing = {
            (self._normalize_name(e.institution or ''), self._normalize_name(e.degree or ''))
            for e in target.education
        }
        for edu in source.education:
            key = (self._normalize_name(edu.institution or ''), self._normalize_name(edu.degree or ''))
            if key not in existing:
                target.education.append(edu.model_copy(deep=True))
                existing.add(key)

    def _merge_skills(self, target: CanonicalProfile, source: CanonicalProfile, source_name: str):
        from .normalizers import normalize_skill
        existing: Dict[str, Skill] = {s.name: s for s in target.skills}

        for skill in source.skills:
            norm = normalize_skill(skill.name)
            if not norm:
                continue
            if norm in existing:
                if source_name not in existing[norm].sources:
                    existing[norm].sources.append(source_name)
                if skill.confidence > existing[norm].confidence:
                    existing[norm].confidence = skill.confidence
            else:
                new_skill = skill.model_copy(deep=True)
                new_skill.name = norm
                if source_name not in new_skill.sources:
                    new_skill.sources.append(source_name)
                target.skills.append(new_skill)
                existing[norm] = new_skill

    def _compute_overall_confidence(self, profile: CanonicalProfile) -> Optional[float]:
        if not profile.provenance:
            return None
        scores = [p.confidence for p in profile.provenance.values()]
        return round(sum(scores) / len(scores), 4)

    def _compute_years_experience(self, profile: CanonicalProfile) -> Optional[float]:
        if not profile.experience:
            return None
        today = date.today()
        total_days = 0
        for exp in profile.experience:
            start = self._parse_date(exp.start)
            end = self._parse_date(exp.end) if exp.end else today
            if start and end and end >= start:
                total_days += (end - start).days
        return round(total_days / 365.25, 1) if total_days > 0 else None

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            if re.match(r'^\d{4}-\d{2}$', date_str.strip()):
                return datetime.strptime(date_str.strip(), '%Y-%m').date()
            elif re.match(r'^\d{4}$', date_str.strip()):
                return datetime.strptime(date_str.strip(), '%Y').date()
        except ValueError:
            pass
        return None
