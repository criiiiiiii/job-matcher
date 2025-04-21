import streamlit as st
import requests
import openai
from PyPDF2 import PdfReader

st.set_page_config(page_title="Job Matcher", layout="centered")

# Sidebar
st.sidebar.title("Settings")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
serpapi_key = st.sidebar.text_input("SerpAPI Key", type="password")

work_type = st.sidebar.radio("Work Type", ["Remote", "Hybrid", "In-Office", "All"], index=0)
search_keywords = st.sidebar.text_input("Search Keywords", value="director mobility")
search_location = st.sidebar.text_input("Location", value="Remote")

date_filter_map = {
    "All time": None,
    "Last 24 hours": "last_24_hours",
    "Last 3 days": "last_3_days",
    "Last 7 days": "last_week",
    "Last 30 days": "last_month"
}
date_filter_ui = st.sidebar.selectbox("Posted Date", list(date_filter_map.keys()))
date_filter_value = date_filter_map[date_filter_ui]

st.title("🔍 AI Job Matcher (GPT Scored + Date Filter)")

# Resume Upload
uploaded_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])
resume_text = ""

if uploaded_file is not None:
    reader = PdfReader(uploaded_file)
    resume_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    
    if resume_text.strip():
        st.success("✅ Resume uploaded and parsed.")
        st.code(resume_text[:500])
    else:
        st.error("❌ Resume parsing failed.")

@st.cache_data
def search_jobs_serpapi(keywords, location, work_type, date_filter, api_key):
    invalid_locations = ["remote", "usa", "united states", "global"]
    if location.strip().lower() in invalid_locations:
        location = "Detroit, MI"

    params = {
        "engine": "google_jobs",
        "q": f"{keywords} {work_type}",
        "location": location,
        "api_key": api_key
    }
    if date_filter:
        params["date_posted"] = date_filter

    url = "https://serpapi.com/search.json"
    response = requests.get(url, params=params)
    st.code(f"Request URL: {response.url}")
    try:
        data = response.json()
        return data.get("jobs_results", [])
    except Exception as e:
        st.error("❌ SerpAPI error: " + str(e))
        return []

def score_job_with_gpt(resume_text, job):
    prompt = (
        f"You are a recruiter evaluating a resume for a job opening.\n\n"
        f"Resume:\n{resume_text}\n\n"
        f"Job Title: {job['title']}\n"
        f"Company: {job['company']}\n"
        f"Location: {job['location']}\n"
        f"Description:\n{job['description']}\n\n"
        f"Rate the resume's fit for this role from 1 to 100.\n"
        f"Then briefly explain the score in 1-2 sentences.\n\n"
        f"Respond in this format:\n"
        f"Score: [number]\nReason: [explanation]"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        output = response.choices[0].message.content.strip()
        st.caption(f"🧠 GPT Output:\n{output}")  # debug
        lines = output.splitlines()
        score_line = next((line for line in lines if "score" in line.lower()), "")
        score = int(''.join([c for c in score_line if c.isdigit()]))
        explanation = next((line for line in lines if "reason" in line.lower()), output)
        return score, explanation
    except Exception as e:
        return 0, f"GPT Error: {e}"

def generate_docs(job, resume_text):
    prompt = (
        f"You are a resume writer.\n\n"
        f"Here is the resume:\n---\n{resume_text}\n---\n\n"
        f"And the job posting:\n---\n"
        f"Title: {job['title']}\n"
        f"Company: {job['company']}\n"
        f"Location: {job['location']}\n"
        f"Description: {job['description']}\n"
        f"Link: {job['link']}\n"
        f"---\n\n"
        f"Write a tailored cover letter and bullet points for the resume to match this job."
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return response.choices[0].message.content

if st.button("🔎 Find Jobs"):
    if not uploaded_file or not resume_text.strip():
        st.warning("Please upload and parse your resume first.")
    elif not openai_api_key or not serpapi_key:
        st.warning("Enter both OpenAI and SerpAPI keys.")
    else:
        openai.api_key = openai_api_key
        with st.spinner("Searching jobs and ranking them..."):
            jobs = search_jobs_serpapi(
                search_keywords, search_location, work_type, date_filter_value, serpapi_key
            )

            if not jobs:
                st.error("❌ No jobs found. Try a broader filter.")
            else:
                scored_jobs = []
                for i, job in enumerate(jobs[:10]):
                    job_info = {
                        "title": job.get("title"),
                        "company": job.get("company_name"),
                        "location": job.get("location"),
                        "description": job.get("description", ""),
                        "link": job.get("related_links", [{}])[0].get("link", "#")
                    }
                    score, reason = score_job_with_gpt(resume_text, job_info)
                    job_info.update({"score": score, "reason": reason})
                    scored_jobs.append(job_info)

                scored_jobs = sorted(scored_jobs, key=lambda x: x["score"], reverse=True)
                st.success(f"✅ Found {len(scored_jobs)} jobs (sorted by match score)")

                for i, job in enumerate(scored_jobs):
                    st.markdown(f"### {job['title']} at {job['company']}")
                    st.write(f"📍 {job['location']} | 🔗 [Job Link]({job['link']})")
                    st.write(f"📝 {job['description'][:300]}...")
                    st.write(f"**Match Score:** {job['score']}/100")
                    st.caption(f"💬 {job['reason']}")
                    if st.button(f"✍️ Tailor Resume & Cover Letter #{i+1}", key=f"button_{i}"):
                        result = generate_docs(job, resume_text)
                        st.code(result)

# Footer
st.markdown("---")
st.markdown("Made by [Christian Sodeikat](https://www.linkedin.com/in/christian-sodeikat/)")

