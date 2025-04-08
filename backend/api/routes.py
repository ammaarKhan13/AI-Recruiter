from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uuid
import logging
from pydantic import BaseModel, Field
from datetime import datetime

from db.database import get_db
from db.models import Job, Candidate, Match, Interview, Feedback, Skill, JobSkill, CandidateSkill
from agents import RecruitmentAgentSystem
from knowledge_graph.skill_graph import SkillKnowledgeGraph

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize agents
recruitment_system = RecruitmentAgentSystem()
skill_graph = SkillKnowledgeGraph()

# Pydantic models for request/response
class JobCreate(BaseModel):
    title: str
    company: str
    description: str
    requirements: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    title: str
    company: str
    description: str
    requirements: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CandidateCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    resume_text: Optional[str] = None

class CandidateResponse(BaseModel):
    candidate_id: str
    name: str
    email: str
    phone: Optional[str] = None
    resume_text: Optional[str] = None
    resume_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class MatchRequest(BaseModel):
    job_id: str
    candidate_id: str

class MatchResponse(BaseModel):
    match_id: str
    job_id: str
    candidate_id: str
    score: float
    justification: Optional[str] = None
    status: str
    created_at: datetime

class InterviewRequest(BaseModel):
    match_id: str
    scheduled_date: datetime
    status: str = "scheduled"
    feedback: Optional[str] = None

class InterviewResponse(BaseModel):
    interview_id: str
    match_id: str
    scheduled_date: datetime
    status: str
    feedback: Optional[str] = None
    created_at: datetime

class FeedbackCreate(BaseModel):
    match_id: str
    feedback_text: str
    feedback_type: str = "human"

class FeedbackResponse(BaseModel):
    feedback_id: str
    match_id: str
    feedback_text: str
    feedback_type: str
    created_at: datetime

class SkillCreate(BaseModel):
    name: str
    category: Optional[str] = None

class SkillResponse(BaseModel):
    skill_id: str
    name: str
    category: Optional[str] = None

class SkillRelationshipCreate(BaseModel):
    skill_name: str
    related_skills: List[Dict[str, Any]]

class SkillRelationshipResponse(BaseModel):
    skill_name: str
    related_skills: List[Dict[str, Any]]

class JobCandidateProcessRequest(BaseModel):
    job_id: str
    job_description: str
    candidate_id: str
    candidate_resume: str

class JobCandidateProcessResponse(BaseModel):
    status: str
    job_data: Optional[Dict[str, Any]] = None
    candidate_data: Optional[Dict[str, Any]] = None
    match_result: Optional[Dict[str, Any]] = None
    interview_request: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

# Routes
@router.post("/jobs/", response_model=JobResponse)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    """Create a new job posting"""
    try:
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Create job record
        db_job = Job(
            job_id=job_id,
            title=job.title,
            company=job.company,
            description=job.description,
            requirements=job.requirements,
            location=job.location,
            salary_range=job.salary_range,
            job_type=job.job_type
        )
        
        # Add to database
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        
        return db_job
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating job: {str(e)}")

@router.get("/jobs/", response_model=List[JobResponse])
def get_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all jobs with pagination"""
    try:
        jobs = db.query(Job).offset(skip).limit(limit).all()
        return jobs
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting jobs: {str(e)}")

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a specific job by ID"""
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting job: {str(e)}")

@router.post("/candidates/", response_model=CandidateResponse)
def create_candidate(candidate: CandidateCreate, db: Session = Depends(get_db)):
    """Create a new candidate"""
    try:
        # Create candidate ID
        candidate_id = str(uuid.uuid4())
        
        # Create candidate record
        db_candidate = Candidate(
            candidate_id=candidate_id,
            name=candidate.name,
            email=candidate.email,
            phone=candidate.phone,
            resume_text=candidate.resume_text
        )
        
        # Add to database
        db.add(db_candidate)
        db.commit()
        db.refresh(db_candidate)
        
        return db_candidate
    except Exception as e:
        logger.error(f"Error creating candidate: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating candidate: {str(e)}")

@router.post("/candidates/upload-resume/", response_model=CandidateResponse)
async def upload_resume(
    candidate_id: str = Form(...),
    resume_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a resume for a candidate"""
    try:
        # Get candidate
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Read file content
        content = await resume_file.read()
        resume_text = content.decode("utf-8")
        
        # Update candidate
        candidate.resume_text = resume_text
        candidate.resume_path = f"resumes/{candidate_id}_{resume_file.filename}"
        
        # Save to database
        db.commit()
        db.refresh(candidate)
        
        return candidate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading resume: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading resume: {str(e)}")

@router.get("/candidates/", response_model=List[CandidateResponse])
def get_candidates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all candidates with pagination"""
    try:
        candidates = db.query(Candidate).offset(skip).limit(limit).all()
        return candidates
    except Exception as e:
        logger.error(f"Error getting candidates: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting candidates: {str(e)}")

@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """Get a specific candidate by ID"""
    try:
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return candidate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting candidate: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting candidate: {str(e)}")

@router.post("/matches/", response_model=MatchResponse)
def create_match(match_request: MatchRequest, db: Session = Depends(get_db)):
    """Create a match between a job and a candidate"""
    try:
        # Get job and candidate
        job = db.query(Job).filter(Job.job_id == match_request.job_id).first()
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        candidate = db.query(Candidate).filter(Candidate.candidate_id == match_request.candidate_id).first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Create match ID
        match_id = str(uuid.uuid4())
        
        # Create match record
        db_match = Match(
            match_id=match_id,
            job_id=match_request.job_id,
            candidate_id=match_request.candidate_id,
            score=0.0,  # Will be updated after matching
            status="pending"
        )
        
        # Add to database
        db.add(db_match)
        db.commit()
        db.refresh(db_match)
        
        return db_match
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating match: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating match: {str(e)}")

@router.get("/matches/", response_model=List[MatchResponse])
def get_matches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all matches with pagination"""
    try:
        matches = db.query(Match).offset(skip).limit(limit).all()
        return matches
    except Exception as e:
        logger.error(f"Error getting matches: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting matches: {str(e)}")

@router.get("/matches/{match_id}", response_model=MatchResponse)
def get_match(match_id: str, db: Session = Depends(get_db)):
    """Get a specific match by ID"""
    try:
        match = db.query(Match).filter(Match.match_id == match_id).first()
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")
        return match
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting match: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting match: {str(e)}")

@router.post("/interviews/", response_model=InterviewResponse)
def create_interview(interview: InterviewRequest, db: Session = Depends(get_db)):
    """Create an interview for a match"""
    try:
        # Get match
        match = db.query(Match).filter(Match.match_id == interview.match_id).first()
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")
        
        # Create interview ID
        interview_id = str(uuid.uuid4())
        
        # Create interview record
        db_interview = Interview(
            interview_id=interview_id,
            match_id=interview.match_id,
            scheduled_date=interview.scheduled_date,
            status=interview.status,
            feedback=interview.feedback
        )
        
        # Add to database
        db.add(db_interview)
        db.commit()
        db.refresh(db_interview)
        
        return db_interview
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating interview: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating interview: {str(e)}")

@router.get("/interviews/", response_model=List[InterviewResponse])
def get_interviews(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all interviews with pagination"""
    try:
        interviews = db.query(Interview).offset(skip).limit(limit).all()
        return interviews
    except Exception as e:
        logger.error(f"Error getting interviews: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting interviews: {str(e)}")

@router.get("/interviews/{interview_id}", response_model=InterviewResponse)
def get_interview(interview_id: str, db: Session = Depends(get_db)):
    """Get a specific interview by ID"""
    try:
        interview = db.query(Interview).filter(Interview.interview_id == interview_id).first()
        if interview is None:
            raise HTTPException(status_code=404, detail="Interview not found")
        return interview
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting interview: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting interview: {str(e)}")

@router.post("/feedback/", response_model=FeedbackResponse)
def create_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    """Create feedback for a match"""
    try:
        # Get match
        match = db.query(Match).filter(Match.match_id == feedback.match_id).first()
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")
        
        # Create feedback ID
        feedback_id = str(uuid.uuid4())
        
        # Create feedback record
        db_feedback = Feedback(
            feedback_id=feedback_id,
            match_id=feedback.match_id,
            feedback_text=feedback.feedback_text,
            feedback_type=feedback.feedback_type
        )
        
        # Add to database
        db.add(db_feedback)
        db.commit()
        db.refresh(db_feedback)
        
        return db_feedback
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating feedback: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating feedback: {str(e)}")

@router.get("/feedback/", response_model=List[FeedbackResponse])
def get_feedback(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all feedback with pagination"""
    try:
        feedback = db.query(Feedback).offset(skip).limit(limit).all()
        return feedback
    except Exception as e:
        logger.error(f"Error getting feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting feedback: {str(e)}")

@router.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
def get_feedback_by_id(feedback_id: str, db: Session = Depends(get_db)):
    """Get a specific feedback by ID"""
    try:
        feedback = db.query(Feedback).filter(Feedback.feedback_id == feedback_id).first()
        if feedback is None:
            raise HTTPException(status_code=404, detail="Feedback not found")
        return feedback
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting feedback: {str(e)}")

@router.post("/skills/", response_model=SkillResponse)
def create_skill(skill: SkillCreate, db: Session = Depends(get_db)):
    """Create a new skill"""
    try:
        # Check if skill already exists
        existing_skill = db.query(Skill).filter(Skill.name == skill.name).first()
        if existing_skill:
            return existing_skill
        
        # Create skill ID
        skill_id = str(uuid.uuid4())
        
        # Create skill record
        db_skill = Skill(
            skill_id=skill_id,
            name=skill.name,
            category=skill.category
        )
        
        # Add to database
        db.add(db_skill)
        db.commit()
        db.refresh(db_skill)
        
        # Add to knowledge graph if available
        if skill_graph.driver:
            skill_graph.add_skill(skill.name, skill.category)
        
        return db_skill
    except Exception as e:
        logger.error(f"Error creating skill: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating skill: {str(e)}")

@router.get("/skills/", response_model=List[SkillResponse])
def get_skills(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all skills with pagination"""
    try:
        skills = db.query(Skill).offset(skip).limit(limit).all()
        return skills
    except Exception as e:
        logger.error(f"Error getting skills: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting skills: {str(e)}")

@router.get("/skills/{skill_id}", response_model=SkillResponse)
def get_skill(skill_id: str, db: Session = Depends(get_db)):
    """Get a specific skill by ID"""
    try:
        skill = db.query(Skill).filter(Skill.skill_id == skill_id).first()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        return skill
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting skill: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting skill: {str(e)}")

@router.post("/skills/relationships/", response_model=SkillRelationshipResponse)
def create_skill_relationship(relationship: SkillRelationshipCreate, db: Session = Depends(get_db)):
    """Create relationships between skills in the knowledge graph"""
    try:
        # Check if skill exists
        skill = db.query(Skill).filter(Skill.name == relationship.skill_name).first()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        # Add relationships to knowledge graph
        if skill_graph.driver:
            success = skill_graph.add_related_skills(relationship.skill_name, relationship.related_skills)
            if not success:
                raise HTTPException(status_code=500, detail="Error adding skill relationships")
            
            return {
                "skill_name": relationship.skill_name,
                "related_skills": relationship.related_skills
            }
        else:
            raise HTTPException(status_code=503, detail="Knowledge graph not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating skill relationship: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating skill relationship: {str(e)}")

@router.get("/skills/relationships/{skill_name}")
def get_skill_relationships(skill_name: str, relationship_type: Optional[str] = None, max_depth: int = 1):
    """Get relationships for a skill from the knowledge graph"""
    try:
        if not skill_graph.driver:
            raise HTTPException(status_code=503, detail="Knowledge graph not available")
        
        relationships = skill_graph.get_related_skills(skill_name, relationship_type, max_depth)
        return relationships
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting skill relationships: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting skill relationships: {str(e)}")

@router.post("/process-job-candidate/", response_model=JobCandidateProcessResponse)
def process_job_candidate(request: JobCandidateProcessRequest, background_tasks: BackgroundTasks):
    """Process a job and candidate through the multi-agent system"""
    try:
        # Process in background to avoid long-running request
        background_tasks.add_task(
            recruitment_system.process_job_candidate,
            request.job_id,
            request.job_description,
            request.candidate_id,
            request.candidate_resume
        )
        
        return {
            "status": "processing",
            "job_data": None,
            "candidate_data": None,
            "match_result": None,
            "interview_request": None,
            "errors": None
        }
    except Exception as e:
        logger.error(f"Error processing job and candidate: {e}")
        return {
            "status": "error",
            "job_data": None,
            "candidate_data": None,
            "match_result": None,
            "interview_request": None,
            "errors": [str(e)]
        }

@router.get("/process-status/{job_id}/{candidate_id}")
def get_process_status(job_id: str, candidate_id: str, db: Session = Depends(get_db)):
    """Get the status of a job-candidate processing"""
    try:
        # Check for match
        match = db.query(Match).filter(
            Match.job_id == job_id,
            Match.candidate_id == candidate_id
        ).first()
        
        if match is None:
            return {"status": "not_found"}
        
        # Check for interview
        interview = db.query(Interview).filter(Interview.match_id == match.match_id).first()
        
        # Check for feedback
        feedback = db.query(Feedback).filter(Feedback.match_id == match.match_id).first()
        
        # Determine status
        if feedback:
            return {"status": "completed", "match_id": match.match_id}
        elif interview:
            return {"status": "interview_scheduled", "match_id": match.match_id}
        else:
            return {"status": "matched", "match_id": match.match_id}
    except Exception as e:
        logger.error(f"Error getting process status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting process status: {str(e)}") 