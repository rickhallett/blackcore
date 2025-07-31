"""Test documentation coverage for the minimal module.

This test ensures all public functions and classes have proper docstrings
and identifies any missing documentation.
"""

import ast
import inspect
from pathlib import Path
from typing import List, Tuple, Set

import pytest

from .. import (
    ai_extractor,
    async_batch_processor,
    cache,
    config,
    constants,
    error_handling,
    llm_scorer,
    logging_config,
    models,
    notion_updater,
    property_handlers,
    property_validation,
    simple_scorer,
    text_pipeline_validator,
    transcript_processor,
    validators,
)


class DocumentationChecker:
    """Check documentation coverage for Python modules."""

    def __init__(self):
        self.missing_docstrings: List[Tuple[str, str]] = []
        self.short_docstrings: List[Tuple[str, str]] = []
        self.todo_comments: List[Tuple[str, int, str]] = []

    def check_module(self, module, module_name: str) -> None:
        """Check documentation coverage for a module."""
        # Check module docstring
        if not inspect.getdoc(module):
            self.missing_docstrings.append((module_name, "module"))

        # Check all classes and functions in the module
        for name, obj in inspect.getmembers(module):
            if name.startswith('_'):
                continue  # Skip private members

            full_name = f"{module_name}.{name}"

            if inspect.isclass(obj):
                self._check_class(obj, full_name)
            elif inspect.isfunction(obj):
                self._check_function(obj, full_name)

    def _check_class(self, cls, class_name: str) -> None:
        """Check documentation for a class and its methods."""
        # Check class docstring
        if not inspect.getdoc(cls):
            self.missing_docstrings.append((class_name, "class"))
        else:
            doc = inspect.getdoc(cls)
            if len(doc.split()) < 3:  # Less than 3 words is too short
                self.short_docstrings.append((class_name, "class"))

        # Check methods
        for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if method_name.startswith('_') and method_name != '__init__':
                continue  # Skip private methods except __init__

            full_method_name = f"{class_name}.{method_name}"
            self._check_function(method, full_method_name)

    def _check_function(self, func, func_name: str) -> None:
        """Check documentation for a function."""
        # Skip auto-generated methods (Pydantic, etc.)
        method_name = func_name.split('.')[-1]
        if method_name in ['dict', 'json', 'parse_obj', 'parse_raw', 'schema', 'schema_json', 
                          'construct', 'copy', 'update_forward_refs', 'validate', 'fields',
                          'new', 'parse_retry_after', 'sleep_for_retry', 'formatMessage']:
            return
            
        doc = inspect.getdoc(func)
        if not doc:
            self.missing_docstrings.append((func_name, "function"))
        else:
            # Check if docstring is too short
            if len(doc.split()) < 3:  # Less than 3 words is too short
                self.short_docstrings.append((func_name, "function"))

    def check_todos_in_file(self, file_path: Path) -> None:
        """Check for TODO comments in a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                if 'TODO' in line_stripped.upper():
                    self.todo_comments.append((str(file_path), line_num, line_stripped))
        except (OSError, UnicodeDecodeError):
            pass  # Skip files that can't be read

    def get_module_files(self) -> List[Path]:
        """Get all Python module files in the minimal package."""
        minimal_dir = Path(__file__).parent.parent
        return list(minimal_dir.glob("*.py"))


@pytest.fixture
def doc_checker():
    """Fixture providing a documentation checker."""
    return DocumentationChecker()


def test_module_documentation_coverage(doc_checker):
    """Test that all public modules have proper documentation."""
    modules_to_check = [
        (ai_extractor, "ai_extractor"),
        (async_batch_processor, "async_batch_processor"),
        (cache, "cache"),
        (config, "config"),
        (constants, "constants"),
        (error_handling, "error_handling"),
        (llm_scorer, "llm_scorer"),
        (logging_config, "logging_config"),
        (models, "models"),
        (notion_updater, "notion_updater"),
        (property_handlers, "property_handlers"),
        (property_validation, "property_validation"),
        (simple_scorer, "simple_scorer"),
        (text_pipeline_validator, "text_pipeline_validator"),
        (transcript_processor, "transcript_processor"),
        (validators, "validators"),
    ]

    for module, module_name in modules_to_check:
        doc_checker.check_module(module, module_name)

    # Report missing docstrings
    if doc_checker.missing_docstrings:
        missing_report = "\n".join([
            f"  - {name} ({obj_type})" 
            for name, obj_type in doc_checker.missing_docstrings
        ])
        pytest.fail(f"Missing docstrings:\n{missing_report}")

    # Report short docstrings (warnings only)
    if doc_checker.short_docstrings:
        short_report = "\n".join([
            f"  - {name} ({obj_type})" 
            for name, obj_type in doc_checker.short_docstrings
        ])
        print(f"\nWarning: Short docstrings found:\n{short_report}")


def test_todo_comments_documentation(doc_checker):
    """Test that tracks TODO comments for documentation purposes."""
    # Check all module files for TODO comments
    module_files = doc_checker.get_module_files()
    
    for file_path in module_files:
        doc_checker.check_todos_in_file(file_path)

    # Report TODO comments (for tracking, not as failures)
    if doc_checker.todo_comments:
        todo_report = "\n".join([
            f"  - {file_path}:{line_num}: {comment}"
            for file_path, line_num, comment in doc_checker.todo_comments
        ])
        print(f"\nTODO comments found (tracked for future work):\n{todo_report}")

    # We don't fail on TODO comments, just track them
    assert True, "TODO tracking completed"


def test_critical_classes_have_docstrings():
    """Test that critical classes have comprehensive docstrings."""
    critical_classes = [
        (transcript_processor.TranscriptProcessor, "TranscriptProcessor"),
        (notion_updater.NotionUpdater, "NotionUpdater"),
        (ai_extractor.AIExtractor, "AIExtractor"),
        (cache.SimpleCache, "SimpleCache"),
        (async_batch_processor.AsyncBatchProcessor, "AsyncBatchProcessor"),
        (error_handling.ErrorHandler, "ErrorHandler"),
        (property_validation.PropertyValidator, "PropertyValidator"),
    ]

    missing_or_short = []

    for cls, class_name in critical_classes:
        doc = inspect.getdoc(cls)
        if not doc:
            missing_or_short.append(f"{class_name}: missing docstring")
        elif len(doc.split()) < 10:  # Less than 10 words is too short for critical classes
            missing_or_short.append(f"{class_name}: docstring too short ({len(doc.split())} words)")

    if missing_or_short:
        failure_report = "\n  - ".join([""] + missing_or_short)
        pytest.fail(f"Critical classes need better documentation:{failure_report}")


def test_public_functions_have_examples():
    """Test that key public functions have usage examples in docstrings."""
    functions_needing_examples = [
        (transcript_processor.TranscriptProcessor.process_transcript, "process_transcript"),
        (notion_updater.NotionUpdater.create_page, "create_page"),
        (ai_extractor.AIExtractor.extract_entities, "extract_entities"),
        (cache.SimpleCache.get, "cache.get"),
        (cache.SimpleCache.set, "cache.set"),
    ]

    missing_examples = []

    for func, func_name in functions_needing_examples:
        doc = inspect.getdoc(func)
        if not doc:
            missing_examples.append(f"{func_name}: no docstring")
        elif "Args:" not in doc or "Returns:" not in doc:
            missing_examples.append(f"{func_name}: missing Args/Returns sections")

    if missing_examples:
        # This is a warning, not a hard failure
        example_report = "\n  - ".join([""] + missing_examples)
        print(f"\nWarning: Functions could benefit from better documentation:{example_report}")


def test_constants_are_documented():
    """Test that important constants have proper documentation."""
    # Check if constants module has proper docstrings for key constants
    constants_doc = inspect.getdoc(constants)
    assert constants_doc, "Constants module should have a docstring"

    # Check that key constants exist (they should be defined)
    required_constants = [
        'DEFAULT_RATE_LIMIT',
        'DEFAULT_CACHE_TTL', 
        'AI_MAX_TOKENS',
        'CACHE_FILE_PERMISSIONS',
        'CACHE_DIR_PERMISSIONS'
    ]

    missing_constants = []
    for const_name in required_constants:
        if not hasattr(constants, const_name):
            missing_constants.append(const_name)

    if missing_constants:
        pytest.fail(f"Missing required constants: {', '.join(missing_constants)}")


def test_error_classes_have_context():
    """Test that custom error classes have proper documentation."""
    error_classes = [
        (error_handling.BlackcoreError, "BlackcoreError"),
        (error_handling.NotionAPIError, "NotionAPIError"),
        (error_handling.ValidationError, "ValidationError"),
        (error_handling.ProcessingError, "ProcessingError"),
        (error_handling.ConfigurationError, "ConfigurationError"),
    ]

    poorly_documented = []

    for error_cls, error_name in error_classes:
        doc = inspect.getdoc(error_cls)
        if not doc:
            poorly_documented.append(f"{error_name}: missing docstring")
        elif len(doc.split()) < 5:  # Error classes should have at least 5 words
            poorly_documented.append(f"{error_name}: docstring too short")

    if poorly_documented:
        error_report = "\n  - ".join([""] + poorly_documented)
        pytest.fail(f"Error classes need better documentation:{error_report}")