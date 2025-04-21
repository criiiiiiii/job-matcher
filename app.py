import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
from PyPDF2 import PdfReader

st.set_page_config(page_title="Job Matcher", layout="centered")

# Sidebar
st.sidebar.title("Settings")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")

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
def search_jobs():
    url = "https://www.indeed.com/jobs?q=director&l=Remote&remotejob=1"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    job_results = []

    for div in soup.find_all("div", class_="cardOutline"):
        title_elem = div.find("h2", class_="jobTitle")
        company_elem = div.find("span", class_="companyName")
        location_elem = div.find("div", class_="companyLocation")
        link_elem = div.find("a", href=True)

        if title_elem and company_elem and location_elem and link_elem:
            job_results.append({
                "title": title_elem.text.strip(),
                "company": company_elem.text.strip(),
                "location": location_elem.text.strip(),
                "link": "https://www.indeed.com" + link_elem["href"]
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
        with st.spinner("Searching and matching jobs..."):
            jobs = search_jobs()
            st.success(f"✅ Found {len(jobs)} jobs.")
            for job in jobs[:5]:
                st.markdown(f"### {job['title']} at {job['company']}")
                st.write(f"📍 {job['location']} | [Job Link]({job['link']})")

                if st.button(f"✍️ Tailor Resume & Cover Letter for {job['title']} ({job['company']})", key=job['link']):
                    result = generate_docs(job, resume_text)
                    st.code(result)

# Footer
st.markdown("---")
st.markdown("Made by [Christian Sodeikat](https://www.linkedin.com/in/christian-sodeikat/)")
# force rebuild - 2025-04-10
