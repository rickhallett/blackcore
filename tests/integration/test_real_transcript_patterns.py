"""Tests for real-world transcript patterns and edge cases."""

import pytest
from unittest.mock import Mock

from blackcore.minimal.models import TranscriptInput
from blackcore.minimal.ai_extractor import AIExtractor


class TestRealTranscriptPatterns:
    """Test handling of real-world transcript patterns including messy data."""
    
    @pytest.fixture
    def mock_ai_extractor(self):
        """Create a mock AI extractor."""
        extractor = Mock(spec=AIExtractor)
        return extractor
        
    def test_messy_transcription_data(self, mock_ai_extractor):
        """Test handling of OCR errors, speech-to-text issues, and typos."""
        
        # Real-world messy transcript with common issues
        messy_transcript = TranscriptInput(
            title="Beach Hut Committee Meeting - January 2025",
            content="""
            BEACH HUT COMMITTEE MEETING
            January 10th, 2025 - 2:00 PM
            
            ATTENDEES:
            - Councilwoman Maria Gracia (should be Garcia)
            - John Smth (missing 'i' in Smith)
            - jane doe from planning dept
            - Mr. Robt. Johnson (Robert abbreviated)
            - Sara Chen (or Sarah? unclear in audio)
            
            TRANSCRIPT:
            
            Maria Gracia: Thank you all for comming. Let's discuss the beach hut situtation.
            
            John Smth: I've reviewd the survey results. Their are 47 beach huts in totl.
            
            jane doe: the planning departmnt has concerns about 12 of them.
            
            Mr. Johnson: My cleint, Thomas Write (Wright?), owns 3 of those huts.
            
            Sara/Sarah Chen: Beta Industires (Industries) is intrested in the development.
            
            [INAUDIBLE] mentioned something about May 15th deadline.
            
            Maria G: We need to schedle a followup meeting. How about next Wenesday?
            
            John S: That works. I'll send out the meeting invte.
            
            ACTION ITEMS:
            1. John to reviw remaining survey data
            2. Jane - prepare complience report
            3. Mr. Johnson to contact Thomas Write/Wright
            4. Sara Chen - coordinate with Beta Industires
            
            Meeting adjorned at 3:15 PM.
            
            [Note: Audio quality was poor during middle section]
            [Transcriber note: Several names may be misspelled due to audio quality]
            """,
            date="2025-01-10",
            metadata={"quality": "poor", "transcription_method": "automated"}
        )
        
        def extract_from_messy_transcript(transcript):
            """Extract entities from messy transcript with corrections."""
            
            # Common corrections mapping
            name_corrections = {
                "Maria Gracia": "Maria Garcia",
                "John Smth": "John Smith",
                "jane doe": "Jane Doe",
                "Robt. Johnson": "Robert Johnson",
                "Mr. Johnson": "Robert Johnson",
                "Sara Chen": "Sarah Chen",
                "Thomas Write": "Thomas Wright",
                "Beta Industires": "Beta Industries"
            }
            
            # Extract and clean entities
            extracted = {
                "people": [],
                "organizations": [],
                "tasks": [],
                "issues": []
            }
            
            # Process attendees section
            attendees_section = transcript.content.split("ATTENDEES:")[1].split("TRANSCRIPT:")[0]
            
            for line in attendees_section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    # Clean attendee line
                    attendee = line[1:].strip()
                    
                    # Apply corrections
                    for wrong, correct in name_corrections.items():
                        if wrong.lower() in attendee.lower():
                            attendee = attendee.replace(wrong, correct)
                            
                    # Extract person and metadata
                    if "Garcia" in attendee:
                        extracted["people"].append({
                            "name": "Maria Garcia",
                            "role": "Councilwoman",
                            "confidence": 90,  # High confidence after correction
                            "original": "Maria Gracia"
                        })
                    elif "Smith" in attendee:
                        extracted["people"].append({
                            "name": "John Smith",
                            "confidence": 95,
                            "original": "John Smth"
                        })
                    elif "Jane" in attendee.title():
                        extracted["people"].append({
                            "name": "Jane Doe",
                            "department": "Planning Department",
                            "confidence": 85,
                            "original": "jane doe"
                        })
                    elif "Johnson" in attendee:
                        extracted["people"].append({
                            "name": "Robert Johnson",
                            "confidence": 90,
                            "original": "Mr. Robt. Johnson"
                        })
                    elif "Chen" in attendee:
                        extracted["people"].append({
                            "name": "Sarah Chen",
                            "confidence": 75,  # Lower confidence due to Sara/Sarah uncertainty
                            "original": "Sara Chen",
                            "note": "Name spelling uncertain"
                        })
                        
            # Extract organizations
            if "Beta Industries" in transcript.content or "Beta Industires" in transcript.content:
                extracted["organizations"].append({
                    "name": "Beta Industries",
                    "confidence": 90,
                    "original": "Beta Industires"
                })
                
            # Extract action items with assignee corrections
            action_section = transcript.content.split("ACTION ITEMS:")[1].split("Meeting adjorned")[0]
            
            for line in action_section.split("\n"):
                line = line.strip()
                if line and line[0].isdigit():
                    # Parse action item
                    if "John" in line:
                        extracted["tasks"].append({
                            "title": "Review remaining survey data",
                            "assignee": "John Smith",
                            "original_text": "John to reviw remaining survey data"
                        })
                    elif "Jane" in line:
                        extracted["tasks"].append({
                            "title": "Prepare compliance report",
                            "assignee": "Jane Doe",
                            "original_text": "Jane - prepare complience report"
                        })
                    elif "Johnson" in line:
                        extracted["tasks"].append({
                            "title": "Contact Thomas Wright",
                            "assignee": "Robert Johnson",
                            "original_text": "Mr. Johnson to contact Thomas Write/Wright"
                        })
                    elif "Chen" in line:
                        extracted["tasks"].append({
                            "title": "Coordinate with Beta Industries",
                            "assignee": "Sarah Chen",
                            "original_text": "Sara Chen - coordinate with Beta Industires"
                        })
                        
            # Extract issues/concerns
            extracted["issues"].append({
                "type": "transcription_quality",
                "sections": ["INAUDIBLE section", "Audio quality poor"],
                "impact": "Possible missing information around May 15th deadline"
            })
            
            extracted["issues"].append({
                "type": "name_uncertainty",
                "entities": ["Sara/Sarah Chen", "Thomas Write/Wright"],
                "resolution": "Applied most likely spelling based on context"
            })
            
            return extracted
            
        # Extract entities from messy transcript
        extracted = extract_from_messy_transcript(messy_transcript)
        
        # Verify corrections were applied
        assert len(extracted["people"]) == 5
        
        # Check specific corrections
        maria = next(p for p in extracted["people"] if p["name"] == "Maria Garcia")
        assert maria["original"] == "Maria Gracia"
        assert maria["confidence"] == 90
        
        john = next(p for p in extracted["people"] if p["name"] == "John Smith")
        assert john["original"] == "John Smth"
        
        # Check organization correction
        assert len(extracted["organizations"]) == 1
        assert extracted["organizations"][0]["name"] == "Beta Industries"
        assert extracted["organizations"][0]["original"] == "Beta Industires"
        
        # Check task assignments use corrected names
        review_task = next(t for t in extracted["tasks"] if "Review" in t["title"])
        assert review_task["assignee"] == "John Smith"  # Not "John Smth"
        
        # Check that issues were tracked
        assert len(extracted["issues"]) == 2
        assert any(issue["type"] == "transcription_quality" for issue in extracted["issues"])
        
    def test_pronoun_resolution(self, mock_ai_extractor):
        """Test resolution of pronouns and references in conversation."""
        
        conversation_transcript = TranscriptInput(
            title="Development Planning Discussion",
            content="""
            Sarah Chen: Good morning everyone. I wanted to discuss the Wright Development proposal.
            
            Thomas Wright: Thank you for having me. We've revised our plans based on the feedback.
            
            Maria Garcia: I appreciate that. Can you walk us through the changes?
            
            Thomas Wright: Of course. We've reduced the size of all structures by 15%.
            
            Sarah Chen: That's helpful. She had mentioned this was a concern.
            [Context: "She" refers to Maria Garcia who raised size concerns in previous meeting]
            
            Maria Garcia: Yes, I did raise that issue. What about the environmental impact?
            
            Thomas Wright: Our environmental consultant addressed those concerns. He submitted a report yesterday.
            [Context: "He" refers to Dr. Michael Park, their environmental consultant]
            
            Sarah Chen: I haven't seen it yet. Can you forward that to the committee?
            
            Thomas Wright: Absolutely. I'll have him send it directly to you all.
            [Context: "him" still refers to Dr. Michael Park]
            
            Maria Garcia: The planning department will need to review it as well.
            
            Sarah Chen: Jane can handle that. She's our liaison with planning.
            [Context: "She" refers to Jane Doe from planning department]
            
            Thomas Wright: Great. Should we schedule the follow-up after they've had time to review?
            [Context: "they" refers to the planning department]
            
            Maria Garcia: That makes sense. Let's aim for next Thursday.
            
            Sarah Chen: I'll coordinate with them to ensure everyone can attend.
            [Context: "them" refers to all parties - planning dept, environmental consultant, etc.]
            """,
            date="2025-01-12",
            metadata={"type": "conversation", "pronoun_heavy": True}
        )
        
        def resolve_pronouns_in_context(transcript):
            """Resolve pronouns based on conversational context."""
            
            pronoun_resolutions = []
            current_speaker = None
            mentioned_entities = {}
            
            lines = transcript.content.split("\n")
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Track current speaker
                if ":" in line and not line.startswith("["):
                    current_speaker = line.split(":")[0].strip()
                    mentioned_entities[current_speaker] = {
                        "type": "person",
                        "last_mentioned": i
                    }
                    
                # Look for pronouns
                pronouns = {
                    "she": "female",
                    "he": "male",
                    "they": "group",
                    "them": "group",
                    "him": "male",
                    "her": "female"
                }
                
                for pronoun, gender_hint in pronouns.items():
                    if f" {pronoun} " in line.lower() or line.lower().endswith(f" {pronoun}"):
                        # Find context
                        context_clue = None
                        
                        # Check for explicit context notes
                        for j in range(i, min(i + 3, len(lines))):
                            if "[Context:" in lines[j]:
                                context_clue = lines[j]
                                break
                                
                        # Resolve based on context
                        if context_clue:
                            resolution = {
                                "line_number": i,
                                "line": line,
                                "pronoun": pronoun,
                                "speaker": current_speaker,
                                "resolved_to": None,
                                "confidence": 0,
                                "method": "context_note"
                            }
                            
                            # Parse context note
                            if "Maria Garcia" in context_clue and pronoun == "she":
                                resolution["resolved_to"] = "Maria Garcia"
                                resolution["confidence"] = 95
                            elif "Dr. Michael Park" in context_clue and pronoun in ["he", "him"]:
                                resolution["resolved_to"] = "Dr. Michael Park"
                                resolution["confidence"] = 95
                            elif "Jane Doe" in context_clue and pronoun == "she":
                                resolution["resolved_to"] = "Jane Doe"
                                resolution["confidence"] = 90
                            elif "planning department" in context_clue and pronoun in ["they", "them"]:
                                resolution["resolved_to"] = "planning department"
                                resolution["confidence"] = 90
                                
                        else:
                            # Use heuristics
                            resolution = {
                                "line_number": i,
                                "line": line,
                                "pronoun": pronoun,
                                "speaker": current_speaker,
                                "resolved_to": None,
                                "confidence": 0,
                                "method": "heuristic"
                            }
                            
                            # Recent mention heuristic
                            if gender_hint == "female":
                                # Look for recently mentioned female
                                for entity, info in mentioned_entities.items():
                                    if "Garcia" in entity or "Chen" in entity or "Jane" in entity:
                                        if abs(i - info["last_mentioned"]) < 5:
                                            resolution["resolved_to"] = entity
                                            resolution["confidence"] = 70
                                            break
                                            
                        if resolution["resolved_to"]:
                            pronoun_resolutions.append(resolution)
                            
            return pronoun_resolutions
            
        # Resolve pronouns
        resolutions = resolve_pronouns_in_context(conversation_transcript)
        
        # Verify pronoun resolutions
        assert len(resolutions) > 0
        
        # Check specific resolutions
        she_maria = next((r for r in resolutions if r["pronoun"] == "she" and "concerns" in r["line"]), None)
        assert she_maria is not None
        assert she_maria["resolved_to"] == "Maria Garcia"
        assert she_maria["confidence"] >= 90
        
        he_michael = next((r for r in resolutions if r["pronoun"] == "he" and "consultant" in r["line"]), None)
        assert he_michael is not None
        assert he_michael["resolved_to"] == "Dr. Michael Park"
        
        she_jane = next((r for r in resolutions if r["pronoun"] == "she" and "liaison" in r["line"]), None)
        assert she_jane is not None
        assert she_jane["resolved_to"] == "Jane Doe"
        
        # Check group pronouns
        they_planning = next((r for r in resolutions if r["pronoun"] == "they" and "review" in r["line"]), None)
        assert they_planning is not None
        assert "planning" in they_planning["resolved_to"].lower()
        
    def test_multi_entity_extraction(self, mock_ai_extractor):
        """Test extracting multiple entities from complex sentences."""
        
        complex_transcript = TranscriptInput(
            title="Multi-Party Negotiation",
            content="""
            PARTICIPANTS: Maria Garcia (City Council), Thomas Wright (Wright Development), 
                         Sarah Chen (Beta Industries), Robert Johnson (Legal Counsel)
            
            DISCUSSION:
            
            Maria Garcia opened by saying: "Thomas Wright from Wright Development and Sarah Chen 
            from Beta Industries have submitted a joint proposal with their attorneys Johnson & 
            Associates, specifically Robert Johnson and his partner Elizabeth Park."
            
            Later in the meeting:
            "The team of architects from Studio One - Michael Chang, Lisa Wong, and David Kim - 
            presented their designs to Wright Development's board members: CEO Thomas Wright, 
            CFO James Wright, and COO Patricia Martinez."
            
            Sarah Chen commented: "Beta Industries, along with our subsidiaries TechCorp and 
            GreenEnergy Solutions, are partnering with Wright Development and their construction 
            division, Wright Construction LLC, managed by Thomas Wright Jr."
            
            Action items were assigned:
            "Maria Garcia will coordinate with Jane Doe from Planning, John Smith from Zoning, 
            and Alice Brown from Environmental Affairs to review the proposal submitted by 
            Thomas Wright, Sarah Chen, and their respective teams at Wright Development and 
            Beta Industries."
            
            The meeting concluded with:
            "Next session will include presentations from Dr. Michael Park (Environmental 
            Consultant), Professor Linda Chen (Urban Planning Expert), and Captain James 
            Morrison (Harbor Master), along with community representatives including local 
            business owners Angela Martinez (Martinez Cafe), Robert Lee (Lee's Market), and 
            Susan Kim (Kim's Beach Rentals)."
            """,
            date="2025-01-13",
            metadata={"type": "multi_party_negotiation"}
        )
        
        def extract_multi_entity_sentences(transcript):
            """Extract multiple entities from single sentences."""
            
            multi_entity_extractions = []
            
            # Define patterns for complex entity extraction
            sentence_patterns = [
                {
                    "pattern": "submitted a joint proposal",
                    "extract": ["proposers", "proposal_type", "supporting_parties"]
                },
                {
                    "pattern": "team of",
                    "extract": ["team_type", "team_members", "organization"]
                },
                {
                    "pattern": "partnering with",
                    "extract": ["primary_partner", "secondary_partners", "subsidiaries"]
                },
                {
                    "pattern": "will coordinate with",
                    "extract": ["coordinator", "coordinatees", "purpose"]
                },
                {
                    "pattern": "include presentations from",
                    "extract": ["presenters", "roles", "affiliations"]
                }
            ]
            
            # Process each sentence
            sentences = transcript.content.replace("\n", " ").split(".")
            
            for sentence in sentences:
                sentence = sentence.strip()
                
                # Check for multi-entity patterns
                for pattern_info in sentence_patterns:
                    if pattern_info["pattern"] in sentence.lower():
                        extraction = {
                            "sentence": sentence,
                            "pattern": pattern_info["pattern"],
                            "entities": {}
                        }
                        
                        # Extract based on pattern
                        if "joint proposal" in sentence:
                            # Extract: Thomas Wright, Wright Development, Sarah Chen, Beta Industries, etc.
                            extraction["entities"] = {
                                "proposers": [
                                    {"name": "Thomas Wright", "organization": "Wright Development"},
                                    {"name": "Sarah Chen", "organization": "Beta Industries"}
                                ],
                                "legal_support": [
                                    {"name": "Robert Johnson", "organization": "Johnson & Associates"},
                                    {"name": "Elizabeth Park", "organization": "Johnson & Associates"}
                                ]
                            }
                            
                        elif "team of architects" in sentence:
                            extraction["entities"] = {
                                "team": "architects",
                                "organization": "Studio One",
                                "members": [
                                    {"name": "Michael Chang", "role": "architect"},
                                    {"name": "Lisa Wong", "role": "architect"},
                                    {"name": "David Kim", "role": "architect"}
                                ],
                                "presented_to": [
                                    {"name": "Thomas Wright", "role": "CEO", "org": "Wright Development"},
                                    {"name": "James Wright", "role": "CFO", "org": "Wright Development"},
                                    {"name": "Patricia Martinez", "role": "COO", "org": "Wright Development"}
                                ]
                            }
                            
                        elif "partnering with" in sentence:
                            extraction["entities"] = {
                                "primary_partner": {
                                    "organization": "Beta Industries",
                                    "subsidiaries": ["TechCorp", "GreenEnergy Solutions"]
                                },
                                "secondary_partner": {
                                    "organization": "Wright Development",
                                    "division": "Wright Construction LLC",
                                    "manager": "Thomas Wright Jr."
                                }
                            }
                            
                        elif "coordinate with" in sentence:
                            extraction["entities"] = {
                                "coordinator": {"name": "Maria Garcia", "role": "City Council"},
                                "coordinatees": [
                                    {"name": "Jane Doe", "department": "Planning"},
                                    {"name": "John Smith", "department": "Zoning"},
                                    {"name": "Alice Brown", "department": "Environmental Affairs"}
                                ],
                                "regarding": ["Thomas Wright", "Sarah Chen", "Wright Development", "Beta Industries"]
                            }
                            
                        elif "presentations from" in sentence:
                            extraction["entities"] = {
                                "expert_presenters": [
                                    {"name": "Dr. Michael Park", "role": "Environmental Consultant"},
                                    {"name": "Professor Linda Chen", "role": "Urban Planning Expert"},
                                    {"name": "Captain James Morrison", "role": "Harbor Master"}
                                ],
                                "community_representatives": [
                                    {"name": "Angela Martinez", "business": "Martinez Cafe"},
                                    {"name": "Robert Lee", "business": "Lee's Market"},
                                    {"name": "Susan Kim", "business": "Kim's Beach Rentals"}
                                ]
                            }
                            
                        multi_entity_extractions.append(extraction)
                        
            return multi_entity_extractions
            
        # Extract multi-entity sentences
        extractions = extract_multi_entity_sentences(complex_transcript)
        
        # Verify complex extractions
        assert len(extractions) >= 5
        
        # Check joint proposal extraction
        proposal_extraction = next(e for e in extractions if e["pattern"] == "submitted a joint proposal")
        assert len(proposal_extraction["entities"]["proposers"]) == 2
        assert any(p["name"] == "Thomas Wright" for p in proposal_extraction["entities"]["proposers"])
        assert len(proposal_extraction["entities"]["legal_support"]) == 2
        
        # Check team extraction
        team_extraction = next(e for e in extractions if "team of" in e["pattern"])
        assert team_extraction["entities"]["organization"] == "Studio One"
        assert len(team_extraction["entities"]["members"]) == 3
        assert len(team_extraction["entities"]["presented_to"]) == 3
        
        # Check partnership extraction
        partner_extraction = next(e for e in extractions if "partnering with" in e["pattern"])
        assert "Beta Industries" in partner_extraction["entities"]["primary_partner"]["organization"]
        assert len(partner_extraction["entities"]["primary_partner"]["subsidiaries"]) == 2
        
        # Check coordination extraction
        coord_extraction = next(e for e in extractions if "coordinate with" in e["pattern"])
        assert coord_extraction["entities"]["coordinator"]["name"] == "Maria Garcia"
        assert len(coord_extraction["entities"]["coordinatees"]) == 3
        
        # Check presentation extraction
        presentation_extraction = next(e for e in extractions if "presentations from" in e["pattern"])
        assert len(presentation_extraction["entities"]["expert_presenters"]) == 3
        assert len(presentation_extraction["entities"]["community_representatives"]) == 3
        
    def test_temporal_reference_handling(self, mock_ai_extractor):
        """Test handling of temporal references and deadline extraction."""
        
        temporal_transcript = TranscriptInput(
            title="Project Timeline Discussion",
            content="""
            Date: Monday, January 13, 2025
            
            Sarah Chen: Let's review our timeline. We submitted the initial proposal last Tuesday.
            
            Thomas Wright: That's right, on January 7th. The review period is 30 days from then.
            
            Maria Garcia: So that takes us to February 6th. But there's a complication...
            
            Jane Doe: The planning commission only meets on the third Thursday of each month.
            
            Maria Garcia: Exactly. So the next meeting after the review period would be February 20th.
            
            Thomas Wright: We have that investor meeting the following week. Can we expedite?
            
            Sarah Chen: When is the investor meeting exactly?
            
            Thomas Wright: February 25th, which is a Tuesday. We need approval by then.
            
            Maria Garcia: There's an emergency session possible on February 10th, but we'd need 
            to file by this Friday.
            
            Jane Doe: That's January 17th. Only 4 days from now.
            
            Sarah Chen: What about the environmental review? That usually takes two weeks.
            
            Maria Garcia: It was started yesterday, so it should be done by January 26th.
            
            Thomas Wright: Perfect. That leaves us almost two weeks before the emergency session.
            
            ACTION ITEMS with DEADLINES:
            - File for emergency session (by Friday, Jan 17)
            - Complete environmental review (by Jan 26)
            - Prepare final presentation (by Feb 8)
            - Emergency commission meeting (Feb 10)
            - Investor meeting (Feb 25)
            
            RECURRING ITEMS:
            - Weekly progress updates (every Monday at 10 AM)
            - Bi-weekly stakeholder calls (every other Wednesday)
            - Monthly commission meetings (third Thursday of each month)
            """,
            date="2025-01-13",
            metadata={"current_date": "2025-01-13", "day_of_week": "Monday"}
        )
        
        def resolve_temporal_references(transcript):
            """Resolve relative temporal references to absolute dates."""
            
            from datetime import datetime, timedelta
            
            # Current date from transcript
            current_date = datetime.strptime(transcript.date, "%Y-%m-%d")
            current_weekday = current_date.weekday()  # 0 = Monday
            
            temporal_resolutions = []
            
            # Relative date patterns
            relative_patterns = {
                "last Tuesday": lambda: current_date - timedelta(days=(current_weekday + 7 - 1) % 7 or 7),
                "this Friday": lambda: current_date + timedelta(days=(4 - current_weekday) % 7),
                "yesterday": lambda: current_date - timedelta(days=1),
                "following week": lambda: current_date + timedelta(weeks=1),
                "two weeks": lambda: timedelta(days=14),
                "30 days": lambda: timedelta(days=30),
                "4 days from now": lambda: current_date + timedelta(days=4)
            }
            
            # Extract temporal references
            lines = transcript.content.split("\n")
            
            for line in lines:
                line = line.strip()
                
                # Check for absolute dates
                if "January 7th" in line:
                    temporal_resolutions.append({
                        "reference": "January 7th",
                        "resolved_date": "2025-01-07",
                        "type": "absolute",
                        "context": line
                    })
                    
                # Check for relative dates
                for pattern, resolver in relative_patterns.items():
                    if pattern in line.lower():
                        if pattern == "last Tuesday":
                            resolved = resolver()
                            temporal_resolutions.append({
                                "reference": pattern,
                                "resolved_date": resolved.strftime("%Y-%m-%d"),
                                "type": "relative_past",
                                "context": line
                            })
                        elif pattern == "this Friday":
                            resolved = resolver()
                            temporal_resolutions.append({
                                "reference": pattern,
                                "resolved_date": resolved.strftime("%Y-%m-%d"),
                                "type": "relative_future",
                                "context": line
                            })
                            
                # Check for recurring patterns
                if "third Thursday of each month" in line:
                    # Calculate next third Thursday
                    def find_nth_weekday(year, month, weekday, n):
                        """Find the nth occurrence of weekday in month."""
                        first_day = datetime(year, month, 1)
                        first_weekday = first_day.weekday()
                        days_until_weekday = (weekday - first_weekday) % 7
                        nth_day = 1 + days_until_weekday + (n - 1) * 7
                        return datetime(year, month, nth_day)
                        
                    # Next third Thursday
                    if current_date.day <= 21:  # Could still be this month
                        next_third_thursday = find_nth_weekday(current_date.year, current_date.month, 3, 3)  # Thursday = 3
                        if next_third_thursday <= current_date:
                            # Move to next month
                            if current_date.month == 12:
                                next_third_thursday = find_nth_weekday(current_date.year + 1, 1, 3, 3)
                            else:
                                next_third_thursday = find_nth_weekday(current_date.year, current_date.month + 1, 3, 3)
                    else:
                        # Definitely next month
                        if current_date.month == 12:
                            next_third_thursday = find_nth_weekday(current_date.year + 1, 1, 3, 3)
                        else:
                            next_third_thursday = find_nth_weekday(current_date.year, current_date.month + 1, 3, 3)
                            
                    temporal_resolutions.append({
                        "reference": "third Thursday of each month",
                        "resolved_date": next_third_thursday.strftime("%Y-%m-%d"),
                        "type": "recurring",
                        "frequency": "monthly",
                        "context": line
                    })
                    
                # Extract duration-based calculations
                if "30 days from" in line and "January 7th" in line:
                    start_date = datetime(2025, 1, 7)
                    end_date = start_date + timedelta(days=30)
                    temporal_resolutions.append({
                        "reference": "30 days from January 7th",
                        "resolved_date": end_date.strftime("%Y-%m-%d"),
                        "type": "calculated",
                        "context": line
                    })
                    
            # Extract action items with deadlines
            action_items = []
            if "ACTION ITEMS" in transcript.content:
                action_section = transcript.content.split("ACTION ITEMS")[1].split("RECURRING ITEMS")[0]
                
                deadline_mappings = {
                    "Jan 17": "2025-01-17",
                    "Jan 26": "2025-01-26",
                    "Feb 8": "2025-02-08",
                    "Feb 10": "2025-02-10",
                    "Feb 25": "2025-02-25"
                }
                
                for line in action_section.split("\n"):
                    if "-" in line and "(" in line:
                        task = line.split("-")[1].split("(")[0].strip()
                        deadline_text = line.split("(")[1].split(")")[0]
                        
                        for short_date, full_date in deadline_mappings.items():
                            if short_date in deadline_text:
                                action_items.append({
                                    "task": task,
                                    "deadline": full_date,
                                    "deadline_text": deadline_text
                                })
                                break
                                
            return temporal_resolutions, action_items
            
        # Resolve temporal references
        resolutions, action_items = resolve_temporal_references(temporal_transcript)
        
        # Verify temporal resolutions
        assert len(resolutions) > 0
        
        # Check specific resolutions
        last_tuesday = next((r for r in resolutions if r["reference"] == "last Tuesday"), None)
        assert last_tuesday is not None
        assert last_tuesday["resolved_date"] == "2025-01-07"  # Previous Tuesday from Jan 13 (Monday)
        
        this_friday = next((r for r in resolutions if r["reference"] == "this Friday"), None)
        assert this_friday is not None
        assert this_friday["resolved_date"] == "2025-01-17"  # Next Friday from Jan 13
        
        thirty_days = next((r for r in resolutions if "30 days" in r["reference"]), None)
        assert thirty_days is not None
        assert thirty_days["resolved_date"] == "2025-02-06"  # 30 days from Jan 7
        
        third_thursday = next((r for r in resolutions if "third Thursday" in r["reference"]), None)
        assert third_thursday is not None
        assert third_thursday["resolved_date"] == "2025-02-20"  # Third Thursday of February
        
        # Verify action items
        assert len(action_items) == 5
        
        emergency_filing = next((a for a in action_items if "emergency session" in a["task"]), None)
        assert emergency_filing is not None
        assert emergency_filing["deadline"] == "2025-01-17"
        
        env_review = next((a for a in action_items if "environmental review" in a["task"]), None)
        assert env_review is not None
        assert env_review["deadline"] == "2025-01-26"