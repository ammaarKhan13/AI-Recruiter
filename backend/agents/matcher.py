from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import os
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SkillMatch(BaseModel):
    skill: str
    match_score: float
    relevance: str

class RequirementMatch(BaseModel):
    requirement: str
    match_score: float
    explanation: str

class MatchResult(BaseModel):
    overall_score: float
    skill_matches: List[SkillMatch]
    requirement_matches: List[RequirementMatch]
    missing_skills: List[str]
    improvement_suggestions: List[str]

class MatcherAgent:
    def __init__(self):
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
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

    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for a list of texts"""
        return self.embedding_model.encode(texts)

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts"""
        embeddings = self._get_embeddings([text1, text2])
        return float(np.dot(embeddings[0], embeddings[1]) / 
                    (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])))

    def match_candidate_to_job(self, 
                             candidate_profile: Dict[str, Any],
                             job_description: Dict[str, Any]) -> MatchResult:
        """Match a candidate profile against a job description"""
        try:
            # Extract skills and requirements
            candidate_skills = candidate_profile.get("skills", [])
            job_skills = job_description.get("required_skills", [])
            job_requirements = job_description.get("requirements", [])

            # Match skills
            skill_matches = []
            for skill in job_skills:
                # Find best matching candidate skill
                best_match = max(
                    [(cs, self.calculate_similarity(skill.lower(), cs.lower())) 
                     for cs in candidate_skills],
                    key=lambda x: x[1]
                )
                skill_matches.append(SkillMatch(
                    skill=skill,
                    match_score=best_match[1],
                    relevance="high" if best_match[1] > 0.7 else "medium" if best_match[1] > 0.4 else "low"
                ))

            # Match requirements
            requirement_matches = []
            for req in job_requirements:
                # Use Ollama to analyze requirement match
                prompt = f"""Analyze how well this candidate matches the following job requirement:
                Requirement: {req}
                Candidate Profile: {json.dumps(candidate_profile)}
                
                Provide a match score (0-1) and explanation.
                Format: score|explanation
                """
                
                response = self._get_ollama_completion(prompt)
                try:
                    score_str, explanation = response.split("|", 1)
                    score = float(score_str.strip())
                except:
                    score = 0.5
                    explanation = "Unable to determine match"
                
                requirement_matches.append(RequirementMatch(
                    requirement=req,
                    match_score=score,
                    explanation=explanation.strip()
                ))

            # Calculate overall score
            skill_score = np.mean([m.match_score for m in skill_matches])
            req_score = np.mean([m.match_score for m in requirement_matches])
            overall_score = 0.7 * skill_score + 0.3 * req_score

            # Find missing skills
            missing_skills = [
                skill for skill in job_skills
                if not any(m.match_score > 0.7 for m in skill_matches if m.skill == skill)
            ]

            # Generate improvement suggestions
            prompt = f"""Based on the following information, suggest specific improvements for the candidate:
            Job Description: {json.dumps(job_description)}
            Candidate Profile: {json.dumps(candidate_profile)}
            Missing Skills: {missing_skills}
            
            Provide 3 specific, actionable suggestions for improvement.
            Format each suggestion on a new line starting with "- "
            """
            
            suggestions_response = self._get_ollama_completion(prompt)
            improvement_suggestions = [
                s.strip("- ").strip() 
                for s in suggestions_response.split("\n") 
                if s.strip().startswith("- ")
            ]

            return MatchResult(
                overall_score=overall_score,
                skill_matches=skill_matches,
                requirement_matches=requirement_matches,
                missing_skills=missing_skills,
                improvement_suggestions=improvement_suggestions
            )

        except Exception as e:
            logger.error(f"Error in match_candidate_to_job: {e}")
            raise

    def generate_counterfactual_analysis(self,
                                       candidate_profile: Dict[str, Any],
                                       job_description: Dict[str, Any]) -> Dict[str, Any]:
        """Generate counterfactual analysis for candidate improvement"""
        try:
            prompt = f"""Analyze how the candidate's profile would change with different scenarios:
            Current Profile: {json.dumps(candidate_profile)}
            Job Description: {json.dumps(job_description)}
            
            Consider the following scenarios:
            1. Adding 2 years of experience in key required skills
            2. Obtaining relevant certifications
            3. Working on similar projects
            
            For each scenario, provide:
            - Impact on match score
            - Specific improvements
            - Time investment required
            - Cost considerations
            
            Format as JSON with scenarios as keys.
            """
            
            response = self._get_ollama_completion(prompt)
            try:
                return json.loads(response)
            except:
                return {
                    "error": "Failed to parse counterfactual analysis",
                    "raw_response": response
                }

        except Exception as e:
            logger.error(f"Error in generate_counterfactual_analysis: {e}")
            raise

# Example usage
if __name__ == "__main__":
    # Sample data
    candidate_profile = {
        "name": "John Doe",
        "skills": ["Python", "Machine Learning", "Data Analysis", "SQL"],
        "experience": "5 years in data science",
        "education": "MS in Computer Science"
    }
    
    job_description = {
        "title": "Senior Data Scientist",
        "required_skills": ["Python", "Machine Learning", "Deep Learning", "AWS"],
        "requirements": [
            "5+ years of experience in machine learning",
            "Experience with cloud platforms",
            "Strong programming skills"
        ]
    }
    
    # Initialize matcher
    matcher = MatcherAgent()
    
    # Match candidate to job
    result = matcher.match_candidate_to_job(candidate_profile, job_description)
    print("\nMatch Result:")
    print(f"Overall Score: {result.overall_score:.2f}")
    print("\nSkill Matches:")
    for match in result.skill_matches:
        print(f"- {match.skill}: {match.match_score:.2f} ({match.relevance})")
    print("\nMissing Skills:")
    for skill in result.missing_skills:
        print(f"- {skill}")
    print("\nImprovement Suggestions:")
    for suggestion in result.improvement_suggestions:
        print(f"- {suggestion}")
    
    # Generate counterfactual analysis
    analysis = matcher.generate_counterfactual_analysis(candidate_profile, job_description)
    print("\nCounterfactual Analysis:")
    print(json.dumps(analysis, indent=2)) 