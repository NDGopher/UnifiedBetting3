import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { AppBar, Toolbar } from '@mui/material';
import PODAlerts from './components/PODAlerts';
import EVCalculator from './components/EVCalculator';
import PropBuilder from './components/PropBuilder';

// Create a dark theme
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              Unified Betting App
            </Typography>
          </Toolbar>
        </AppBar>
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          <Grid container spacing={3}>
            {/* POD Alerts Section */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column' }}>
                <Typography component="h2" variant="h6" color="primary" gutterBottom>
                  POD Alerts
                </Typography>
                <PODAlerts />
              </Paper>
            </Grid>

            {/* PropBuilder Section - Main focus */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column' }}>
                <Typography component="h2" variant="h6" color="primary" gutterBottom>
                  PropBuilder
                </Typography>
                <PropBuilder />
              </Paper>
            </Grid>

            {/* EV Calculator Section - Smaller and out of the way */}
            <Grid item xs={12} md={4} lg={3}>
              <Paper sx={{ p: 1, display: 'flex', flexDirection: 'column', maxHeight: '400px' }}>
                <Typography component="h3" variant="subtitle1" color="primary" gutterBottom>
                  EV Calculator
                </Typography>
                <EVCalculator />
              </Paper>
            </Grid>
          </Grid>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App; 