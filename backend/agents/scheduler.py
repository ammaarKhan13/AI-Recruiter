from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Define output structure for interview scheduling
class InterviewSlot(BaseModel):
    date: str = Field(description="Date of the interview slot in ISO format (YYYY-MM-DD)")
    start_time: str = Field(description="Start time in 24-hour format (HH:MM)")
    end_time: str = Field(description="End time in 24-hour format (HH:MM)")

class InterviewRequest(BaseModel):
    candidate_name: str = Field(description="Name of the candidate")
    candidate_email: str = Field(description="Email of the candidate")
    job_title: str = Field(description="Title of the job")
    company_name: str = Field(description="Name of the company")
    recruiter_name: str = Field(description="Name of the recruiter")
    interview_type: str = Field(description="Type of interview (e.g., 'Technical', 'Behavioral', 'Initial Screening')")
    suggested_slots: List[InterviewSlot] = Field(description="List of suggested interview time slots")
    personalized_message: str = Field(description="Personalized message for the candidate")
    email_subject: str = Field(description="Subject for the email")
    email_body: str = Field(description="Complete email body to send to the candidate")

class SchedulerAgent:
    def __init__(self):
        # Get Ollama configuration
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
        
        # Email configuration
        self.smtp_server = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
    
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
    
    def generate_available_slots(self, days_ahead: int = 7, slots_per_day: int = 3) -> List[Dict[str, str]]:
        """
        Generate available time slots for interviews
        
        Args:
            days_ahead: Number of business days to look ahead
            slots_per_day: Number of slots to generate per day
            
        Returns:
            List[Dict[str, str]]: List of available time slots
        """
        available_slots = []
        current_date = datetime.now()
        
        # Generate slots for the next N business days
        days_generated = 0
        while days_generated < days_ahead:
            current_date += timedelta(days=1)
            
            # Skip weekends
            if current_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
                continue
            
            # Generate slots for this day
            for i in range(slots_per_day):
                # Create slots at 10:00, 13:00, and 15:00
                if i == 0:
                    start_hour = 10
                elif i == 1:
                    start_hour = 13
                else:
                    start_hour = 15
                
                slot = {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "start_time": f"{start_hour:02d}:00",
                    "end_time": f"{start_hour+1:02d}:00"
                }
                
                available_slots.append(slot)
            
            days_generated += 1
        
        return available_slots
    
    def create_interview_request(self, candidate_info: Dict[str, Any], job_info: Dict[str, Any], 
                                match_info: Dict[str, Any], available_slots: List[Dict[str, str]] = None) -> InterviewRequest:
        """
        Create an interview request for a candidate
        
        Args:
            candidate_info: Information about the candidate
            job_info: Information about the job
            match_info: Information about the match
            available_slots: List of available time slots, if None will be generated
            
        Returns:
            InterviewRequest: Structure with the interview request information
        """
        try:
            # Generate available slots if not provided
            if available_slots is None:
                available_slots = self.generate_available_slots()
            
            # Format the available slots for the prompt
            slots_text = ""
            for slot in available_slots:
                slots_text += f"- Date: {slot['date']}, Time: {slot['start_time']} - {slot['end_time']}\n"
            
            # Create prompt for Ollama
            prompt = f"""
            You are an experienced recruiter responsible for scheduling interviews with candidates.
            Please generate a personalized interview request for the following candidate and job.
            
            CANDIDATE INFORMATION:
            {json.dumps(candidate_info, indent=2)}
            
            JOB INFORMATION:
            {json.dumps(job_info, indent=2)}
            
            MATCH INFORMATION:
            {json.dumps(match_info, indent=2)}
            
            AVAILABLE TIME SLOTS:
            {slots_text}
            
            Create a professional and personalized email to invite the candidate for an interview.
            The email should:
            1. Be warm and encouraging
            2. Highlight the candidate's fit for the role (use details from the match information)
            3. Suggest multiple interview time slots
            4. Explain the interview process and what to expect
            5. Include a call to action for scheduling
            
            Format the response as a valid JSON object with the following structure:
            {{
              "candidate_name": "string",
              "candidate_email": "string",
              "job_title": "string",
              "company_name": "string",
              "recruiter_name": "string",
              "interview_type": "string",
              "suggested_slots": [
                {{
                  "date": "string (YYYY-MM-DD)",
                  "start_time": "string (HH:MM)",
                  "end_time": "string (HH:MM)"
                }}
              ],
              "personalized_message": "string",
              "email_subject": "string",
              "email_body": "string"
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
                    
                    # Convert to InterviewRequest model
                    return InterviewRequest(**data)
                else:
                    raise ValueError("No valid JSON found in response")
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                logger.error(f"Raw response: {response}")
                raise
            
        except Exception as e:
            logger.error(f"Error creating interview request: {e}")
            raise
    
    def send_interview_request(self, interview_request: InterviewRequest) -> bool:
        """
        Send the interview request email to the candidate
        
        Args:
            interview_request: The interview request to send
            
        Returns:
            bool: True if the email was sent successfully, False otherwise
        """
        if not self.smtp_username or not self.smtp_password:
            logger.error("SMTP credentials not configured")
            return False
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = interview_request.candidate_email
            msg['Subject'] = interview_request.email_subject
            
            # Attach email body
            msg.attach(MIMEText(interview_request.email_body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Interview request email sent to {interview_request.candidate_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending interview request email: {e}")
            return False

# Example usage
if __name__ == "__main__":
    scheduler = SchedulerAgent()
    
    # Example candidate information
    candidate = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "skills": ["Python", "Machine Learning", "SQL", "React"],
        "experience": "7+ years in software engineering",
        "education": "Master's in Computer Science from Stanford University"
    }
    
    # Example job information
    job = {
        "title": "Senior Software Engineer - Machine Learning",
        "company": "ABC Tech Inc.",
        "location": "San Francisco, CA",
        "description": "Designing and developing machine learning systems for our flagship product"
    }
    
    # Example match information
    match = {
        "score": 0.85,
        "strengths": [
            "Strong Python skills",
            "Experience with machine learning",
            "Advanced education in Computer Science"
        ],
        "recommendation": "Strong Match"
    }
    
    # Generate interview request
    request = scheduler.create_interview_request(candidate, job, match)
    
    print(f"Email Subject: {request.email_subject}")
    print("\nEmail Body:")
    print(request.email_body)
    
    # Send email (if SMTP credentials are configured)
    if scheduler.smtp_username and scheduler.smtp_password:
        scheduler.send_interview_request(request) 