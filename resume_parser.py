import pdfplumber
import re

EXPECTED_FIELDS = [
    'Candidate Name',
    'Total Years of Experience',
    'Skills',
    'Achievements List',
    'Projects List'
]

def extract_text_from_pdf(pdf_file_path):
    text = ""
    try:
        with pdfplumber.open(pdf_file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None
    return text

def merge_multiline_projects(project_lines):
    merged_projects = []
    buffer = ""

    for line in project_lines:
        # Agar line "ProjectName:" ya similar se shuru hoti hai toh naya project start
        if re.match(r'^[A-Za-z0-9].*:', line):
            if buffer:
                merged_projects.append(buffer.strip())
            buffer = line
        else:
            # Continue previous project description
            buffer += " " + line

    if buffer:
        merged_projects.append(buffer.strip())

    return merged_projects

def parse_resume_data(text):
    data = {
        'Candidate Name': "Not found",
        'Total Years of Experience': 0.0,
        'Skills': "",
        'Achievements List': [],
        'Projects List': [],
        'Full_Text': text if text else "",
        'Total_Skills': 0,
        'Total_Achievements': 0,
        'Total_Projects': 0
    }
    if not text:
        return data

    lines = text.split('\n')

    # Candidate Name extraction
    name_match = re.search(r"^([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3})\s*\n", text, re.MULTILINE)
    if not name_match:
        name_match = re.search(r"^([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})(?!.*(?:@|\d{3}))", text, re.MULTILINE)
    if name_match:
        data['Candidate Name'] = name_match.group(1).strip()
    else:
        if lines and lines[0].strip():
            potential_name = lines[0].strip()
            if 1 < len(potential_name.split()) <= 4 and not any(char.isdigit() for char in potential_name) and '@' not in potential_name:
                data['Candidate Name'] = potential_name
            elif len(potential_name.split()) == 1 and potential_name.isalpha() and len(potential_name) > 2:
                data['Candidate Name'] = potential_name

    # Total Years of Experience extraction
    exp_patterns = [
        r"(?:Total|Overall)\s+(?:Years\s+of\s+)?Experience\s*[:-]?\s*(\d{1,2}(?:\.\d{1,2})?)",
        r"(?:Total|Overall)\s+Experience\s*[:-]?\s*(\d{1,2}(?:\.\d{1,2})?)\s*(?:Years?|Yrs)",
        r"(\d{1,2}(?:\.\d{1,2})?)\s*(?:Years?|Yrs)\s+(?:of\s+)?Experience"
    ]
    max_exp = 0.0
    for pattern in exp_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                exp_val = float(match)
                if exp_val > max_exp:
                    max_exp = exp_val
            except ValueError:
                continue
    if max_exp > 0.0:
        data['Total Years of Experience'] = max_exp

    # Skills extraction (improved with start and end keywords logic)
    start_keywords_skills = ['skills', 'technical skills', 'proficiencies', 'expertise', 'technologies', 'tools', 'languages', 'frameworks']
    end_keywords_skills = ['education', 'experience', 'projects', 'achievements', 'awards', 'summary', 'objective']

    skills_lines = []
    collecting_skills = False
    for line in lines:
        clean_line = line.strip()
        lower_line = clean_line.lower()

        if not collecting_skills and any(kw in lower_line for kw in start_keywords_skills):
            collecting_skills = True
            # Agar us line me skill section ke baad kuch likha ho, use capture karo
            after_colon = re.split(r':', clean_line, maxsplit=1)
            if len(after_colon) > 1:
                skills_lines.append(after_colon[1].strip())
            continue

        if collecting_skills:
            if any(kw in lower_line for kw in end_keywords_skills):
                break
            if clean_line:
                skills_lines.append(clean_line)

    skills_text = ' '.join(skills_lines)

    extracted_skills = set()
    # Split by common delimiters and 'and'
    skills = re.split(r'[,;•●▪➢❖⁃*\-–]|\s+and\s+|\n', skills_text)
    for skill in skills:
        skill_cleaned = re.sub(r'[\(\[\{].*?[\)\]\}]', '', skill).strip()
        if skill_cleaned and 2 <= len(skill_cleaned) <= 30 and not skill_cleaned.isdigit() \
           and ':' not in skill_cleaned and skill_cleaned.lower() not in ['etc', 'various', 'other']:
            extracted_skills.add(skill_cleaned.title())

    common_skills = [
        'Python', 'Java', 'JavaScript', 'C++', 'C#', 'Ruby', 'PHP', 'Swift', 'Kotlin', 'Go', 'Scala',
        'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Oracle', 'Redis', 'React', 'Angular', 'Vue.js', 'Node.js',
        'Django', 'Flask', 'Spring', 'ASP.NET', 'HTML', 'CSS', 'AWS', 'Azure', 'Docker', 'Kubernetes'
    ]
    # SEARCH common_skills only in skills_text (fix)
    for skill in common_skills:
        if re.search(rf'\b{re.escape(skill)}\b', skills_text, re.IGNORECASE):
            extracted_skills.add(skill.title())

    if extracted_skills:
        data['Skills'] = ", ".join(sorted(extracted_skills))
        data['Total_Skills'] = len(extracted_skills)

    # Achievements List extraction
    start_keywords_ach = ['achievements', 'awards', 'accomplishments', 'recognition', 'achieved', 'won', 'delivered', 'improved', 'increased', 'reduced', 'led', 'optimized', 'completed', 'received', 'certifications', 'certified']
    end_keywords_ach = [
        'project', 'projects', 'name', 'email', 'portfolio', 'skills', 'education',
        'work experience', 'experience', 'summary', 'objective', 'contact',
        'soft skills', 'technical skills', 'non-technical skills', 'hard skills',
        'expected salary', 'personal information', 'hobbies', 'interests', 'references',
        'certifications'
    ]

    achievement_lines = []
    collecting = False

    for line in lines:
        clean_line = line.strip()
        lower_line = clean_line.lower()

        if not collecting and any(kw in lower_line for kw in start_keywords_ach):
            collecting = True
            # Handle inline entries after colon or dash
            inline_items = re.split(r'[-•●▪➢❖⁃*]', clean_line)
            for item in inline_items[1:]:
                item = item.strip()
                if item and not any(kw in item.lower() for kw in end_keywords_ach) and not re.match(r'^[-]+$', item):
                    achievement_lines.append(item)
            continue

        if collecting:
            if not clean_line or re.match(r'^[-]+$', clean_line):
                continue
            if any(kw in lower_line for kw in end_keywords_ach):
                break
            achievement_lines.append(clean_line)

    data['Achievements List'] = achievement_lines
    data['Total_Achievements'] = len(achievement_lines)

    # Projects List extraction
    start_keywords_proj = ['projects', 'key projects', 'portfolio', 'project experience', 'selected projects']
    end_keywords_proj = [
        'achievements', 'awards', 'name', 'email', 'skills', 'education',
        'work experience', 'experience', 'summary', 'objective', 'contact',
        'soft skills', 'technical skills', 'non-technical skills', 'hard skills',
        'expected salary', 'personal information', 'hobbies', 'interests', 'references',
        'certifications'
    ]

    project_lines = []
    collecting_proj = False

    for line in lines:
        clean_line = line.strip()
        lower_line = clean_line.lower()

        if not collecting_proj and any(kw in lower_line for kw in start_keywords_proj):
            collecting_proj = True
            continue

        if collecting_proj:
            if not clean_line or re.match(r'^[-]+$', clean_line):
                continue
            if any(kw in lower_line for kw in end_keywords_proj):
                break
            project_lines.append(clean_line)

    # Merge multiline projects properly
    data['Projects List'] = merge_multiline_projects(project_lines)
    data['Total_Projects'] = len(data['Projects List'])

    return data
