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

# ✅ New: Posted Date Filter
date_filter_map = {
    "All time": None,
    "Last 24 hours": "last_24_hours",
    "Last 3 days": "last_3_days",
    "Last 7 days": "last_week",
    "Last 30 days": "last_month"
}
date_filter_ui = st.sidebar.selectbox("Posted Date", list(date_filter_map.keys()))
date_filter_value = date_filter_map[date_filter_ui]

st.title("🔍 AI Job Matcher (GPT-Ranked, Date Filtered)")

# Resume Upload
uploaded_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])
resume_text = ""

if uploaded_file is not None:
    reader = PdfReader(uploaded_file)
    resume_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    
    if resume_text.strip():
        st.success("✅ Resume uploaded and parsed.")
        st.write("👀 Preview of parsed resume:")
        st.code(resume_text[:500])
    else:
        st.error("❌ Failed to extract text from resume. Try a different PDF.")

# SerpAPI Job Search
@st.cache_data
def search_jobs_serpapi(keywords, location, work_type, date_filter, api_key):
    invalid_locations = ["remote", "usa", "united states", "global"]
    if location.strip().lower() in invalid_locations:
        location = "Detroit, MI"

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_jobs",
        "q": f"{keywords} {work_type}",
        "location": location,
        "api_key": api_key
    }
    if date_filter:
        params["date_posted"] = date_filter

    response = requests.get(url, params=params)

    st.code(f"Request URL: {response.url}")
    st.code(response.text[:1000])

    try:
        data = response.json()
    except:
        st.error("❌ Failed to parse JSON response from SerpAPI.")
        return []

    jobs = []
    for job in data.get("jobs_results", []):
        jobs.append({
            "title": job.get("title"),
            "company": job.get("company_name"),
            "location": job.get("location"),
            "description": job.get("description", "")[:1000],
            "link": job.get("related_links", [{}])[0].get("link", "#")
        })

    return jobs

# ✅ GPT Match Scoring
def score_job_with_gpt(resume_text, job):
    prompt = (
        f"You're a recruiter evaluating a resume for a job opening.\n\n"
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

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    output = response.choices[0].message.content
    try:
        score_line = output.splitlines()[0]
        score = int(score_line.split(":")[1].strip())
    except:
        score = 0

    return score, output

# GPT Resume + Cover Letter Generator
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

# Main Logic
if st.button("🔎 Find Jobs"):
    if not uploaded_file:
        st.warning("Please upload your resume first.")
    elif not openai_api_key or not serpapi_key:
        st.warning("Enter both OpenAI and SerpAPI keys in the sidebar.")
    else:
        openai.api_key = openai_api_key
