from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
import logging
from pydantic import BaseModel
from .jd_analyzer import JDAnalyzerAgent
from .cv_parser import CVParserAgent
from .matcher import MatcherAgent
from .scheduler import SchedulerAgent
from knowledge_graph.skill_graph import SkillKnowledgeGraph
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Define the state structure for the multi-agent system
class RecruitmentState(TypedDict):
    job_id: str
    job_description: str
    job_data: Optional[Dict[str, Any]]
    candidate_id: Optional[str]
    candidate_resume: Optional[str]
    candidate_data: Optional[Dict[str, Any]]
    match_result: Optional[Dict[str, Any]]
    interview_request: Optional[Dict[str, Any]]
    feedback: Optional[Dict[str, Any]]
    errors: Optional[List[str]]
    status: str

# Initialize agents
class RecruitmentAgentSystem:
    def __init__(self):
        self.jd_analyzer = JDAnalyzerAgent()
        self.cv_parser = CVParserAgent()
        self.matcher = MatcherAgent()
        self.scheduler = SchedulerAgent()
        self.skill_graph = SkillKnowledgeGraph()
        
        # Initialize the state graph
        self.workflow = self._build_workflow()
        
    def _build_workflow(self) -> StateGraph:
        """
        Build the multi-agent workflow graph
        
        Returns:
            StateGraph: The workflow graph
        """
        # Create the workflow
        workflow = StateGraph(RecruitmentState)
        
        # Add nodes for each agent
        workflow.add_node("analyze_job", self._analyze_job_description)
        workflow.add_node("parse_resume", self._parse_resume)
        workflow.add_node("match_candidate", self._match_candidate)
        workflow.add_node("schedule_interview", self._schedule_interview)
        workflow.add_node("process_feedback", self._process_feedback)
        workflow.add_node("handle_error", self._handle_error)
        
        # Define the entry point
        workflow.set_entry_point("analyze_job")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "analyze_job",
            self._route_after_job_analysis,
            {
                "success": "parse_resume",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "parse_resume",
            self._route_after_resume_parsing,
            {
                "success": "match_candidate",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "match_candidate",
            self._route_after_matching,
            {
                "schedule": "schedule_interview",
                "reject": END,
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "schedule_interview",
            self._route_after_scheduling,
            {
                "success": "process_feedback",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("process_feedback", END)
        workflow.add_edge("handle_error", END)
        
        # Compile the workflow
        return workflow.compile()
    
    def _analyze_job_description(self, state: RecruitmentState) -> RecruitmentState:
        """
        Analyze job description using JD Analyzer agent
        
        Args:
            state: Current workflow state
            
        Returns:
            RecruitmentState: Updated workflow state
        """
        try:
            logger.info(f"Analyzing job description for job ID: {state['job_id']}")
            job_data = self.jd_analyzer.analyze(state["job_description"])
            
            # Update state
            state["job_data"] = job_data.dict()
            state["status"] = "job_analyzed"
            
            return state
        except Exception as e:
            logger.error(f"Error analyzing job description: {e}")
            state["errors"] = state.get("errors", []) + [f"Job analysis error: {str(e)}"]
            state["status"] = "error"
            return state
    
    def _parse_resume(self, state: RecruitmentState) -> RecruitmentState:
        """
        Parse candidate resume using CV Parser agent
        
        Args:
            state: Current workflow state
            
        Returns:
            RecruitmentState: Updated workflow state
        """
        try:
            logger.info(f"Parsing resume for candidate ID: {state['candidate_id']}")
            candidate_data = self.cv_parser.parse(resume_text=state["candidate_resume"])
            
            # Update state
            state["candidate_data"] = candidate_data.dict()
            state["status"] = "resume_parsed"
            
            return state
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            state["errors"] = state.get("errors", []) + [f"Resume parsing error: {str(e)}"]
            state["status"] = "error"
            return state
    
    def _match_candidate(self, state: RecruitmentState) -> RecruitmentState:
        """
        Match candidate to job using Matcher agent
        
        Args:
            state: Current workflow state
            
        Returns:
            RecruitmentState: Updated workflow state
        """
        try:
            logger.info(f"Matching candidate {state['candidate_id']} to job {state['job_id']}")
            
            # Get job and candidate data
            job_data = state["job_data"]
            job_data["job_id"] = state["job_id"]
            
            candidate_data = state["candidate_data"]
            candidate_data["candidate_id"] = state["candidate_id"]
            
            # Match candidate to job
            match_result = self.matcher.match(job_data, candidate_data)
            
            # Add knowledge graph insights
            if self.skill_graph.driver:
                # Extract skills
                job_skills = [skill["name"] for skill in job_data.get("skills", [])]
                candidate_skills = [skill["name"] for skill in candidate_data.get("skills", [])]
                
                # Get skill acquisition suggestions
                skill_suggestions = self.skill_graph.suggest_skill_acquisition(candidate_skills, job_skills)
                
                # Add counterfactual analysis
                counterfactual = self.matcher.generate_counterfactual_analysis(match_result)
                
                # Update match result with graph insights
                match_data = match_result.dict()
                match_data["skill_suggestions"] = skill_suggestions
                match_data["counterfactual_analysis"] = counterfactual
            else:
                match_data = match_result.dict()
            
            # Update state
            state["match_result"] = match_data
            state["status"] = "candidate_matched"
            
            return state
        except Exception as e:
            logger.error(f"Error matching candidate to job: {e}")
            state["errors"] = state.get("errors", []) + [f"Matching error: {str(e)}"]
            state["status"] = "error"
            return state
    
    def _schedule_interview(self, state: RecruitmentState) -> RecruitmentState:
        """
        Schedule interview using Scheduler agent
        
        Args:
            state: Current workflow state
            
        Returns:
            RecruitmentState: Updated workflow state
        """
        try:
            logger.info(f"Scheduling interview for candidate {state['candidate_id']}")
            
            # Get candidate, job, and match data
            candidate_info = {
                "name": state["candidate_data"]["name"],
                "email": state["candidate_data"]["email"],
                "skills": [skill["name"] for skill in state["candidate_data"].get("skills", [])],
                "experience": state["candidate_data"].get("summary", ""),
                "education": ", ".join([f"{edu['degree']} from {edu['institution']}" 
                                       for edu in state["candidate_data"].get("educations", [])])
            }
            
            job_info = {
                "title": state["job_data"]["title"],
                "company": state["job_data"].get("company", "Our Company"),
                "location": state["job_data"].get("location", ""),
                "description": state["job_data"].get("summary", "")
            }
            
            match_info = {
                "score": state["match_result"]["overall_match_score"],
                "strengths": state["match_result"]["strengths"],
                "recommendation": state["match_result"]["recommendation"]
            }
            
            # Create interview request
            interview_request = self.scheduler.create_interview_request(
                candidate_info, job_info, match_info
            )
            
            # Send email if credentials are configured
            if self.scheduler.smtp_username and self.scheduler.smtp_password:
                self.scheduler.send_interview_request(interview_request)
            
            # Update state
            state["interview_request"] = interview_request.dict()
            state["status"] = "interview_scheduled"
            
            return state
        except Exception as e:
            logger.error(f"Error scheduling interview: {e}")
            state["errors"] = state.get("errors", []) + [f"Scheduling error: {str(e)}"]
            state["status"] = "error"
            return state
    
    def _process_feedback(self, state: RecruitmentState) -> RecruitmentState:
        """
        Process feedback for continuous improvement
        
        Args:
            state: Current workflow state
            
        Returns:
            RecruitmentState: Updated workflow state
        """
        # This is a placeholder for feedback processing
        # In a real implementation, this would integrate with a feedback system
        state["status"] = "completed"
        return state
    
    def _handle_error(self, state: RecruitmentState) -> RecruitmentState:
        """
        Handle errors in the workflow
        
        Args:
            state: Current workflow state
            
        Returns:
            RecruitmentState: Updated workflow state
        """
        logger.error(f"Handling errors: {state.get('errors', [])}")
        state["status"] = "error_handled"
        return state
    
    def _route_after_job_analysis(self, state: RecruitmentState) -> str:
        """
        Determine the next step after job analysis
        
        Args:
            state: Current workflow state
            
        Returns:
            str: Next step in the workflow
        """
        if state["status"] == "error":
            return "error"
        return "success"
    
    def _route_after_resume_parsing(self, state: RecruitmentState) -> str:
        """
        Determine the next step after resume parsing
        
        Args:
            state: Current workflow state
            
        Returns:
            str: Next step in the workflow
        """
        if state["status"] == "error":
            return "error"
        return "success"
    
    def _route_after_matching(self, state: RecruitmentState) -> str:
        """
        Determine the next step after candidate matching
        
        Args:
            state: Current workflow state
            
        Returns:
            str: Next step in the workflow
        """
        if state["status"] == "error":
            return "error"
        
        # Check match score and recommendation
        match_score = state["match_result"]["overall_match_score"]
        recommendation = state["match_result"]["recommendation"]
        
        if match_score >= 0.7 or recommendation in ["Strong Match", "Potential Match"]:
            return "schedule"
        else:
            return "reject"
    
    def _route_after_scheduling(self, state: RecruitmentState) -> str:
        """
        Determine the next step after interview scheduling
        
        Args:
            state: Current workflow state
            
        Returns:
            str: Next step in the workflow
        """
        if state["status"] == "error":
            return "error"
        return "success"
    
    def process_job_candidate(self, job_id: str, job_description: str, candidate_id: str, 
                              candidate_resume: str) -> Dict[str, Any]:
        """
        Process a job and candidate through the entire workflow
        
        Args:
            job_id: ID of the job
            job_description: Job description text
            candidate_id: ID of the candidate
            candidate_resume: Candidate resume text
            
        Returns:
            Dict[str, Any]: Final state of the workflow
        """
        # Initialize state
        initial_state: RecruitmentState = {
            "job_id": job_id,
            "job_description": job_description,
            "job_data": None,
            "candidate_id": candidate_id,
            "candidate_resume": candidate_resume,
            "candidate_data": None,
            "match_result": None,
            "interview_request": None,
            "feedback": None,
            "errors": [],
            "status": "initialized"
        }
        
        # Run the workflow
        try:
            final_state = self.workflow.invoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"Error in recruitment workflow: {e}")
            return {
                **initial_state,
                "errors": [f"Workflow error: {str(e)}"],
                "status": "workflow_error"
            }

# Example usage
if __name__ == "__main__":
    # Initialize the multi-agent system
    recruitment_system = RecruitmentAgentSystem()
    
    # Example job description
    job_description = """
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
    
    # Example resume
    resume = """
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
    
    # Process the job and candidate
    result = recruitment_system.process_job_candidate(
        job_id="job123",
        job_description=job_description,
        candidate_id="cand456",
        candidate_resume=resume
    )
    
    # Print the result
    print(f"Final status: {result['status']}")
    if result["match_result"]:
        print(f"Match score: {result['match_result']['overall_match_score']}")
        print(f"Recommendation: {result['match_result']['recommendation']}")
    
    if result["interview_request"]:
        print("\nInterview Request:")
        print(f"Subject: {result['interview_request']['email_subject']}")
        print("Email Preview:")
        print(result['interview_request']['email_body']) 