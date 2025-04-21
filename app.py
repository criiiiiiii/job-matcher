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
search_location = st.sidebar.text_input("Location", value="USA")

st.title("🔍 AI Job Matcher (Powered by SerpAPI)")

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
def search_jobs_serpapi(keywords, location, work_type, api_key):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_jobs",
        "q": f"{keywords} {work_type}",
        "location": location,
        "api_key": api_key
    }

    response = requests.get(url, params=params)
    data = response.json()

    jobs = []
    for job in data.get("jobs_results", []):
        jobs.append({
            "title": job.get("title"),
            "company": job.get("company_name"),
            "location": job.get("location"),
            "description": job.get("description", "")[:500],
            "link": job.get("related_links", [{}])[0].get("link", job.get("job_highlights", [{}])[0].get("link", "#"))
        })

    return jobs

# GPT Generator
def generate_docs(job, resume_text):
    prompt = (
        f"You are a career coach and resume writer.\n\n"
        f"Given this resume:\n---\n{resume_text}\n---\n\n"
        f"And this job:\n---\n"
        f"Title: {job['title']}\n"
        f"Company: {job['company']}\n"
        f"Location: {job['location']}\n"
        f"Description: {job['description']}\n"
        f"Link: {job['link']}\n"
        f"---\n\n"
        f"Generate a tailored cover letter and suggested resume bullet points that match this job."
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
        with st.spinner("Searching jobs using SerpAPI..."):
            jobs = search_jobs_serpapi(search_keywords, search_location, work_type, serpapi_key)
            st.success(f"✅ Found {len(jobs)} jobs.")
            if len(jobs) == 0:
                st.info("Try a different keyword, location, or work type.")
            for i, job in enumerate(jobs[:5]):
                st.markdown(f"### {job['title']} at {job['company']}")
                st.write(f"📍 {job['location']}")
                st.write(f"🔗 [Job Link]({job['link']})")
                st.write(f"📝 {job['description']}...")

                if st.button(f"✍️ Tailor Resume & Cover Letter #{i+1}", key=job['link']):
                    result = generate_docs(job, resume_text)
                    st.code(result)

# Footer
st.markdown("---")
st.markdown("Made by [Christian Sodeikat](https://www.linkedin.com/in/christian-sodeikat/)")
