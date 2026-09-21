"""
Automatic knowledge base loader.

On startup, this module scans the `data/knowledge/` directory for PDF and
text-based files and indexes any that are not already present in the
JSON-backed knowledge store (documents.json / chunks.json). This ensures
the bot has a populated knowledge base immediately after deployment,
without requiring a manual upload through the admin API.

The process is idempotent: files that are already indexed (matched by
filename) are skipped on subsequent runs/deployments.
"""

import os
import logging

from backend.database import get_all_documents
from backend.knowledge import (
    process_pdf_file,
    process_text_content,
    KNOWLEDGE_DATA_DIR
)

logger = logging.getLogger("firebird.init_knowledge")

# Extensions treated as plain-text content
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".log"}
PDF_EXTENSIONS = {".pdf"}


def _get_indexed_filenames():
    """Returns the set of filenames already present in documents.json."""
    try:
        docs = get_all_documents()
    except Exception as e:
        logger.warning(f"[Knowledge Init] Could not read existing documents: {e}")
        return set()

    indexed = set()
    for doc in docs:
        name = doc.get("name") or doc.get("filename")
        if name:
            indexed.add(name)
    return indexed


def auto_load_knowledge_from_directory(knowledge_dir: str = None) -> dict:
    """
    Scans `knowledge_dir` (defaults to backend.knowledge.KNOWLEDGE_DATA_DIR) for
    PDF and text files, and indexes any file that is not already represented in
    documents.json. Safe to call on every startup/deployment.

    Returns a summary dict with counts of files loaded/skipped/failed.
    """
    directory = knowledge_dir or KNOWLEDGE_DATA_DIR

    summary = {
        "directory": directory,
        "loaded": [],
        "skipped": [],
        "failed": []
    }

    if not os.path.isdir(directory):
        logger.info(f"[Knowledge Init] Knowledge directory '{directory}' does not exist. Skipping auto-load.")
        return summary

    try:
        filenames = sorted(os.listdir(directory))
    except Exception as e:
        logger.warning(f"[Knowledge Init] Could not list knowledge directory '{directory}': {e}")
        return summary

    if not filenames:
        logger.info(f"[Knowledge Init] Knowledge directory '{directory}' is empty. Nothing to index.")
        return summary

    already_indexed = _get_indexed_filenames()

    for filename in filenames:
        file_path = os.path.join(directory, filename)
        if not os.path.isfile(file_path):
            continue

        if filename in already_indexed:
            summary["skipped"].append(filename)
            continue

        ext = os.path.splitext(filename)[1].lower()

        try:
            if ext in PDF_EXTENSIONS:
                result = process_pdf_file(file_path, filename)
            elif ext in TEXT_EXTENSIONS or ext == "":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if not content.strip():
                    logger.info(f"[Knowledge Init] Skipping empty text file '{filename}'.")
                    continue
                file_type = ext.replace(".", "") if ext else "text"
                result = process_text_content(content, filename, file_type=file_type)
            else:
                # Unknown extension: attempt to read as text; skip on binary/decoding failure
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    logger.info(f"[Knowledge Init] Skipping unsupported file type: '{filename}'.")
                    continue
                result = process_text_content(content, filename, file_type="text")

            chunk_count = result.get("chunk_count", 0)
            summary["loaded"].append({"filename": filename, "chunk_count": chunk_count})
            logger.info(f"[Knowledge Init] Indexed '{filename}': {chunk_count} chunks created.")

        except Exception as e:
            summary["failed"].append({"filename": filename, "error": str(e)})
            logger.warning(f"[Knowledge Init] Failed to index '{filename}': {e}")

    total_loaded = len(summary["loaded"])
    total_skipped = len(summary["skipped"])
    total_failed = len(summary["failed"])

    if total_loaded:
        logger.info(
            f"[Knowledge Init] Auto-load complete: {total_loaded} file(s) newly indexed, "
            f"{total_skipped} already indexed (skipped), {total_failed} failed."
        )
    else:
        logger.info(
            f"[Knowledge Init] Auto-load complete: no new files to index "
            f"({total_skipped} already indexed, {total_failed} failed)."
        )

    return summary
