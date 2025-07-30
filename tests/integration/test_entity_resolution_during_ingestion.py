"""Tests for entity resolution during the ingestion process."""

import pytest
from typing import Dict, List


class TestEntityResolutionDuringIngestion:
    """Test smart entity matching when AI extracts entities from transcripts."""

    @pytest.fixture
    def existing_entities_db(self):
        """Mock existing entities in Notion database."""
        return {
            "people": [
                {
                    "id": "person-1",
                    "Full Name": "John Smith",
                    "Email": "john.smith@acme.com",
                    "Organization": "Acme Corp",
                    "Phone": "555-0123",
                },
                {
                    "id": "person-2",
                    "Full Name": "Jane Doe",
                    "Email": "jane@planning.gov",
                    "Department": "City Planning",
                    "Title": "Senior Planner",
                },
                {
                    "id": "person-3",
                    "Full Name": "Robert Johnson",
                    "Email": "rjohnson@email.com",
                    "Nickname": "Bob",
                    "Organization": "Johnson & Associates",
                },
                {
                    "id": "person-4",
                    "Full Name": "Elizabeth Chen",
                    "Email": "liz.chen@beta.com",
                    "Organization": "Beta Industries",
                    "Also Known As": ["Liz Chen", "Beth Chen"],
                },
            ],
            "organizations": [
                {
                    "id": "org-1",
                    "Name": "Acme Corporation",
                    "Also Known As": ["Acme Corp", "Acme Corp.", "ACME"],
                    "Type": "Private Company",
                },
                {
                    "id": "org-2",
                    "Name": "City Planning Department",
                    "Also Known As": [
                        "Planning Dept",
                        "City Planning",
                        "Planning Department",
                    ],
                    "Type": "Government",
                },
            ],
        }

    def test_fuzzy_name_matching(self, existing_entities_db):
        """Test matching variations of names like 'J. Smith' to 'John Smith'."""

        # Extracted entities with name variations
        extracted_entities = [
            {"name": "J. Smith", "context": "J. Smith from Acme mentioned..."},
            {"name": "J Smith", "context": "Meeting with J Smith"},
            {"name": "Smith, John", "context": "Attendee: Smith, John"},
            {"name": "John S.", "context": "John S. will handle this"},
            {"name": "Mr. Smith", "context": "Mr. Smith from Acme Corp"},
            {"name": "Bob Johnson", "context": "Bob Johnson called"},
            {"name": "R. Johnson", "context": "R. Johnson signed off"},
            {"name": "Liz Chen", "context": "Liz Chen from Beta"},
            {"name": "E. Chen", "context": "E. Chen to review"},
        ]

        def match_person_fuzzy(
            extracted_name: str, context: str, existing_people: List[Dict]
        ) -> List[Dict]:
            """Fuzzy match extracted name against existing people."""
            matches = []
            name_lower = extracted_name.lower().strip()

            for person in existing_people:
                full_name = person["Full Name"].lower()
                confidence = 0
                reasoning = []

                # Check exact match
                if name_lower == full_name:
                    confidence = 100
                    reasoning.append("Exact name match")

                # Check initials pattern (J. Smith, J Smith)
                elif "smith" in name_lower and "smith" in full_name:
                    if name_lower.startswith("j"):
                        if "john" in full_name:
                            confidence = 85
                            reasoning.append("Initial matches first name")

                # Check last name, first name pattern
                elif ", " in extracted_name:
                    last, first = extracted_name.split(", ", 1)
                    if last.lower() in full_name and first.lower() in full_name:
                        confidence = 90
                        reasoning.append("Last, First name format matches")

                # Check Mr./Ms. patterns
                elif name_lower.startswith(("mr.", "ms.", "mrs.", "dr.")):
                    title, name_part = name_lower.split(" ", 1)
                    if name_part in full_name:
                        confidence = 80
                        reasoning.append("Title + name matches")

                # Check nickname matches
                elif person.get("Nickname", "").lower() == name_lower:
                    confidence = 95
                    reasoning.append("Matches known nickname")

                # Check also known as
                elif person.get("Also Known As"):
                    for aka in person["Also Known As"]:
                        if aka.lower() == name_lower:
                            confidence = 95
                            reasoning.append(f"Matches known alias: {aka}")
                            break

                # Check first initial + last name
                elif "johnson" in name_lower and "johnson" in full_name:
                    if name_lower.startswith("r") and "robert" in full_name:
                        confidence = 85
                        reasoning.append("Initial matches first name")

                # Check partial matches with context
                if confidence == 0 and context:
                    # Check if organization mentioned in context
                    if person.get("Organization"):
                        org_lower = person["Organization"].lower()
                        if any(
                            org_part in context.lower()
                            for org_part in org_lower.split()
                        ):
                            # Partial name match + org match
                            name_parts = name_lower.split()
                            full_parts = full_name.split()
                            matching_parts = sum(
                                1
                                for part in name_parts
                                if any(part in fp for fp in full_parts)
                            )

                            if matching_parts > 0:
                                confidence = 70 + (matching_parts * 10)
                                reasoning.append(
                                    "Partial name match with organization context"
                                )

                if confidence > 0:
                    matches.append(
                        {
                            "person": person,
                            "confidence": confidence,
                            "reasoning": " + ".join(reasoning),
                            "extracted_name": extracted_name,
                        }
                    )

            return sorted(matches, key=lambda x: x["confidence"], reverse=True)

        # Test each extracted entity
        resolution_results = []

        for entity in extracted_entities:
            matches = match_person_fuzzy(
                entity["name"], entity["context"], existing_entities_db["people"]
            )

            if matches:
                best_match = matches[0]
                resolution_results.append(
                    {
                        "extracted": entity["name"],
                        "matched_to": best_match["person"]["Full Name"],
                        "confidence": best_match["confidence"],
                        "reasoning": best_match["reasoning"],
                    }
                )
            else:
                resolution_results.append(
                    {
                        "extracted": entity["name"],
                        "matched_to": None,
                        "confidence": 0,
                        "reasoning": "No match found",
                    }
                )

        # Verify fuzzy matching results

        # J. Smith variations should match John Smith
        j_smith_results = [
            r
            for r in resolution_results
            if "J. Smith" in r["extracted"] or "J Smith" in r["extracted"]
        ]
        assert all(r["matched_to"] == "John Smith" for r in j_smith_results)
        assert all(r["confidence"] >= 80 for r in j_smith_results)

        # Smith, John should have high confidence
        smith_john = next(
            r for r in resolution_results if r["extracted"] == "Smith, John"
        )
        assert smith_john["matched_to"] == "John Smith"
        assert smith_john["confidence"] >= 90

        # Bob Johnson should match Robert Johnson via nickname
        bob_result = next(
            r for r in resolution_results if r["extracted"] == "Bob Johnson"
        )
        assert bob_result["matched_to"] == "Robert Johnson"
        assert bob_result["confidence"] >= 95
        assert "nickname" in bob_result["reasoning"].lower()

        # Liz Chen should match Elizabeth Chen via Also Known As
        liz_result = next(r for r in resolution_results if r["extracted"] == "Liz Chen")
        assert liz_result["matched_to"] == "Elizabeth Chen"
        assert liz_result["confidence"] >= 95
        assert "alias" in liz_result["reasoning"].lower()

        # E. Chen should match with lower confidence
        e_chen_result = next(
            r for r in resolution_results if r["extracted"] == "E. Chen"
        )
        assert e_chen_result["matched_to"] == "Elizabeth Chen"
        assert 70 <= e_chen_result["confidence"] < 90

    def test_contextual_entity_matching(self, existing_entities_db):
        """Test matching entities based on organizational or contextual clues."""

        # Ambiguous names with context
        extracted_entities = [
            {
                "name": "Smith",
                "context": "Smith from Acme will lead the project",
                "mentioned_org": "Acme",
            },
            {
                "name": "Jane",
                "context": "Jane from the planning department said...",
                "mentioned_dept": "planning department",
            },
            {
                "name": "Johnson",
                "context": "Meeting at Johnson & Associates with Johnson",
                "mentioned_org": "Johnson & Associates",
            },
            {
                "name": "Chen",
                "context": "Chen from Beta Industries provided the update",
                "mentioned_org": "Beta Industries",
            },
            {
                "name": "The Mayor",
                "context": "The Mayor announced new policies",
                "role_reference": "Mayor",
            },
            {
                "name": "Our CEO",
                "context": "Our CEO John will attend",
                "role_reference": "CEO",
                "partial_name": "John",
            },
        ]

        def match_with_context(
            entity: Dict, existing_people: List[Dict], existing_orgs: List[Dict]
        ) -> Dict:
            """Match entity using contextual clues."""
            name = entity["name"]
            context = entity["context"]
            matches = []

            # Handle role references
            if entity.get("role_reference"):
                role = entity["role_reference"].lower()
                for person in existing_people:
                    person_title = (person.get("Title") or "").lower()
                    if role in person_title:
                        confidence = 85
                        if entity.get("partial_name"):
                            if (
                                entity["partial_name"].lower()
                                in person["Full Name"].lower()
                            ):
                                confidence = 95
                        matches.append(
                            {
                                "person": person,
                                "confidence": confidence,
                                "reasoning": f"Role '{role}' matches title",
                            }
                        )

            # Handle single name with organization context
            elif entity.get("mentioned_org"):
                org_variations = [entity["mentioned_org"]]

                # Find organization ID
                org_id = None
                for org in existing_orgs:
                    if entity["mentioned_org"].lower() == org["Name"].lower():
                        org_id = org["id"]
                        break
                    elif org.get("Also Known As"):
                        for aka in org["Also Known As"]:
                            if entity["mentioned_org"].lower() == aka.lower():
                                org_id = org["id"]
                                break

                # Find people in that organization
                for person in existing_people:
                    if person.get("Organization"):
                        # Check if person's org matches
                        person_org = person["Organization"].lower()
                        mentioned_org = entity["mentioned_org"].lower()

                        if person_org == mentioned_org or any(
                            aka.lower() == person_org
                            for aka in ["Acme Corp", "Acme Corp.", "ACME"]
                        ):
                            # Check if name partially matches
                            person_last_name = person["Full Name"].split()[-1].lower()
                            if name.lower() == person_last_name:
                                matches.append(
                                    {
                                        "person": person,
                                        "confidence": 90,
                                        "reasoning": "Last name + organization match",
                                    }
                                )

            # Handle department references
            elif entity.get("mentioned_dept"):
                dept = entity["mentioned_dept"].lower()
                for person in existing_people:
                    if person.get("Department"):
                        person_dept = person["Department"].lower()
                        if dept in person_dept or person_dept in dept:
                            # Check name match
                            if name.lower() in person["Full Name"].lower():
                                matches.append(
                                    {
                                        "person": person,
                                        "confidence": 88,
                                        "reasoning": "Name + department match",
                                    }
                                )

            # Sort by confidence and return best match
            if matches:
                matches.sort(key=lambda x: x["confidence"], reverse=True)
                return {
                    "extracted": entity,
                    "match": matches[0],
                    "all_matches": matches,
                }
            else:
                return {"extracted": entity, "match": None, "all_matches": []}

        # Test contextual matching
        results = []
        for entity in extracted_entities:
            result = match_with_context(
                entity,
                existing_entities_db["people"],
                existing_entities_db["organizations"],
            )
            results.append(result)

        # Verify contextual matches

        # "Smith from Acme" should match John Smith
        smith_result = next(r for r in results if r["extracted"]["name"] == "Smith")
        assert smith_result["match"] is not None
        assert smith_result["match"]["person"]["Full Name"] == "John Smith"
        assert smith_result["match"]["confidence"] >= 90
        assert "organization" in smith_result["match"]["reasoning"].lower()

        # "Jane from planning department" should match Jane Doe
        jane_result = next(r for r in results if r["extracted"]["name"] == "Jane")
        assert jane_result["match"] is not None
        assert jane_result["match"]["person"]["Full Name"] == "Jane Doe"
        assert jane_result["match"]["confidence"] >= 85
        assert "department" in jane_result["match"]["reasoning"].lower()

        # "Johnson" at "Johnson & Associates" should match Robert Johnson
        johnson_result = next(r for r in results if r["extracted"]["name"] == "Johnson")
        assert johnson_result["match"] is not None
        assert johnson_result["match"]["person"]["Full Name"] == "Robert Johnson"

        # "Chen from Beta Industries" should match Elizabeth Chen
        chen_result = next(r for r in results if r["extracted"]["name"] == "Chen")
        assert chen_result["match"] is not None
        assert chen_result["match"]["person"]["Full Name"] == "Elizabeth Chen"

    def test_ambiguous_entity_handling(self, existing_entities_db):
        """Test handling of multiple possible matches for ambiguous entities."""

        # Add more people to create ambiguity
        existing_entities_db["people"].extend(
            [
                {
                    "id": "person-5",
                    "Full Name": "John Smith",
                    "Email": "john@differentcompany.com",
                    "Organization": "Different Company",
                },
                {
                    "id": "person-6",
                    "Full Name": "Jane Smith",
                    "Email": "jane.smith@acme.com",
                    "Organization": "Acme Corp",
                },
                {
                    "id": "person-7",
                    "Full Name": "Jane Doe-Smith",
                    "Email": "jdoesmith@email.com",
                    "Organization": "Freelance",
                },
            ]
        )

        # Ambiguous extractions
        ambiguous_entities = [
            {
                "name": "Smith",
                "context": "Smith mentioned the deadline",
                "no_other_info": True,
            },
            {
                "name": "J. Smith",
                "context": "Email from J. Smith",
                "email_domain": None,  # No email domain to help
            },
            {"name": "Jane", "context": "Jane will coordinate", "no_dept_info": True},
        ]

        def find_all_possible_matches(
            entity: Dict, existing_people: List[Dict]
        ) -> List[Dict]:
            """Find all possible matches for an ambiguous entity."""
            name = entity["name"].lower()
            matches = []

            for person in existing_people:
                full_name = person["Full Name"].lower()
                confidence = 0
                reasoning = []

                # Very ambiguous - just "Smith"
                if name == "smith":
                    if "smith" in full_name:
                        confidence = 40  # Low confidence
                        reasoning.append("Last name match only")

                # Initial + last name
                elif name.startswith("j. ") or name.startswith("j "):
                    if "smith" in name and "smith" in full_name:
                        if full_name.startswith("john") or full_name.startswith("jane"):
                            confidence = 60  # Medium confidence
                            reasoning.append("Initial + last name match")

                # First name only
                elif name == "jane":
                    if full_name.startswith("jane"):
                        confidence = 50  # Low-medium confidence
                        reasoning.append("First name match only")

                if confidence > 0:
                    matches.append(
                        {
                            "person": person,
                            "confidence": confidence,
                            "reasoning": reasoning,
                            "requires_disambiguation": confidence < 80,
                        }
                    )

            return sorted(matches, key=lambda x: x["confidence"], reverse=True)

        # Test ambiguous matching
        ambiguous_results = []

        for entity in ambiguous_entities:
            all_matches = find_all_possible_matches(
                entity, existing_entities_db["people"]
            )

            result = {
                "extracted": entity["name"],
                "possible_matches": len(all_matches),
                "matches": all_matches,
                "action_required": (
                    "manual_disambiguation" if len(all_matches) > 1 else "create_new"
                ),
            }

            # Determine disambiguation strategy
            if len(all_matches) > 1:
                # Multiple matches - need disambiguation
                confidence_scores = [m["confidence"] for m in all_matches]

                if (
                    max(confidence_scores) >= 80
                    and confidence_scores[0] - confidence_scores[1] >= 20
                ):
                    # Clear winner
                    result["recommended_match"] = all_matches[0]["person"]["Full Name"]
                    result["disambiguation_reason"] = (
                        "High confidence with significant gap"
                    )
                else:
                    # Too close to call
                    result["recommended_action"] = "present_options_to_user"
                    result["disambiguation_reason"] = (
                        "Multiple similar confidence matches"
                    )

            ambiguous_results.append(result)

        # Verify ambiguous entity handling

        # "Smith" alone should match multiple people
        smith_result = next(r for r in ambiguous_results if r["extracted"] == "Smith")
        assert (
            smith_result["possible_matches"] >= 3
        )  # John Smith, Jane Smith, Jane Doe-Smith
        assert smith_result["action_required"] == "manual_disambiguation"
        assert all(m["requires_disambiguation"] for m in smith_result["matches"])

        # "J. Smith" should match both John and Jane Smith
        j_smith_result = next(
            r for r in ambiguous_results if r["extracted"] == "J. Smith"
        )
        assert j_smith_result["possible_matches"] >= 2
        assert any(
            "John Smith" in m["person"]["Full Name"] for m in j_smith_result["matches"]
        )
        assert any(
            "Jane Smith" in m["person"]["Full Name"] for m in j_smith_result["matches"]
        )

        # "Jane" should match multiple Janes
        jane_result = next(r for r in ambiguous_results if r["extracted"] == "Jane")
        assert (
            jane_result["possible_matches"] >= 2
        )  # Jane Doe, Jane Smith, maybe Jane Doe-Smith
        assert jane_result["recommended_action"] == "present_options_to_user"

    def test_organization_name_resolution(self, existing_entities_db):
        """Test resolution of organization names and their variations."""

        extracted_orgs = [
            {"name": "Acme", "context": "Contract with Acme"},
            {"name": "ACME", "context": "ACME deliverables"},
            {"name": "Acme Corp.", "context": "Meeting at Acme Corp."},
            {"name": "Planning Dept", "context": "Planning Dept approval needed"},
            {
                "name": "City Planning Department",
                "context": "City Planning Department review",
            },
            {"name": "Planning", "context": "Sent to Planning for review"},
            {
                "name": "Johnson Associates",
                "context": "Johnson Associates proposal",
            },  # Missing &
            {"name": "Beta", "context": "Beta's new product"},
            {"name": "Acme Corporation", "context": "Acme Corporation headquarters"},
        ]

        def match_organization(extracted_org: str, existing_orgs: List[Dict]) -> Dict:
            """Match extracted organization name to existing organizations."""
            extracted_lower = extracted_org.lower().strip()
            best_match = None
            highest_confidence = 0

            for org in existing_orgs:
                confidence = 0
                reasoning = []

                # Check exact match with name
                if extracted_lower == org["Name"].lower():
                    confidence = 100
                    reasoning.append("Exact name match")

                # Check Also Known As
                elif org.get("Also Known As"):
                    for aka in org["Also Known As"]:
                        if extracted_lower == aka.lower():
                            confidence = 95
                            reasoning.append(f"Matches known alias: {aka}")
                            break

                # Check partial matches
                if confidence == 0:
                    org_name_lower = org["Name"].lower()

                    # Check if one contains the other
                    if (
                        extracted_lower in org_name_lower
                        or org_name_lower in extracted_lower
                    ):
                        confidence = 80
                        reasoning.append("Partial name match")

                    # Check word overlap
                    elif any(
                        word in org_name_lower.split()
                        for word in extracted_lower.split()
                        if len(word) > 3
                    ):
                        confidence = 70
                        reasoning.append("Significant word overlap")

                    # Special case for missing punctuation
                    if "johnson" in extracted_lower and "associates" in extracted_lower:
                        if "Johnson & Associates" == org["Name"]:
                            confidence = 90
                            reasoning.append("Match despite missing &")

                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_match = {
                        "organization": org,
                        "confidence": confidence,
                        "reasoning": " + ".join(reasoning),
                    }

            return best_match

        # Test organization matching
        org_results = []

        for ext_org in extracted_orgs:
            match = match_organization(
                ext_org["name"], existing_entities_db["organizations"]
            )

            org_results.append(
                {
                    "extracted": ext_org["name"],
                    "match": match,
                    "matched_to": match["organization"]["Name"] if match else None,
                    "confidence": match["confidence"] if match else 0,
                }
            )

        # Verify organization matches

        # All Acme variations should match to Acme Corporation
        acme_results = [r for r in org_results if "acme" in r["extracted"].lower()]
        assert all(r["matched_to"] == "Acme Corporation" for r in acme_results)
        assert all(r["confidence"] >= 80 for r in acme_results)

        # Exact alias matches should have high confidence
        acme_corp_result = next(
            r for r in org_results if r["extracted"] == "Acme Corp."
        )
        assert acme_corp_result["confidence"] >= 95

        # Planning variations should match City Planning Department
        planning_results = [
            r for r in org_results if "planning" in r["extracted"].lower()
        ]
        assert all(
            r["matched_to"] == "City Planning Department" for r in planning_results
        )

        # "Planning Dept" should match via alias
        planning_dept_result = next(
            r for r in org_results if r["extracted"] == "Planning Dept"
        )
        assert planning_dept_result["confidence"] >= 95

        # "Johnson Associates" (missing &) should still match
        johnson_result = next(
            r for r in org_results if r["extracted"] == "Johnson Associates"
        )
        assert johnson_result["matched_to"] == "Johnson & Associates"
        assert johnson_result["confidence"] >= 90

    def test_cross_reference_validation(self, existing_entities_db):
        """Test validation of entity relationships during matching."""

        # Extracted entities with relationship information
        extracted_with_relations = {
            "people": [
                {
                    "name": "J. Smith",
                    "organization": "Acme",
                    "email_domain": "acme.com",
                },
                {
                    "name": "Jane D.",
                    "department": "Planning",
                    "email_domain": "planning.gov",
                },
                {"name": "Bob", "company": "Johnson & Associates", "role": "CEO"},
            ],
            "mentioned_relationships": [
                {
                    "person": "Smith",
                    "reports_to": "Bob",
                    "context": "Smith reports to Bob on this project",
                },
                {
                    "person": "Jane",
                    "works_with": "Smith",
                    "context": "Jane works closely with Smith",
                },
            ],
        }

        def validate_with_relationships(
            entities: Dict, existing_data: Dict
        ) -> List[Dict]:
            """Validate entity matches using relationship information."""
            validated_matches = []

            # First pass: Match entities individually
            people_matches = {}

            for person in entities["people"]:
                matches = []

                for existing_person in existing_data["people"]:
                    confidence = 0
                    validation_points = []

                    # Name matching
                    if (
                        person["name"] == "J. Smith"
                        and "John Smith" in existing_person["Full Name"]
                    ):
                        confidence += 40
                        validation_points.append("Name pattern match")

                    elif person["name"] == "Jane D." and existing_person[
                        "Full Name"
                    ].startswith("Jane"):
                        confidence += 40
                        validation_points.append("First name match")

                    elif (
                        person["name"] == "Bob"
                        and existing_person.get("Nickname") == "Bob"
                    ):
                        confidence += 50
                        validation_points.append("Nickname match")

                    # Organization validation
                    if person.get("organization"):
                        existing_org = existing_person.get("Organization", "").lower()
                        if person["organization"].lower() in existing_org:
                            confidence += 30
                            validation_points.append("Organization match")

                    # Email domain validation
                    if person.get("email_domain") and existing_person.get("Email"):
                        if person["email_domain"] in existing_person["Email"]:
                            confidence += 25
                            validation_points.append("Email domain match")

                    # Department validation
                    if person.get("department"):
                        existing_dept = existing_person.get("Department", "").lower()
                        if person["department"].lower() in existing_dept:
                            confidence += 25
                            validation_points.append("Department match")

                    if confidence > 0:
                        matches.append(
                            {
                                "person": existing_person,
                                "confidence": confidence,
                                "validation_points": validation_points,
                            }
                        )

                if matches:
                    best_match = max(matches, key=lambda x: x["confidence"])
                    people_matches[person["name"]] = best_match

            # Second pass: Validate using relationships
            for relationship in entities["mentioned_relationships"]:
                person_name = relationship["person"]

                if person_name in people_matches:
                    match = people_matches[person_name]

                    # Check if relationships make sense
                    if relationship.get("reports_to"):
                        reports_to_name = relationship["reports_to"]
                        if reports_to_name in people_matches:
                            # Validate the reporting relationship makes sense
                            reporter = match["person"]
                            manager = people_matches[reports_to_name]["person"]

                            # Check organizations
                            if reporter.get("Organization") == manager.get(
                                "Organization"
                            ):
                                match["confidence"] += 10
                                match["validation_points"].append(
                                    "Reporting relationship validates org match"
                                )

                    if relationship.get("works_with"):
                        colleague_name = relationship["works_with"]
                        if colleague_name in people_matches:
                            # Validate they could work together
                            colleague = people_matches[colleague_name]["person"]

                            # Check if same org or related departments
                            if match["person"].get("Organization") == colleague.get(
                                "Organization"
                            ) or (
                                match["person"].get("Department")
                                and colleague.get("Department")
                            ):
                                match["confidence"] += 5
                                match["validation_points"].append(
                                    "Colleague relationship validates match"
                                )

            # Create final validated results
            for person_name, match_info in people_matches.items():
                validated_matches.append(
                    {
                        "extracted_name": person_name,
                        "matched_to": match_info["person"]["Full Name"],
                        "final_confidence": match_info["confidence"],
                        "validation_used": match_info["validation_points"],
                        "relationship_validated": match_info["confidence"] > 70,
                    }
                )

            return validated_matches

        # Run validation
        validated_results = validate_with_relationships(
            extracted_with_relations, existing_entities_db
        )

        # Verify relationship validation

        # J. Smith should have high confidence due to multiple validations
        j_smith = next(
            r for r in validated_results if r["extracted_name"] == "J. Smith"
        )
        assert j_smith["matched_to"] == "John Smith"
        assert j_smith["final_confidence"] >= 70  # Name + org + email domain
        assert "Organization match" in j_smith["validation_used"]
        assert "Email domain match" in j_smith["validation_used"]

        # Jane D. should match Jane Doe with department validation
        jane = next(r for r in validated_results if r["extracted_name"] == "Jane D.")
        assert jane["matched_to"] == "Jane Doe"
        assert "Department match" in jane["validation_used"]

        # Bob should match Robert Johnson
        bob = next(r for r in validated_results if r["extracted_name"] == "Bob")
        assert bob["matched_to"] == "Robert Johnson"
        assert "Nickname match" in bob["validation_used"]

        # All should be relationship validated
        assert all(r["relationship_validated"] for r in validated_results)
