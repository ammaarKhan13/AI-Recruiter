from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import spacy
from dateutil import parser as date_parser
import re
from PyPDF2 import PdfReader
import logging
import json
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Define output structure for CV parsing
class Education(BaseModel):
    institution: str = Field(description="Name of the educational institution")
    degree: str = Field(description="Degree obtained or pursued")
    field_of_study: Optional[str] = Field(description="Field or major of study")
    start_date: Optional[str] = Field(description="Start date in ISO format (YYYY-MM-DD) if available")
    end_date: Optional[str] = Field(description="End date in ISO format (YYYY-MM-DD) or 'present' if ongoing")

class Experience(BaseModel):
    company: str = Field(description="Name of the company or organization")
    title: str = Field(description="Job title or position")
    description: str = Field(description="Description of responsibilities and achievements")
    start_date: Optional[str] = Field(description="Start date in ISO format (YYYY-MM-DD) if available")
    end_date: Optional[str] = Field(description="End date in ISO format (YYYY-MM-DD) or 'present' if current position")
    is_current: bool = Field(description="Whether this is the current position")

class CandidateSkill(BaseModel):
    name: str = Field(description="Name of the skill")
    proficiency: Optional[str] = Field(description="Proficiency level if mentioned (e.g., beginner, intermediate, expert)")
    years_experience: Optional[int] = Field(description="Years of experience with this skill, if mentioned")

class Project(BaseModel):
    name: str = Field(description="Name of the project")
    description: str = Field(description="Description of the project")
    technologies: List[str] = Field(description="Technologies or skills used in the project")
    url: Optional[str] = Field(description="URL of the project, if available")

class CandidateProfile(BaseModel):
    name: str = Field(description="Candidate's full name")
    email: Optional[str] = Field(description="Candidate's email address")
    phone: Optional[str] = Field(description="Candidate's phone number")
    summary: Optional[str] = Field(description="Professional summary or objective")
    skills: List[CandidateSkill] = Field(description="List of candidate's skills")
    experiences: List[Experience] = Field(description="List of work experiences")
    educations: List[Education] = Field(description="List of educational background")
    projects: Optional[List[Project]] = Field(description="List of projects, if mentioned")
    certifications: Optional[List[str]] = Field(description="List of certifications, if mentioned")
    languages: Optional[List[str]] = Field(description="List of languages the candidate knows")

class CVParserAgent:
    def __init__(self):
        # Get Ollama configuration
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
        
        # Load spaCy model for NER
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            os.system("python -m spacy download en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
    
    def _get_ollama_completion(self, prompt: str) -> str:
        """Get completion from Ollama API"""
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Error getting Ollama completion: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            str: Extracted text from the PDF
        """
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def extract_contact_info(self, text: str) -> Dict[str, str]:
        """
        Extract contact information using regex patterns
        
        Args:
            text: Resume text
            
        Returns:
            Dict[str, str]: Dictionary of contact information
        """
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        email = email_match.group(0) if email_match else None
        
        # Extract phone
        phone_pattern = r'(\+\d{1,3}\s?)?(\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}'
        phone_match = re.search(phone_pattern, text)
        phone = phone_match.group(0) if phone_match else None
        
        return {"email": email, "phone": phone}
    
    def parse(self, resume_text: str = None, pdf_path: str = None) -> CandidateProfile:
        """
        Parse a resume and extract structured information
        
        Args:
            resume_text: Raw text of the resume
            pdf_path: Path to a PDF resume file
            
        Returns:
            CandidateProfile: Structured candidate information
        """
        if resume_text is None and pdf_path is None:
            raise ValueError("Either resume_text or pdf_path must be provided")
        
        if resume_text is None:
            resume_text = self.extract_text_from_pdf(pdf_path)
        
        # Pre-process with spaCy for named entities
        doc = self.nlp(resume_text)
        
        # Extract contact information
        contact_info = self.extract_contact_info(resume_text)
        
        try:
            # Create prompt for Ollama
            prompt = f"""
            You are an expert recruiter specialized in parsing and analyzing resumes/CVs.
            Please extract the key information from the following resume text.
            
            Resume/CV:
            {resume_text}
            
            Extract the following information in JSON format:
            1. Candidate's full name
            2. Email address (if available)
            3. Phone number (if available)
            4. Professional summary or objective
            5. List of skills with:
               - Name of the skill
               - Proficiency level if mentioned (e.g., beginner, intermediate, expert)
               - Years of experience with this skill, if mentioned
            6. List of work experiences with:
               - Company name
               - Job title
               - Description of responsibilities and achievements
               - Start date (in ISO format YYYY-MM-DD if available)
               - End date (in ISO format YYYY-MM-DD or 'present' if current position)
               - Whether this is the current position
            7. List of educational background with:
               - Institution name
               - Degree obtained or pursued
               - Field of study
               - Start date (in ISO format YYYY-MM-DD if available)
               - End date (in ISO format YYYY-MM-DD or 'present' if ongoing)
            8. List of projects with:
               - Project name
               - Description
               - Technologies or skills used
               - URL (if available)
            9. List of certifications (if mentioned)
            10. List of languages the candidate knows (if mentioned)
            
            Format the response as a valid JSON object that matches the following structure:
            {{
              "name": "string",
              "email": "string or null",
              "phone": "string or null",
              "summary": "string or null",
              "skills": [
                {{
                  "name": "string",
                  "proficiency": "string or null",
                  "years_experience": "number or null"
                }}
              ],
              "experiences": [
                {{
                  "company": "string",
                  "title": "string",
                  "description": "string",
                  "start_date": "string or null",
                  "end_date": "string or null",
                  "is_current": "boolean"
                }}
              ],
              "educations": [
                {{
                  "institution": "string",
                  "degree": "string",
                  "field_of_study": "string or null",
                  "start_date": "string or null",
                  "end_date": "string or null"
                }}
              ],
              "projects": [
                {{
                  "name": "string",
                  "description": "string",
                  "technologies": ["string"],
                  "url": "string or null"
                }}
              ],
              "certifications": ["string"],
              "languages": ["string"]
            }}
            
            Return ONLY the JSON object, no additional text.
            """
            
            # Get response from Ollama
            response = self._get_ollama_completion(prompt)
            
            # Parse JSON response
            try:
                # Clean up the response to ensure it's valid JSON
                # Find the first { and last } to extract just the JSON part
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    data = json.loads(json_str)
                    
                    # If email or phone were not extracted by LLM but by regex, add them
                    if data.get("email") is None and contact_info["email"] is not None:
                        data["email"] = contact_info["email"]
                    if data.get("phone") is None and contact_info["phone"] is not None:
                        data["phone"] = contact_info["phone"]
                    
                    # Convert to CandidateProfile model
                    return CandidateProfile(**data)
                else:
                    raise ValueError("No valid JSON found in response")
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                logger.error(f"Raw response: {response}")
                raise
            
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            raise

# Example usage
if __name__ == "__main__":
    parser = CVParserAgent()
    test_resume = """
    JOHN DOE
    123 Main St, San Francisco, CA 94105
    john.doe@example.com | (555) 123-4567
    
    SUMMARY
    Experienced software engineer with 7+ years of experience in building scalable web applications and machine learning systems. Passionate about solving complex problems with elegant solutions.
    
    SKILLS
    Programming: Python (8 years), JavaScript (6 years), Java (3 years), SQL (5 years)
    Frameworks: React, Django, Flask, TensorFlow
    Cloud: AWS (EC2, S3, Lambda), Google Cloud Platform
    Tools: Git, Docker, Kubernetes, CI/CD pipelines
    
    EXPERIENCE
    
    Senior Software Engineer | XYZ Tech Inc. | Jan 2020 - Present
    - Led the development of a real-time recommendation system using Python and TensorFlow
    - Improved system performance by 40% through optimization of database queries and caching
    - Mentored junior engineers and conducted code reviews
    - Implemented CI/CD pipelines using GitHub Actions and Docker
    
    Software Engineer | ABC Software | Mar 2017 - Dec 2019
    - Developed RESTful APIs using Django and PostgreSQL
    - Built front-end components with React and Redux
    - Designed and implemented data processing pipelines for analyzing user behavior
    - Collaborated with data scientists to implement machine learning models
    
    EDUCATION
    
    Master of Science in Computer Science | Stanford University | 2015 - 2017
    Bachelor of Science in Computer Engineering | University of California, Berkeley | 2011 - 2015
    
    PROJECTS
    
    Personal Website (johndoe.dev)
    - Built a portfolio website using Next.js, Tailwind CSS, and Vercel
    - Implemented a blog section with MDX for writing technical articles
    
    Machine Learning Cookbook
    - Open-source repository of common machine learning algorithms and techniques
    - Over 500 stars on GitHub
    
    CERTIFICATIONS
    
    AWS Certified Solutions Architect
    Google Professional Data Engineer
    """
    
    result = parser.parse(resume_text=test_resume)
    print(result) 