import React, { useState, useEffect } from 'react';
import { Container, Typography, Box, Paper, Chip, CircularProgress } from '@mui/material';
import { Link } from 'react-router-dom';
import { checkHealth } from '../services/api';

const Home = () => {
  const [isHealthy, setIsHealthy] = useState(null);
  
  useEffect(() => {
    const checkAPIHealth = async () => {
      try {
        const healthy = await checkHealth();
        setIsHealthy(healthy);
      } catch (error) {
        console.error("Error checking API health:", error);
        setIsHealthy(false);
      }
    };
    
    checkAPIHealth();
  }, []);
  
  return (
    <Container maxWidth="md">
      <Box my={4}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          AI Recruiter
        </Typography>
        
        <Typography variant="h6" component="h2" gutterBottom align="center">
          Automating the hiring process with AI
        </Typography>
        
        <Box display="flex" justifyContent="center" my={2}>
          {isHealthy === null ? (
            <CircularProgress size={24} />
          ) : (
            <Chip 
              label={isHealthy ? "API Connected" : "API Disconnected"} 
              color={isHealthy ? "success" : "error"} 
            />
          )}
        </Box>
        
        <Box mt={4} display="flex" flexWrap="wrap" justifyContent="center" gap={2}>
          <FeatureCard 
            title="Job Management" 
            description="Create and manage job listings with AI-analyzed requirements"
            link="/jobs"
          />
          <FeatureCard 
            title="Candidate Management" 
            description="Parse and manage candidate resumes with AI"
            link="/candidates"
          />
          <FeatureCard 
            title="Skill Matching" 
            description="Match candidates to jobs based on skills and requirements"
            link="/matches"
          />
          <FeatureCard 
            title="Interview Scheduling" 
            description="Automatically schedule and manage interviews"
            link="/interviews"
          />
        </Box>
      </Box>
    </Container>
  );
};

const FeatureCard = ({ title, description, link }) => {
  return (
    <Paper 
      component={Link} 
      to={link}
      sx={{
        p: 3,
        width: 250,
        textDecoration: 'none',
        color: 'inherit',
        transition: 'transform 0.2s',
        '&:hover': {
          transform: 'translateY(-5px)',
          boxShadow: 3
        }
      }}
      elevation={2}
    >
      <Typography variant="h6" component="h3" gutterBottom>
        {title}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {description}
      </Typography>
    </Paper>
  );
};

export default Home; 