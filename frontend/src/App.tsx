import React, { createContext, useRef, useContext } from "react";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { AppBar, Toolbar, IconButton } from "@mui/material";
import { TrendingUp, Analytics, Calculate } from "@mui/icons-material";
import PODAlerts from "./components/PODAlerts";
import EVCalculator from "./components/EVCalculator";
import PropBuilder from "./components/PropBuilder";
import BuckeyeScraper from './components/BuckeyeScraper';
import BetBCKStatusPopup from './components/BetBCKStatusPopup';
import HighEVHistory from './components/HighEVHistory';

// Modern dark theme inspired by Onlook
const modernTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#43a047", // Green
      light: "#66bb6a",
      dark: "#2e7031",
    },
    secondary: {
      main: "#bdbdbd", // Light gray
      light: "#e0e0e0",
      dark: "#757575",
    },
    background: {
      default: "#181c24", // Deep gray
      paper: "#23272f", // Slightly lighter gray
    },
    text: {
      primary: "#fff",
      secondary: "#bdbdbd",
    },
    error: {
      main: "#e53935",
    },
    success: {
      main: "#43a047",
    },
    warning: {
      main: "#ffb300",
    },
    info: {
      main: "#00bcd4",
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 800,
      letterSpacing: "-0.02em",
    },
    h6: {
      fontWeight: 700,
      letterSpacing: "-0.01em",
      fontSize: "1.25rem",
    },
    subtitle1: {
      fontWeight: 600,
      fontSize: "1.1rem",
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: "#23272f",
          border: "1px solid #333",
          borderRadius: "14px",
          boxShadow: "0 4px 32px 0 rgba(67, 160, 71, 0.08)",
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: "#181c24",
          borderBottom: "1px solid #333",
          boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          fontWeight: 700,
          borderRadius: 8,
          textTransform: "none",
        },
        containedPrimary: {
          backgroundColor: "#43a047",
          color: "#fff",
          '&:hover': {
            backgroundColor: "#388e3c",
          },
        },
        outlinedSecondary: {
          borderColor: "#bdbdbd",
          color: "#bdbdbd",
          '&:hover': {
            borderColor: "#fff",
            color: "#fff",
          },
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: 'rgba(67, 160, 71, 0.08)',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid #333',
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          background: 'rgba(255,255,255,0.07)',
        },
      },
    },
  },
});

// Context for BetBCK tab reference
export const BetbckTabContext = createContext<{ betbckTabRef: React.MutableRefObject<Window | null> }>({ betbckTabRef: { current: null } });

function openBetbckTabOnLoad(betbckTabRef: React.MutableRefObject<Window | null>) {
  if (!betbckTabRef.current || betbckTabRef.current.closed) {
    betbckTabRef.current = window.open('https://betbck.com', 'betbck_tab');
  }
}

function App() {
  const betbckTabRef = useRef<Window | null>(null);

  React.useEffect(() => {
    openBetbckTabOnLoad(betbckTabRef);
  }, []);

  return (
    <BetbckTabContext.Provider value={{ betbckTabRef }}>
      <ThemeProvider theme={modernTheme}>
        <CssBaseline />
        <Box
          sx={{
            minHeight: "100vh",
            background: "#101214",
          }}
        >
          {/* Modern Header */}
          <AppBar position="static" elevation={0}>
            <Toolbar sx={{ py: 1, justifyContent: 'center', minHeight: 56 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  p: 1,
                  borderRadius: "8px",
                  background: "rgba(67, 160, 71, 0.12)",
                  border: "1px solid #43a047",
                  width: '100%',
                  justifyContent: 'center',
                  maxWidth: 700,
                  mx: 'auto',
                }}
              >
                <Typography
                  variant="h5"
                  component="div"
                  sx={{
                    fontWeight: 700,
                    background:
                      "linear-gradient(135deg, #43a047 0%, #bdbdbd 100%)",
                    backgroundClip: "text",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    textAlign: 'center',
                    width: '100%',
                  }}
                >
                  Unified Betting
                </Typography>
              </Box>
            </Toolbar>
          </AppBar>
          <Container maxWidth="xl" sx={{ py: 4 }}>
            <Grid container spacing={3}>
              {/* POD Alerts Section */}
              <Grid item xs={12}>
                <Paper
                  sx={{
                    p: 3,
                    display: "flex",
                    flexDirection: "column",
                    position: "relative",
                    overflow: "hidden",
                    transition: 'box-shadow 0.2s, transform 0.2s',
                    '&:hover': {
                      boxShadow: '0 8px 32px 0 rgba(67, 160, 71, 0.18)',
                      transform: 'scale(1.012)',
                    },
                    border: '1.5px solid #333',
                    '::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '3px',
                      background: 'linear-gradient(90deg, #43a047 0%, #23272f 100%)',
                      zIndex: 1,
                    },
                  }}
                >
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 2,
                      mb: 2,
                    }}
                  >
                    <Typography
                      component="h2"
                      variant="h6"
                      sx={{ color: '#fff', fontWeight: 700 }}
                    >
                      POD Alerts
                    </Typography>
                    <Box sx={{ flexGrow: 1 }} />
                    <Box
                      sx={{
                        px: 1.5,
                        py: 0.2,
                        borderRadius: '12px',
                        background: '#23272f',
                        border: '1px solid #bdbdbd',
                        height: 22,
                        display: 'flex',
                        alignItems: 'center',
                        fontSize: '0.85rem',
                        color: '#bdbdbd',
                        fontWeight: 600,
                        letterSpacing: 0,
                      }}
                    >
                      LIVE
                    </Box>
                  </Box>
                  <PODAlerts />
                </Paper>
              </Grid>
              {/* PropBuilder Section */}
              <Grid item xs={12}>
                <Paper
                  sx={{
                    p: 3,
                    display: "flex",
                    flexDirection: "column",
                    position: "relative",
                    overflow: "hidden",
                    transition: 'box-shadow 0.2s, transform 0.2s',
                    '&:hover': {
                      boxShadow: '0 8px 32px 0 rgba(67, 160, 71, 0.18)',
                      transform: 'scale(1.012)',
                    },
                    border: '1.5px solid #333',
                    '::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '3px',
                      background: 'linear-gradient(90deg, #43a047 0%, #23272f 100%)',
                      zIndex: 1,
                    },
                  }}
                >
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 2,
                      mb: 2,
                    }}
                  >
                    <Typography
                      component="h2"
                      variant="h6"
                      sx={{ color: '#fff', fontWeight: 700 }}
                    >
                      PropBuilder EV
                    </Typography>
                  </Box>
                  <PropBuilder />
                </Paper>
              </Grid>
              {/* BuckeyeScraper Section */}
              <Grid item xs={12}>
                <Paper
                  sx={{
                    p: 3,
                    display: "flex",
                    flexDirection: "column",
                    position: "relative",
                    overflow: "hidden",
                    transition: 'box-shadow 0.2s, transform 0.2s',
                    '&:hover': {
                      boxShadow: '0 8px 32px 0 rgba(67, 160, 71, 0.18)',
                      transform: 'scale(1.012)',
                    },
                    border: '1.5px solid #333',
                    '::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '3px',
                      background: 'linear-gradient(90deg, #43a047 0%, #23272f 100%)',
                      zIndex: 1,
                    },
                  }}
                >
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 2,
                      mb: 2,
                    }}
                  >
                    <Typography
                      component="h2"
                      variant="h6"
                      sx={{ color: '#fff', fontWeight: 700 }}
                    >
                      EV Bets
                    </Typography>
                  </Box>
                  <BuckeyeScraper />
                </Paper>
              </Grid>
              {/* High EV History Section */}
              <Grid item xs={12}>
                <Paper
                  sx={{
                    p: 3,
                    display: "flex",
                    flexDirection: "column",
                    position: "relative",
                    overflow: "hidden",
                    transition: 'box-shadow 0.2s, transform 0.2s',
                    '&:hover': {
                      boxShadow: '0 8px 32px 0 rgba(67, 160, 71, 0.18)',
                      transform: 'scale(1.012)',
                    },
                    border: '1.5px solid #333',
                    '::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '3px',
                      background: 'linear-gradient(90deg, #43a047 0%, #23272f 100%)',
                      zIndex: 1,
                    },
                  }}
                >
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 2,
                      mb: 2,
                    }}
                  >
                    <Typography
                      component="h2"
                      variant="h6"
                      sx={{ color: '#fff', fontWeight: 700 }}
                    >
                      High EV Alert History
                    </Typography>
                  </Box>
                  <HighEVHistory />
                </Paper>
              </Grid>
              
              {/* EV Calculator at the bottom, centered */}
              <Grid item xs={12}>
                <Paper
                  sx={{
                    p: 3,
                    display: "flex",
                    flexDirection: "column",
                    position: "relative",
                    overflow: "hidden",
                    transition: 'box-shadow 0.2s, transform 0.2s',
                    '&:hover': {
                      boxShadow: '0 8px 32px 0 rgba(67, 160, 71, 0.18)',
                      transform: 'scale(1.012)',
                    },
                    border: '1.5px solid #333',
                    '::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '3px',
                      background: 'linear-gradient(90deg, #43a047 0%, #23272f 100%)',
                      zIndex: 1,
                    },
                  }}
                >
                  <EVCalculator />
                </Paper>
              </Grid>
            </Grid>
          </Container>
        </Box>
        
        {/* BetBCK Status Popup - appears only when needed */}
        <BetBCKStatusPopup />
      </ThemeProvider>
    </BetbckTabContext.Provider>
  );
}

export default App;