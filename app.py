import streamlit as st
import requests
import openai
from PyPDF2 import PdfReader

st.set_page_config(page_title="Job Matcher", layout="centered")

# Sidebar: Keys and Filters
st.sidebar.title("Settings")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
serpapi_key = st.sidebar.text_input("SerpAPI Key", type="password")

work_type = st.sidebar.radio("Work Type", ["Remote", "Hybrid", "In-Office", "All"], index=0)
search_keywords = st.sidebar.text_input("Search Keywords", value="director mobility")
search_location = st.sidebar.text_input("Location", value="Remote")

# Posted date filter
date_filter_map = {
    "All time": None,
    "Last 24 hours": "last_24_hours",
    "Last 3 days": "last_3_days",
    "Last 7 days": "last_week",
    "Last 30 days": "last_month"
}
date_filter_ui = st.sidebar.selectbox("Posted Date", list(date_filter_map.keys()))
date_filter_value = date_filter_map[date_filter_ui]

# Job count toggle
job_count = st.sidebar.selectbox("Number of Jobs to Show", [10, 20, 30], index=0)

# Industry/field exclusions
all_exclusions = [
    "Education", "Finance", "Healthcare", "Insurance", "Government", "Legal", "Retail",
    "Nonprofit", "Accounting", "Human Resources", "Banking", "Real Estate", "Hospitality",
    "Construction", "Customer Service", "Media", "Marketing", "Sales", "Clerical",
    "Administration", "Religious", "Food Services", "Social Services", "Arts", "Public Sector",
    "Transportation", "Call Center"
]
excluded_fields = st.sidebar.multiselect("Exclude Industries/Fields", all_exclusions)

st.title("🔍 AI Job Matcher (GPT Scored + Salary Estimation + Filters)")

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

def should_exclude(job, exclusions):
    text = f"{job.get('title', '')} {job.get('company_name', '')} {job.get('description', '')}".lower()
    for word in exclusions:
        if word.lower() in text:
            return True
    return False

def score_job_with_gpt(client, resume_text, job):
    prompt = (
        f"You're evaluating a resume for this job:\n"
        f"Resume:\n{resume_text}\n\n"
        f"Job:\nTitle: {job['title']}\nCompany: {job['company']}\nLocation: {job['location']}\nDescription:\n{job['description']}\n\n"
        f"Rate fit from 1 to 100. Format:\nScore: [number]\nReason: [why]"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        output = response.choices[0].message.content.strip()
        lines = output.splitlines()
        score_line = next((l for l in lines if "score" in l.lower()), "")
        score = int(''.join(c for c in score_line if c.isdigit()))
        reason = next((l for l in lines if "reason" in l.lower()), output)
        return score, reason
    except Exception as e:
        return 0, f"GPT scoring error: {e}"

def estimate_salary_with_gpt(client, title, location):
    prompt = (
        f"Estimate a realistic salary range for this job in the U.S.:\n"
        f"Title: {title}\nLocation: {location}\nFormat:\nEstimated Salary: $X–$Y"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Salary estimate error: {e}"

def generate_docs(client, job, resume_text):
    prompt = (
        f"You are a resume writer.\nResume:\n---\n{resume_text}\n---\n\n"
        f"Job Posting:\n---\nTitle: {job['title']}\nCompany: {job['company']}\n"
        f"Location: {job['location']}\nDescription: {job['description']}\nLink: {job['link']}\n---\n\n"
        f"Write a tailored cover letter and bullet points for this job."
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()

if st.button("🔎 Find Jobs"):
    if not uploaded_file or not resume_text.strip():
        st.warning("Upload your resume first.")
    elif not openai_api_key or not serpapi_key:
        st.warning("Add both API keys.")
    else:
        client = openai.OpenAI(api_key=openai_api_key)

        with st.spinner("Searching + scoring + estimating salaries..."):
            jobs = search_jobs_serpapi(
                search_keywords, search_location, work_type, date_filter_value, serpapi_key
            )

            if not jobs:
                st.error("No jobs found.")
            else:
                results = []
                for i, job in enumerate(jobs):
                    if len(results) >= job_count:
                        break
                    if should_exclude(job, excluded_fields):
                        continue

                    job_info = {
                        "title": job.get("title"),
                        "company": job.get("company_name"),
                        "location": job.get("location"),
                        "description": job.get("description", ""),
                        "link": job.get("job_google_link", job.get("related_links", [{}])[0].get("link", "#")),
                        "salary": job.get("detected_extensions", {}).get("salary", None)
                    }

                    score, reason = score_job_with_gpt(client, resume_text, job_info)

                    if not job_info["salary"]:
                        job_info["salary"] = estimate_salary_with_gpt(
                            client, job_info["title"], job_info["location"]
                        )

                    job_info.update({"score": score, "reason": reason})
                    results.append(job_info)

                results = sorted(results, key=lambda x: x["score"], reverse=True)
                st.success(f"✅ Showing {len(results)} jobs, sorted by best match")

                for i, job in enumerate(results):
                    st.markdown(f"### {job['title']} at {job['company']}")
                    st.write(f"📍 {job['location']}")
                    st.write(f"💰 {job['salary']}")
                    st.markdown(f"[🔗 View Job Posting]({job['link']})", unsafe_allow_html=True)
                    st.write(f"📝 {job['description'][:300]}...")
                    st.write(f"**Match Score:** {job['score']}/100")
                    st.caption(f"💬 {job['reason']}")

                    if st.button(f"✍️ Tailor Resume & Cover Letter #{i+1}", key=f"tailor_button_{i}"):
                        result = generate_docs(client, job, resume_text)
                        st.code(result)

# Footer
st.markdown("---")
st.markdown("Made by [Christian Sodeikat](https://www.linkedin.com/in/christian-sodeikat/)")
