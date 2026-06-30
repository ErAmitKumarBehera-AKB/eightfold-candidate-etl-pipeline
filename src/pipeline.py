import os
import json
from typing import List, Dict, Any, Optional

from .extractors import RecruiterCSVExtractor, ATSJSONExtractor, GitHubJSONExtractor, GitHubAPIExtractor
from .merger import Merger
from .projector import Projector


class Pipeline:
    def __init__(self, data_dir: str, config_path: str, github_usernames: Optional[List[str]] = None):
        self.data_dir = data_dir
        self.github_usernames = github_usernames or []

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.merger = Merger()
        self.projector = Projector(self.config)

    def run(self) -> List[Dict[str, Any]]:
        extracted_profiles = []

        try:
            files = os.listdir(self.data_dir)
        except FileNotFoundError:
            print(f"Warning: Data directory not found: {self.data_dir}")
            files = []

        for filename in files:
            if filename.startswith('_') or filename in ('config.json', 'temp_config.json'):
                continue

            file_path = os.path.join(self.data_dir, filename)

            if filename.endswith('.csv'):
                profiles = RecruiterCSVExtractor().extract(file_path)
                for p in profiles:
                    extracted_profiles.append(('RecruiterCSV', p))

            elif filename == 'ats.json':
                profiles = ATSJSONExtractor().extract(file_path)
                for p in profiles:
                    extracted_profiles.append(('ATS', p))

            elif filename == 'github.json':
                profiles = GitHubJSONExtractor().extract(file_path)
                for p in profiles:
                    extracted_profiles.append(('GitHub', p))

        for username in self.github_usernames:
            profiles = GitHubAPIExtractor().extract(username)
            for p in profiles:
                extracted_profiles.append(('GitHub', p))

        canonical_profiles = self.merger.merge(extracted_profiles)
        return self.projector.project(canonical_profiles)
