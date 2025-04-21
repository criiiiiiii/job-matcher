import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
from PyPDF2 import PdfReader

st.set_page_config(page_title="Job Matcher", layout="centered")

# Sidebar: OpenAI Key + Filters
st.sidebar.title("Settings")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")

# Work type selector
work_type = st.sidebar.radio(
    "Work Type",
    ["Remote", "Hybrid", "In-Office", "All"],
    index=0
)

# New: Search Filters
search_keywords = st.sidebar.text_input("Search Keywords", value="director")
search_location = st.sidebar.text_input("Location", value="Remote")

# Title
st.title("🔍 AI Job Matcher")

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

# Job Search Function
@st.cache_data
def search_jobs(keywords, location, work_type):
    headers = {"User-Agent": "Mozilla/5.0"}

    query = f"{keywords}"
    if work_type == "Hybrid":
        query += "+hybrid"
    elif work_type == "In-Office":
        query += "+\"on site\""

    url = f"https://www.indeed.com/jobs?q={query.replace(' ', '+')}&l={location.replace(' ', '+')}"
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    job_results = []

    for job_card in soup.select("a.tapItem"):
        title = job_card.select_one("h2.jobTitle")
        company = job_card.select_one("span.companyName")
        location = job_card.select_one("div.companyLocation")

        if title and company and location:
            job_results.append({
                "title": title.text.strip(),
                "company": company.text.strip(),
                "location": location.text.strip(),
                "link": "https://www.indeed.com" + job_card["href"]
            })

    return job_results

# GPT Generator
def generate_docs(job, resume_text):
    prompt = f"""
You are a career coach and resume writer.

Given this resume:
---
{resume_text}
---

And this job:
---
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
Link: {job['link']}
---

Generate a tailored cover letter and suggested resume bullet points that match this job.
"""

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
    elif not openai_api_key:
        st.warning("Enter your OpenAI API key in the sidebar.")
    else:
        openai.api_key = openai_api_key
        with st.spinner(f"Searching {work_type.lower()} jobs for '{search_keywords}' in {search_location}..."):
            jobs = search_jobs(search_keywords, search_location, work_type)
            st.success(f"✅
