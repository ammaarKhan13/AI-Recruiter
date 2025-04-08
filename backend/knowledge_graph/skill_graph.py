from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class SkillKnowledgeGraph:
    """
    Class to manage the skill knowledge graph using Neo4j
    """
    def __init__(self, uri=None, user=None, password=None):
        # Get Neo4j credentials from environment variables if not provided
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        
        # Initialize embedding model for semantic similarity
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
        
        # Connect to Neo4j
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Successfully connected to Neo4j")
        except Exception as e:
            logger.warning(f"Neo4j connection not available: {e}")
            logger.warning("Knowledge graph features will be limited or disabled")
            self.driver = None
    
    def close(self):
        """
        Close the Neo4j connection
        """
        if self.driver:
            self.driver.close()
    
    def setup_schema(self):
        """
        Set up the Neo4j schema with constraints and indexes
        """
        if not self.driver:
            logger.warning("Neo4j not connected, skipping schema setup")
            return False
        
        try:
            with self.driver.session() as session:
                # Create constraints
                session.run("""
                    CREATE CONSTRAINT skill_name_unique IF NOT EXISTS
                    FOR (s:Skill) REQUIRE s.name IS UNIQUE
                """)
                
                # Create indexes
                session.run("CREATE INDEX skill_category IF NOT EXISTS FOR (s:Skill) ON (s.category)")
                
                logger.info("Neo4j schema setup complete")
                return True
        except Exception as e:
            logger.error(f"Error setting up Neo4j schema: {e}")
            return False
    
    def add_skill(self, name: str, category: str = None, properties: Dict[str, Any] = None) -> bool:
        """
        Add a skill node to the knowledge graph
        
        Args:
            name: Name of the skill
            category: Category of the skill (e.g., 'programming', 'soft skill', 'framework')
            properties: Additional properties for the skill
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.driver:
            logger.warning(f"Neo4j not connected, skill '{name}' not added to graph")
            return False
        
        properties = properties or {}
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MERGE (s:Skill {name: $name})
                    ON CREATE SET s.category = $category
                    WITH s
                    SET s += $properties
                    RETURN s
                """, name=name, category=category, properties=properties)
                
                return result.single() is not None
        except Exception as e:
            logger.error(f"Error adding skill '{name}': {e}")
            return False
    
    def add_related_skills(self, skill_name: str, related_skills: List[Dict[str, Any]]) -> bool:
        """
        Add relationships between a skill and related skills
        
        Args:
            skill_name: Name of the main skill
            related_skills: List of related skills with relationship properties
                            [{"name": "skill_name", "relationship_type": "REQUIRES", "properties": {...}}]
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.driver:
            logger.warning(f"Neo4j not connected, related skills for '{skill_name}' not added to graph")
            return False
        
        try:
            with self.driver.session() as session:
                for related in related_skills:
                    rel_name = related.get("name")
                    rel_type = related.get("relationship_type", "RELATED_TO")
                    properties = related.get("properties", {})
                    
                    session.run("""
                        MERGE (s1:Skill {name: $skill_name})
                        MERGE (s2:Skill {name: $related_name})
                        MERGE (s1)-[r:%s]->(s2)
                        SET r += $properties
                    """ % rel_type, skill_name=skill_name, related_name=rel_name, properties=properties)
                
                return True
        except Exception as e:
            logger.error(f"Error adding related skills for '{skill_name}': {e}")
            return False
    
    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a skill node by name
        
        Args:
            name: Name of the skill
            
        Returns:
            Optional[Dict[str, Any]]: Skill data if found, None otherwise
        """
        if not self.driver:
            logger.error("No connection to Neo4j")
            return None
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (s:Skill {name: $name})
                    RETURN s
                """, name=name)
                
                record = result.single()
                if record:
                    return dict(record["s"])
                return None
        except Exception as e:
            logger.error(f"Error getting skill '{name}': {e}")
            return None
    
    def get_related_skills(self, name: str, relationship_type: str = None, max_depth: int = 1) -> List[Dict[str, Any]]:
        """
        Get skills related to a given skill
        
        Args:
            name: Name of the skill
            relationship_type: Type of relationship to filter by (optional)
            max_depth: Maximum depth to traverse in the graph (default: 1)
            
        Returns:
            List[Dict[str, Any]]: List of related skills with relationship info
        """
        if not self.driver:
            logger.error("No connection to Neo4j")
            return []
        
        rel_query = ""
        if relationship_type:
            rel_query = f":{relationship_type}"
        
        try:
            with self.driver.session() as session:
                result = session.run(f"""
                    MATCH (s:Skill {{name: $name}})-[r{rel_query}*1..{max_depth}]->(related:Skill)
                    RETURN related, 
                           [rel IN r | type(rel)] AS relationship_types, 
                           [rel IN r | properties(rel)] AS relationship_properties
                """, name=name)
                
                related_skills = []
                for record in result:
                    related = dict(record["related"])
                    relationship_types = record["relationship_types"]
                    relationship_properties = record["relationship_properties"]
                    
                    skill_info = {
                        "skill": related,
                        "relationship": {
                            "types": relationship_types,
                            "properties": relationship_properties
                        }
                    }
                    related_skills.append(skill_info)
                
                return related_skills
        except Exception as e:
            logger.error(f"Error getting related skills for '{name}': {e}")
            return []
    
    def find_skill_path(self, from_skill: str, to_skill: str) -> List[Dict[str, Any]]:
        """
        Find a path between two skills in the knowledge graph
        
        Args:
            from_skill: Starting skill name
            to_skill: Target skill name
            
        Returns:
            List[Dict[str, Any]]: Path between skills as a list of nodes and relationships
        """
        if not self.driver:
            logger.error("No connection to Neo4j")
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH path = shortestPath((s1:Skill {name: $from_skill})-[*]-(s2:Skill {name: $to_skill}))
                    RETURN [node IN nodes(path) | properties(node)] AS nodes,
                           [rel IN relationships(path) | {type: type(rel), properties: properties(rel)}] AS relationships
                """, from_skill=from_skill, to_skill=to_skill)
                
                record = result.single()
                if record:
                    return {
                        "nodes": record["nodes"],
                        "relationships": record["relationships"]
                    }
                return None
        except Exception as e:
            logger.error(f"Error finding path from '{from_skill}' to '{to_skill}': {e}")
            return None
    
    def find_similar_skills(self, skill_name: str, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Find semantically similar skills using embeddings
        
        Args:
            skill_name: Name of the skill to find similar skills for
            threshold: Similarity threshold (default: 0.7)
            
        Returns:
            List[Dict[str, Any]]: List of similar skills with similarity scores
        """
        if not self.driver:
            logger.error("No connection to Neo4j")
            return []
        
        try:
            # Get all skills from Neo4j
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (s:Skill)
                    RETURN s.name AS name
                """)
                
                all_skills = [record["name"] for record in result]
                
                # If the skill_name is not in the database, return empty list
                if skill_name not in all_skills:
                    return []
                
                # Calculate embeddings
                skill_embedding = self.embedding_model.encode([skill_name])[0]
                all_embeddings = self.embedding_model.encode(all_skills)
                
                # Calculate similarities
                similarities = cosine_similarity([skill_embedding], all_embeddings)[0]
                
                # Create result list
                similar_skills = []
                for i, sim in enumerate(similarities):
                    if all_skills[i] != skill_name and sim >= threshold:
                        similar_skills.append({
                            "name": all_skills[i],
                            "similarity": float(sim)
                        })
                
                # Sort by similarity
                similar_skills.sort(key=lambda x: x["similarity"], reverse=True)
                
                return similar_skills
        except Exception as e:
            logger.error(f"Error finding similar skills for '{skill_name}': {e}")
            return []
    
    def suggest_skill_acquisition(self, candidate_skills: List[str], job_skills: List[str]) -> List[Dict[str, Any]]:
        """
        Suggest skills a candidate should learn based on their current skills and job requirements
        
        Args:
            candidate_skills: List of skills the candidate has
            job_skills: List of skills required for the job
            
        Returns:
            List[Dict[str, Any]]: Suggested skills with reasoning
        """
        # If Neo4j is not available, use a simpler approach with embeddings
        if not self.driver:
            logger.info("Using fallback skill suggestion method (Neo4j not connected)")
            return self._fallback_skill_suggestions(candidate_skills, job_skills)
        
        try:
            # First identify missing skills directly
            missing_skills = [skill for skill in job_skills if skill not in candidate_skills]
            
            suggestions = []
            
            # For each missing skill, find related skills the candidate has
            for skill in missing_skills:
                with self.driver.session() as session:
                    # Find paths from candidate skills to this missing skill
                    result = session.run("""
                        MATCH (candidate_skill:Skill)
                        WHERE candidate_skill.name IN $candidate_skills
                        MATCH (job_skill:Skill {name: $job_skill})
                        MATCH path = shortestPath((candidate_skill)-[*1..3]-(job_skill))
                        RETURN path, length(path) AS path_length
                        ORDER BY path_length
                        LIMIT 1
                    """, candidate_skills=candidate_skills, job_skill=skill)
                    
                    record = result.single()
                    suggestion = {
                        "skill": skill,
                        "priority": "high" if skill in job_skills else "medium",
                        "reasoning": f"This skill is directly required for the job"
                    }
                    
                    if record:
                        # Extract path information if available
                        path = record["path"]
                        suggestion["related_to_candidate_skill"] = path.start_node["name"]
                        suggestion["path_length"] = record["path_length"]
                    
                    suggestions.append(suggestion)
            
            return suggestions
        except Exception as e:
            logger.error(f"Error suggesting skills: {e}")
            return self._fallback_skill_suggestions(candidate_skills, job_skills)
    
    def _fallback_skill_suggestions(self, candidate_skills: List[str], job_skills: List[str]) -> List[Dict[str, Any]]:
        """
        Fallback method for skill suggestions when Neo4j is not available
        
        Args:
            candidate_skills: List of skills the candidate has
            job_skills: List of skills required for the job
            
        Returns:
            List[Dict[str, Any]]: Suggested skills with reasoning
        """
        suggestions = []
        missing_skills = [skill for skill in job_skills if skill not in candidate_skills]
        
        # If embedding model is available, use it for similarity calculation
        if self.embedding_model and missing_skills and candidate_skills:
            try:
                # Get embeddings
                candidate_embeddings = self.embedding_model.encode(candidate_skills)
                missing_embeddings = self.embedding_model.encode(missing_skills)
                
                # Calculate similarities
                similarities = cosine_similarity(missing_embeddings, candidate_embeddings)
                
                for i, skill in enumerate(missing_skills):
                    # Find most similar candidate skill
                    most_similar_idx = np.argmax(similarities[i])
                    similarity_score = similarities[i][most_similar_idx]
                    related_skill = candidate_skills[most_similar_idx]
                    
                    suggestions.append({
                        "skill": skill,
                        "priority": "high" if skill in job_skills else "medium",
                        "reasoning": f"Required for the job and related to your {related_skill} skill",
                        "related_to_candidate_skill": related_skill,
                        "similarity_score": float(similarity_score)
                    })
                
                return suggestions
            except Exception as e:
                logger.error(f"Error in fallback skill suggestions with embeddings: {e}")
        
        # Simple fallback without embeddings
        for skill in missing_skills:
            suggestions.append({
                "skill": skill,
                "priority": "high" if skill in job_skills else "medium",
                "reasoning": "This skill is directly required for the job"
            })
        
        return suggestions
    
    def build_skill_prerequisites_tree(self, skill_name: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        Build a tree of prerequisites for a skill
        
        Args:
            skill_name: Name of the skill
            max_depth: Maximum depth of the tree
            
        Returns:
            Dict[str, Any]: Tree structure of skill prerequisites
        """
        if not self.driver:
            logger.error("No connection to Neo4j")
            return {}
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (s:Skill {name: $skill_name})
                    OPTIONAL MATCH path = (s)-[:REQUIRES*1..%d]->(prereq:Skill)
                    WITH s, collect(path) AS paths
                    RETURN s.name AS skill_name,
                           [path IN paths | [node IN nodes(path) | node.name]] AS prerequisite_paths
                """ % max_depth, skill_name=skill_name)
                
                record = result.single()
                if not record:
                    return {"skill": skill_name, "prerequisites": []}
                
                # Build tree structure
                tree = {"skill": record["skill_name"], "prerequisites": []}
                
                # Process paths
                for path in record["prerequisite_paths"]:
                    current_level = tree
                    for i in range(1, len(path)):
                        skill = path[i]
                        # Check if this skill already exists in prerequisites
                        existing = next((p for p in current_level["prerequisites"] if p["skill"] == skill), None)
                        
                        if existing:
                            current_level = existing
                        else:
                            new_level = {"skill": skill, "prerequisites": []}
                            current_level["prerequisites"].append(new_level)
                            current_level = new_level
                
                return tree
        except Exception as e:
            logger.error(f"Error building skill prerequisites tree for '{skill_name}': {e}")
            return {"skill": skill_name, "prerequisites": []}

# Example usage
if __name__ == "__main__":
    # Initialize knowledge graph
    kg = SkillKnowledgeGraph()
    
    # Set up schema
    kg.setup_schema()
    
    # Add some skills
    kg.add_skill("Python", "Programming Language")
    kg.add_skill("JavaScript", "Programming Language")
    kg.add_skill("React", "Frontend Framework")
    kg.add_skill("Machine Learning", "Data Science")
    kg.add_skill("TensorFlow", "Machine Learning Framework")
    kg.add_skill("PyTorch", "Machine Learning Framework")
    kg.add_skill("Data Analysis", "Data Science")
    kg.add_skill("SQL", "Database")
    kg.add_skill("Natural Language Processing", "Data Science")
    
    # Add relationships
    kg.add_related_skills("Machine Learning", [
        {"name": "Python", "relationship_type": "REQUIRES", "properties": {"importance": "high"}},
        {"name": "Data Analysis", "relationship_type": "REQUIRES", "properties": {"importance": "high"}},
        {"name": "TensorFlow", "relationship_type": "RELATED_TO", "properties": {"strength": 0.9}},
        {"name": "PyTorch", "relationship_type": "RELATED_TO", "properties": {"strength": 0.9}},
        {"name": "Natural Language Processing", "relationship_type": "RELATED_TO", "properties": {"strength": 0.7}}
    ])
    
    kg.add_related_skills("TensorFlow", [
        {"name": "Python", "relationship_type": "REQUIRES", "properties": {"importance": "high"}},
        {"name": "Machine Learning", "relationship_type": "REQUIRES", "properties": {"importance": "high"}}
    ])
    
    kg.add_related_skills("React", [
        {"name": "JavaScript", "relationship_type": "REQUIRES", "properties": {"importance": "high"}}
    ])
    
    # Find related skills
    related = kg.get_related_skills("Machine Learning")
    print("Skills related to Machine Learning:", related)
    
    # Find skill path
    path = kg.find_skill_path("JavaScript", "Machine Learning")
    print("Path from JavaScript to Machine Learning:", path)
    
    # Build skill prerequisites tree
    tree = kg.build_skill_prerequisites_tree("TensorFlow")
    print("Prerequisites for TensorFlow:", tree)
    
    # Close connection
    kg.close() 