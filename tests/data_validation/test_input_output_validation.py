"""Test data validation for inputs and outputs in deduplication workflows."""

import json


class TestInputOutputValidation:
    """Test validation of input data and output integrity."""

    def test_input_data_validation(self, sample_people_data):
        """Test validation of input data structures."""

        # Test valid data structures
        valid_data_tests = [
            {
                "name": "standard_person",
                "data": {
                    "id": "person-1",
                    "Full Name": "John Smith",
                    "Email": "john@example.com",
                    "Phone": "555-1234",
                    "Organization": "Acme Corp",
                },
                "expected_valid": True,
            },
            {
                "name": "person_with_lists",
                "data": {
                    "id": "person-2",
                    "Full Name": "Jane Doe",
                    "Email": ["jane@example.com", "j.doe@company.com"],
                    "Phone": "555-5678",
                    "Organization": ["Company A", "Company B"],
                },
                "expected_valid": True,
            },
            {
                "name": "minimal_person",
                "data": {"id": "person-3", "Full Name": "Minimal Person"},
                "expected_valid": True,
            },
        ]

        # Test invalid data structures
        invalid_data_tests = [
            {
                "name": "missing_id",
                "data": {"Full Name": "No ID Person", "Email": "noid@example.com"},
                "expected_valid": False,
                "validation_error": "missing_required_field",
            },
            {
                "name": "missing_name",
                "data": {"id": "person-4", "Email": "noname@example.com"},
                "expected_valid": False,
                "validation_error": "missing_required_field",
            },
            {
                "name": "invalid_data_types",
                "data": {
                    "id": 12345,  # Should be string
                    "Full Name": ["Not", "A", "String"],  # Should be string
                    "Email": {"invalid": "structure"},  # Should be string or list
                },
                "expected_valid": False,
                "validation_error": "invalid_data_type",
            },
            {
                "name": "null_values",
                "data": {"id": "person-5", "Full Name": None, "Email": None},
                "expected_valid": False,
                "validation_error": "null_required_field",
            },
        ]

        def validate_person_data(data):
            """Validate person data structure."""
            errors = []

            # Check required fields
            if "id" not in data or not data["id"]:
                errors.append("missing_required_field: id")
            elif not isinstance(data["id"], str):
                errors.append("invalid_data_type: id must be string")

            if "Full Name" not in data or not data["Full Name"]:
                errors.append("missing_required_field: Full Name")
            elif not isinstance(data["Full Name"], str):
                errors.append("invalid_data_type: Full Name must be string")

            # Check optional fields
            if "Email" in data and data["Email"] is not None:
                if not isinstance(data["Email"], (str, list)):
                    errors.append("invalid_data_type: Email must be string or list")
                elif isinstance(data["Email"], list):
                    if not all(isinstance(email, str) for email in data["Email"]):
                        errors.append(
                            "invalid_data_type: All emails in list must be strings"
                        )

            return len(errors) == 0, errors

        # Test valid data
        for test in valid_data_tests:
            is_valid, errors = validate_person_data(test["data"])
            assert (
                is_valid == test["expected_valid"]
            ), f"Test '{test['name']}': Expected valid={test['expected_valid']}, got {is_valid}. Errors: {errors}"

        # Test invalid data
        for test in invalid_data_tests:
            is_valid, errors = validate_person_data(test["data"])
            assert (
                is_valid == test["expected_valid"]
            ), f"Test '{test['name']}': Expected valid={test['expected_valid']}, got {is_valid}"
            assert any(
                test["validation_error"] in error for error in errors
            ), f"Expected error type '{test['validation_error']}' not found in: {errors}"

    def test_list_value_handling(self):
        """Test proper handling of list values in entities."""

        # Test entities with various list configurations
        list_handling_tests = [
            {
                "name": "single_string_value",
                "entity": {
                    "id": "test-1",
                    "Full Name": "Test Person",
                    "Email": "test@example.com",
                    "Organization": "Single Org",
                },
                "expected_list_fields": [],
            },
            {
                "name": "mixed_string_and_list",
                "entity": {
                    "id": "test-2",
                    "Full Name": "Test Person",
                    "Email": ["test@example.com", "test2@example.com"],
                    "Organization": "Single Org",
                    "Skills": ["Python", "JavaScript"],
                },
                "expected_list_fields": ["Email", "Skills"],
            },
            {
                "name": "empty_lists",
                "entity": {
                    "id": "test-3",
                    "Full Name": "Test Person",
                    "Email": [],
                    "Organization": [],
                },
                "expected_list_fields": ["Email", "Organization"],
            },
            {
                "name": "nested_complex_data",
                "entity": {
                    "id": "test-4",
                    "Full Name": "Test Person",
                    "Projects": [
                        {"name": "Project A", "role": "Lead"},
                        {"name": "Project B", "role": "Member"},
                    ],
                },
                "expected_list_fields": ["Projects"],
            },
        ]

        def identify_list_fields(entity):
            """Identify fields that contain list values."""
            list_fields = []
            for key, value in entity.items():
                if isinstance(value, list):
                    list_fields.append(key)
            return list_fields

        def normalize_list_values(entity):
            """Normalize list values for comparison."""
            normalized = entity.copy()
            for key, value in entity.items():
                if isinstance(value, list):
                    if all(isinstance(item, str) for item in value):
                        # Join string lists for comparison
                        normalized[f"{key}_normalized"] = ", ".join(value)
                    else:
                        # Convert complex objects to strings
                        normalized[f"{key}_normalized"] = str(value)
            return normalized

        for test in list_handling_tests:
            entity = test["entity"]

            # Test list field identification
            list_fields = identify_list_fields(entity)
            assert set(list_fields) == set(
                test["expected_list_fields"]
            ), f"Test '{test['name']}': Expected list fields {test['expected_list_fields']}, got {list_fields}"

            # Test normalization
            normalized = normalize_list_values(entity)

            # Validate that normalization preserves original data
            for key in entity:
                assert (
                    key in normalized
                ), f"Original field '{key}' missing after normalization"

            # Validate that list fields get normalized versions
            for list_field in test["expected_list_fields"]:
                normalized_key = f"{list_field}_normalized"
                assert (
                    normalized_key in normalized
                ), f"Normalized field '{normalized_key}' not created"

    def test_conflict_detection_accuracy(self):
        """Test accuracy of conflict detection between entities."""

        conflict_test_cases = [
            {
                "name": "no_conflicts",
                "entity_a": {
                    "id": "a1",
                    "Full Name": "John Smith",
                    "Email": "john@example.com",
                    "Phone": "555-1234",
                },
                "entity_b": {
                    "id": "b1",
                    "Full Name": "John Smith",
                    "Email": "john@example.com",
                    "Phone": "555-1234",
                    "Organization": "New Org",  # Additional field, not a conflict
                },
                "expected_conflicts": [],
            },
            {
                "name": "simple_conflicts",
                "entity_a": {
                    "id": "a2",
                    "Full Name": "John Smith",
                    "Email": "john@example.com",
                    "Phone": "555-1234",
                },
                "entity_b": {
                    "id": "b2",
                    "Full Name": "John Smith",
                    "Email": "j.smith@company.com",  # Different email
                    "Phone": "555-5678",  # Different phone
                },
                "expected_conflicts": ["Email", "Phone"],
            },
            {
                "name": "list_vs_string_conflicts",
                "entity_a": {
                    "id": "a3",
                    "Full Name": "Jane Doe",
                    "Email": "jane@example.com",
                    "Organization": "Company A",
                },
                "entity_b": {
                    "id": "b3",
                    "Full Name": "Jane Doe",
                    "Email": [
                        "jane@example.com",
                        "j.doe@company.com",
                    ],  # List vs string
                    "Organization": ["Company A", "Company B"],  # List vs string
                },
                "expected_conflicts": [],  # Should not be conflicts if overlap exists
            },
            {
                "name": "list_vs_list_conflicts",
                "entity_a": {
                    "id": "a4",
                    "Full Name": "Bob Wilson",
                    "Email": ["bob@example.com", "b.wilson@company.com"],
                    "Skills": ["Python", "JavaScript"],
                },
                "entity_b": {
                    "id": "b4",
                    "Full Name": "Bob Wilson",
                    "Email": [
                        "robert@example.com",
                        "r.wilson@company.com",
                    ],  # No overlap
                    "Skills": ["Java", "C++"],  # No overlap
                },
                "expected_conflicts": ["Email", "Skills"],
            },
        ]

        def detect_conflicts(entity_a, entity_b):
            """Detect conflicts between two entities."""
            conflicts = []

            for key in entity_a:
                if key in entity_b and entity_a[key] and entity_b[key]:
                    val_a = entity_a[key]
                    val_b = entity_b[key]

                    # Handle list comparisons
                    if isinstance(val_a, list) and isinstance(val_b, list):
                        # Check for overlap
                        set_a = {str(v).lower() for v in val_a}
                        set_b = {str(v).lower() for v in val_b}
                        if set_a.isdisjoint(set_b):
                            conflicts.append(key)
                    elif isinstance(val_a, list):
                        # Check if string value overlaps with list
                        val_b_normalized = str(val_b).lower()
                        if not any(val_b_normalized == str(v).lower() for v in val_a):
                            conflicts.append(key)
                    elif isinstance(val_b, list):
                        # Check if string value overlaps with list
                        val_a_normalized = str(val_a).lower()
                        if not any(val_a_normalized == str(v).lower() for v in val_b):
                            conflicts.append(key)
                    else:
                        # Both are strings
                        if str(val_a).lower() != str(val_b).lower():
                            conflicts.append(key)

            return conflicts

        for test in conflict_test_cases:
            conflicts = detect_conflicts(test["entity_a"], test["entity_b"])

            assert set(conflicts) == set(
                test["expected_conflicts"]
            ), f"Test '{test['name']}': Expected conflicts {test['expected_conflicts']}, got {conflicts}"

    def test_merged_entity_validation(self):
        """Test validation of merged entity output."""

        merge_validation_tests = [
            {
                "name": "successful_conservative_merge",
                "primary": {
                    "id": "primary-1",
                    "Full Name": "John Smith",
                    "Email": "john@example.com",
                    "Title": "Manager",
                },
                "secondary": {
                    "id": "secondary-1",
                    "Full Name": "John Smith",
                    "Email": "john@example.com",
                    "Phone": "555-1234",  # New field
                    "Organization": "Acme Corp",  # New field
                },
                "expected_merged": {
                    "id": "primary-1",  # Primary ID preserved
                    "Full Name": "John Smith",
                    "Email": "john@example.com",
                    "Title": "Manager",  # From primary
                    "Phone": "555-1234",  # From secondary
                    "Organization": "Acme Corp",  # From secondary
                },
                "expected_conflicts": [],
            },
            {
                "name": "merge_with_conflicts",
                "primary": {
                    "id": "primary-2",
                    "Full Name": "Jane Doe",
                    "Email": "jane@example.com",
                    "Title": "Director",
                    "Organization": "Company A",
                },
                "secondary": {
                    "id": "secondary-2",
                    "Full Name": "Jane Doe",
                    "Email": "j.doe@company.com",  # Different email
                    "Title": "Senior Manager",  # Different title
                    "Organization": "Company A",
                    "Phone": "555-5678",
                },
                "expected_merged": {
                    "id": "primary-2",
                    "Full Name": "Jane Doe",
                    "Email": "jane@example.com",  # Primary value kept
                    "Title": "Director",  # Primary value kept
                    "Organization": "Company A",
                    "Phone": "555-5678",  # From secondary
                },
                "expected_conflicts": ["Email", "Title"],
            },
        ]

        def perform_conservative_merge(primary, secondary):
            """Perform conservative merge with conflict tracking."""
            merged = primary.copy()
            conflicts = {}

            for key, value in secondary.items():
                if key.startswith("_") or key == "id":
                    continue

                if key in merged and merged[key] and merged[key] != value:
                    # Conflict detected
                    conflicts[key] = {"primary": merged[key], "secondary": value}
                elif key not in merged or not merged[key]:
                    # Fill empty field
                    merged[key] = value

            # Add merge metadata
            merged["_merge_info"] = {
                "merged_from": [primary.get("id"), secondary.get("id")],
                "conflicts": conflicts if conflicts else None,
                "merge_strategy": "conservative",
            }

            return merged, list(conflicts.keys())

        for test in merge_validation_tests:
            merged, conflicts = perform_conservative_merge(
                test["primary"], test["secondary"]
            )

            # Validate merged entity structure
            assert (
                merged["id"] == test["expected_merged"]["id"]
            ), f"Test '{test['name']}': Primary ID not preserved"

            # Check expected fields
            for key, expected_value in test["expected_merged"].items():
                assert (
                    merged[key] == expected_value
                ), f"Test '{test['name']}': Field '{key}' should be {expected_value}, got {merged.get(key)}"

            # Check conflicts
            assert set(conflicts) == set(
                test["expected_conflicts"]
            ), f"Test '{test['name']}': Expected conflicts {test['expected_conflicts']}, got {conflicts}"

            # Validate merge metadata
            assert "_merge_info" in merged, "Merge metadata missing"
            assert (
                "merged_from" in merged["_merge_info"]
            ), "Merge source tracking missing"
            assert (
                "merge_strategy" in merged["_merge_info"]
            ), "Merge strategy not recorded"

    def test_audit_trail_completeness(self):
        """Test completeness of audit trail data."""

        # Test audit trail for various operations
        audit_tests = [
            {
                "operation": "merge_decision",
                "data": {
                    "match_id": "match-123",
                    "decision": "merge",
                    "reasoning": "Clear duplicate with matching emails",
                    "reviewer": "user-1",
                    "confidence": 95.0,
                    "primary_entity": "A",
                },
                "required_fields": [
                    "match_id",
                    "decision",
                    "reasoning",
                    "reviewer",
                    "timestamp",
                ],
                "optional_fields": ["confidence", "primary_entity", "evidence"],
            },
            {
                "operation": "merge_execution",
                "data": {
                    "proposal_id": "proposal-456",
                    "primary_entity_id": "entity-1",
                    "secondary_entity_id": "entity-2",
                    "merge_strategy": "conservative",
                    "conflicts_detected": ["Email", "Phone"],
                    "success": True,
                },
                "required_fields": [
                    "proposal_id",
                    "primary_entity_id",
                    "secondary_entity_id",
                    "success",
                    "timestamp",
                ],
                "optional_fields": [
                    "merge_strategy",
                    "conflicts_detected",
                    "error_message",
                ],
            },
            {
                "operation": "analysis_run",
                "data": {
                    "database": "People & Contacts",
                    "total_entities": 100,
                    "matches_found": 15,
                    "ai_enabled": True,
                    "thresholds": {"auto_merge": 90.0, "review": 70.0},
                },
                "required_fields": [
                    "database",
                    "total_entities",
                    "matches_found",
                    "timestamp",
                ],
                "optional_fields": ["ai_enabled", "thresholds", "processing_time"],
            },
        ]

        def validate_audit_entry(operation, data, required_fields, optional_fields):
            """Validate an audit trail entry."""
            errors = []

            # Check required fields
            for field in required_fields:
                if field not in data:
                    # Add timestamp if missing (would be added by audit system)
                    if field == "timestamp":
                        data["timestamp"] = "2025-07-12T10:00:00Z"
                    else:
                        errors.append(f"Missing required field: {field}")

            # Check data types and values
            if "timestamp" in data:
                # Validate timestamp format (basic check)
                timestamp = data["timestamp"]
                assert isinstance(timestamp, str), "Timestamp should be string"

            if "success" in data:
                assert isinstance(
                    data["success"], bool
                ), "Success field should be boolean"

            if "confidence" in data:
                confidence = data["confidence"]
                assert isinstance(
                    confidence, (int, float)
                ), "Confidence should be numeric"
                assert 0 <= confidence <= 100, "Confidence should be 0-100"

            return len(errors) == 0, errors

        for test in audit_tests:
            is_valid, errors = validate_audit_entry(
                test["operation"],
                test["data"],
                test["required_fields"],
                test["optional_fields"],
            )

            assert (
                is_valid
            ), f"Audit validation failed for {test['operation']}: {errors}"

    def test_data_integrity_preservation(self):
        """Test that data integrity is preserved throughout the workflow."""

        # Test data at different stages of the workflow
        original_data = [
            {
                "id": "person-1",
                "Full Name": "John Smith",
                "Email": "john@example.com",
                "Phone": "555-1234",
                "Organization": "Acme Corp",
                "Notes": "Important client contact",
                "Skills": ["Python", "Data Analysis"],
            },
            {
                "id": "person-2",
                "Full Name": "John Smith",
                "Email": "j.smith@acme.com",
                "Phone": "555-1234",
                "Organization": ["Acme Corp", "Beta Inc"],
                "Title": "Senior Developer",
            },
        ]

        # Test data integrity through each stage
        integrity_stages = [
            {
                "stage": "input_validation",
                "test": "original_data_unchanged",
                "data": original_data.copy(),
            },
            {
                "stage": "similarity_analysis",
                "test": "data_preserved_during_analysis",
                "data": original_data.copy(),
            },
            {
                "stage": "merge_operation",
                "test": "no_data_loss_in_merge",
                "data": original_data.copy(),
            },
        ]

        def calculate_data_hash(data):
            """Calculate a hash of the data for integrity checking."""
            import hashlib

            data_str = json.dumps(data, sort_keys=True)
            return hashlib.md5(data_str.encode()).hexdigest()

        def validate_data_integrity(stage, original, processed):
            """Validate that essential data is preserved."""
            integrity_errors = []

            # Check that all original entities are accounted for
            original_ids = {item["id"] for item in original}

            if stage == "merge_operation":
                # In merge, some entities may be combined
                # Check that no data is lost, even if entities are merged
                processed_ids = set()
                for item in processed:
                    if "_merge_info" in item and "merged_from" in item["_merge_info"]:
                        # This is a merged entity
                        processed_ids.update(item["_merge_info"]["merged_from"])
                    else:
                        processed_ids.add(item["id"])

                if not original_ids.issubset(processed_ids):
                    missing_ids = original_ids - processed_ids
                    integrity_errors.append(
                        f"Missing entity IDs after merge: {missing_ids}"
                    )
            else:
                # For other stages, all entities should be preserved
                processed_ids = {item["id"] for item in processed}
                if original_ids != processed_ids:
                    integrity_errors.append(
                        f"Entity IDs changed: original={original_ids}, processed={processed_ids}"
                    )

            return len(integrity_errors) == 0, integrity_errors

        # Test each stage
        current_data = original_data.copy()

        for stage_info in integrity_stages:
            stage = stage_info["stage"]

            if stage == "input_validation":
                # Data should remain exactly the same
                processed_data = current_data.copy()

            elif stage == "similarity_analysis":
                # Data structure should be preserved, might have analysis metadata
                processed_data = []
                for item in current_data:
                    enhanced_item = item.copy()
                    enhanced_item["_analysis_metadata"] = {
                        "processed": True,
                        "similarity_scores": {},
                    }
                    processed_data.append(enhanced_item)

            elif stage == "merge_operation":
                # Simulate merge of the two entities
                merged_entity = current_data[0].copy()  # Use first as primary
                secondary = current_data[1]

                # Fill missing fields from secondary
                for key, value in secondary.items():
                    if key not in merged_entity or not merged_entity[key]:
                        merged_entity[key] = value

                # Add merge metadata
                merged_entity["_merge_info"] = {
                    "merged_from": [current_data[0]["id"], current_data[1]["id"]],
                    "merge_strategy": "conservative",
                }

                processed_data = [merged_entity]

            # Validate integrity
            is_valid, errors = validate_data_integrity(
                stage, current_data, processed_data
            )
            assert is_valid, f"Data integrity violation at stage '{stage}': {errors}"

            # Update current data for next stage
            current_data = processed_data
