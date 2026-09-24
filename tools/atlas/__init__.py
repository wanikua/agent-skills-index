"""Skill Atlas - CLI tools for managing the agent skills index."""

from .hashing import compute_content_hash, compute_folder_sha256, compute_skill_md_sha256

__version__ = "0.1.0"

__all__ = [
    "compute_content_hash",
    "compute_folder_sha256",
    "compute_skill_md_sha256",
]
