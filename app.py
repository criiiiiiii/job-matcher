import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
from io import BytesIO
import base64
from PyPDF2 import PdfReader

# -------------------------------
# Sidebar: OpenAI API Key
# -------------------------------
st.sidebar.title("🔑 Configuration")
openai_api_key = st.sidebar.text_input("Enter your OpenAI API key", type="password")

# -------------------------------
# App Title
# -------------------------------
st.title("🔍 AI-Powered Job Matcher")
st.write("Upload your resume, search for roles, and auto-generate tailored resumes & cover letters.")

# -------------------------------
# Resume Upload
# -------------------------------
uploaded_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])
resume_text = ""

if uploaded_file is not None:
    reader = PdfReader(uploaded_file)
    resume_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

    if resume_text.strip():
        st.success("✅ Resume uploaded and parsed.")
        st.write("👀 Preview of parsed resume:")
        st.code(resume_text[:500])  # show first 500 characters
    else:
        st.error("❌ Failed to extract text from your resume. Try a different PDF or use a text-based one.")

# -------------------------------
# Job Search Logic (Indeed Scraper)
# -------------------------------
@st.cache_data(show_spinner=False)
def search_jobs(query="Director", location="Remote"):
    url = f"https://www.indeed.com/jobs?q={query.replace(' ', '+')}&l={location}&remotejob=1"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    jobs = []

    for div in soup.find_all(name="div", attrs={"class": "cardOutline"}):
        title_elem = div.find("h2", {"class": "jobTitle"})
        company_elem = div.find("span", {"class": "companyName"})
        location_elem = div.find("div", {"class": "companyLocation"})
        link_elem = div.find("a", href=True)

        if title_elem and company_elem and location_elem and link_elem:
            jobs.append({
                "title": title_elem.text.strip(),
                "company": company_elem.text.strip(),
                "location": location_elem.text.strip(),
                "link": "https://www.indeed.com" + link_elem["href"]
            })

    return jobs

# -------------------------------
# Relevance Scoring (Simple Matching)
# -------------------------------
def score_job(job, resume_text):
    score = 0
    title_keywords = ["director", "vp", "head", "senior"]
    industry_keywords = ["mobility", "automotive", "ev", "strategy", "transformation"]

    job_text = (job['title'] + " " + job['company']).lower()

    score += sum(1 for word in title_keywords if word in job_text)
    score += sum(1 for word in industry_keywords if word in job_text)
    score += sum(1 for word in industry_keywords if word in resume_text.lower())

    return score

# -------------------------------
# GPT Resume & Cover Letter
# -------------------------------
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

# -------------------------------
# Run Job Search
# -------------------------------
if st.button("🔎 Find Jobs"):
    if not uploaded_file:
        st.warning("Please upload your resume first.")
    elif not openai_api_key:
        st.warning("Enter your OpenAI API key in the sidebar.")
    else:
        openai.api_key = openai_api_key
        with st.spinner("Searching jobs and scoring relevance..."):
            jobs = search_jobs()
            for job in jobs:
                job["score"] = score_job(job, resume_text)

            jobs = sorted(jobs, key=lambda x: x["score"], reverse=True)

            for job in jobs[:10]:
                st.markdown(f"### {job['title']} at {job['company']}")
                st.write(f"📍 {job['location']} | 🔗 [Job Link]({job['link']})")
                st.write(f"**Relevance Score:** {job['score']}")

                if st.button(f"✍️ Tailor Resume & Cover Letter for {job['title']} at {job['company']}", key=job['link']):
                    with st.spinner("Generating..."):
                        result = generate_docs(job, resume_text)
                        st.code(result)

# -------------------------------
# Footer
# -------------------------------
st.markdown("---")
st.markdown("Made by [Christian Sodeikat](https://www.linkedin.com/in/christian-sodeikat/)")
