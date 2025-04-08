from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, BLOB, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
import uuid

Base = declarative_base()

class Job(Base):
    __tablename__ = 'jobs'
    
    job_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text)
    location = Column(String)
    salary_range = Column(String)
    job_type = Column(String)
    embedding = Column(BLOB)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    skills = relationship("JobSkill", back_populates="job")
    matches = relationship("Match", back_populates="job")
    
    def __repr__(self):
        return f"<Job(title='{self.title}', company='{self.company}')>"


class Candidate(Base):
    __tablename__ = 'candidates'
    
    candidate_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String)
    resume_text = Column(Text)
    resume_path = Column(String)
    embedding = Column(BLOB)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    skills = relationship("CandidateSkill", back_populates="candidate")
    experiences = relationship("Experience", back_populates="candidate")
    educations = relationship("Education", back_populates="candidate")
    matches = relationship("Match", back_populates="candidate")
    
    def __repr__(self):
        return f"<Candidate(name='{self.name}', email='{self.email}')>"


class Skill(Base):
    __tablename__ = 'skills'
    
    skill_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    category = Column(String)
    
    candidate_skills = relationship("CandidateSkill", back_populates="skill")
    job_skills = relationship("JobSkill", back_populates="skill")
    
    def __repr__(self):
        return f"<Skill(name='{self.name}', category='{self.category}')>"


class CandidateSkill(Base):
    __tablename__ = 'candidate_skills'
    
    candidate_id = Column(String, ForeignKey('candidates.candidate_id'), primary_key=True)
    skill_id = Column(String, ForeignKey('skills.skill_id'), primary_key=True)
    proficiency = Column(String)
    years_experience = Column(Integer)
    
    candidate = relationship("Candidate", back_populates="skills")
    skill = relationship("Skill", back_populates="candidate_skills")
    
    def __repr__(self):
        return f"<CandidateSkill(proficiency='{self.proficiency}', years_experience='{self.years_experience}')>"


class JobSkill(Base):
    __tablename__ = 'job_skills'
    
    job_id = Column(String, ForeignKey('jobs.job_id'), primary_key=True)
    skill_id = Column(String, ForeignKey('skills.skill_id'), primary_key=True)
    importance = Column(String)  # 'required', 'preferred', 'nice-to-have'
    years_required = Column(Integer)
    
    job = relationship("Job", back_populates="skills")
    skill = relationship("Skill", back_populates="job_skills")
    
    def __repr__(self):
        return f"<JobSkill(importance='{self.importance}', years_required='{self.years_required}')>"


class Experience(Base):
    __tablename__ = 'experiences'
    
    experience_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String, ForeignKey('candidates.candidate_id'))
    company = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_current = Column(Integer, default=0)  # SQLite doesn't have boolean, using Integer as boolean
    
    candidate = relationship("Candidate", back_populates="experiences")
    
    def __repr__(self):
        return f"<Experience(company='{self.company}', title='{self.title}')>"


class Education(Base):
    __tablename__ = 'educations'
    
    education_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String, ForeignKey('candidates.candidate_id'))
    institution = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    field_of_study = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    candidate = relationship("Candidate", back_populates="educations")
    
    def __repr__(self):
        return f"<Education(institution='{self.institution}', degree='{self.degree}')>"


class Match(Base):
    __tablename__ = 'matches'
    
    match_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey('jobs.job_id'))
    candidate_id = Column(String, ForeignKey('candidates.candidate_id'))
    score = Column(Float, nullable=False)
    justification = Column(Text)
    status = Column(String, default='pending')  # 'pending', 'accepted', 'rejected', 'interviewed'
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    job = relationship("Job", back_populates="matches")
    candidate = relationship("Candidate", back_populates="matches")
    interviews = relationship("Interview", back_populates="match")
    feedbacks = relationship("Feedback", back_populates="match")
    
    def __repr__(self):
        return f"<Match(score='{self.score}', status='{self.status}')>"


class Interview(Base):
    __tablename__ = 'interviews'
    
    interview_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    match_id = Column(String, ForeignKey('matches.match_id'))
    scheduled_date = Column(DateTime)
    status = Column(String, default='scheduled')  # 'scheduled', 'completed', 'cancelled'
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    match = relationship("Match", back_populates="interviews")
    
    def __repr__(self):
        return f"<Interview(scheduled_date='{self.scheduled_date}', status='{self.status}')>"


class Feedback(Base):
    __tablename__ = 'feedbacks'
    
    feedback_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    match_id = Column(String, ForeignKey('matches.match_id'))
    feedback_text = Column(Text, nullable=False)
    feedback_type = Column(String)  # 'human', 'system'
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    match = relationship("Match", back_populates="feedbacks")
    
    def __repr__(self):
        return f"<Feedback(feedback_type='{self.feedback_type}')>"


# Create engine and tables
def init_db(db_path="sqlite:///ai_recruiter.db"):
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    return engine 