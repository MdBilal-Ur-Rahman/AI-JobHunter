import os

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI


from app.tools.job_search_tool import (
    JobAgentContext,
    search_jobs,
)


# =========================================================
# GEMINI MODEL
# =========================================================

model = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    temperature=0,
    google_api_key=os.getenv("GEMINI_API_KEY")
)


# =========================================================
# JOB SEARCH AGENT
# =========================================================

job_agent = create_agent(
    model=model,
    tools=[
        search_jobs
    ],
    context_schema=JobAgentContext,
    system_prompt="""
You are an AI job search assistant.

Your job is to help the user search for relevant jobs using the available job search tool.

IMPORTANT:
You are NOT limited to any specific job domain, technology, role, or industry.

Examples of valid job searches include:
- MERN Developer
- Python Developer
- Java Developer
- Data Analyst
- Data Scientist
- DevOps Engineer
- Machine Learning Engineer
- UI/UX Designer
- Product Manager
- Business Analyst
- Any other legitimate job role requested by the user

Rules:

1. Understand the user's requested job role or domain from their message.

2. Understand the user's requested location from their message.

3. Do not assume that the job domain is MERN, software development, or any other specific domain unless the user says so.

4. Use the search_jobs tool when the user asks to search for jobs.

5. Convert the user's request into job preferences for the tool.

6. Pass job_titles and locations to search_jobs when the user provides them.
   The authenticated user ID is supplied separately by the backend and must
   never be guessed or requested from the user.

7. If the user provides a specific job role, use that role in job_titles.

8. If the user provides a specific location, use that location in locations.

9. If the user does not provide a job role, use the user's saved job preferences when available.

10. If the user does not provide a location, use the user's saved location preferences when available.

11. Do not invent a job role, location, experience, salary, company, or other user information.

12. Do not claim that jobs were found unless the search_jobs tool actually returns results.

13. After the tool completes, briefly summarize the search result.

14. Keep the job search relevant to the user's request.

15. Never claim that you searched all jobs on the internet. The search is based on the available job-search sources.
"""
)