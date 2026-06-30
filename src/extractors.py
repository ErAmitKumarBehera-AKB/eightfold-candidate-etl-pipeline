import csv
import json
import urllib.request
import urllib.error
from typing import Any, List, Optional
from .models import CanonicalProfile, Location, Links, Skill, Experience, Education


class Extractor:
    def extract(self, source: Any) -> List[CanonicalProfile]:
        raise NotImplementedError


class RecruiterCSVExtractor(Extractor):
    def extract(self, file_path: str) -> List[CanonicalProfile]:
        profiles = []
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                for i, row in enumerate(csv.DictReader(f)):
                    profile = CanonicalProfile(candidate_id=f"csv_{i}")
                    if row.get('name'):
                        profile.full_name = row['name'].strip()
                    if row.get('email'):
                        profile.emails.append(row['email'].strip().lower())
                    if row.get('phone'):
                        profile.phones.append(row['phone'].strip())
                    if row.get('current_company') or row.get('title'):
                        profile.experience.append(Experience(
                            company=row.get('current_company', '').strip() or None,
                            title=row.get('title', '').strip() or None
                        ))
                    if row.get('skills'):
                        for s in row['skills'].split(','):
                            s = s.strip()
                            if s:
                                profile.skills.append(Skill(name=s, confidence=0.6, sources=['RecruiterCSV']))
                    if row.get('linkedin'):
                        profile.links = Links(linkedin=row['linkedin'].strip())
                    if row.get('location'):
                        profile.location = Location(city=row['location'].strip())
                    profiles.append(profile)
        except FileNotFoundError:
            print(f"Warning: CSV file not found: {file_path}")
        except Exception as e:
            print(f"Warning: Error reading CSV '{file_path}': {e}")
        return profiles


class ATSJSONExtractor(Extractor):
    def extract(self, file_path: str) -> List[CanonicalProfile]:
        profiles = []
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                print(f"Warning: Expected a JSON array in ATS file. Skipping.")
                return []

            for item in data:
                if not isinstance(item, dict):
                    print(f"Warning: Skipping malformed ATS record.")
                    continue

                profile = CanonicalProfile(candidate_id=item.get('id', 'unknown'))
                profile.full_name = item.get('fullName')

                contact = item.get('contact', {})
                if isinstance(contact, dict):
                    if contact.get('primaryEmail'):
                        profile.emails.append(contact['primaryEmail'].lower())
                    if contact.get('secondaryEmail'):
                        profile.emails.append(contact['secondaryEmail'].lower())
                    if contact.get('mobilePhone'):
                        profile.phones.append(contact['mobilePhone'])

                loc = item.get('location', {})
                if isinstance(loc, dict) and loc:
                    profile.location = Location(
                        city=loc.get('city'),
                        region=loc.get('region') or loc.get('state'),
                        country=loc.get('country')
                    )

                links_data = item.get('links', {})
                if isinstance(links_data, dict):
                    profile.links = Links(
                        linkedin=links_data.get('linkedin'),
                        github=links_data.get('github'),
                        portfolio=links_data.get('portfolio')
                    )

                if item.get('headline'):
                    profile.headline = item['headline']

                experience_data = item.get('experience')
                if isinstance(experience_data, list):
                    for exp_item in experience_data:
                        if not isinstance(exp_item, dict):
                            continue
                        profile.experience.append(Experience(
                            company=exp_item.get('employer') or exp_item.get('company'),
                            title=exp_item.get('jobTitle') or exp_item.get('title'),
                            start=exp_item.get('startDate') or exp_item.get('start'),
                            end=exp_item.get('endDate') or exp_item.get('end'),
                            summary=exp_item.get('summary')
                        ))

                education_data = item.get('education')
                if isinstance(education_data, list):
                    for edu_item in education_data:
                        if not isinstance(edu_item, dict):
                            continue
                        profile.education.append(Education(
                            institution=edu_item.get('institution') or edu_item.get('school'),
                            degree=edu_item.get('degree'),
                            field=edu_item.get('field') or edu_item.get('major'),
                            end_year=str(edu_item.get('endYear') or edu_item.get('graduationYear') or '') or None
                        ))

                tags_data = item.get('tags')
                if isinstance(tags_data, list):
                    for tag in tags_data:
                        if isinstance(tag, str) and tag.strip():
                            profile.skills.append(Skill(name=tag.strip(), confidence=0.7, sources=['ATS']))

                skills_data = item.get('skills')
                if isinstance(skills_data, list):
                    for s in skills_data:
                        if isinstance(s, str) and s.strip():
                            profile.skills.append(Skill(name=s.strip(), confidence=0.7, sources=['ATS']))
                        elif isinstance(s, dict) and s.get('name'):
                            profile.skills.append(Skill(name=s['name'], confidence=float(s.get('confidence', 0.7)), sources=['ATS']))

                profiles.append(profile)
        except FileNotFoundError:
            print(f"Warning: ATS file not found: {file_path}")
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in ATS file '{file_path}': {e}")
        except Exception as e:
            print(f"Warning: Error reading ATS JSON '{file_path}': {e}")
        return profiles


class GitHubJSONExtractor(Extractor):
    def extract(self, file_path: str) -> List[CanonicalProfile]:
        profiles = []
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                data = [data]
            for item in data:
                if isinstance(item, dict):
                    profiles.append(self._parse(item))
        except FileNotFoundError:
            print(f"Warning: GitHub JSON file not found: {file_path}")
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in GitHub file '{file_path}': {e}")
        except Exception as e:
            print(f"Warning: Error reading GitHub JSON '{file_path}': {e}")
        return profiles

    def _parse(self, item: dict) -> CanonicalProfile:
        profile = CanonicalProfile(candidate_id=item.get('login', 'unknown'))
        profile.full_name = item.get('name')
        if item.get('email'):
            profile.emails.append(item['email'].lower())
        if item.get('location'):
            profile.location = Location(city=item['location'])
        profile.headline = item.get('bio')
        profile.links = Links(github=item.get('html_url'))

        lang_counts: dict = {}
        for repo in item.get('repos', []):
            lang = repo.get('language')
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        for lang, count in lang_counts.items():
            confidence = min(0.6 + count * 0.05, 0.95)
            profile.skills.append(Skill(name=lang, confidence=confidence, sources=['GitHub']))
        return profile


class GitHubAPIExtractor(Extractor):
    BASE_URL = "https://api.github.com"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def extract(self, username: str) -> List[CanonicalProfile]:
        try:
            user = self._get(f"{self.BASE_URL}/users/{username}")
            if not user:
                return []
            repos = self._get(f"{self.BASE_URL}/users/{username}/repos?per_page=100&sort=pushed") or []
            profile = GitHubJSONExtractor()._parse({**user, "repos": repos})
            return [profile]
        except Exception as e:
            print(f"Warning: Failed to fetch GitHub profile for '{username}': {e}")
            return []

    def _get(self, url: str) -> Optional[Any]:
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "candidate-data-transformer/1.0"
            })
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"Warning: GitHub user not found: {url}")
            elif e.code == 403:
                print(f"Warning: GitHub API rate limit exceeded.")
            else:
                print(f"Warning: GitHub API HTTP error {e.code}")
            return None
        except urllib.error.URLError as e:
            print(f"Warning: Network error: {e.reason}")
            return None
