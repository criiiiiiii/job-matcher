import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
from PyPDF2 import PdfReader

st.set_page_config(page_title="Job Matcher", layout="centered")

# Sidebar
st.sidebar.title("Settings")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")

work_type = st.sidebar.radio("Work Type", ["Remote", "Hybrid", "In-Office", "All"], index=0)
search_keywords = st.sidebar.text_input("Search Keywords", value="director mobility")
search_location = st.sidebar.text_input("Location", value="USA")

st.title("🔍 AI Job Matcher (Google Jobs Version)")

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

# Job Search via Google
@st.cache_data
def search_google_jobs(keywords, location, work_type):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    query = f"{keywords} jobs {location} site:linkedin.com/jobs OR site:indeed.com OR site:lever.co"
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    job_results = []

    for g_card in soup.select("div.g"):
        title_elem = g_card.select_one("h3")
        link_elem = g_card.select_one("a")
        desc_elem = g_card.select_one("div.VwiC3b")

        if title_elem and link_elem:
            job = {
                "title": title_elem.get_text(),
                "link": link_elem['href'],
                "description": desc_elem.get_text() if desc_elem else "No description provided"
            }

            # Basic filtering based on work type keyword match
            if work_type == "Remote" and "remote" not in job["description"].lower():
                continue
            elif work_type == "Hybrid" and "hybrid" not in job["description"].lower():
                continue
            elif work_type == "In-Office" and ("remote" in job["description"].lower() or "hybrid" in job["description"].lower()):
                continue

            job_results.append(job)

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
Link: {job['link']}
Description: {job['description']}
---

Generate a tailored cover letter and suggested resume bullet points that match this job.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return response.choices[0].message.content

# Main Button
if st.button("🔎 Find Jobs"):
    if not uploaded_file:
        st.warning("Please upload your resume first.")
    elif not openai_api_key:
        st.warning("Enter your OpenAI API key in the sidebar.")
    else:
        openai.api_key = openai_api_key
        with st.spinner("Searching Google for jobs..."):
            jobs = search_google_jobs(search_keywords, search_location, work_type)
            st.success(f"✅ Found {len(jobs)} jobs.")
            if len(jobs) == 0:
                st.info("
