import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline, AppBar, Toolbar, Typography, Box, Container } from '@mui/material';
import Home from './components/Home';

// Create a theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5'
    }
  },
});

// Simple placeholder components for the routes
const Jobs = () => (
  <Container sx={{ mt: 4 }}>
    <Typography variant="h4">Jobs Management</Typography>
    <Typography variant="body1" sx={{ mt: 2 }}>
      This page will allow you to create and manage job listings.
    </Typography>
  </Container>
);

const Candidates = () => (
  <Container sx={{ mt: 4 }}>
    <Typography variant="h4">Candidates Management</Typography>
    <Typography variant="body1" sx={{ mt: 2 }}>
      This page will allow you to manage candidates and their resumes.
    </Typography>
  </Container>
);

const Matches = () => (
  <Container sx={{ mt: 4 }}>
    <Typography variant="h4">Skill Matching</Typography>
    <Typography variant="body1" sx={{ mt: 2 }}>
      This page will show matches between candidates and jobs.
    </Typography>
  </Container>
);

const Interviews = () => (
  <Container sx={{ mt: 4 }}>
    <Typography variant="h4">Interview Scheduling</Typography>
    <Typography variant="body1" sx={{ mt: 2 }}>
      This page will allow you to manage interview schedules.
    </Typography>
  </Container>
);

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ flexGrow: 1 }}>
          <AppBar position="static">
            <Toolbar>
              <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                AI Recruiter
              </Typography>
            </Toolbar>
          </AppBar>
          
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/candidates" element={<Candidates />} />
            <Route path="/matches" element={<Matches />} />
            <Route path="/interviews" element={<Interviews />} />
          </Routes>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App; 