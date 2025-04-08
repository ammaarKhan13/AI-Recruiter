import os
import logging
from dotenv import load_dotenv
from db.database import engine, Base
from db.models import Job, Candidate, Match, Interview, Feedback, Skill, JobSkill, CandidateSkill
from knowledge_graph.skill_graph import SkillKnowledgeGraph

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def init_database():
    """Initialize the database and create tables"""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

def init_knowledge_graph():
    """Initialize the knowledge graph if Neo4j is available"""
    logger.info("Initializing knowledge graph...")
    skill_graph = SkillKnowledgeGraph()
    
    if skill_graph.driver:
        # Set up schema
        skill_graph.setup_schema()
        
        # Add some initial skills
        sample_skills = [
            {"name": "Python", "category": "programming"},
            {"name": "JavaScript", "category": "programming"},
            {"name": "SQL", "category": "database"},
            {"name": "Machine Learning", "category": "ai"},
            {"name": "Deep Learning", "category": "ai"},
            {"name": "FastAPI", "category": "framework"},
            {"name": "React", "category": "framework"},
            {"name": "Communication", "category": "soft_skill"},
            {"name": "Problem Solving", "category": "soft_skill"}
        ]
        
        for skill in sample_skills:
            skill_graph.add_skill(skill["name"], skill["category"])
        
        # Add relationships
        relationships = [
            {
                "skill_name": "Machine Learning",
                "related_skills": [
                    {"name": "Python", "relationship_type": "REQUIRES"},
                    {"name": "Deep Learning", "relationship_type": "RELATED_TO"}
                ]
            },
            {
                "skill_name": "FastAPI",
                "related_skills": [
                    {"name": "Python", "relationship_type": "REQUIRES"}
                ]
            },
            {
                "skill_name": "React",
                "related_skills": [
                    {"name": "JavaScript", "relationship_type": "REQUIRES"}
                ]
            }
        ]
        
        for rel in relationships:
            skill_graph.add_related_skills(rel["skill_name"], rel["related_skills"])
        
        logger.info("Knowledge graph initialized successfully")
    else:
        logger.warning("Neo4j not available, skipping knowledge graph initialization")
    
    # Close the connection
    skill_graph.close()

if __name__ == "__main__":
    # Initialize SQLite database
    init_database()
    
    # Initialize Neo4j knowledge graph
    init_knowledge_graph()
    
    logger.info("Initialization complete") 