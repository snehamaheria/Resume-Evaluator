import streamlit as st
import pandas as pd
import re
from resume_parser import extract_text_from_pdf, parse_resume_data

# --- Light Theme Background ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .gradient-text {
        background: -webkit-linear-gradient(45deg, #09009f, #00ff95 80%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    .stExpander {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        padding: 15px;
        margin-bottom: 15px;
    }
    .stButton>button {
        transition: all 0.3s ease;
        background: linear-gradient(45deg, #4b6cb7, #182848);
        color: white !important;
        border: none;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
    .stFileUploader>div {
        border: 2px dashed #4b6cb7;
        border-radius: 10px;
        padding: 20px;
        background-color: rgba(255,255,255,0.7);
    }
    .skill-chip {
        display: inline-block;
        padding: 2px 8px;
        background: linear-gradient(45deg, #a1c4fd, #c2e9fb);
        border-radius: 16px;
        margin: 2px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- Title ---
st.markdown("<h1 class='gradient-text'>📝 Resume Evaluator</h1>", unsafe_allow_html=True)

# --- Instructions ---
with st.expander("📌 Instructions & Supported Resume Format", expanded=False):
    st.markdown("""
    <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px;'>
        <h4 style='color: #2c3e50;'>📋 Important Notes:</h4>
        <ul style='color: #34495e;'>
            <li>This tool works best with resumes in <strong>English</strong>, and in <strong>structured formats</strong></li>
            <li>PDF files only. Scanned images or pictures won't be parsed correctly</li>
            <li>Ideal resume structure for best results:
                <ul>
                    <li><strong>Name</strong> should be at the top, preferably as the first line</li>
                    <li>Include clearly labeled sections like: <code>Skills</code>, <code>Work Experience</code>, etc.</li>
                </ul>
            </li>
            <li>Avoid heavily designed formats (e.g. tables, multiple columns, graphics)</li>
            <li>For testing we have provided 5 resumes zip files that you can download and test our app.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Sample resumes download button inside instructions
    with open("sample_resumes.zip", "rb") as f:
        zip_bytes = f.read()
    st.download_button(
        label="📥 Download Sample Resumes",
        data=zip_bytes,
        file_name="sample_resumes.zip",
        mime="application/zip",
        help="Download sample resumes for testing"
    )

# --- Input section ---
with st.container():
    st.markdown("### 🎯 Job Requirements")
    col1, col2 = st.columns(2)

    with col1:
        job_title = st.text_input("*Enter Job Title:*",
                                  placeholder="e.g. Senior Python Developer")
        skills_input = st.text_input("*Enter Required Skills:*",
                                     placeholder="Python, Java, SQL")

    with col2:
        experience_choice = st.selectbox("*Select Minimum Experience Required:*",
                                         ["All", "Minimum 1 Year", "Minimum 3 Years", "Minimum 5 Years"],
                                         index=2)
        expected_salary = st.text_input("*Enter Expected Salary (Optional):*",
                                        placeholder="e.g. $80,000")

user_skills = [skill.strip().title() for skill in skills_input.split(",") if skill.strip()]

# --- File uploader ---
st.markdown("### 📤 Upload Resumes")
uploaded_files = st.file_uploader("",
                                  type=["pdf"],
                                  accept_multiple_files=True)

# --- Submit button ---
submit_btn = st.button("🚀 Evaluate Resumes")

# --- Process resumes ---
if submit_btn:
    if not uploaded_files:
        st.warning("⚠️ Please upload at least one resume.")
    elif not job_title:
        st.warning("⚠️ Please enter Job Title.")
    elif not user_skills:
        st.warning("⚠️ Please enter at least one required skill.")
    else:
        with st.spinner('🔍 Processing resumes...'):
            resume_data_list = []
            for file in uploaded_files:
                text = extract_text_from_pdf(file)
                parsed_data = parse_resume_data(text)
                parsed_data['file_name'] = file.name
                resume_data_list.append(parsed_data)

        filtered_resumes = []
        for data in resume_data_list:
            exp_years = float(data['Total Years of Experience'])
            exp_ok = (
                (experience_choice == "All") or
                (experience_choice == "Minimum 1 Year" and exp_years >= 1.0) or
                (experience_choice == "Minimum 3 Years" and exp_years >= 3.0) or
                (experience_choice == "Minimum 5 Years" and exp_years >= 5.0)
            )
            if not exp_ok:
                continue

            candidate_skills = [s.strip().lower() for s in data['Skills'].split(",")]
            user_skills_lower = [s.lower() for s in user_skills]
            matched_skills = [s for s in candidate_skills if s in user_skills_lower]
            skills_matched = len(matched_skills)

            salary_ok = True
            if expected_salary:
                salary_pattern = re.compile(rf"(?i).{re.escape(expected_salary)}.")
                if not salary_pattern.search(data['Full_Text']):
                    salary_ok = False
            if not salary_ok:
                continue

            score = (
                min(exp_years * 2.0, 10.0) +
                (skills_matched * 3.0) +
                (len(data['Projects List']) * 1.5) +
                (len(data['Achievements List']) * 1.5)
            )
            data['Rank_Score'] = round(score, 2)
            data['Skills Matched'] = skills_matched
            filtered_resumes.append(data)

        filtered_resumes.sort(key=lambda x: x['Rank_Score'], reverse=True)

        if filtered_resumes:
            st.markdown(f"<h2 style='text-align: center;'>📊 Ranked Resumes for <span style='color: #4b6cb7;'>{job_title}</span></h2>",
                        unsafe_allow_html=True)

            table_data = []
            for idx, item in enumerate(filtered_resumes, 1):
                table_data.append({
                    " ": idx,
                    "Candidate": item['Candidate Name'],
                    "Exp (Yrs)": round(float(item['Total Years of Experience']), 1),
                    "Skills Match": f"{item['Skills Matched']}/{len(user_skills)}",
                    "Skills": ", ".join(item['Skills'].split(",")[:5]),
                    "Projects": len(item['Projects List']),
                    "Achievements": len(item['Achievements List']),
                    "Resume": item['file_name']
                })

            df = pd.DataFrame(table_data)


            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Ranked Results CSV", data=csv,
                               file_name=f"{job_title.replace(' ', '_')}_ranked_results.csv",
                               mime='text/csv')

            st.markdown("### 📑 Detailed Resume Information")
            for item in filtered_resumes:
                with st.expander(f"👤 {item['Candidate Name']} - Score: {item['Rank_Score']} - {item['file_name']}"):
                    st.markdown(f"*⭐ Rank Score:* {item['Rank_Score']}")
                    st.markdown(f"*⏳ Experience:* {item['Total Years of Experience']} years")
                    st.markdown(f"*✅ Skills Matched:* {item['Skills Matched']}/{len(user_skills)}")
                    st.markdown(f"*📋 Projects:* {len(item['Projects List'])}")
                    st.markdown(f"*🏆 Achievements:* {len(item['Achievements List'])}")

                    skills_html = " ".join([f"<span class='skill-chip'>{s.strip()}</span>" for s in item['Skills'].split(",")])
                    st.markdown("*🔧 Skills:*")
                    st.markdown(skills_html, unsafe_allow_html=True)
        else:
            st.error("❌ No resumes matched the given criteria. Try adjusting your filters.")

# --- Footer ---
st.markdown("---")
st.markdown("""
<div class='footer' style='text-align: center; color: #666; font-size: 14px;'>
    Built with ❤️ using 
    <span style='background: linear-gradient(45deg, #4b6cb7, #182848); color: white; padding: 4px 8px; border-radius: 4px;'>
        <strong>ResumeEvaluator AI</strong> 🚀
    </span>
    <br>
    <small>For best results, use structured resumes in PDF format</small>
</div>
""", unsafe_allow_html=True)
