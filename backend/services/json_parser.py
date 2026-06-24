import json
import uuid
from typing import List, Tuple, Dict, Any

def parse_json_document(json_content: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    data = json.loads(json_content)
    
    sections = []
    footnotes = []
    sort_order = 0

    def process_section(sec_data: Dict[str, Any], context: Dict[str, Any]):
        nonlocal sort_order
        section_id = str(uuid.uuid4())
        
        # Determine start and end page
        start_page = sec_data.get("start_page") or sec_data.get("page_number")
        end_page = sec_data.get("end_page") or start_page

        sec_row = {
            "id": section_id,
            "chapter_code": context.get("chapter_code"),
            "chapter_heading": context.get("chapter_heading"),
            "part_code": context.get("part_code"),
            "part_heading": context.get("part_heading"),
            "division_code": context.get("division_code"),
            "division_heading": context.get("division_heading"),
            "section_code": str(sec_data.get("code", "")),
            "section_heading": sec_data.get("heading", ""),
            "start_page": start_page,
            "end_page": end_page,
            "html_content": sec_data.get("html", ""),
            "plain_text": sec_data.get("plain_text", ""),
            "sort_order": sort_order,
            "review_status": "pending"
        }
        sections.append(sec_row)
        sort_order += 1

        # Process footnotes
        sec_footnotes = sec_data.get("footnotes", [])
        for fn in sec_footnotes:
            fn_id = str(uuid.uuid4())
            footnotes.append({
                "id": fn_id,
                "section_id": section_id,
                "marker": fn.get("marker", ""),
                "page": fn.get("page") or start_page,
                "text": fn.get("text", ""),
                "review_status": "pending"
            })

    # Walk chapters
    for ch in data.get("chapters", []):
        ch_context = {
            "chapter_code": ch.get("code"),
            "chapter_heading": ch.get("heading"),
            "part_code": None,
            "part_heading": None,
            "division_code": None,
            "division_heading": None,
        }
        
        # Process sections directly in chapter
        for sec in ch.get("sections", []):
            process_section(sec, ch_context)
            
        # Process parts in chapter
        for part in ch.get("parts", []):
            part_context = ch_context.copy()
            part_context["part_code"] = part.get("code")
            part_context["part_heading"] = part.get("heading")
            
            # Process sections directly in part
            for sec in part.get("sections", []):
                process_section(sec, part_context)
                
            # Process divisions in part
            for div in part.get("divisions", []):
                div_context = part_context.copy()
                div_context["division_code"] = div.get("code")
                div_context["division_heading"] = div.get("heading")
                
                for sec in div.get("sections", []):
                    process_section(sec, div_context)
                    
        # Process divisions directly in chapter
        for div in ch.get("divisions", []):
            div_context = ch_context.copy()
            div_context["division_code"] = div.get("code")
            div_context["division_heading"] = div.get("heading")
            
            for sec in div.get("sections", []):
                process_section(sec, div_context)

    # Walk schedules
    for sch in data.get("schedules", []):
        sch_context = {
            "chapter_code": sch.get("code"),
            "chapter_heading": sch.get("heading"),
            "part_code": None,
            "part_heading": None,
            "division_code": None,
            "division_heading": None,
        }
        
        # Process sections directly in schedule
        for sec in sch.get("sections", []):
            process_section(sec, sch_context)
            
        # Process parts in schedule
        for part in sch.get("parts", []):
            part_context = sch_context.copy()
            part_context["part_code"] = part.get("code")
            part_context["part_heading"] = part.get("heading")
            
            # Process sections directly in part
            for sec in part.get("sections", []):
                process_section(sec, part_context)
                
            # Process divisions in part
            for div in part.get("divisions", []):
                div_context = part_context.copy()
                div_context["division_code"] = div.get("code")
                div_context["division_heading"] = div.get("heading")
                
                for sec in div.get("sections", []):
                    process_section(sec, div_context)
                    
        # Process divisions directly in schedule
        for div in sch.get("divisions", []):
            div_context = sch_context.copy()
            div_context["division_code"] = div.get("code")
            div_context["division_heading"] = div.get("heading")
            
            for sec in div.get("sections", []):
                process_section(sec, div_context)

    return sections, footnotes
