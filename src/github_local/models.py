from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class IssueComment:
    number: int
    created_at: str
    body: str
    path: Path


@dataclass(frozen=True, slots=True)
class Issue:
    number: int
    issue_id: str
    state: str
    title: str
    body: str
    created_at: str
    updated_at: str
    path: Path
    url: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.issue_id,
            "number": self.number,
            "state": self.state,
            "title": self.title,
            "body": self.body,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "path": self.path.as_posix(),
            "url": self.url,
        }


@dataclass(frozen=True, slots=True)
class IssueChange:
    issue: int
    branch: str
    head: str
    current: bool
    relation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "issue": self.issue,
            "branch": self.branch,
            "head": self.head,
            "current": self.current,
            "relation": self.relation,
        }
