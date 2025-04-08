from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import json
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Define output structure for JD analysis
class Skill(BaseModel):
    name: str = Field(description="Name of the skill")
    importance: str = Field(description="Importance level: 'required', 'preferred', or 'nice-to-have'")
    years_required: Optional[int] = Field(description="Years of experience required, if specified")

class JobRequirement(BaseModel):
    description: str = Field(description="Description of the job requirement")
    category: str = Field(description="Category of the requirement (e.g., 'education', 'certification', 'experience')")

class JobResponsibility(BaseModel):
    description: str = Field(description="Description of the job responsibility")

class JobDescription(BaseModel):
    title: str = Field(description="Job title")
    company: Optional[str] = Field(description="Company name, if available")
    location: Optional[str] = Field(description="Job location, if available")
    job_type: Optional[str] = Field(description="Job type (e.g., full-time, part-time, contract)")
    salary_range: Optional[str] = Field(description="Salary range, if available")
    summary: str = Field(description="Brief summary of the job")
    skills: List[Skill] = Field(description="List of skills required or preferred for the job")
    requirements: List[JobRequirement] = Field(description="List of job requirements")
    responsibilities: List[JobResponsibility] = Field(description="List of job responsibilities")

# Create JD Analyzer agent
class JDAnalyzerAgent:
    def __init__(self):
        # Get Ollama configuration
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
    
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
    
    def analyze(self, job_description: str) -> JobDescription:
        """
        Analyze a job description and extract structured information
        
        Args:
            job_description: The raw job description text
            
        Returns:
            JobDescription: Structured job description data
        """
        try:
            # Create prompt for Ollama
            prompt = f"""
            You are an expert recruiter with years of experience analyzing job descriptions. 
            Please analyze the following job description and extract the key components.
            
            Job Description:
            {job_description}
            
            Extract the following information in JSON format:
            1. Job title
            2. Company name (if available)
            3. Location (if available)
            4. Job type (if available)
            5. Salary range (if available)
            6. Brief summary of the job
            7. List of skills with:
               - Name of the skill
               - Importance level ('required', 'preferred', or 'nice-to-have')
               - Years of experience required (if specified)
            8. List of job requirements with:
               - Description of the requirement
               - Category (e.g., 'education', 'certification', 'experience')
            9. List of job responsibilities with:
               - Description of the responsibility
            
            Format the response as a valid JSON object that matches the following structure:
            {{
              "title": "string",
              "company": "string or null",
              "location": "string or null",
              "job_type": "string or null",
              "salary_range": "string or null",
              "summary": "string",
              "skills": [
                {{
                  "name": "string",
                  "importance": "string",
                  "years_required": "number or null"
                }}
              ],
              "requirements": [
                {{
                  "description": "string",
                  "category": "string"
                }}
              ],
              "responsibilities": [
                {{
                  "description": "string"
                }}
              ]
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
                    
                    # Convert to JobDescription model
                    return JobDescription(**data)
                else:
                    raise ValueError("No valid JSON found in response")
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                logger.error(f"Raw response: {response}")
                raise
            
        except Exception as e:
            logger.error(f"Error analyzing job description: {e}")
            raise

# Example usage
if __name__ == "__main__":
    analyzer = JDAnalyzerAgent()
    test_jd = """
    Senior Software Engineer - Machine Learning
    
    ABC Tech Inc. is looking for a Senior Software Engineer specializing in Machine Learning to join our team in San Francisco, CA. This is a full-time position with a salary range of $140,000 - $180,000 depending on experience.
    
    About the role:
    You will be responsible for designing, developing, and maintaining machine learning systems for our flagship product. You will work closely with data scientists and product managers to implement ML models and deploy them to production.
    
    Required Skills:
    - 5+ years of experience in software engineering
    - 3+ years of experience with Python
    - Experience with machine learning frameworks like TensorFlow or PyTorch
    - Strong understanding of data structures and algorithms
    - Experience with cloud platforms (AWS, GCP, or Azure)
    
    Preferred Skills:
    - Experience with NLP
    - Knowledge of React and frontend development
    - Experience with Docker and Kubernetes
    - Familiarity with CI/CD pipelines
    
    Educational Requirements:
    - Bachelor's degree in Computer Science, Engineering, or a related field
    - Master's degree preferred
    
    Responsibilities:
    - Design and develop scalable ML systems
    - Collaborate with data scientists to implement ML models
    - Optimize model performance and reliability
    - Write clean, testable code
    - Participate in code reviews and mentor junior engineers
    - Stay updated with the latest ML research and technologies
    """
    
    result = analyzer.analyze(test_jd)
    print(result) 